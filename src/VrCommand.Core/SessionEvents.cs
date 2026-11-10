using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Simulation;

namespace VrCommand.Core;

public enum SessionEventKind { Created, PlayerJoined, PlayerLeft, ControlApplied, CombatRecorded, CombatStreamOpened, StreamCombatRecorded, CombatStreamSealed }
public record SessionCreated(SessionMode Mode, int[] RoomIds, Mission Mission,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? IndependentSetId = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? IndependentSetPlanSha256 = null);
public record PlayerLeft(Guid PlayerId, int? RoomId = null, Guid AdmissionId = default, Guid? ExpectedAdmissionId = null);
public record VenueTransition(long PhaseSinceSequence, int TargetCount,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? EnvironmentSinceSequence = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? EnemiesSinceSequence = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)] bool RequireFullTracking = false,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueTrackingFrame? TrackingFrame = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)] bool RequireFullParticipation = false,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueTrackingFrame? ParticipationFrame = null);
public record SessionEvent(int SchemaVersion, Guid EventId, Guid SessionId, long Sequence,
    DateTimeOffset RecordedAtUtc, SessionEventKind Kind, JsonElement Payload, OperatorIdentity? Actor = null,
    Guid? RequestId = null, [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] VenueTransition? Venue = null)
{
    public T Read<T>() => Payload.Deserialize<T>(JsonFormat.Options)
        ?? throw new InvalidDataException("Missing event payload.");
    internal static SessionEvent Create<T>(Guid id, long sequence, SessionEventKind kind, T payload, OperatorIdentity actor,
        Guid? requestId = null, VenueTransition? venue = null)
    {
        var eventId = Guid.NewGuid();
        var data = kind == SessionEventKind.PlayerJoined && payload is Player player
            ? JsonSerializer.SerializeToElement(player with { AdmissionId = eventId }, JsonFormat.Options)
            : JsonSerializer.SerializeToElement(payload, JsonFormat.Options);
        return new(7, eventId, id, sequence, DateTimeOffset.UtcNow, kind, data, actor, requestId, venue);
    }
}

// Use the same transition rules for commands and reconstruction after a restart.
internal static class SessionProjection
{
    internal static void ValidateCreation(SessionCreated data)
    {
        ArgumentNullException.ThrowIfNull(data.RoomIds);
        ArgumentNullException.ThrowIfNull(data.Mission);
        if (data.Mission.Id == Guid.Empty || data.Mission.SchemaVersion != 1)
            throw new ArgumentException("Unsupported mission identity or schema.");
        MissionStore.Validate(data.Mission.Definition);
        if (!Enum.IsDefined(data.Mode)) throw new ArgumentException("Invalid session mode.");
        var expected = data.Mode == SessionMode.Independent ? 1 : SessionManager.RoomCount;
        if (data.RoomIds.Length != expected || data.RoomIds.Distinct().Count() != expected
            || data.RoomIds.Any(id => id < 1 || id > SessionManager.RoomCount))
            throw new ArgumentException("Independent mode requires one room; linked mode requires rooms 1–5.");
    }

