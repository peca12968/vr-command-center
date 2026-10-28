namespace VrCommand.Core;

public enum SessionMode { Independent, Linked }
public enum HeadsetKind { ViveXr, Quest3 }
public enum SessionState { Preparing, Running, Paused, Ended }
public enum ControlAction { Unspecified, Begin, Pause, Resume, End, SetEnvironment, SetEnemies }
public record Player(Guid Id, string Name, int RoomId, HeadsetKind Headset, int Seat = -1);
public record SessionView(Guid Id, SessionMode Mode, int[] RoomIds, Mission Mission,
    DateTimeOffset CreatedAtUtc, DateTimeOffset? StartedAtUtc, DateTimeOffset? EndedAtUtc,
    SessionState State, Player[] Players, EnvironmentSettings Environment, EnemySettings Enemies, long Sequence);
public record RoomView(int Id, int Capacity, Guid? SessionId, int PlayerCount);
public record ControlCommand(Guid CommandId, ControlAction Action, EnvironmentSettings? Environment = null,
    EnemySettings? Enemies = null, long? ExpectedSequence = null);
public record CommandReceipt(Guid CommandId, long AppliedAtSequence, bool Duplicate, SessionView Session);

// Management and combat telemetry; this does not simulate a 3D world or determine physical collisions.
public sealed class SessionManager
{
    public const int RoomCount = 5;
    public const int PlayersPerRoom = 5;
    public const int MaxPlayers = RoomCount * PlayersPerRoom;
    private readonly object gate = new();
    private readonly ISessionEventStore eventStore;
    private readonly Dictionary<Guid, History> sessions = [];
    private sealed record History(SessionView View, List<SessionEvent> Events, Dictionary<Guid, SessionEvent> Commands, CombatLedger Combat);

    public SessionManager(ISessionEventStore? eventStore = null)
    {
        this.eventStore = eventStore ?? new MemorySessionEventStore();
        foreach (var events in this.eventStore.Load())
        {
            SessionView? view = null;
            var ids = new HashSet<Guid>();
            var commands = new Dictionary<Guid, SessionEvent>();
            var combat = new CombatLedger();
            foreach (var entry in events)
            {
                if (!ids.Add(entry.EventId)) throw new InvalidDataException("Duplicate event ID in session history.");
                if (entry.Kind == SessionEventKind.ControlApplied && !commands.TryAdd(entry.Read<ControlCommand>().CommandId, entry))
                    throw new InvalidDataException("Duplicate command ID in session history.");
                var next = SessionProjection.Apply(view, entry);
                combat.Prepare(view, entry)();
                view = next;
            }
            if (view is null || !sessions.TryAdd(view.Id, new(view, [.. events], commands, combat)))
                throw new InvalidDataException("Empty or duplicate session history.");
        }
        var active = Active().ToArray();
        var rooms = active.SelectMany(s => s.RoomIds).ToArray();
        var players = active.SelectMany(s => s.Players).Select(p => p.Id).ToArray();
        if (rooms.Distinct().Count() != rooms.Length || players.Distinct().Count() != players.Length)
            throw new InvalidDataException("Restored active sessions contain conflicting reservations.");
    }

    public SessionView Create(SessionMode mode, int[] roomIds, Mission mission, OperatorIdentity? actor = null)
    {
        actor ??= OperatorIdentity.Internal;
        SessionProjection.ValidateCreation(new(mode, roomIds, mission));
        AccessPolicy.Manage(actor, mode, roomIds);
        lock (gate)
        {
            if (Active().Any(s => s.RoomIds.Intersect(roomIds).Any()))
                throw new InvalidOperationException("A requested room is already in use.");
            var id = Guid.NewGuid();
            var entry = SessionEvent.Create(id, 1, SessionEventKind.Created,
                new SessionCreated(mode, roomIds.Order().ToArray(), mission), actor);
            return Commit(null, entry);
        }
    }

    public SessionView Get(Guid id, OperatorIdentity? actor = null)
    {
        lock (gate)
        {
            var view = Find(id).View;
            AccessPolicy.Read(actor ?? OperatorIdentity.Internal, view.RoomIds);
            return Snapshot(view);
        }
    }

    public SessionView[] List(bool includeEnded = false, OperatorIdentity? actor = null)
    {
        lock (gate) return sessions.Values.Select(h => h.View)
            .Where(s => includeEnded || s.State != SessionState.Ended)
            .Where(s => AccessPolicy.CanRead(actor ?? OperatorIdentity.Internal, s.RoomIds))
            .OrderByDescending(s => s.CreatedAtUtc).Select(Snapshot).ToArray();
    }

    public SessionEvent[] Events(Guid id, long after = 0, int limit = 100, OperatorIdentity? actor = null)
    {
        if (after < 0 || limit is < 1 or > 500) throw new ArgumentException("Use after >= 0 and limit 1–500.");
        lock (gate)
        {
            var history = Find(id);
            AccessPolicy.Read(actor ?? OperatorIdentity.Internal, history.View.RoomIds);
            var start = (int)Math.Min(after, history.Events.Count);
            return history.Events.GetRange(start, Math.Min(limit, history.Events.Count - start)).ToArray();
        }
    }

