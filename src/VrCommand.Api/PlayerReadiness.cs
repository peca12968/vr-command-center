using System.Text.Json.Serialization;
using VrCommand.Core;

using VrCommand.Simulation;

namespace VrCommand.Api;

public record PlayerReadiness(Guid PlayerId, Guid AdmissionId, int RoomId, int Seat, string State, string RigKind, bool CanParticipate);
public record SessionReadiness(int Version, Guid SessionId, long SessionSequence, DateTimeOffset SampledAtUtc,
    string SourceState, string? Origin, long WorldSequence, long ObservedSequence, DateTimeOffset? CapturedAtUtc,
    double? SourceAgeMilliseconds, PlayerReadiness[] Players, string? MrStartState, string? MrResumeState,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? MrTrackingState,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomMrPause? MrPause = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVrPause? VrPause = null);
public record RoomReadiness(int RoomId, Guid? SessionId, long SessionSequence, int Registered, int SimulatedReady,
    int TrackedReady, string SourceState, double? SourceAgeMilliseconds,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int? MrLiving = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomMissionTime? Clock = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVenuePhase? VenuePhase = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] bool? VenueBeginReady = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVenueEnvironment? VenueEnvironment = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVenueEnemies? VenueEnemies = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] ConnectionEndpoint? Endpoint = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVrParticipation? VrParticipation = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVenueBegin? VenueBegin = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomEnvironmentEvidence? Environment = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomEnemiesEvidence? Enemies = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] bool? MrTrackingPauseAvailable = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomMrPause? MrPause = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVenueTracking? VenueTracking = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] bool? VrParticipationPauseAvailable = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomVrPause? VrPause = null);
