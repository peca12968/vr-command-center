namespace VrCommand.Core;

public enum SessionMode { Independent, Linked }
public enum HeadsetKind { ViveXr, Quest3 }
public enum SessionState { Preparing, Running, Paused, Ended }
public enum ControlAction { Unspecified, Begin, Pause, Resume, End, SetEnvironment, SetEnemies }
public record Player(Guid Id, string Name, int RoomId, HeadsetKind Headset);
public record SessionView(Guid Id, SessionMode Mode, int[] RoomIds, Mission Mission,
    DateTimeOffset CreatedAtUtc, DateTimeOffset? StartedAtUtc, DateTimeOffset? EndedAtUtc,
    SessionState State, Player[] Players, EnvironmentSettings Environment, EnemySettings Enemies, long Sequence);
public record RoomView(int Id, int Capacity, Guid? SessionId, int PlayerCount);
public record ControlCommand(Guid CommandId, ControlAction Action, EnvironmentSettings? Environment = null,
    EnemySettings? Enemies = null, long? ExpectedSequence = null);
public record CommandReceipt(Guid CommandId, long AppliedAtSequence, bool Duplicate, SessionView Session);

// Control-plane only. Management events do not contain a 3D world or combat simulation.
public sealed class SessionManager
{
    public const int RoomCount = 5;
    public const int PlayersPerRoom = 5;
    public const int MaxPlayers = RoomCount * PlayersPerRoom;
    private readonly object gate = new();
    private readonly ISessionEventStore eventStore;
    private readonly Dictionary<Guid, History> sessions = [];
    private sealed record History(SessionView View, SessionEvent[] Events);

    public SessionManager(ISessionEventStore? eventStore = null)
    {
        this.eventStore = eventStore ?? new MemorySessionEventStore();
        foreach (var events in this.eventStore.Load())
        {
            SessionView? view = null;
            var ids = new HashSet<Guid>();
            var commands = new HashSet<Guid>();
            foreach (var entry in events)
            {
                if (!ids.Add(entry.EventId)) throw new InvalidDataException("Duplicate event ID in session history.");
                if (entry.Kind == SessionEventKind.ControlApplied && !commands.Add(entry.Read<ControlCommand>().CommandId))
                    throw new InvalidDataException("Duplicate command ID in session history.");
                view = SessionProjection.Apply(view, entry);
            }
            if (view is null || !sessions.TryAdd(view.Id, new(view, events)))
                throw new InvalidDataException("Empty or duplicate session history.");
        }
        var active = Active().ToArray();
        var rooms = active.SelectMany(s => s.RoomIds).ToArray();
        var players = active.SelectMany(s => s.Players).Select(p => p.Id).ToArray();
        if (rooms.Distinct().Count() != rooms.Length || players.Distinct().Count() != players.Length)
            throw new InvalidDataException("Restored active sessions contain conflicting reservations.");
    }

    public SessionView Create(SessionMode mode, int[] roomIds, Mission mission)
    {
        SessionProjection.ValidateCreation(new(mode, roomIds, mission));
        lock (gate)
        {
            if (Active().Any(s => s.RoomIds.Intersect(roomIds).Any()))
                throw new InvalidOperationException("A requested room is already in use.");
            var id = Guid.NewGuid();
            var entry = SessionEvent.Create(id, 1, SessionEventKind.Created,
                new SessionCreated(mode, roomIds.Order().ToArray(), mission));
            return Commit(null, entry);
        }
    }

    public SessionView Get(Guid id)
    {
        lock (gate) return Snapshot(Find(id).View);
    }

    public SessionView[] List(bool includeEnded = false)
    {
        lock (gate) return sessions.Values.Select(h => h.View)
            .Where(s => includeEnded || s.State != SessionState.Ended)
            .OrderByDescending(s => s.CreatedAtUtc).Select(Snapshot).ToArray();
    }

    public SessionEvent[] Events(Guid id, long after = 0, int limit = 100)
    {
        if (after < 0 || limit is < 1 or > 500) throw new ArgumentException("Use after >= 0 and limit 1–500.");
        lock (gate) return Find(id).Events.Where(e => e.Sequence > after).Take(limit).ToArray();
    }

    public SessionView Join(Guid sessionId, Guid playerId, string name, int roomId, HeadsetKind headset)
    {
        lock (gate)
        {
            var history = Find(sessionId);
            if (Active().Any(s => s.Players.Any(p => p.Id == playerId)))
                throw new InvalidOperationException("Player already belongs to a session.");
            return Commit(history, SessionEvent.Create(sessionId, history.View.Sequence + 1,
                SessionEventKind.PlayerJoined, new Player(playerId, name, roomId, headset)));
        }
    }

    public void Leave(Guid sessionId, Guid playerId)
    {
        lock (gate)
        {
            var history = Find(sessionId);
            Commit(history, SessionEvent.Create(sessionId, history.View.Sequence + 1,
                SessionEventKind.PlayerLeft, new PlayerLeft(playerId)));
        }
    }

    public CommandReceipt Execute(Guid id, ControlCommand command)
    {
        ArgumentNullException.ThrowIfNull(command);
        SessionProjection.ValidateCommand(command);
        lock (gate)
        {
            var history = Find(id);
            var previous = history.Events.FirstOrDefault(e => e.Kind == SessionEventKind.ControlApplied
                && e.Read<ControlCommand>().CommandId == command.CommandId);
            if (previous is not null)
            {
                if (previous.Read<ControlCommand>() != command)
                    throw new InvalidOperationException("Command ID already used with different content.");
                return new(command.CommandId, previous.Sequence, true, Snapshot(history.View));
            }
            if (command.ExpectedSequence.HasValue && command.ExpectedSequence != history.View.Sequence)
                throw new InvalidOperationException("Session changed; refresh before issuing this command.");
            var entry = SessionEvent.Create(id, history.View.Sequence + 1, SessionEventKind.ControlApplied, command);
            var updated = Commit(history, entry);
            return new(command.CommandId, entry.Sequence, false, updated);
        }
    }

    public void End(Guid id) => Execute(id, new(Guid.NewGuid(), ControlAction.End));

    public RoomView[] Rooms()
    {
        lock (gate) return Enumerable.Range(1, RoomCount).Select(id =>
        {
            var session = Active().SingleOrDefault(s => s.RoomIds.Contains(id));
            return new RoomView(id, PlayersPerRoom, session?.Id, session?.Players.Count(p => p.RoomId == id) ?? 0);
        }).ToArray();
    }

    private SessionView Commit(History? previous, SessionEvent entry)
    {
        var view = SessionProjection.Apply(previous?.View, entry);
        SessionEvent[] events = [.. previous?.Events ?? [], entry];
        eventStore.Save(entry.SessionId, events); // Memory advances only after the durable write succeeds.
        sessions[entry.SessionId] = new(view, events);
        return Snapshot(view);
    }

    private IEnumerable<SessionView> Active() => sessions.Values.Select(h => h.View).Where(s => s.State != SessionState.Ended);
    private History Find(Guid id) => sessions.TryGetValue(id, out var history)
        ? history : throw new KeyNotFoundException("Session does not exist.");
    private static SessionView Snapshot(SessionView session) => session with
    {
        RoomIds = [.. session.RoomIds], Players = [.. session.Players],
        Mission = session.Mission with { Definition = session.Mission.Definition with { Props = [.. session.Mission.Definition.Props] } }
    };
}
