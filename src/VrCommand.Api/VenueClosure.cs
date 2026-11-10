using System.Text.Json.Serialization;
using VrCommand.Core;

namespace VrCommand.Api;

internal enum VenueArchiveState { NoSource, Missing, Waiting, SourceMismatch, Sealed }
internal sealed record VenueReplay(Guid StreamId, long ThroughSequence);
internal sealed record VenueReplayMatch(Guid RequestId, Guid FromSessionId, long FromFrame, int RoomId,
    DateTimeOffset CapturedAtUtc, DateTimeOffset FrameCapturedAtUtc, WorldRecordingInfo Recording, WorldFrameView Frame);
internal sealed record VenueClosureSession(Guid SessionId, long AppliedAtSequence, int[] RoomIds, string MissionName,
    VenueArchiveState Combat, VenueArchiveState World, bool FieldEvidenceReady,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueReplay? Replay,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueTrackingBegin? TrackingBegin,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueParticipationBegin? ParticipationBegin);
internal sealed record VenueClosureBatch(Guid RequestId, DateTimeOffset RecordedAtUtc, VenueClosureSession[] Sessions);
internal sealed record VenueClosureResponse(VenueClosureBatch? Batch,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueBattleScores? Scores,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueDebriefSummary? DebriefReceipts);
internal sealed record VenueDebriefSummary(Guid RequestId, VenueDebriefRoom[] Rooms);
internal sealed record VenueDebriefRoom(Guid SessionId, int RoomId, int RosterCount, int? ConfirmedCount);
internal sealed record VenueBattleScores(Guid RequestId, VenueRoomScore[] Rooms, VenueBattleTotals Total);
internal sealed record VenueRoomScore(int RoomId, Guid SessionId, VenueBattleTotals Totals);
internal sealed record VenueBattleTotals(int Players, long AmmoUsed, long ShotsHit, long Kills, long HitsReceived, long DamageTaken)
{
    public decimal AccuracyPercent => AmmoUsed == 0 ? 0 : decimal.Round(100m * ShotsHit / AmmoUsed, 2);

    internal static VenueBattleTotals From(PlayerStatistics[] players) => new(players.Length,
        players.Sum(player => player.AmmoUsed), players.Sum(player => player.ShotsHit), players.Sum(player => player.Kills),
        players.Sum(player => player.HitsReceived), players.Sum(player => player.DamageTaken));
}

public sealed partial class WorldRecordings
{
    internal VenueReplayMatch ReadVenueReplayAt(Guid batchId, Guid fromSessionId, long fromFrame, int roomId, OperatorIdentity actor)
    {
        if (fromFrame < 1 || roomId is < 1 or > SessionManager.RoomCount)
            throw new ArgumentException("Specify an original frame and a room from 1 to 5.");
        lock (gate)
        {
            var batch = manager.ReadVenueEnd(batchId, actor);
            var sessions = batch.Sessions.Select(row => manager.Get(row.SessionId, actor))
                .Where(session => session.Mode == SessionMode.Independent && session.State == SessionState.Ended && session.RoomIds.Length == 1)
                .ToArray();
            var source = sessions.SingleOrDefault(session => session.Id == fromSessionId);
            var destination = sessions.SingleOrDefault(session => session.RoomIds[0] == roomId);
            if (source is null || destination is null || sessions.Length < 2)
                throw new KeyNotFoundException("The source and destination must belong to the original independent End batch.");

            var sourceInfo = ReadTimedVenueReplay(source, actor);
            if (fromFrame > sourceInfo.AcceptedSequence || Frame(source.Id, fromFrame, actor) is not { } original)
                throw new KeyNotFoundException("No source frame at this sealed sequence.");
            var captured = sourceInfo.CapturedAtUtc!.Value.AddMilliseconds(original.Packet.elapsedMilliseconds - sourceInfo.DurationMilliseconds);
            var recording = destination.Id == source.Id ? sourceInfo : ReadTimedVenueReplay(destination, actor);
            var start = recording.CapturedAtUtc!.Value.AddMilliseconds(-recording.DurationMilliseconds);
            if (captured < start || captured > recording.CapturedAtUtc.Value)
                throw new InvalidOperationException("The destination recording does not cover the source capture time.");

            var elapsed = (captured - start).Ticks / TimeSpan.TicksPerMillisecond;
            var frame = destination.Id == source.Id ? original : Frame(destination.Id, Seek(destination.Id, elapsed, actor), actor);
            if (frame is null || frame.Packet.elapsedMilliseconds > elapsed
                || captured - start.AddMilliseconds(frame.Packet.elapsedMilliseconds) > TimeSpan.FromMilliseconds(500))
                throw new InvalidOperationException("No destination frame within 500 milliseconds at or before the source capture time.");
            return new(batchId, fromSessionId, fromFrame, roomId, captured, start.AddMilliseconds(frame.Packet.elapsedMilliseconds), recording, frame);
        }
    }

    private WorldRecordingInfo ReadTimedVenueReplay(SessionView session, OperatorIdentity actor)
    {
        var info = Info(session.Id, actor);
        if (session.CombatStream is not { Sealed: true } stream || !info.Complete || info.AcceptedSequence < 1
            || info.CapturedAtUtc is null || !MatchesVenueSource(session, stream, info))
            throw new InvalidOperationException("Both original recordings need sealed streams and recorded UTC capture clocks.");
        return info;
    }

