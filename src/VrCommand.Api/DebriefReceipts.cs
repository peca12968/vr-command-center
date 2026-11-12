using System.Text.Json.Serialization;
using VrCommand.Core;

namespace VrCommand.Api;

internal sealed record DebriefReceiptAdmission(Guid PlayerId, Guid AdmissionId, int RoomId);
internal sealed record DebriefReceiptBatch(Guid StreamId, long ThroughSequence, long FinalStreamSequence,
    long WorldSequence, DebriefReceiptAdmission[] Players);
public sealed record DebriefReceiptPlayer(Guid PlayerId, Guid AdmissionId, int RoomId, string Name, bool Acknowledged);
public sealed record DebriefReceiptView(Guid StreamId, long ThroughSequence, long FinalStreamSequence,
    long WorldSequence, DebriefReceiptPlayer[] Players);
internal sealed record VenueDebriefExport(int Version, Guid RequestId, VenueDebriefExportSession[] Sessions);
internal sealed record VenueDebriefExportSession(Guid SessionId, Guid StreamId, long ThroughSequence,
    long FinalStreamSequence, long WorldSequence, VenueDebriefExportPlayer[] Players);
internal sealed record VenueDebriefExportPlayer(Guid PlayerId, Guid AdmissionId, int RoomId, bool Acknowledged);
internal sealed record VenueDebriefSeat(int Seat, string Name, bool Acknowledged,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueDebriefSeatScore? Score,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? PlayerId);
internal sealed record VenueDebriefSeatScore(long AmmoUsed, long ShotsHit, long Kills, long HitsReceived,
    long DamageTaken, decimal AccuracyPercent, int Health)
{
    internal static VenueDebriefSeatScore From(PlayerStatistics player) => new(player.AmmoUsed, player.ShotsHit,
        player.Kills, player.HitsReceived, player.DamageTaken, player.AccuracyPercent, player.Health);
}
internal sealed record VenueDebriefSeats(int Version, Guid RequestId, Guid SessionId, int RoomId, Guid StreamId,
    long ThroughSequence, long FinalStreamSequence, long WorldSequence, VenueDebriefSeat[] Players);
internal sealed record VenueDebriefBatchSeats(int Version, Guid RequestId, VenueDebriefSeats[] Rooms);

public sealed partial class WorldRecordings
{
    internal void PublishDebriefReceipts(Guid id, DebriefReceiptBatch batch, OperatorIdentity actor)
    {
        if (actor.Role != OperatorRole.GameServer)
            throw new AccessDeniedException("Only the original game server can report debrief receipts.");
        if (batch.Players is not { Length: > 0 and <= SessionManager.MaxPlayers }
            || batch.Players.Any(player => player is null || player.AdmissionId == Guid.Empty)
            || batch.Players.Select(player => player.AdmissionId).Distinct().Count() != batch.Players.Length)
            throw new ArgumentException("Provide one to 25 distinct original admissions.");

        lock (gate)
        {
            var session = Owner(id, actor);
            var world = Info(id, actor);
            if (!HasDebriefBoundary(session, world) || session.CombatStream!.StreamId != batch.StreamId
                || session.Sequence != batch.ThroughSequence || session.CombatStream.AcceptedSequence != batch.FinalStreamSequence
                || world.AcceptedSequence != batch.WorldSequence)
                throw new InvalidOperationException("Debrief receipts require the original sealed combat and world boundaries.");
            if (batch.Players.Any(receipt => !session.Players.Any(player => player.Id == receipt.PlayerId
                && player.AdmissionId == receipt.AdmissionId && player.RoomId == receipt.RoomId)))
                throw new InvalidOperationException("Debrief receipt does not match a terminal roster admission.");

            using var transaction = db.BeginTransaction();
            using var insert = Command("INSERT INTO debrief_receipts(session,admission) VALUES($session,$admission) ON CONFLICT DO NOTHING",
                ("$session", id.ToString("D")), ("$admission", ""));
            insert.Transaction = transaction;
            foreach (var player in batch.Players)
            {
                insert.Parameters["$admission"].Value = player.AdmissionId.ToString("D");
                insert.ExecuteNonQuery();
            }
            transaction.Commit();
        }
    }

    internal WorldRecordingInfo ReadWorldWithDebriefReceipts(Guid id, OperatorIdentity actor)
    {
        if (actor.Role is not (OperatorRole.Master or OperatorRole.RoomController))
            throw new AccessDeniedException("Debrief receipts require an operator identity.");
        lock (gate)
        {
            var session = manager.Get(id, actor);
            var world = Info(id, actor);
            if (!HasDebriefBoundary(session, world)) return world;
            var acknowledged = ReadDebriefAdmissions(id);
            var players = session.Players.Where(player => actor.Role == OperatorRole.Master || player.RoomId == actor.RoomId)
                .OrderBy(player => player.RoomId).ThenBy(player => player.Seat)
                .Select(player => new DebriefReceiptPlayer(player.Id, player.AdmissionId, player.RoomId, player.Name,
                    acknowledged.Contains(player.AdmissionId))).ToArray();
            return world with { DebriefReceipts = new(session.CombatStream!.StreamId, session.Sequence,
                session.CombatStream.AcceptedSequence, world.AcceptedSequence, players) };
        }
    }

