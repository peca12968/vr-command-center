using System.Text.Json.Serialization;
using VrCommand.Core;

using VrCommand.Simulation;

namespace VrCommand.Api;

public record PlayerReadiness(Guid PlayerId, Guid AdmissionId, int RoomId, int Seat, string State, string RigKind, bool CanParticipate);
public record SessionReadiness(int Version, Guid SessionId, long SessionSequence, DateTimeOffset SampledAtUtc,
    string SourceState, string? Origin, long WorldSequence, long ObservedSequence, DateTimeOffset? CapturedAtUtc,
    double? SourceAgeMilliseconds, PlayerReadiness[] Players, string? MrStartState, string? MrResumeState,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? MrTrackingState);
public record RoomReadiness(int RoomId, Guid? SessionId, long SessionSequence, int Registered, int SimulatedReady,
    int TrackedReady, string SourceState, double? SourceAgeMilliseconds,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int? MrLiving = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomMissionTime? Clock = null);
public record RoomMissionTime(string Phase, long ElapsedSeconds, long RemainingSeconds, int DurationSeconds, bool AutoEnd);

public sealed partial class WorldRecordings
{
    private const double MaxSourceAgeMilliseconds = 1500;
    private const double FutureSourceToleranceMilliseconds = 1000;

    public CommandReceipt ExecuteCommand(Guid id, ControlCommand command, OperatorIdentity actor)
    {
        if (command.Action is not (ControlAction.Begin or ControlAction.Resume)) return manager.Execute(id, command, actor);
        lock (gate)
        {
            var current = manager.Get(id, actor);
            AccessPolicy.Manage(actor, current.Mode, current.RoomIds);
            if (!SessionManager.RequiresMrReadiness(current, command.Action))
                return manager.Execute(id, command, actor);

            var report = Readiness(id, actor);
            var readiness = command.Action == ControlAction.Resume ? report.MrResumeState : report.MrStartState;
            var ready = report.SessionSequence == current.Sequence && readiness == "Ready";
            return manager.Execute(id, command, actor, ready ? current.Sequence : null);
        }
    }

    public VenuePhaseReceipt ExecuteVenuePhase(ControlAction action, VenuePhaseFence?[]? fences, Guid requestId, OperatorIdentity actor)
    {
        if (action != ControlAction.Resume) return manager.ExecuteVenuePhase(action, fences, requestId, actor);
        lock (gate)
        {
            var expected = (fences ?? []).OfType<VenuePhaseFence>().ToHashSet();
            var reports = new List<SessionReadiness>();
            foreach (var target in manager.ReadVenuePhase(actor).Resume.Where(target => expected.Contains(new(target.SessionId, target.PhaseSinceSequence))))
            {
                var session = manager.Get(target.SessionId, actor);
                if (!SessionManager.RequiresMrReadiness(session, action)) continue;
                var report = Readiness(target.SessionId, actor);
                if (report.MrResumeState == "Ready" && report.SessionSequence == session.Sequence)
                    reports.Add(report);
            }
            var now = readinessClock.GetUtcNow();
            var ready = reports.Where(report => report.CapturedAtUtc is { } captured
                && (now - captured).TotalMilliseconds is >= -FutureSourceToleranceMilliseconds and <= MaxSourceAgeMilliseconds)
                .ToDictionary(report => report.SessionId, report => report.SessionSequence);
            return manager.ExecuteVenuePhase(action, fences, requestId, actor, ready);
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
            .ToDictionary(id => id, id => ReadReadinessSnapshot(id, actor));
        return rooms.Select(room =>
        {
            if (room.SessionId is not { } id) return new RoomReadiness(room.Id, null, 0, 0, 0, 0, "Idle", null);
            var (report, clock) = sessions[id];
            var players = report.Players.Where(player => player.RoomId == room.Id).ToArray();
            return new RoomReadiness(room.Id, id, report.SessionSequence, players.Length,
                players.Count(player => player.CanParticipate && player.RigKind == "Simulated"),
                players.Count(player => player.CanParticipate && player.RigKind == "Tracked"),
                report.SourceState, report.SourceAgeMilliseconds,
                report.MrTrackingState is "Ready" or "WaitingPlayers"
                    ? players.Count(player => player.State != "Eliminated") : null, clock);
        }).ToArray();
    }

    // A scoped view of accepted snapshots. Both MR transitions require the exact current roster revision.
    public SessionReadiness Readiness(Guid id, OperatorIdentity actor) => ReadReadinessSnapshot(id, actor).Report;

    private (SessionReadiness Report, RoomMissionTime? Clock) ReadReadinessSnapshot(Guid id, OperatorIdentity actor)
    {
        RequireReadinessActor(actor);
        lock (gate)
        {
            var (current, phaseSince) = manager.GetWithPhase(id, actor);
            using var exists = Command("SELECT 1 FROM recordings WHERE session=$id", ("$id", id.ToString("D")));
            var info = exists.ExecuteScalar() is null ? null : Info(id, actor);
            var frame = info is null || info.AcceptedSequence == 0 ? null : Frame(id, info.AcceptedSequence, actor);
            var observed = frame is null ? null : manager.Observed(id, frame.Packet.observedSequence, actor);
            var now = readinessClock.GetUtcNow();
            var age = info?.CapturedAtUtc is { } captured ? (double?)(now - captured).TotalMilliseconds : null;
            var source = current.State == SessionState.Ended ? "Ended"
                : info is null ? "NoRecording" : frame is null ? "WaitingFrame"
                : age is null ? "UnknownCaptureTime" : age < -FutureSourceToleranceMilliseconds ? "ClockSkew" : age > MaxSourceAgeMilliseconds ? "Stale"
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
            var starting = SessionManager.RequiresMrReadiness(current, ControlAction.Begin);
            var resuming = SessionManager.RequiresMrReadiness(current, ControlAction.Resume);
            var tracking = current.Environment.Mode == ExperienceMode.MR && current.State == SessionState.Running;
            var mrState = !starting && !resuming && !tracking ? null
                : starting && players.Length == 0 ? "EmptyRoster"
                : source != "Fresh" ? "WaitingSource"
                : info?.Header is not { origin: "GameServer", calibration: WorldRecordingHeader.QuestMixedRealityProfile } ? "WaitingProfile"
                : !tracking && observedSequence != current.Sequence ? "WaitingRevision"
                : players.All(player => (!starting && player.State == "Eliminated") || (player.CanParticipate && player.RigKind == "Tracked"))
                    ? "Ready" : "WaitingPlayers";
            var report = new SessionReadiness(1, id, current.Sequence, now, source, info?.Header.origin, info?.AcceptedSequence ?? 0,
                observedSequence, info?.CapturedAtUtc, age, players, starting ? mrState : null, resuming ? mrState : null,
                tracking ? mrState : null);
            var duration = current.Mission.Definition.DurationSeconds;
            RoomMissionTime? clock = null;
            if (source == "Fresh" && current.State is SessionState.Running or SessionState.Paused
                && current.CombatStream is { MissionClockVersion: 1 } && info?.Header is { missionClockVersion: 1 } header
                && header.missionDurationSeconds == duration && frame is not null && observedSequence >= phaseSince)
            {
                var tick = frame.Packet.frame.tick;
                clock = new(frame.Packet.frame.phase, tick / MissionClock.TicksPerSecond, MissionClock.RemainingSeconds(tick, duration),
                    duration, current.MissionClock is { Version: 1, AutoEnd: true });
            }
            return (report, clock);
        }
    }
}
