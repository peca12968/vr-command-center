using System.Text.Json.Serialization;
using VrCommand.Core;

namespace VrCommand.Api;

internal enum VenueArchiveState { NoSource, Missing, Waiting, SourceMismatch, Sealed }
internal sealed record VenueReplay(Guid StreamId, long ThroughSequence);
internal sealed record VenueClosureSession(Guid SessionId, long AppliedAtSequence, int[] RoomIds, string MissionName,
    VenueArchiveState Combat, VenueArchiveState World, bool FieldEvidenceReady,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueReplay? Replay);
internal sealed record VenueClosureBatch(Guid RequestId, DateTimeOffset RecordedAtUtc, VenueClosureSession[] Sessions);

public sealed partial class WorldRecordings
{
    internal VenueClosureBatch? ReadVenueClosure(OperatorIdentity actor, Guid? batchId = null)
    {
        lock (gate) return ReadVenueClosureData(actor, batchId)?.Batch;
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
        return (new(session.Id, applied.AppliedAtSequence, session.RoomIds, session.Mission.Definition.Name,
            combat, world, evidence is not null, replay), evidence);
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
