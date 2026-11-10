using System.Text.Json.Serialization;
using VrCommand.Core;

namespace VrCommand.Api;

internal enum VenueArchiveState { NoSource, Missing, Waiting, SourceMismatch, Sealed }
internal sealed record VenueReplay(Guid StreamId, long ThroughSequence);
internal sealed record VenueClosureSession(Guid SessionId, long AppliedAtSequence, int[] RoomIds, string MissionName,
    VenueArchiveState Combat, VenueArchiveState World, bool FieldEvidenceReady,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueReplay? Replay,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueTrackingBegin? TrackingBegin,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueParticipationBegin? ParticipationBegin);
internal sealed record VenueClosureBatch(Guid RequestId, DateTimeOffset RecordedAtUtc, VenueClosureSession[] Sessions);
internal sealed record VenueClosureResponse(VenueClosureBatch? Batch,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueBattleScores? Scores);
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
    internal VenueClosureResponse ReadVenueClosure(OperatorIdentity actor, bool includeScores, Guid? batchId = null)
    {
        lock (gate)
        {
            var batch = ReadVenueClosureData(actor, batchId)?.Batch;
            if (!includeScores || batch is null
                || batch.Sessions.Any(session => session.Combat is not (VenueArchiveState.Sealed or VenueArchiveState.NoSource)))
                return new(batch, null);

            var final = manager.FinalVenueReports(batch.RequestId, actor);
            var rooms = final.Sessions.SelectMany(item => item.Report.RoomIds.Select(room =>
                new VenueRoomScore(room, item.Report.SessionId, VenueBattleTotals.From(item.Report.ForRoom(room).Players))))
                .OrderBy(score => score.RoomId).ToArray();
            return new(batch, new(final.RequestId, rooms,
                VenueBattleTotals.From(final.Sessions.SelectMany(item => item.Report.Players).ToArray())));
        }
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

        var header = world.Header;
        if (header.schemaVersion != 1 || header.sessionId != session.Id.ToString("D")
            || header.streamId != stream.StreamId.ToString("D") || header.origin != stream.Origin.ToString()
            || !header.roomIds.SequenceEqual(session.RoomIds) || header.missionClockVersion != stream.MissionClockVersion
            || (stream.MissionClockVersion == 1 && header.missionDurationSeconds != session.Mission.Definition.DurationSeconds))
            return (VenueArchiveState.SourceMismatch, null);
        if (world.AcceptedSequence <= 0) return (VenueArchiveState.Waiting, null);
        return (world.Complete && stream.Sealed ? VenueArchiveState.Sealed : VenueArchiveState.Waiting,
            new(stream.StreamId, world.AcceptedSequence));
    }
}
