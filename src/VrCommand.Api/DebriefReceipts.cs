using VrCommand.Core;

namespace VrCommand.Api;

internal sealed record DebriefReceiptAdmission(Guid PlayerId, Guid AdmissionId, int RoomId);
internal sealed record DebriefReceiptBatch(Guid StreamId, long ThroughSequence, long FinalStreamSequence,
    long WorldSequence, DebriefReceiptAdmission[] Players);
public sealed record DebriefReceiptPlayer(Guid PlayerId, Guid AdmissionId, int RoomId, string Name, bool Acknowledged);
public sealed record DebriefReceiptView(Guid StreamId, long ThroughSequence, long FinalStreamSequence,
    long WorldSequence, DebriefReceiptPlayer[] Players);

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
            using var query = Command("SELECT admission FROM debrief_receipts WHERE session=$session", ("$session", id.ToString("D")));
            using var rows = query.ExecuteReader();
            var acknowledged = new HashSet<Guid>();
            while (rows.Read()) acknowledged.Add(Guid.Parse(rows.GetString(0)));

            var players = session.Players.Where(player => actor.Role == OperatorRole.Master || player.RoomId == actor.RoomId)
                .OrderBy(player => player.RoomId).ThenBy(player => player.Seat)
                .Select(player => new DebriefReceiptPlayer(player.Id, player.AdmissionId, player.RoomId, player.Name,
                    acknowledged.Contains(player.AdmissionId))).ToArray();
            return world with { DebriefReceipts = new(session.CombatStream!.StreamId, session.Sequence,
                session.CombatStream.AcceptedSequence, world.AcceptedSequence, players) };
        }
    }

    private static bool HasDebriefBoundary(SessionView session, WorldRecordingInfo world) =>
        session.State == SessionState.Ended && session.CombatStream is { Sealed: true } stream
        && world.Complete && world.AcceptedSequence > 0 && MatchesVenueSource(session, stream, world);
}