public record RoomMrPause(long AppliedAtSequence, long? WorldSequence);
public record RoomVrPause(int TriggerRoomId, long AppliedAtSequence, long? WorldSequence,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] bool? ReadyToResume = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int[]? WaitingSeats = null);
public record RoomVenueTracking(int[] TrackedSeats, int[] SimulatedSeats, int[] WaitingSeats, int[] EliminatedSeats);
public record RoomEnvironmentEvidence(RoomVenueEnvironment Setting, string? StreamId, bool Venue);
public record RoomEnemiesEvidence(RoomVenueEnemies Setting, string? StreamId, bool Venue, int TargetCount, RoomEnemyPopulation? Population);
public record RoomEnemyPopulation(int Present, int Alive);
public record RoomVenueBegin(string State, int[] WaitingSeats);
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
        if (command.MrTrackingRoomId is null && command.VrParticipationRoomId is null
            && command.Action is not (ControlAction.Begin or ControlAction.Resume))
            return manager.Execute(id, command, actor);
        lock (gate)
        {
            var (current, _, _, _, _, _) = manager.GetWithPhase(id, actor, out _, out var vrPauseRoom);
            AccessPolicy.Manage(actor, current.Mode, current.RoomIds);
            if (command.MrTrackingRoomId is { } room)
            {
                var tracking = current.State == SessionState.Running && current.Environment.Mode == ExperienceMode.MR
                    ? Readiness(id, actor) : null;
                var witnessed = tracking?.SessionSequence == current.Sequence && tracking.MrTrackingState == "WaitingPlayers"
                    && tracking.Players.Any(player => player.RoomId == room && player.State == "PoseUnavailable");
                return manager.Execute(id, command, actor, witnessed ? current.Sequence : null);
            }
            if (command.VrParticipationRoomId is { } vrRoom)
            {
                var snapshot = ReadReadinessSnapshot(id, actor);
                var witnessed = snapshot.Report.SessionSequence == current.Sequence && snapshot.VrParticipationObserved
                    && HasUnavailablePose(snapshot.Report.Players, vrRoom);
                return manager.Execute(id, command, actor, readyVrSequence: witnessed ? current.Sequence : null);
            }
            if (command.Action == ControlAction.Resume && vrPauseRoom.HasValue)
            {
                var recovery = Readiness(id, actor);
                var readyToResume = recovery.SessionSequence == current.Sequence && recovery.VrPause?.ReadyToResume == true;
                return manager.Execute(id, command, actor, readyVrSequence: readyToResume ? current.Sequence : null);
            }
            if (!SessionManager.RequiresMrReadiness(current, command.Action))
                return manager.Execute(id, command, actor);

            var report = Readiness(id, actor);
            var readiness = command.Action == ControlAction.Resume ? report.MrResumeState : report.MrStartState;
            var ready = report.SessionSequence == current.Sequence && readiness == "Ready";
            return manager.Execute(id, command, actor, ready ? current.Sequence : null);
        }
    }

    public VenuePhaseReceipt ExecuteVenuePhase(ControlAction action, VenuePhaseFence?[]? fences, Guid requestId, OperatorIdentity actor,
        VenueClimate? climate = null, VenueEnemyPolicy? enemyPolicy = null, bool requireFullTracking = false, bool requireFullParticipation = false)
    {
        if (action is not (ControlAction.Begin or ControlAction.Resume))
            return manager.ExecuteVenuePhase(action, fences, requestId, actor, climate: climate, enemyPolicy: enemyPolicy,
                requireFullTracking: requireFullTracking, requireFullParticipation: requireFullParticipation);
        lock (gate)
        {
            var plan = manager.ReadVenuePhase(actor);
            var begin = action == ControlAction.Begin;
            var requireFullRoster = requireFullTracking || requireFullParticipation;
            var expected = (fences ?? []).OfType<VenuePhaseFence>().ToHashSet();
            var reports = new List<(SessionReadiness Report, VenuePhaseWitness Witness)>();
            foreach (var target in (begin ? plan.Begin : plan.Resume)
                .Where(target => expected.Contains(new(target.SessionId, target.PhaseSinceSequence, target.SessionSequence))))
            {
                var (report, _, phase, beginState, _, _, _, _, beginFrame, _) = ReadReadinessSnapshot(target.SessionId, actor,
                    includeBeginFrame: requireFullRoster);
                if (begin ? beginState == "Ready" || requireFullParticipation && beginState == "WaitingPlayers"
                    : phase is { Action: ControlAction.Pause, WorldSequence: not null }
                    && phase.AppliedAtSequence == target.PhaseSinceSequence)
                {
                    var trackedRequired = requireFullTracking || report.MrStartState is not null;
                    var fullRooms = requireFullRoster ? report.Players.GroupBy(player => player.RoomId)
                        .Where(room => room.Count() == SessionManager.PlayersPerRoom && room.All(player => ReadyToBegin(player, trackedRequired)))
                        .Select(room => room.Key).ToArray() : null;
                    reports.Add((report, new(target.PhaseSinceSequence, report.SessionSequence, begin || report.MrResumeState == "Ready",
                        fullRooms, beginFrame)));
                }
            }
            var now = readinessClock.GetUtcNow();
            var ready = reports.Where(row => row.Report.CapturedAtUtc is { } captured
                && (now - captured).TotalMilliseconds is >= -FutureSourceToleranceMilliseconds and <= MaxSourceAgeMilliseconds)
                .ToDictionary(row => row.Report.SessionId, row => row.Witness);
            return manager.ExecuteVenuePhase(action, fences, requestId, actor, ready, climate, enemyPolicy, requireFullTracking, requireFullParticipation);
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
            .ToDictionary(id => id, id => ReadReadinessSnapshot(id, actor, includeRoomDetails: true));
        return rooms.Select(room =>
        {
            if (room.SessionId is not { } id) return new RoomReadiness(room.Id, null, 0, 0, 0, 0, "Idle", null);
            var (report, clock, venuePhase, beginState, environment, enemyRooms, endpoint, vrParticipationObserved, _, venueTrackingObserved) = sessions[id];
            var enemies = enemyRooms?.GetValueOrDefault(room.Id);
            var players = report.Players.Where(player => player.RoomId == room.Id).ToArray();
            var participation = vrParticipationObserved ? new RoomVrParticipation(
                players.Where(player => player.State == "AwaitingAdmission").Select(player => player.Seat + 1).Order().ToArray(),
                players.Where(player => player.State is "AwaitingPose" or "PoseUnavailable").Select(player => player.Seat + 1).Order().ToArray(),
                players.Where(player => player.State == "Eliminated").Select(player => player.Seat + 1).Order().ToArray()) : null;
            var begin = actor.Role == OperatorRole.Master && beginState is not null
                ? new RoomVenueBegin(beginState, beginState == "WaitingPlayers"
                    ? players.Where(player => !ReadyToBegin(player, report.MrStartState is not null)).Select(player => player.Seat + 1).Order().ToArray()
                    : [])
                : null;
            RoomVenueTracking? venueTracking = venueTrackingObserved ? new(
                players.Where(player => player.CanParticipate && player.RigKind == "Tracked").Select(player => player.Seat + 1).Order().ToArray(),
                players.Where(player => player.CanParticipate && player.RigKind == "Simulated").Select(player => player.Seat + 1).Order().ToArray(),
                players.Where(player => !player.CanParticipate && player.State != "Eliminated").Select(player => player.Seat + 1).Order().ToArray(),
                players.Where(player => player.State == "Eliminated").Select(player => player.Seat + 1).Order().ToArray()) : null;
            return new RoomReadiness(room.Id, id, report.SessionSequence, players.Length,
                players.Count(player => player.CanParticipate && player.RigKind == "Simulated"),
                players.Count(player => player.CanParticipate && player.RigKind == "Tracked"),
                report.SourceState, report.SourceAgeMilliseconds,
                report.MrTrackingState is "Ready" or "WaitingPlayers"
                    ? players.Count(player => player.State != "Eliminated") : null, clock, venuePhase,
                beginState is null ? null : beginState == "Ready", environment is { Venue: true } ? environment.Setting : null,
                enemies is { Venue: true } ? enemies.Setting : null, endpoint, participation, begin, environment, enemies,
                report.MrTrackingState == "WaitingPlayers" && players.Any(player => player.State == "PoseUnavailable") ? true : null,
                report.MrPause, venueTracking, vrParticipationObserved && beginState is null && HasUnavailablePose(players, room.Id) ? true : null,
                report.VrPause is { } pause ? pause with
                {
                    WaitingSeats = pause.WorldSequence.HasValue && report.ObservedSequence == report.SessionSequence
                        ? players.Where(player => !ReadyForVrResume(player)).Select(player => player.Seat + 1).Order().ToArray() : null
                } : null);
        }).ToArray();
    }

    // A scoped view of accepted snapshots. Both MR transitions require the exact current roster revision.
    public SessionReadiness Readiness(Guid id, OperatorIdentity actor) => ReadReadinessSnapshot(id, actor).Report;

    private static bool ReadyToBegin(PlayerReadiness player, bool trackedRequired) =>
        player.CanParticipate && (!trackedRequired || player.RigKind == "Tracked");

    private static bool HasUnavailablePose(IEnumerable<PlayerReadiness> players, int room) =>
        players.Any(player => player.RoomId == room && player.State == "PoseUnavailable");

    private static bool ReadyForVrResume(PlayerReadiness player) => player.CanParticipate || player.State == "Eliminated";

    private (SessionReadiness Report, RoomMissionTime? Clock, RoomVenuePhase? VenuePhase, string? BeginState,
        RoomEnvironmentEvidence? Environment, Dictionary<int, RoomEnemiesEvidence>? EnemyRooms, ConnectionEndpoint? Endpoint,
        bool VrParticipationObserved, VenueTrackingFrame? BeginFrame, bool VenueTrackingObserved)
        ReadReadinessSnapshot(Guid id, OperatorIdentity actor, bool includeRoomDetails = false, bool includeBeginFrame = false)
    {
        RequireReadinessActor(actor);
        lock (gate)
        {
            var (current, phaseSince, venueAction, venueEnvironmentSince, venueEnemiesSince, environmentSince) =
                manager.GetWithPhase(id, actor, out var enemiesSince, out var vrPauseRoom);
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
            var confirmed = source == "Fresh" && observedSequence >= phaseSince;
            var starting = SessionManager.RequiresMrReadiness(current, ControlAction.Begin);
            var resuming = SessionManager.RequiresMrReadiness(current, ControlAction.Resume);
            var tracking = current.Environment.Mode == ExperienceMode.MR && current.State == SessionState.Running;
            var mrState = !starting && !resuming && !tracking ? null
                : starting && players.Length == 0 ? "EmptyRoster"
                : source != "Fresh" ? "WaitingSource"
                : info?.Header is not { origin: "GameServer", calibration: WorldRecordingHeader.QuestMixedRealityProfile } ? "WaitingProfile"
                : !tracking && observedSequence != current.Sequence ? "WaitingRevision"
                : players.All(player => (!starting && player.State == "Eliminated") || ReadyToBegin(player, trackedRequired: true))
                    ? "Ready" : "WaitingPlayers";
            var report = new SessionReadiness(1, id, current.Sequence, now, source, info?.Header.origin, info?.AcceptedSequence ?? 0,
                observedSequence, info?.CapturedAtUtc, age, players, starting ? mrState : null, resuming ? mrState : null,
                tracking ? mrState : null,
                resuming ? new(phaseSince, confirmed && info?.Header is { origin: "GameServer", calibration: WorldRecordingHeader.QuestMixedRealityProfile }
                    ? info.AcceptedSequence : null) : null,
                vrPauseRoom is { } trigger ? new(trigger, phaseSince, confirmed ? info!.AcceptedSequence : null,
                    confirmed && observedSequence == current.Sequence && (actor.Role == OperatorRole.Master || current.Mode == SessionMode.Independent)
                        ? players.All(ReadyForVrResume) : null) : null);
            var duration = current.Mission.Definition.DurationSeconds;
            RoomMissionTime? clock = null;
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
            var beginState = current.State != SessionState.Preparing ? null
                : starting ? mrState
                : players.Length == 0 ? "EmptyRoster"
                : source != "Fresh" ? "WaitingSource"
                : observedSequence != current.Sequence ? "WaitingRevision"
                : players.All(player => ReadyToBegin(player, trackedRequired: false)) ? "Ready" : "WaitingPlayers";
            RoomEnvironmentEvidence? environmentEvidence = null;
            if (environmentSince > 1 && current.State is SessionState.Running or SessionState.Paused)
            {
                var environment = current.Environment;
                var applied = confirmed && observedSequence >= environmentSince && frame is not null
                    && frame.Packet.weather == environment.Weather.ToString() && frame.Packet.lightning == environment.Lightning
                    && frame.Packet.frame.night == (environment.TimeOfDay == TimeOfDay.Night);
                environmentEvidence = new(new(environment.Weather, environment.TimeOfDay, environment.Lightning, environmentSince,
                    applied ? report.WorldSequence : null), applied ? info!.Header.streamId : null, venueEnvironmentSince == environmentSince);
            }
            Dictionary<int, RoomEnemiesEvidence>? enemyRooms = null;
            if (includeRoomDetails && enemiesSince > 1 && current.State is SessionState.Running or SessionState.Paused)
            {
                var enemies = current.Enemies;
                var applied = confirmed && observedSequence >= enemiesSince && frame is not null
                    && frame.Packet.frame.behavior == enemies.Behavior.ToString() && frame.Packet.frame.autoAttack == enemies.AutoAttack;
                var setting = new RoomVenueEnemies(enemies.Behavior, enemies.AutoAttack, enemiesSince, applied ? report.WorldSequence : null);
                var byRoom = applied ? frame!.Packet.frame.enemies.ToLookup(enemy => enemy.roomId) : null;
                enemyRooms = current.RoomIds.ToDictionary(room => room, room =>
                {
                    var observedEnemies = byRoom?[room];
                    var population = observedEnemies is null ? null
                        : new RoomEnemyPopulation(observedEnemies.Count(), observedEnemies.Count(enemy => enemy.health > 0));
                    return new RoomEnemiesEvidence(setting, applied ? info!.Header.streamId : null, venueEnemiesSince == enemiesSince,
                        enemies.Count, population);
                });
            }
            var endpoint = includeRoomDetails && current.State != SessionState.Ended ? EndpointRow(current) : null;
            var vrParticipationObserved = confirmed && current.State is SessionState.Preparing or SessionState.Running
                && current.Environment.Mode == ExperienceMode.VR;
            var beginFrame = includeBeginFrame && (beginState is "Ready" or "WaitingPlayers") && frame is not null
                && Guid.TryParseExact(info?.Header.streamId, "D", out var sourceId)
                ? new VenueTrackingFrame(sourceId, frame.Packet.sequence, frame.Packet.elapsedMilliseconds) : null;
            var venueTrackingObserved = includeRoomDetails && actor.Role == OperatorRole.Master && current.State == SessionState.Running
                && confirmed && (!tracking || mrState is "Ready" or "WaitingPlayers")
                && observed?.Players.Length == players.Length && players.All(player => player.State != "AwaitingAdmission");
            return (report, clock, venuePhase, beginState, environmentEvidence, enemyRooms, endpoint, vrParticipationObserved, beginFrame,
                venueTrackingObserved);
        }
    }
}