    public SessionView Join(Guid sessionId, Guid playerId, string name, int roomId, HeadsetKind headset, OperatorIdentity? actor = null)
    {
        lock (gate)
        {
            var history = Find(sessionId);
            actor ??= OperatorIdentity.Internal;
            AccessPolicy.Player(actor, history.View, roomId);
            if (Active().Any(s => s.Players.Any(p => p.Id == playerId)))
                throw new InvalidOperationException("Player already belongs to a session.");
            var seat = Enumerable.Range(0, PlayersPerRoom)
                .FirstOrDefault(candidate => !history.View.Players.Any(p => p.RoomId == roomId && p.Seat == candidate), -1);
            return Commit(history, SessionEvent.Create(sessionId, history.View.Sequence + 1,
                SessionEventKind.PlayerJoined, new Player(playerId, name, roomId, headset, seat), actor));
        }
    }

    public void Leave(Guid sessionId, Guid playerId, OperatorIdentity? actor = null)
    {
        lock (gate)
        {
            var history = Find(sessionId);
            actor ??= OperatorIdentity.Internal;
            AccessPolicy.Read(actor, history.View.RoomIds);
            var player = history.View.Players.SingleOrDefault(p => p.Id == playerId)
                ?? throw new KeyNotFoundException("Player does not exist.");
            AccessPolicy.Player(actor, history.View, player.RoomId);
            Commit(history, SessionEvent.Create(sessionId, history.View.Sequence + 1,
                SessionEventKind.PlayerLeft, new PlayerLeft(playerId), actor));
        }
    }

    public CommandReceipt Execute(Guid id, ControlCommand command, OperatorIdentity? actor = null)
    {
        ArgumentNullException.ThrowIfNull(command);
        SessionProjection.ValidateCommand(command);
        lock (gate)
        {
            var history = Find(id);
            actor ??= OperatorIdentity.Internal;
            AccessPolicy.Manage(actor, history.View.Mode, history.View.RoomIds);
            if (history.Commands.TryGetValue(command.CommandId, out var previous))
            {
                if (previous.Read<ControlCommand>() != command || (previous.Actor ?? OperatorIdentity.Internal) != actor)
                    throw new InvalidOperationException("Command ID already used with different content.");
                return new(command.CommandId, previous.Sequence, true, Snapshot(history.View));
            }
            if (command.ExpectedSequence.HasValue && command.ExpectedSequence != history.View.Sequence)
                throw new InvalidOperationException("Session changed; refresh before issuing this command.");
            var entry = SessionEvent.Create(id, history.View.Sequence + 1, SessionEventKind.ControlApplied, command, actor);
            var updated = Commit(history, entry);
            return new(command.CommandId, entry.Sequence, false, updated);
        }
    }

    public void End(Guid id, OperatorIdentity? actor = null) => Execute(id, new(Guid.NewGuid(), ControlAction.End), actor);

    public SessionStatistics Statistics(Guid id, OperatorIdentity? actor = null)
    {
        lock (gate)
        {
            var history = Find(id);
            AccessPolicy.Read(actor ?? OperatorIdentity.Internal, history.View.RoomIds);
            return history.Combat.Snapshot(id, history.View.Sequence);
        }
    }

    public CombatReceipt ReportCombat(Guid id, CombatReport report, OperatorIdentity? actor = null)
    {
        actor ??= OperatorIdentity.Internal;
        AccessPolicy.ReportCombat(actor);
        CombatLedger.Validate(report);
        lock (gate)
        {
            var history = Find(id);
            var previous = history.Combat.Find(report.ReportId);
            if (previous is not null)
            {
                if (previous.Read<CombatReport>() != report || previous.Actor != actor)
                    throw new InvalidOperationException("Report ID already used with different content or source identity.");
                return new(report.ReportId, previous.Sequence, true, history.Combat.Snapshot(id, history.View.Sequence));
            }
            var entry = SessionEvent.Create(id, history.View.Sequence + 1, SessionEventKind.CombatRecorded, report, actor);
            Commit(history, entry);
            return new(report.ReportId, entry.Sequence, false, history.Combat.Snapshot(id, entry.Sequence));
        }
    }

    public RoomView[] Rooms(OperatorIdentity? actor = null)
    {
        lock (gate) return Enumerable.Range(1, RoomCount)
            .Where(id => AccessPolicy.CanRead(actor ?? OperatorIdentity.Internal, [id])).Select(id =>
        {
            var session = Active().SingleOrDefault(s => s.RoomIds.Contains(id));
            return new RoomView(id, PlayersPerRoom, session?.Id, session?.Players.Count(p => p.RoomId == id) ?? 0);
        }).ToArray();
    }

    private SessionView Commit(History? previous, SessionEvent entry)
    {
        var view = SessionProjection.Apply(previous?.View, entry);
        var combat = previous?.Combat ?? new CombatLedger();
        var applyCombat = combat.Prepare(previous?.View, entry);
        eventStore.Append(entry); // Memory advances only after the durable append succeeds.
        applyCombat();
        var events = previous?.Events ?? [];
        var commands = previous?.Commands ?? [];
        events.Add(entry);
        if (entry.Kind == SessionEventKind.ControlApplied) commands.Add(entry.Read<ControlCommand>().CommandId, entry);
        sessions[entry.SessionId] = new(view, events, commands, combat);
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
