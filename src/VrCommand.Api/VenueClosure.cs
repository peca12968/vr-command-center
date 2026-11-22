using System.Text.Json.Serialization;
using VrCommand.Core;
using VrCommand.Simulation;

namespace VrCommand.Api;

internal enum VenueArchiveState { NoSource, Missing, Waiting, SourceMismatch, Sealed }
internal sealed record VenueReplay(Guid StreamId, long ThroughSequence);
internal sealed record VenueReplayMatch(Guid RequestId, Guid FromSessionId, long FromFrame, int RoomId,
    DateTimeOffset CapturedAtUtc, DateTimeOffset FrameCapturedAtUtc, WorldRecordingInfo Recording, WorldFrameView Frame);
internal sealed record VenueMissionReplayMatch(Guid RequestId, Guid FromSessionId, long FromFrame, int RoomId,
    long FromTick, long FrameTick, WorldRecordingInfo Recording, WorldFrameView Frame);
internal sealed record VenueClosureSession(Guid SessionId, long AppliedAtSequence, int[] RoomIds, Guid MissionId, string MissionName,
    VenueArchiveState Combat, VenueArchiveState World, bool FieldEvidenceReady,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueReplay? Replay,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueTrackingBegin? TrackingBegin,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueParticipationBegin? ParticipationBegin,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int? RosterDepartureCount = null);
internal sealed record VenueClosureBatch(Guid RequestId, DateTimeOffset RecordedAtUtc, VenueClosureSession[] Sessions);
internal sealed record VenueDepartedPlayer(Guid AdmissionId, int Seat, long JoinedAtSequence, long LeftAtSequence, PlayerStatistics Statistics);
internal sealed record VenueDepartedPlayers(Guid RequestId, Guid SessionId, Guid StreamId, long WorldSequence,
    long FinalStreamSequence, long EndedAtSequence, long ThroughSequence, VenueDepartedPlayer[] Players);
internal sealed record VenueClosureResponse(VenueClosureBatch? Batch,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueBattleScores? Scores,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueDebriefSummary? DebriefReceipts,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueReadyRoomScores? ReadyRoomScores = null);
internal sealed record VenueDebriefSummary(Guid RequestId, VenueDebriefRoom[] Rooms);
internal sealed record VenueDebriefRoom(Guid SessionId, int RoomId, int RosterCount, int? ConfirmedCount);
internal sealed record VenueBattleScores(Guid RequestId, VenueRoomScore[] Rooms, VenueBattleTotals Total)
{
    internal static VenueBattleScores From(FinalVenueReport report)
    {
        var rooms = report.Sessions.SelectMany(item => RoomScores(item.Report))
            .OrderBy(score => score.RoomId).ToArray();
        return new(report.RequestId, rooms,
            VenueBattleTotals.From(report.Sessions.SelectMany(item => item.Report.Players).ToArray()));
    }