    internal VenueDebriefExport ExportVenueDebriefReceipts(Guid id, OperatorIdentity actor)
    {
        lock (gate)
        {
            var batch = manager.ReadVenueEnd(id, actor);
            var sessions = new List<VenueDebriefExportSession>(batch.Sessions.Length);
            foreach (var original in batch.Sessions)
            {
                var session = manager.Get(original.SessionId, actor);
                if (session.State != SessionState.Ended || session.CombatStream is not { Sealed: true } stream
                    || VenueWorldArchive(session, stream, actor) is not (VenueArchiveState.Sealed, { } replay))
                    throw new InvalidOperationException("Every original session needs sealed combat and world data.");
                sessions.Add(BuildDebriefExportSession(session, stream, replay.ThroughSequence));
            }
            return new(1, batch.RequestId, sessions.ToArray());
        }
    }

    private VenueDebriefExportSession BuildDebriefExportSession(SessionView session, CombatStreamView stream, long worldSequence)
    {
        var confirmed = ReadDebriefAdmissions(session.Id);
        var players = session.Players.OrderBy(player => player.RoomId).ThenBy(player => player.Seat)
            .Select(player => new VenueDebriefExportPlayer(player.Id, player.AdmissionId, player.RoomId,
                confirmed.Contains(player.AdmissionId))).ToArray();
        return new(session.Id, stream.StreamId, session.Sequence, stream.AcceptedSequence, worldSequence, players);
    }

    internal VenueDebriefSeats ReadVenueDebriefSeats(Guid id, int roomId, OperatorIdentity actor, bool includeScores, bool includePlayerIds)
    {
        lock (gate)
        {
            var (session, replay) = SealedVenueDebriefRoom(id, roomId, actor);
            var confirmed = ReadDebriefAdmissions(session.Id);
            var scores = includeScores ? manager.FinalReport(session.Id, actor, roomId).Players
                .ToDictionary(player => player.PlayerId, VenueDebriefSeatScore.From) : null;
            return BuildVenueDebriefSeats(id, roomId, session, replay, confirmed, scores, includePlayerIds);
        }
    }

    internal VenueDebriefBatchSeats ReadVenueDebriefBatchSeats(Guid id, OperatorIdentity actor)
    {
        lock (gate)
        {
            var batch = manager.ReadVenueEnd(id, actor);
            var rooms = new List<VenueDebriefSeats>(SessionManager.RoomCount);
            foreach (var original in batch.Sessions)
            {
                var session = manager.Get(original.SessionId, actor);
                if (session.Players.Length == 0 || session.State != SessionState.Ended
                    || session.CombatStream is not { Sealed: true } stream
                    || VenueWorldArchive(session, stream, actor) is not (VenueArchiveState.Sealed, { } replay)) continue;
                var confirmed = ReadDebriefAdmissions(session.Id);
                var scores = manager.FinalReport(session.Id, actor).Players.ToDictionary(player => player.PlayerId, VenueDebriefSeatScore.From);
                foreach (var roomId in session.Players.Select(player => player.RoomId).Distinct())
                    rooms.Add(BuildVenueDebriefSeats(id, roomId, session, replay, confirmed, scores, includePlayerIds: true));
            }
            return new(1, id, rooms.OrderBy(room => room.RoomId).ToArray());
        }
    }

    private static VenueDebriefSeats BuildVenueDebriefSeats(Guid id, int roomId, SessionView session, VenueReplay replay,
        HashSet<Guid> confirmed, Dictionary<Guid, VenueDebriefSeatScore>? scores, bool includePlayerIds)
    {
        var stream = session.CombatStream!;
        var players = session.Players.Where(player => player.RoomId == roomId).OrderBy(player => player.Seat)
            .Select(player => new VenueDebriefSeat(player.Seat + 1, player.Name, confirmed.Contains(player.AdmissionId),
                scores?[player.Id], includePlayerIds ? player.Id : null)).ToArray();
        return new(1, id, session.Id, roomId, stream.StreamId, session.Sequence,
            stream.AcceptedSequence, replay.ThroughSequence, players);
    }

    internal FinalSessionReport ReadVenueDebriefSeatReport(Guid id, int roomId, int seat, OperatorIdentity actor)
    {
        lock (gate)
        {
            var (session, _) = SealedVenueDebriefRoom(id, roomId, actor);
            var player = session.Players.SingleOrDefault(player => player.RoomId == roomId && player.Seat + 1 == seat)
                ?? throw new KeyNotFoundException("The original terminal roster does not include this seat.");
            return manager.FinalPlayerReport(session.Id, player.Id, actor);
        }
    }

    private (SessionView Session, VenueReplay Replay) SealedVenueDebriefRoom(Guid id, int roomId, OperatorIdentity actor)
    {
        var batch = manager.ReadVenueEnd(id, actor);
        var session = batch.Sessions.Select(item => manager.Get(item.SessionId, actor))
            .SingleOrDefault(original => original.RoomIds.Contains(roomId))
            ?? throw new KeyNotFoundException("The original End batch does not include this room.");
        if (session.State != SessionState.Ended || session.CombatStream is not { Sealed: true } stream
            || VenueWorldArchive(session, stream, actor) is not (VenueArchiveState.Sealed, { } replay))
            throw new InvalidOperationException("The original session needs sealed combat and world data.");
        return (session, replay);
    }

    private HashSet<Guid> ReadDebriefAdmissions(Guid id)
    {
        using var query = Command("SELECT admission FROM debrief_receipts WHERE session=$session", ("$session", id.ToString("D")));
        using var rows = query.ExecuteReader();
        var acknowledged = new HashSet<Guid>();
        while (rows.Read()) acknowledged.Add(Guid.Parse(rows.GetString(0)));
        return acknowledged;
    }

    private static bool HasDebriefBoundary(SessionView session, WorldRecordingInfo world) =>
        session.State == SessionState.Ended && session.CombatStream is { Sealed: true } stream
        && world.Complete && world.AcceptedSequence > 0 && MatchesVenueSource(session, stream, world);
}