    internal static void ValidateCommand(ControlCommand command)
    {
        if (command.CommandId == Guid.Empty || command.Action == ControlAction.Unspecified
            || !Enum.IsDefined(command.Action) || command.ExpectedSequence < 0)
            throw new ArgumentException("A command requires a non-empty ID, valid action and non-negative expected sequence.");
        if (command.Action == ControlAction.SetEnvironment)
            MissionStore.ValidateEnvironment(command.Environment);
        else if (command.Environment is not null)
            throw new ArgumentException("Environment is only allowed for SetEnvironment.");
        if (command.Action == ControlAction.SetEnemies)
            MissionStore.ValidateEnemies(command.Enemies);
        else if (command.Enemies is not null)
            throw new ArgumentException("Enemies is only allowed for SetEnemies.");
        if ((command.Action == ControlAction.SetRoomEnemies) != (command.RoomEnemyPolicy is not null)
            || command.RoomEnemyPolicy is { } roomPolicy && (roomPolicy.RoomId is < 1 or > SessionManager.RoomCount
                || roomPolicy.Policy is { } policy && (policy.Behavior is not { } behavior || !Enum.IsDefined(behavior) || !policy.AutoAttack.HasValue)))
            throw new ArgumentException("A room enemy policy requires a room and complete settings, or null to use venue settings.");
        if ((command.Action == ControlAction.SetMissionClock) != (command.MissionClock is not null))
            throw new ArgumentException("Mission clock settings are required only for SetMissionClock.");
        if ((command.Action == ControlAction.SetRoomAlignment) != (command.RoomAlignment is not null))
            throw new ArgumentException("Room alignment pins are required only for SetRoomAlignment.");
        if (command.ClockExpiration is { } expiration && (command.Action != ControlAction.End || expiration.StreamId == Guid.Empty
            || expiration.ObservedSequence < 1 || expiration.Tick < 0))
            throw new ArgumentException("Clock expiration requires an End and valid source evidence.");
        if (command.MrTrackingRoomId is int room && (command.Action != ControlAction.Pause
            || room is < 1 or > SessionManager.RoomCount || command.ExpectedSequence is null or < 1))
            throw new ArgumentException("MR tracking pause requires Pause, a room and an expected sequence.");
        if (command.VrParticipationRoomId is int vrRoom && (command.Action != ControlAction.Pause
            || vrRoom is < 1 or > SessionManager.RoomCount || command.ExpectedSequence is null or < 1 || command.MrTrackingRoomId.HasValue))
            throw new ArgumentException("VR participation pause requires Pause, a room and an expected sequence.");
    }

