using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Simulation;

namespace VrCommand.Core;

public enum SessionEventKind { Created, PlayerJoined, PlayerLeft, ControlApplied, CombatRecorded, CombatStreamOpened, StreamCombatRecorded, CombatStreamSealed }
public record SessionCreated(SessionMode Mode, int[] RoomIds, Mission Mission,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? IndependentSetId = null);
public record PlayerLeft(Guid PlayerId, int? RoomId = null, Guid AdmissionId = default, Guid? ExpectedAdmissionId = null);
public record VenueTransition(long PhaseSinceSequence, int TargetCount,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? EnvironmentSinceSequence = null);
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
        if ((command.Action == ControlAction.SetMissionClock) != (command.MissionClock is not null))
            throw new ArgumentException("Mission clock settings are required only for SetMissionClock.");
        if ((command.Action == ControlAction.SetRoomAlignment) != (command.RoomAlignment is not null))
            throw new ArgumentException("Room alignment pins are required only for SetRoomAlignment.");
        if (command.ClockExpiration is { } expiration && (command.Action != ControlAction.End || expiration.StreamId == Guid.Empty
            || expiration.ObservedSequence < 1 || expiration.Tick < 0))
            throw new ArgumentException("Clock expiration requires an End and valid source evidence.");
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
                AccessPolicy.Manage(actor, current.Mode, current.RoomIds);
                var command = entry.Read<ControlCommand>();
                if ((command.MissionClock is not null || command.ClockExpiration is not null) && entry.SchemaVersion < 7)
                    throw new InvalidDataException("Mission clocks require event schema 7.");
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

    private static bool ValidVenueCommand(ControlCommand command, long sequence, VenueTransition venue, SessionView? session) => command.Action switch
    {
        ControlAction.Begin => command.ExpectedSequence == sequence - 1 && venue.EnvironmentSinceSequence is null,
        ControlAction.Pause or ControlAction.Resume or ControlAction.End => command.ExpectedSequence is null && command.ClockExpiration is null
            && venue.EnvironmentSinceSequence is null,
        ControlAction.SetEnvironment => command.ExpectedSequence is null && venue.EnvironmentSinceSequence is > 0
            && venue.EnvironmentSinceSequence < sequence && session?.State == SessionState.Running && command.Environment?.Mode == session.Environment.Mode,
        _ => false
    };

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
            ControlAction.SetEnemies => session with { Enemies = command.Enemies! },
            ControlAction.SetMissionClock when session.State == SessionState.Preparing
                && (!command.MissionClock!.AutoEnd || session.CombatStream?.MissionClockVersion == 1)
                => session with { MissionClock = new(1, command.MissionClock!.AutoEnd, sequence) },
            ControlAction.SetRoomAlignment => PinAlignment(session, command.RoomAlignment!),
            _ => throw new InvalidOperationException($"Cannot apply {command.Action} while {session.State} or without players.")
        };
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
