using VrCommand.Core;

using VrCommand.Simulation;

namespace VrCommand.Api;

public record PlayerReadiness(Guid PlayerId, Guid AdmissionId, int RoomId, int Seat, string State, string RigKind, bool CanParticipate);
public record SessionReadiness(int Version, Guid SessionId, long SessionSequence, DateTimeOffset SampledAtUtc,
    string SourceState, string? Origin, long WorldSequence, long ObservedSequence, DateTimeOffset? CapturedAtUtc,
    double? SourceAgeMilliseconds, PlayerReadiness[] Players, string? MrStartState);
public record RoomReadiness(int RoomId, Guid? SessionId, long SessionSequence, int Registered, int SimulatedReady,
    int TrackedReady, string SourceState, double? SourceAgeMilliseconds);

public sealed partial class WorldRecordings
{
    public CommandReceipt ExecuteCommand(Guid id, ControlCommand command, OperatorIdentity actor)
    {
        if (command.Action != ControlAction.Begin) return manager.Execute(id, command, actor);
        lock (gate)
        {
            var current = manager.Get(id, actor);
            AccessPolicy.Manage(actor, current.Mode, current.RoomIds);
            if (current.Environment.Mode != ExperienceMode.MR || current.State != SessionState.Preparing)
                return manager.Execute(id, command, actor);

            var report = Readiness(id, actor);
            var ready = report.SessionSequence == current.Sequence && report.MrStartState == "Ready";
            return manager.Execute(id, command, actor, ready ? current.Sequence : null);
        }
    }

    private static void RequireReadinessActor(OperatorIdentity actor)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role is not (OperatorRole.Master or OperatorRole.RoomController))
            throw new AccessDeniedException("Player readiness is for control desks only.");
    }

    public RoomReadiness[] ReadinessByRoom(OperatorIdentity actor)
    {
        RequireReadinessActor(actor);
        var rooms = manager.Rooms(actor);
        // A linked game uses the same accepted snapshot for all of its visible rooms.
        var sessions = rooms.Select(room => room.SessionId).OfType<Guid>().Distinct()
            .ToDictionary(id => id, id => Readiness(id, actor));
        return rooms.Select(room =>
        {
            if (room.SessionId is not { } id) return new RoomReadiness(room.Id, null, 0, 0, 0, 0, "Idle", null);
            var report = sessions[id];
            var players = report.Players.Where(player => player.RoomId == room.Id).ToArray();
            return new RoomReadiness(room.Id, id, report.SessionSequence, players.Length,
                players.Count(player => player.CanParticipate && player.RigKind == "Simulated"),
                players.Count(player => player.CanParticipate && player.RigKind == "Tracked"),
                report.SourceState, report.SourceAgeMilliseconds);
        }).ToArray();
    }

    // A scoped view of accepted snapshots. The MR start policy requires the exact current roster revision.
    public SessionReadiness Readiness(Guid id, OperatorIdentity actor)
    {
        RequireReadinessActor(actor);
        lock (gate)
        {
            var current = manager.Get(id, actor);
            using var exists = Command("SELECT 1 FROM recordings WHERE session=$id", ("$id", id.ToString("D")));
            var info = exists.ExecuteScalar() is null ? null : Info(id, actor);
            var frame = info is null || info.AcceptedSequence == 0 ? null : Frame(id, info.AcceptedSequence, actor);
            var observed = frame is null ? null : manager.Observed(id, frame.Packet.observedSequence, actor);
            var now = readinessClock.GetUtcNow();
            var age = info?.CapturedAtUtc is { } captured ? (double?)(now - captured).TotalMilliseconds : null;
            var source = current.State == SessionState.Ended ? "Ended"
                : info is null ? "NoRecording" : frame is null ? "WaitingFrame"
                : age is null ? "UnknownCaptureTime" : age < -1000 ? "ClockSkew" : age > 1500 ? "Stale"
                : info.Complete ? "Ended" : frame.Packet.suspended ? "Suspended"
                : frame.Packet.frame.phase != current.State.ToString() ? "PhasePending" : "Fresh";
            var players = current.Players.Select(player =>
            {
                var previous = observed?.Players.SingleOrDefault(value => value.Id == player.Id);
                var sameAdmission = previous is not null && previous.AdmissionId == player.AdmissionId
                    && previous.RoomId == player.RoomId && previous.Seat == player.Seat;
                var body = sameAdmission ? frame?.Packet.frame.players.SingleOrDefault(value => value.id == player.Id.ToString("D")) : null;
                var kind = body?.rig.kind ?? "None";
                var state = source != "Fresh" ? source : !sameAdmission ? "AwaitingAdmission"
                    : body is null ? "AwaitingPose" : body.health == 0 ? "Eliminated"
                    : !body.connected || kind is not ("Simulated" or "Tracked") ? "PoseUnavailable" : "Participating";
                return new PlayerReadiness(player.Id, player.AdmissionId, player.RoomId, player.Seat, state, kind, state == "Participating");
            }).ToArray();
            var observedSequence = frame?.Packet.observedSequence ?? 0;
            var mrStart = current.Environment.Mode != ExperienceMode.MR || current.State != SessionState.Preparing ? null
                : players.Length == 0 ? "EmptyRoster"
                : source != "Fresh" ? "WaitingSource"
                : info?.Header is not { origin: "GameServer", calibration: WorldRecordingHeader.QuestMixedRealityProfile } ? "WaitingProfile"
                : observedSequence != current.Sequence ? "WaitingRevision"
                : players.All(player => player.CanParticipate && player.RigKind == "Tracked") ? "Ready" : "WaitingPlayers";
            return new(1, id, current.Sequence, now, source, info?.Header.origin, info?.AcceptedSequence ?? 0,
                observedSequence, info?.CapturedAtUtc, age, players, mrStart);
        }
    }
}