    internal static SessionView Apply(SessionView? current, SessionEvent entry)
    {
        if (entry.SchemaVersion is not (1 or 2 or 3 or 4 or 5 or 6 or 7) || entry.EventId == Guid.Empty || entry.SessionId == Guid.Empty
            || entry.Sequence != (current?.Sequence ?? 0) + 1 || !Enum.IsDefined(entry.Kind)
            || entry.RecordedAtUtc == default || entry.RecordedAtUtc.Offset != TimeSpan.Zero
            || (current is not null && current.Id != entry.SessionId))
            throw new InvalidDataException("Unsupported or inconsistent event envelope.");
        if (entry.SchemaVersion >= 2 && entry.Actor is null)
            throw new InvalidDataException("Version 2+ events require an authenticated or internal actor.");
        if (entry.Kind == SessionEventKind.CombatRecorded && entry.SchemaVersion < 3)
            throw new InvalidDataException("Combat events require schema version 3+.");
        if (entry.Kind is SessionEventKind.CombatStreamOpened or SessionEventKind.StreamCombatRecorded or SessionEventKind.CombatStreamSealed
            && entry.SchemaVersion < 5) throw new InvalidDataException("Combat streams require schema version 5.");
        if (entry.RequestId.HasValue && (entry.SchemaVersion < 4 || entry.RequestId == Guid.Empty
            || entry.Kind is not (SessionEventKind.Created or SessionEventKind.PlayerJoined or SessionEventKind.PlayerLeft)))
            throw new InvalidDataException("Request IDs require a version 4 lifecycle event and a non-empty ID.");
        if (entry.SchemaVersion == 1 && entry.Actor is not null)
            throw new InvalidDataException("Legacy events cannot assert an authenticated actor.");
        var actor = entry.Actor ?? OperatorIdentity.Internal;
        AccessPolicy.Validate(actor);
        if (entry.Venue is { } venue && (entry.SchemaVersion < 7 || actor.Role != OperatorRole.Master
            || entry.Kind != SessionEventKind.ControlApplied || venue.TargetCount is < 1 or > SessionManager.RoomCount
            || venue.PhaseSinceSequence < 1 || venue.PhaseSinceSequence >= entry.Sequence
            || !ValidVenueCommand(entry.Read<ControlCommand>(), entry.Sequence, venue, current)))
            throw new InvalidDataException("Invalid venue phase transition envelope.");
        if (current is null)
        {
            if (entry.Kind != SessionEventKind.Created) throw new InvalidDataException("History must begin with Created.");
            var created = entry.Read<SessionCreated>();
            ValidateCreation(created);
            AccessPolicy.Manage(actor, created.Mode, created.RoomIds);
            if (created.IndependentSetId is { } set && (entry.SchemaVersion < 7 || set == Guid.Empty
                || actor.Role != OperatorRole.Master || created.Mode != SessionMode.Independent
                || entry.RequestId != (created.RoomIds[0] == 1 ? set : (Guid?)null)))
                throw new InvalidDataException("Invalid five-room creation receipt.");
            if (created.IndependentSetPlanSha256 is not null && (created.IndependentSetId is null || created.RoomIds[0] != 1))
                throw new InvalidDataException("A five-room plan digest belongs to the first room's creation receipt.");
            return new(entry.SessionId, created.Mode, created.RoomIds, created.Mission,
                entry.RecordedAtUtc, null, null, SessionState.Preparing, [],
                created.Mission.Definition.Environment, created.Mission.Definition.Enemies, entry.Sequence);
        }
        if (entry.Kind is SessionEventKind.CombatStreamOpened or SessionEventKind.StreamCombatRecorded or SessionEventKind.CombatStreamSealed)
            return CombatStreamProjection.Apply(current, entry) with { Sequence = entry.Sequence };
        if (current.State == SessionState.Ended) throw new InvalidOperationException("Session has ended.");
        switch (entry.Kind)
        {
            case SessionEventKind.PlayerJoined:
                AccessPolicy.Player(actor, current, entry.Read<Player>().RoomId);
                break;
            case SessionEventKind.PlayerLeft:
                var leaving = entry.Read<PlayerLeft>();
                var player = current.Players.SingleOrDefault(p => p.Id == leaving.PlayerId)
                    ?? throw new KeyNotFoundException("Player does not exist.");
                if (entry.SchemaVersion >= 4 && leaving.RoomId != player.RoomId)
                    throw new InvalidDataException("Leave event must retain the admitted player's room.");
                if (entry.SchemaVersion >= 6 && (leaving.AdmissionId != player.AdmissionId
                    || leaving.ExpectedAdmissionId == Guid.Empty || (leaving.ExpectedAdmissionId.HasValue && leaving.ExpectedAdmissionId != player.AdmissionId)))
                    throw new InvalidDataException("Leave event must target its exact admitted player instance.");
                if (entry.SchemaVersion < 6 && ((leaving.AdmissionId != Guid.Empty && leaving.AdmissionId != player.AdmissionId) || leaving.ExpectedAdmissionId.HasValue))
                    throw new InvalidDataException("Admission fences require event schema 6.");
                AccessPolicy.Player(actor, current, player.RoomId);
                break;
            case SessionEventKind.ControlApplied:
                var command = entry.Read<ControlCommand>();
                AccessPolicy.Control(actor, current, command);
                if (command.Action == ControlAction.SetRoomEnemies && entry.SchemaVersion < 7)
                    throw new InvalidDataException("Room enemy policies require event schema 7.");
                if ((command.MissionClock is not null || command.ClockExpiration is not null) && entry.SchemaVersion < 7)
                    throw new InvalidDataException("Mission clocks require event schema 7.");
                if (command.MrTrackingRoomId is { } trackingRoom && (entry.SchemaVersion < 7
                    || current.State != SessionState.Running || current.Environment.Mode != ExperienceMode.MR
                    || !current.RoomIds.Contains(trackingRoom) || current.CombatStream?.Origin != CombatOrigin.GameServer
                    || command.ExpectedSequence != current.Sequence))
                    throw new InvalidDataException("MR tracking pause must retain its original room, mode and revision.");
                if (command.VrParticipationRoomId is { } vrRoom && (entry.SchemaVersion < 7
                    || current.State != SessionState.Running || current.Environment.Mode != ExperienceMode.VR
                    || !current.RoomIds.Contains(vrRoom) || current.CombatStream is null || command.ExpectedSequence != current.Sequence))
                    throw new InvalidDataException("VR participation pause must retain its original room, mode and revision.");
                if (command.Action == ControlAction.SetRoomAlignment)
                {
                    if (entry.SchemaVersion < 7) throw new InvalidDataException("Room alignment pins require event schema 7.");
                    if (actor.Role is not (OperatorRole.Master or OperatorRole.Internal))
                        throw new AccessDeniedException("Only the master may pin room alignment files.");
                }
                if (command.ClockExpiration is { } expiration)
                {
                    if (actor != SessionManager.ClockIdentity) throw new AccessDeniedException("Only the internal mission clock may expire a session.");
                    SessionManager.ValidateClockExpiration(current, expiration);
                }
                break;
            case SessionEventKind.CombatRecorded:
                AccessPolicy.ReportCombat(actor);
                if (current.CombatStream is not null) throw new InvalidOperationException("Legacy reports cannot bypass a bound stream.");
                if (current.State != SessionState.Running) throw new InvalidOperationException("Combat requires Running.");
                break;
        }
        var updated = entry.Kind switch
        {
            SessionEventKind.PlayerJoined => Join(current, entry.Read<Player>(), entry.EventId, entry.SchemaVersion),
            SessionEventKind.PlayerLeft => Leave(current, entry.Read<PlayerLeft>().PlayerId),
            SessionEventKind.ControlApplied => Control(current, entry.Read<ControlCommand>(), entry.RecordedAtUtc, entry.Sequence),
            SessionEventKind.CombatRecorded => current,
            _ => throw new InvalidDataException("Unexpected event kind.")
        };
        return updated with { Sequence = entry.Sequence };
    }