    internal VenueClosureResponse ReadVenueClosure(OperatorIdentity actor, bool includeScores, bool includeDebriefReceipts, Guid? batchId = null)
    {
        lock (gate)
        {
            var batch = ReadVenueClosureData(actor, batchId)?.Batch;
            var receipts = includeDebriefReceipts && batch is not null ? SummarizeVenueDebriefReceipts(batch, actor) : null;
            if (!includeScores || batch is null
                || batch.Sessions.Any(session => session.Combat is not (VenueArchiveState.Sealed or VenueArchiveState.NoSource)))
                return new(batch, null, receipts);

            var final = manager.FinalVenueReports(batch.RequestId, actor);
            var rooms = final.Sessions.SelectMany(item => item.Report.RoomIds.Select(room =>
                new VenueRoomScore(room, item.Report.SessionId, VenueBattleTotals.From(item.Report.ForRoom(room).Players))))
                .OrderBy(score => score.RoomId).ToArray();
            return new(batch, new(final.RequestId, rooms,
                VenueBattleTotals.From(final.Sessions.SelectMany(item => item.Report.Players).ToArray())), receipts);
        }
    }

    private VenueDebriefSummary SummarizeVenueDebriefReceipts(VenueClosureBatch batch, OperatorIdentity actor)
    {
        var rooms = new List<VenueDebriefRoom>(SessionManager.RoomCount);
        foreach (var row in batch.Sessions)
        {
            var session = manager.Get(row.SessionId, actor);
            var acknowledged = row.Combat == VenueArchiveState.Sealed && row.World == VenueArchiveState.Sealed
                ? ReadDebriefAdmissions(row.SessionId) : null;
            foreach (var room in row.RoomIds)
            {
                var roster = session.Players.Where(player => player.RoomId == room).ToArray();
                rooms.Add(new(row.SessionId, room, roster.Length,
                    acknowledged is null ? null : roster.Count(player => acknowledged.Contains(player.AdmissionId))));
            }
        }
        return new(batch.RequestId, rooms.OrderBy(room => room.RoomId).ToArray());
    }

    private (VenueClosureBatch Batch, FieldEvidence?[] Evidence)? ReadVenueClosureData(OperatorIdentity actor, Guid? batchId)
    {
        var batch = batchId is { } id ? manager.ReadVenueEnd(id, actor) : manager.ReadLatestVenueEnd(actor);
        if (batch is null) return null;
        var sessions = batch.Sessions.Select(applied => ReadVenueClosureSession(applied, actor))
            .OrderBy(session => session.Row.RoomIds[0]).ToArray();
        return (new(batch.RequestId, batch.RecordedAtUtc, sessions.Select(session => session.Row).ToArray()),
            sessions.Select(session => session.Evidence).ToArray());
    }

    private (VenueClosureSession Row, FieldEvidence? Evidence) ReadVenueClosureSession(VenuePhaseApplied applied, OperatorIdentity actor)
    {
        var session = manager.Get(applied.SessionId, actor);
        var combat = VenueArchiveState.NoSource;
        var world = VenueArchiveState.NoSource;
        VenueReplay? replay = null;
        FieldEvidence? evidence = null;
        if (session.CombatStream is { } stream)
        {
            combat = stream.Sealed ? VenueArchiveState.Sealed : VenueArchiveState.Waiting;
            (world, replay) = VenueWorldArchive(session, stream, actor);
            if (world == VenueArchiveState.Sealed) evidence = BuildFieldEvidence(session, stream, actor).Evidence;
        }
        var (tracking, participation) = manager.ReadVenueBeginEvidence(session.Id, actor);
        return (new(session.Id, applied.AppliedAtSequence, session.RoomIds, session.Mission.Definition.Name,
            combat, world, evidence is not null, replay, tracking, participation), evidence);
    }

    private (VenueArchiveState State, VenueReplay? Replay) VenueWorldArchive(SessionView session, CombatStreamView stream, OperatorIdentity actor)
    {
        WorldRecordingInfo world;
        try { world = Info(session.Id, actor); }
        catch (KeyNotFoundException) { return (VenueArchiveState.Missing, null); }

        if (!MatchesVenueSource(session, stream, world)) return (VenueArchiveState.SourceMismatch, null);
        if (world.AcceptedSequence <= 0) return (VenueArchiveState.Waiting, null);
        return (world.Complete && stream.Sealed ? VenueArchiveState.Sealed : VenueArchiveState.Waiting,
            new(stream.StreamId, world.AcceptedSequence));
    }

    private static bool MatchesVenueSource(SessionView session, CombatStreamView stream, WorldRecordingInfo world)
    {
        var header = world.Header;
        return header.schemaVersion == 1 && header.sessionId == session.Id.ToString("D")
            && header.streamId == stream.StreamId.ToString("D") && header.origin == stream.Origin.ToString()
            && header.roomIds.SequenceEqual(session.RoomIds) && header.missionClockVersion == stream.MissionClockVersion
            && (stream.MissionClockVersion != 1 || header.missionDurationSeconds == session.Mission.Definition.DurationSeconds);
    }
}
