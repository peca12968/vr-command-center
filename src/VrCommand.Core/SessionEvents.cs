using System.Text.Json;

namespace VrCommand.Core;

public enum SessionEventKind { Created, PlayerJoined, PlayerLeft, ControlApplied }
public record SessionCreated(SessionMode Mode, int[] RoomIds, Mission Mission);
public record PlayerLeft(Guid PlayerId);
public record SessionEvent(int SchemaVersion, Guid EventId, Guid SessionId, long Sequence,
    DateTimeOffset RecordedAtUtc, SessionEventKind Kind, JsonElement Payload)
{
    public T Read<T>() => Payload.Deserialize<T>(JsonFormat.Options)
        ?? throw new InvalidDataException("Missing event payload.");
    internal static SessionEvent Create<T>(Guid id, long sequence, SessionEventKind kind, T payload) =>
        new(1, Guid.NewGuid(), id, sequence, DateTimeOffset.UtcNow, kind,
            JsonSerializer.SerializeToElement(payload, JsonFormat.Options));
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
    }

    internal static SessionView Apply(SessionView? current, SessionEvent entry)
    {
        if (entry.SchemaVersion != 1 || entry.EventId == Guid.Empty || entry.SessionId == Guid.Empty
            || entry.Sequence != (current?.Sequence ?? 0) + 1 || !Enum.IsDefined(entry.Kind)
            || entry.RecordedAtUtc == default || entry.RecordedAtUtc.Offset != TimeSpan.Zero
            || (current is not null && current.Id != entry.SessionId))
            throw new InvalidDataException("Unsupported or inconsistent event envelope.");
        if (current is null)
        {
            if (entry.Kind != SessionEventKind.Created) throw new InvalidDataException("History must begin with Created.");
            var created = entry.Read<SessionCreated>();
            ValidateCreation(created);
            return new(entry.SessionId, created.Mode, created.RoomIds, created.Mission,
                entry.RecordedAtUtc, null, null, SessionState.Preparing, [],
                created.Mission.Definition.Environment, created.Mission.Definition.Enemies, entry.Sequence);
        }
        if (current.State == SessionState.Ended) throw new InvalidOperationException("Session has ended.");
        var updated = entry.Kind switch
        {
            SessionEventKind.PlayerJoined => Join(current, entry.Read<Player>()),
            SessionEventKind.PlayerLeft => Leave(current, entry.Read<PlayerLeft>().PlayerId),
            SessionEventKind.ControlApplied => Control(current, entry.Read<ControlCommand>(), entry.RecordedAtUtc),
            _ => throw new InvalidDataException("Unexpected event kind.")
        };
        return updated with { Sequence = entry.Sequence };
    }

    private static SessionView Join(SessionView session, Player player)
    {
        if (player.Id == Guid.Empty || string.IsNullOrWhiteSpace(player.Name) || player.Name.Length > 80
            || !Enum.IsDefined(player.Headset)) throw new ArgumentException("Invalid player details.");
        if (session.State != SessionState.Preparing) throw new InvalidOperationException("Players may join only while preparing.");
        if (!session.RoomIds.Contains(player.RoomId)) throw new ArgumentException("Room is outside this session.");
        if (session.Players.Any(p => p.Id == player.Id)) throw new InvalidOperationException("Player already joined.");
        if (session.Players.Count(p => p.RoomId == player.RoomId) >= SessionManager.PlayersPerRoom)
            throw new InvalidOperationException("Player capacity reached.");
        return session with { Players = [.. session.Players, player] };
    }

    private static SessionView Leave(SessionView session, Guid playerId)
    {
        if (!session.Players.Any(p => p.Id == playerId)) throw new KeyNotFoundException("Player does not exist.");
        return session with { Players = session.Players.Where(p => p.Id != playerId).ToArray() };
    }

    private static SessionView Control(SessionView session, ControlCommand command, DateTimeOffset now)
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
            _ => throw new InvalidOperationException($"Cannot apply {command.Action} while {session.State} or without players.")
        };
    }
}