    internal static IEnumerable<VenueRoomScore> RoomScores(FinalSessionReport report) => report.RoomIds.Select(room =>
        new VenueRoomScore(room, report.SessionId, VenueBattleTotals.From(report.ForRoom(room).Players)));
}
internal sealed record VenueReadyRoomScores(Guid RequestId, VenueRoomScore[] Rooms);
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
            var (source, destination) = VenueReplaySessions(batchId, fromSessionId, roomId, actor);
            var sourceInfo = ReadVenueReplayRecording(source, actor, missionClock: false);
            var original = VenueReplaySourceFrame(source, sourceInfo, fromFrame, actor);
            var captured = sourceInfo.CapturedAtUtc!.Value.AddMilliseconds(original.Packet.elapsedMilliseconds - sourceInfo.DurationMilliseconds);
            var recording = destination.Id == source.Id ? sourceInfo : ReadVenueReplayRecording(destination, actor, missionClock: false);
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

    internal VenueMissionReplayMatch ReadVenueReplayAtTick(Guid batchId, Guid fromSessionId, long fromFrame, int roomId, OperatorIdentity actor)
    {
        if (fromFrame < 1 || roomId is < 1 or > SessionManager.RoomCount)
            throw new ArgumentException("Specify an original frame and a room from 1 to 5.");
        lock (gate)
        {
            var (source, destination) = VenueReplaySessions(batchId, fromSessionId, roomId, actor);
            var sourceInfo = ReadVenueReplayRecording(source, actor, missionClock: true);
            var original = VenueReplaySourceFrame(source, sourceInfo, fromFrame, actor);
            var tick = original.Packet.frame.tick;
            if (tick < 1) throw new InvalidOperationException("Select a source frame with positive recorded mission time.");
            if (destination.Id == source.Id) return new(batchId, fromSessionId, fromFrame, roomId, tick, tick, sourceInfo, original);

            var recording = ReadVenueReplayRecording(destination, actor, missionClock: true);
            var tail = recording.AcceptedSequence;
            if (tick > RecordedTick(destination.Id, tail))
                throw new InvalidOperationException("The destination recording does not cover the source mission time.");
            var sequence = FirstFrameAtOrAfterTick(destination.Id, tick, tail);
            var matchedTick = RecordedTick(destination.Id, sequence);
            if (matchedTick > tick)
            {
                matchedTick = RecordedTick(destination.Id, sequence - 1);
                sequence = FirstFrameAtOrAfterTick(destination.Id, matchedTick, sequence - 1);
            }
            if (matchedTick < 1 || tick - matchedTick > MissionClock.TicksPerSecond / 2)
                throw new InvalidOperationException("No destination frame within half a second of recorded mission time.");
            var frame = Frame(destination.Id, sequence, actor) ?? throw new InvalidDataException("Missing destination frame.");
            return new(batchId, fromSessionId, fromFrame, roomId, tick, matchedTick, recording, frame);
        }
    }

    private (SessionView Source, SessionView Destination) VenueReplaySessions(Guid batchId, Guid fromSessionId, int roomId, OperatorIdentity actor)
    {
        var batch = manager.ReadVenueEnd(batchId, actor);
        var sessions = batch.Sessions.Select(row => manager.Get(row.SessionId, actor))
            .Where(session => session.Mode == SessionMode.Independent && session.State == SessionState.Ended && session.RoomIds.Length == 1)
            .ToArray();
        var source = sessions.SingleOrDefault(session => session.Id == fromSessionId);
        var destination = sessions.SingleOrDefault(session => session.RoomIds[0] == roomId);
        if (source is null || destination is null || sessions.Length < 2)
            throw new KeyNotFoundException("The source and destination must belong to the original independent End batch.");
        return (source, destination);
    }

    private WorldFrameView VenueReplaySourceFrame(SessionView source, WorldRecordingInfo recording, long sequence, OperatorIdentity actor)
        => sequence <= recording.AcceptedSequence && Frame(source.Id, sequence, actor) is { } frame
            ? frame : throw new KeyNotFoundException("No source frame at this sealed sequence.");

    private WorldRecordingInfo ReadVenueReplayRecording(SessionView session, OperatorIdentity actor, bool missionClock)
    {
        var info = Info(session.Id, actor);
        if (session.CombatStream is not { Sealed: true } stream || !info.Complete || info.AcceptedSequence < 1
            || !MatchesVenueSource(session, stream, info)
            || (missionClock ? info.Header.missionClockVersion != MissionClock.Version : info.CapturedAtUtc is null))
            throw new InvalidOperationException(missionClock ? "Both original recordings need sealed streams and mission clocks."
                : "Both original recordings need sealed streams and recorded UTC capture clocks.");
        return info;
    }

    private long RecordedTick(Guid id, long sequence)
    {
        using var command = Command("SELECT json_extract(packet,'$.frame.tick') FROM world_frames WHERE session=$id AND sequence=$seq",
            ("$id", id.ToString("D")), ("$seq", sequence));
        return command.ExecuteScalar() is long tick ? tick : throw new InvalidDataException("Missing recorded mission tick.");
    }

    private long FirstFrameAtOrAfterTick(Guid id, long tick, long last)
    {
        // Accepted frame ticks are monotonic. Read only the tick at each primary-key probe, even across long pauses.
        long first = 1;
        while (first < last)
        {
            var middle = first + (last - first) / 2;
            if (RecordedTick(id, middle) < tick) first = middle + 1;
            else last = middle;
        }
        return first;
    }

    internal VenueClosureResponse ReadVenueClosure(OperatorIdentity actor, bool includeScores, bool includeDebriefReceipts, Guid? batchId = null)
    {
        lock (gate)
        {
            var batch = ReadVenueClosureData(actor, batchId)?.Batch;
            var receipts = includeDebriefReceipts && batch is not null ? SummarizeVenueDebriefReceipts(batch, actor) : null;
            if (!includeScores || batch is null)
                return new(batch, null, receipts);

            var ready = batch.Sessions.Where(session => session.Combat is VenueArchiveState.Sealed or VenueArchiveState.NoSource).ToArray();
            if (ready.Length != batch.Sessions.Length)
            {
                var rooms = ready.SelectMany(session => VenueBattleScores.RoomScores(manager.FinalReport(session.SessionId, actor)))
                    .OrderBy(score => score.RoomId).ToArray();
                return new(batch, null, receipts, new(batch.RequestId, rooms));
            }
            return new(batch, VenueBattleScores.From(manager.FinalVenueReports(batch.RequestId, actor)), receipts);
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

    internal VenueDepartedPlayers ReadVenueDepartedPlayers(Guid batchId, Guid sessionId, OperatorIdentity actor)
    {
        lock (gate)
        {
            var original = manager.ReadVenueEnd(batchId, actor).Sessions.SingleOrDefault(item => item.SessionId == sessionId)
                ?? throw new KeyNotFoundException("Session does not belong to the original End batch.");
            var (row, evidence) = ReadVenueClosureSession(original, actor);
            if (row.Replay is null || evidence?.Session.CombatStream is not { Sealed: true } stream)
                throw new InvalidOperationException("Departed player review requires the original sealed field evidence.");
            var scores = evidence.Statistics.Players.ToDictionary(player => player.PlayerId);
            var players = evidence.RosterDepartures?.Players.Select(player =>
            {
                var admission = manager.Observed(sessionId, player.JoinedAtSequence, actor).Players.Single(p =>
                    p.Id == player.PlayerId && p.AdmissionId == player.AdmissionId && p.RoomId == player.RoomId);
                return new VenueDepartedPlayer(admission.AdmissionId, admission.Seat, player.JoinedAtSequence,
                    player.LeftAtSequence, scores[player.PlayerId]);
            }).ToArray() ?? [];
            return new(batchId, sessionId, stream.StreamId, row.Replay.ThroughSequence, stream.AcceptedSequence,
                original.AppliedAtSequence, evidence.Statistics.ThroughSequence, players);
        }
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
            if (world == VenueArchiveState.Sealed) evidence = BuildFieldEvidence(session, stream, replay!.ThroughSequence, actor, applied.AppliedAtSequence).Evidence;
        }
        var (tracking, participation) = manager.ReadVenueBeginEvidence(session.Id, actor);
        return (new(session.Id, applied.AppliedAtSequence, session.RoomIds, session.Mission.Id, session.Mission.Definition.Name,
            combat, world, evidence is not null, replay, tracking, participation, evidence?.RosterDepartures?.Players.Length), evidence);
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