    private static bool ValidVenueCommand(ControlCommand command, long sequence, VenueTransition venue, SessionView? session)
    {
        var fullRoster = venue.RequireFullTracking || venue.RequireFullParticipation;
        if (command.Action != ControlAction.SetEnvironment && venue.EnvironmentSinceSequence is not null
            || command.Action != ControlAction.SetEnemies && venue.EnemiesSinceSequence is not null
            || fullRoster && command.Action != ControlAction.Begin
            || venue.RequireFullTracking && venue.RequireFullParticipation
            || venue.TrackingFrame is not null && !venue.RequireFullTracking
            || venue.RequireFullParticipation != (venue.ParticipationFrame is not null)
            || (venue.TrackingFrame ?? venue.ParticipationFrame) is { } frame && (frame.WorldSequence < 1
                || frame.ElapsedMilliseconds < 0 || frame.StreamId == Guid.Empty || session?.CombatStream?.StreamId != frame.StreamId)) return false;
        return command.Action switch
        {
            ControlAction.Begin => command.ExpectedSequence == sequence - 1 && (!fullRoster || session is not null
                && session.RoomIds.All(room => session.Players.Count(player => player.RoomId == room) == SessionManager.PlayersPerRoom)),
            ControlAction.Pause or ControlAction.Resume or ControlAction.End => command.ExpectedSequence is null && command.ClockExpiration is null,
            ControlAction.SetEnvironment => command.ExpectedSequence is null && venue.EnvironmentSinceSequence is > 0
                && venue.EnvironmentSinceSequence < sequence && session?.State == SessionState.Running && command.Environment?.Mode == session.Environment.Mode,
            ControlAction.SetEnemies => command.ExpectedSequence is null && venue.EnemiesSinceSequence is > 0
                && venue.EnemiesSinceSequence < sequence && session?.State == SessionState.Running && command.Enemies?.Count == session.Enemies.Count,
            _ => false
        };
    }

