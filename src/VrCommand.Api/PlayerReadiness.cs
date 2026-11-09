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
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomMissionTime? Clock = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVenuePhase? VenuePhase = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] bool? VenueBeginReady = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVenueEnvironment? VenueEnvironment = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVenueEnemies? VenueEnemies = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] ConnectionEndpoint? Endpoint = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVrParticipation? VrParticipation = null);
public record RoomVrParticipation(int[] AwaitingAdmission, int[] AwaitingPose, int[] Eliminated);
public record RoomMissionTime(string Phase, long ElapsedSeconds, long RemainingSeconds, int DurationSeconds, bool AutoEnd);
public record RoomVenuePhase(ControlAction Action, long AppliedAtSequence, long? WorldSequence, bool ReadyToResume);
public record RoomVenueEnvironment(Weather Weather, TimeOfDay TimeOfDay, bool Lightning, long AppliedAtSequence, long? WorldSequence);
public record RoomVenueEnemies(EnemyBehavior Behavior, bool AutoAttack, long AppliedAtSequence, long? WorldSequence);

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

    public VenuePhaseReceipt ExecuteVenuePhase(ControlAction action, VenuePhaseFence?[]? fences, Guid requestId, OperatorIdentity actor,
        VenueClimate? climate = null, VenueEnemyPolicy? enemyPolicy = null)
    {
        if (action is not (ControlAction.Begin or ControlAction.Resume))
            return manager.ExecuteVenuePhase(action, fences, requestId, actor, climate: climate, enemyPolicy: enemyPolicy);
        lock (gate)
        {
            var plan = manager.ReadVenuePhase(actor);
            var begin = action == ControlAction.Begin;
            var expected = (fences ?? []).OfType<VenuePhaseFence>().ToHashSet();
            var reports = new List<(SessionReadiness Report, VenuePhaseWitness Witness)>();
            foreach (var target in (begin ? plan.Begin : plan.Resume)
                .Where(target => expected.Contains(new(target.SessionId, target.PhaseSinceSequence, target.SessionSequence))))
            {
                var (report, _, phase, beginReady, _, _, _, _) = ReadReadinessSnapshot(target.SessionId, actor);
                if (begin ? beginReady == true : phase is { Action: ControlAction.Pause, WorldSequence: not null }
                    && phase.AppliedAtSequence == target.PhaseSinceSequence)
                    reports.Add((report, new(target.PhaseSinceSequence, report.SessionSequence, begin || report.MrResumeState == "Ready")));
            }
            var now = readinessClock.GetUtcNow();
            var ready = reports.Where(row => row.Report.CapturedAtUtc is { } captured
                && (now - captured).TotalMilliseconds is >= -FutureSourceToleranceMilliseconds and <= MaxSourceAgeMilliseconds)
                .ToDictionary(row => row.Report.SessionId, row => row.Witness);
            return manager.ExecuteVenuePhase(action, fences, requestId, actor, ready, climate, enemyPolicy);
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
            .ToDictionary(id => id, id => ReadReadinessSnapshot(id, actor, includeEndpoint: true));
        return rooms.Select(room =>
        {
            if (room.SessionId is not { } id) return new RoomReadiness(room.Id, null, 0, 0, 0, 0, "Idle", null);
            var (report, clock, venuePhase, beginReady, venueEnvironment, venueEnemies, endpoint, vrParticipationObserved) = sessions[id];
            var players = report.Players.Where(player => player.RoomId == room.Id).ToArray();
            var participation = vrParticipationObserved ? new RoomVrParticipation(
                players.Where(player => player.State == "AwaitingAdmission").Select(player => player.Seat + 1).Order().ToArray(),
                players.Where(player => player.State is "AwaitingPose" or "PoseUnavailable").Select(player => player.Seat + 1).Order().ToArray(),
                players.Where(player => player.State == "Eliminated").Select(player => player.Seat + 1).Order().ToArray()) : null;
            return new RoomReadiness(room.Id, id, report.SessionSequence, players.Length,
                players.Count(player => player.CanParticipate && player.RigKind == "Simulated"),
                players.Count(player => player.CanParticipate && player.RigKind == "Tracked"),
                report.SourceState, report.SourceAgeMilliseconds,
                report.MrTrackingState is "Ready" or "WaitingPlayers"
                    ? players.Count(player => player.State != "Eliminated") : null, clock, venuePhase, beginReady, venueEnvironment, venueEnemies, endpoint, participation);
        }).ToArray();
    }

    // A scoped view of accepted snapshots. Both MR transitions require the exact current roster revision.
    public SessionReadiness Readiness(Guid id, OperatorIdentity actor) => ReadReadinessSnapshot(id, actor).Report;

    private (SessionReadiness Report, RoomMissionTime? Clock, RoomVenuePhase? VenuePhase, bool? BeginReady,
        RoomVenueEnvironment? VenueEnvironment, RoomVenueEnemies? VenueEnemies, ConnectionEndpoint? Endpoint, bool VrParticipationObserved)
        ReadReadinessSnapshot(Guid id, OperatorIdentity actor, bool includeEndpoint = false)
    {
        RequireReadinessActor(actor);
        lock (gate)
        {
            var (current, phaseSince, venueAction, environmentSince, enemiesSince) = manager.GetWithPhase(id, actor);
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
            var confirmed = source == "Fresh" && observedSequence >= phaseSince;
            if (confirmed && current.State is SessionState.Running or SessionState.Paused
                && current.CombatStream is { MissionClockVersion: 1 } && info?.Header is { missionClockVersion: 1 } header
                && header.missionDurationSeconds == duration && frame is not null)
            {
                var tick = frame.Packet.frame.tick;
                clock = new(frame.Packet.frame.phase, tick / MissionClock.TicksPerSecond, MissionClock.RemainingSeconds(tick, duration),
                    duration, current.MissionClock is { Version: 1, AutoEnd: true });
            }
            RoomVenuePhase? venuePhase = venueAction is { } action && current.State is SessionState.Paused or SessionState.Running
                ? new(action, phaseSince,
                    confirmed ? report.WorldSequence : null, confirmed && current.State == SessionState.Paused && (!resuming || mrState == "Ready"))
                : null;
            bool? beginReady = current.State == SessionState.Preparing
                ? source == "Fresh" && observedSequence == current.Sequence && players.Length > 0
                    && (starting ? mrState == "Ready" : players.All(player => player.CanParticipate))
                : null;
            RoomVenueEnvironment? venueEnvironment = null;
            if (environmentSince is { } sequence && current.State is SessionState.Running or SessionState.Paused)
            {
                var environment = current.Environment;
                var applied = confirmed && observedSequence >= sequence && frame is not null
                    && frame.Packet.weather == environment.Weather.ToString() && frame.Packet.lightning == environment.Lightning
                    && frame.Packet.frame.night == (environment.TimeOfDay == TimeOfDay.Night);
                venueEnvironment = new(environment.Weather, environment.TimeOfDay, environment.Lightning, sequence,
                    applied ? report.WorldSequence : null);
            }
            RoomVenueEnemies? venueEnemies = null;
            if (enemiesSince is { } enemySequence && current.State is SessionState.Running or SessionState.Paused)
            {
                var enemies = current.Enemies;
                var applied = confirmed && observedSequence >= enemySequence && frame is not null
                    && frame.Packet.frame.behavior == enemies.Behavior.ToString() && frame.Packet.frame.autoAttack == enemies.AutoAttack;
                venueEnemies = new(enemies.Behavior, enemies.AutoAttack, enemySequence, applied ? report.WorldSequence : null);
            }
            var endpoint = includeEndpoint && current.State != SessionState.Ended ? EndpointRow(current) : null;
            var vrParticipationObserved = confirmed && current.State is SessionState.Preparing or SessionState.Running
                && current.Environment.Mode == ExperienceMode.VR;
            return (report, clock, venuePhase, beginReady, venueEnvironment, venueEnemies, endpoint, vrParticipationObserved);
        }
    }
}