    private static SessionView Join(SessionView session, Player player, Guid admission, int schema)
    {
        if ((schema >= 6 && player.AdmissionId != admission) || (player.AdmissionId != Guid.Empty && player.AdmissionId != admission))
            throw new InvalidDataException("Player admission must be the immutable joining event ID.");
        if (player.Id == Guid.Empty || string.IsNullOrWhiteSpace(player.Name) || player.Name.Length > 80
            || !Enum.IsDefined(player.Headset)) throw new ArgumentException("Invalid player details.");
        if (session.State != SessionState.Preparing) throw new InvalidOperationException("Players may join only while preparing.");
        if (!session.RoomIds.Contains(player.RoomId)) throw new ArgumentException("Room is outside this session.");
        if (session.Players.Any(p => p.Id == player.Id)) throw new InvalidOperationException("Player already joined.");
        if (session.Players.Count(p => p.RoomId == player.RoomId) >= SessionManager.PlayersPerRoom)
            throw new InvalidOperationException("Player capacity reached.");
        var seat = player.Seat == -1 ? Enumerable.Range(0, SessionManager.PlayersPerRoom)
            .First(candidate => !session.Players.Any(p => p.RoomId == player.RoomId && p.Seat == candidate)) : player.Seat;
        if (seat is < 0 or >= SessionManager.PlayersPerRoom || session.Players.Any(p => p.RoomId == player.RoomId && p.Seat == seat))
            throw new ArgumentException("Player seat is invalid or already occupied.");
        return session with { Players = [.. session.Players, player with { Seat = seat, AdmissionId = admission }] };
    }

    private static SessionView Leave(SessionView session, Guid playerId)
    {
        if (!session.Players.Any(p => p.Id == playerId)) throw new KeyNotFoundException("Player does not exist.");
        return session with { Players = session.Players.Where(p => p.Id != playerId).ToArray() };
    }

    private static SessionView Control(SessionView session, ControlCommand command, DateTimeOffset now, long sequence)
    {
        ValidateCommand(command);
        if (command.ExpectedSequence.HasValue && command.ExpectedSequence != session.Sequence)
            throw new InvalidDataException("Command sequence does not match prior state.");
        return command.Action switch
        {
            ControlAction.Begin when session.State == SessionState.Preparing && session.Players.Length > 0
                => session with { State = SessionState.Running, StartedAtUtc = now },
            ControlAction.Pause when session.State == SessionState.Running => session with { State = SessionState.Paused },
            ControlAction.Resume when session.State == SessionState.Paused => session with { State = SessionState.Running },
            ControlAction.End => session with { State = SessionState.Ended, EndedAtUtc = now },
            ControlAction.SetEnvironment => session with { Environment = command.Environment! },
            ControlAction.SetEnemies => session with { Enemies = command.Enemies!, RoomEnemyPolicies = null },
            ControlAction.SetRoomEnemies when session.CombatStream?.RoomEnemyPolicyVersion == 1
                => SetRoomEnemyPolicy(session, command.RoomEnemyPolicy!, sequence),
            ControlAction.SetMissionClock when session.State == SessionState.Preparing
                && (!command.MissionClock!.AutoEnd || session.CombatStream?.MissionClockVersion == 1)
                => session with { MissionClock = new(1, command.MissionClock!.AutoEnd, sequence) },
            ControlAction.SetRoomAlignment => PinAlignment(session, command.RoomAlignment!),
            _ => throw new InvalidOperationException($"Cannot apply {command.Action} while {session.State} or without players.")
        };
    }

    private static SessionView SetRoomEnemyPolicy(SessionView session, RoomEnemyPolicyChange change, long sequence)
    {
        var next = (session.RoomEnemyPolicies ?? []).Where(policy => policy.RoomId != change.RoomId).ToList();
        if (change.Policy is { } policy)
            next.Add(new(change.RoomId, policy.Behavior!.Value, policy.AutoAttack!.Value, sequence));
        return session with { RoomEnemyPolicies = next.Count == 0 ? null : next.OrderBy(row => row.RoomId).ToArray() };
    }

    private static SessionView PinAlignment(SessionView session, RoomAlignmentPins pins)
    {
        if (session.Environment.Mode != ExperienceMode.MR || session.State != SessionState.Preparing
            || session.CombatStream is not null || session.RoomAlignment is not null)
            throw new InvalidOperationException("Room alignment files can be pinned once while an MR session is Preparing and has no game source.");
        foreach (var room in Enumerable.Range(1, SessionManager.RoomCount))
        {
            var hash = pins.ForRoom(room);
            if (session.RoomIds.Contains(room) ? !ArenaConnectionProfile.IsAlignmentHash(hash) : hash is not null)
                throw new ArgumentException("Provide one lowercase SHA-256 for each room in the session, and omit other rooms.");
        }
        return session with { RoomAlignment = pins };
    }
}
