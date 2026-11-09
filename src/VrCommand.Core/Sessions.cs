using System.Text.Json.Serialization;

namespace VrCommand.Core;

public enum SessionMode { Independent, Linked }
public enum HeadsetKind { ViveXr, Quest3 }
public enum SessionState { Preparing, Running, Paused, Ended }
public enum ControlAction { Unspecified, Begin, Pause, Resume, End, SetEnvironment, SetEnemies, SetMissionClock, SetRoomAlignment }
public record MissionClockSettings(bool AutoEnd);
public record MissionClockStatus(int Version, bool AutoEnd, long ConfiguredAtSequence);
public record MissionClockExpiration(Guid StreamId, long ObservedSequence, long Tick);
public sealed record RoomAlignmentPins(string? Room1 = null, string? Room2 = null, string? Room3 = null, string? Room4 = null, string? Room5 = null)
{
    public string? ForRoom(int room) => room switch { 1 => Room1, 2 => Room2, 3 => Room3, 4 => Room4, 5 => Room5, _ => null };
}
public record Player(Guid Id, string Name, int RoomId, HeadsetKind Headset, int Seat = -1, Guid AdmissionId = default);
public record SessionView(Guid Id, SessionMode Mode, int[] RoomIds, Mission Mission,
    DateTimeOffset CreatedAtUtc, DateTimeOffset? StartedAtUtc, DateTimeOffset? EndedAtUtc,
    SessionState State, Player[] Players, EnvironmentSettings Environment, EnemySettings Enemies, long Sequence,
    CombatStreamView? CombatStream = null, MissionClockStatus? MissionClock = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomAlignmentPins? RoomAlignment = null);
public record RoomView(int Id, int Capacity, Guid? SessionId, int PlayerCount);
public record ControlCommand(Guid CommandId, ControlAction Action, EnvironmentSettings? Environment = null,
    EnemySettings? Enemies = null, long? ExpectedSequence = null, MissionClockSettings? MissionClock = null, MissionClockExpiration? ClockExpiration = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] RoomAlignmentPins? RoomAlignment = null);
public record CommandReceipt(Guid CommandId, long AppliedAtSequence, bool Duplicate, SessionView Session);
public sealed class MixedRealityNotReadyException(ControlAction action) : InvalidOperationException(action == ControlAction.Resume
    ? "MR resume requires a fresh paused snapshot with tracked Quest 3 poses for living players."
    : "MR start requires fresh tracked Quest 3 poses for the current roster.")
{
    public ControlAction Action { get; } = action;
}

// Management and combat telemetry; this does not simulate a 3D world or determine physical collisions.
public sealed partial class SessionManager
{
    public const int RoomCount = 5;
    public const int PlayersPerRoom = 5;
    public const int MaxPlayers = RoomCount * PlayersPerRoom;
    private readonly object gate = new();
    private readonly ISessionEventStore eventStore;
    private readonly TimeProvider clock;
    private readonly Dictionary<Guid, History> sessions = [];
    // A lifecycle request key is global across creation and roster mutations, including archived sessions.
    private readonly Dictionary<Guid, SessionEvent> requests = [];
    private sealed record History(SessionView View, List<SessionEvent> Events, Dictionary<Guid, SessionEvent> Commands, CombatLedger Combat,
        List<SessionView> Authority, long RunningSinceSequence);

    public SessionManager(ISessionEventStore? eventStore = null) : this(eventStore, TimeProvider.System) { }

    public SessionManager(ISessionEventStore? eventStore, TimeProvider clock)
    {
        this.eventStore = eventStore ?? new MemorySessionEventStore();
        this.clock = clock ?? throw new ArgumentNullException(nameof(clock));
        foreach (var events in this.eventStore.Load())
        {
            SessionView? view = null;
            var ids = new HashSet<Guid>();
            var commands = new Dictionary<Guid, SessionEvent>();
            var combat = new CombatLedger();
            var authority = new List<SessionView>();
            long runningSince = 0;
            foreach (var entry in events)
            {
                if (!ids.Add(entry.EventId)) throw new InvalidDataException("Duplicate event ID in session history.");
                if (entry.Kind == SessionEventKind.ControlApplied && !commands.TryAdd(entry.Read<ControlCommand>().CommandId, entry))
                    throw new InvalidDataException("Duplicate command ID in session history.");
                var next = SessionProjection.Apply(view, entry);
                combat.Prepare(CombatBefore(view, entry, authority), entry)();
                runningSince = RunningSince(view, next, runningSince);
                view = next;
                if (IsAuthority(entry)) authority.Add(view);
                if (entry.RequestId.HasValue && !requests.TryAdd(entry.RequestId.Value, entry))
                    throw new InvalidDataException("Duplicate lifecycle request ID in persisted histories.");
            }
            if (view is null || !sessions.TryAdd(view.Id, new(view, [.. events], commands, combat, authority, runningSince)))
                throw new InvalidDataException("Empty or duplicate session history.");
        }
        var active = Active().ToArray();
        var rooms = active.SelectMany(s => s.RoomIds).ToArray();
        var players = active.SelectMany(s => s.Players).Select(p => p.Id).ToArray();
        if (rooms.Distinct().Count() != rooms.Length || players.Distinct().Count() != players.Length)
            throw new InvalidDataException("Restored active sessions contain conflicting reservations.");
    }

    public SessionView Create(SessionMode mode, int[] roomIds, Mission mission, OperatorIdentity? actor = null, Guid? requestId = null)
    {
        actor ??= OperatorIdentity.Internal;
        SessionProjection.ValidateCreation(new(mode, roomIds, mission));
        AccessPolicy.Manage(actor, mode, roomIds);
        ValidateRequestId(requestId);
        lock (gate)
        {
            var creation = new SessionCreated(mode, roomIds.Order().ToArray(), mission);
            var previous = Request(requestId, SessionEventKind.Created, actor);
            if (previous is not null)
            {
                if (System.Text.Json.JsonSerializer.Serialize(previous.Read<SessionCreated>(), JsonFormat.Options)
                    != System.Text.Json.JsonSerializer.Serialize(creation, JsonFormat.Options))
                    throw new InvalidOperationException("Request ID already used with different content.");
                return Snapshot(Find(previous.SessionId).View);
            }
            if (Active().Any(s => s.RoomIds.Intersect(roomIds).Any()))
                throw new InvalidOperationException("A requested room is already in use.");
            // Replayed histories and confirmed historical request keys retain the
            // original acceptance. Only a genuinely new reservation uses preflight.
            MissionLayout.RequireNewStart(mission.Definition, mode);
            var id = Guid.NewGuid();
            var entry = SessionEvent.Create(id, 1, SessionEventKind.Created,
                creation, actor, requestId);
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

    public SessionView Join(Guid sessionId, Guid playerId, string name, int roomId, HeadsetKind headset, OperatorIdentity? actor = null, Guid? requestId = null)
    {
        ValidateRequestId(requestId);
        lock (gate)
        {
            var history = Find(sessionId);
            actor ??= OperatorIdentity.Internal;
            AccessPolicy.Player(actor, history.View, roomId);
            var previous = Request(requestId, SessionEventKind.PlayerJoined, actor);
            if (previous is not null)
            {
                var joined = previous.Read<Player>();
                if (previous.SessionId != sessionId || joined.Id != playerId || joined.Name != name
                    || joined.RoomId != roomId || joined.Headset != headset)
                    throw new InvalidOperationException("Request ID already used with different content.");
                return Snapshot(history.View);
            }
            if (Active().Any(s => s.Players.Any(p => p.Id == playerId)))
                throw new InvalidOperationException("Player already belongs to a session.");
            if (history.View.Environment.Mode == ExperienceMode.MR && headset != HeadsetKind.Quest3)
                throw new InvalidOperationException("MR sessions currently require Quest 3 players.");
            var seat = Enumerable.Range(0, PlayersPerRoom)
                .FirstOrDefault(candidate => !history.View.Players.Any(p => p.RoomId == roomId && p.Seat == candidate), -1);
            return Commit(history, SessionEvent.Create(sessionId, history.View.Sequence + 1,
                SessionEventKind.PlayerJoined, new Player(playerId, name, roomId, headset, seat), actor, requestId));
        }
    }

    public void Leave(Guid sessionId, Guid playerId, OperatorIdentity? actor = null, Guid? requestId = null, Guid? expectedAdmissionId = null, bool requireAdmissionMatch = false)
    {
        ValidateRequestId(requestId);
        if (expectedAdmissionId == Guid.Empty) throw new ArgumentException("Expected admission must be a non-empty UUID.");
        lock (gate)
        {
            var history = Find(sessionId);
            actor ??= OperatorIdentity.Internal;
            AccessPolicy.Read(actor, history.View.RoomIds);
            var previous = Request(requestId, SessionEventKind.PlayerLeft, actor);
            if (previous is not null)
            {
                var left = previous.Read<PlayerLeft>();
                if (previous.SessionId != sessionId || left.PlayerId != playerId || left.ExpectedAdmissionId != expectedAdmissionId)
                    throw new InvalidOperationException("Request ID already used with different content.");
                AccessPolicy.Player(actor, history.View, left.RoomId!.Value);
                return;
            }
            var player = history.View.Players.SingleOrDefault(p => p.Id == playerId)
                ?? throw new KeyNotFoundException("Player does not exist.");
            AccessPolicy.Player(actor, history.View, player.RoomId);
            if (requireAdmissionMatch && !expectedAdmissionId.HasValue)
                throw new ArgumentException("If-Match-Admission is required; reload the current roster before removing a player.");
            if (expectedAdmissionId.HasValue && expectedAdmissionId != player.AdmissionId)
                throw new InvalidOperationException("Player admission changed; reload the current roster.");
            Commit(history, SessionEvent.Create(sessionId, history.View.Sequence + 1,
                SessionEventKind.PlayerLeft, new PlayerLeft(playerId, player.RoomId, player.AdmissionId, expectedAdmissionId), actor, requestId));
        }
    }

    public CommandReceipt Execute(Guid id, ControlCommand command, OperatorIdentity? actor = null, long? readyMrSequence = null)
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
            if (command.Environment is { } environment && environment.Mode != history.View.Environment.Mode)
                throw new InvalidOperationException("Experience mode is fixed when a session is created.");
            if (command.Enemies is { } enemies && enemies.Count > history.View.Enemies.Count)
                MissionLayout.RequireEnemyCapacity(history.View, enemies.Count);
            if (RequiresMrReadiness(history.View, command.Action)
                && (readyMrSequence != history.View.Sequence || history.View.CombatStream?.Origin != CombatOrigin.GameServer
                    || history.View.Players.Any(player => player.Headset != HeadsetKind.Quest3)))
                throw new MixedRealityNotReadyException(command.Action);
            var entry = SessionEvent.Create(id, history.View.Sequence + 1, SessionEventKind.ControlApplied, command, actor);
            var updated = Commit(history, entry);
            return new(command.CommandId, entry.Sequence, false, updated);
        }
    }

    public static bool RequiresMrReadiness(SessionView session, ControlAction action) =>
        session.Environment.Mode == ExperienceMode.MR && (action, session.State) is
            (ControlAction.Begin, SessionState.Preparing) or (ControlAction.Resume, SessionState.Paused);

    public void End(Guid id, OperatorIdentity? actor = null) => Execute(id, new(Guid.NewGuid(), ControlAction.End), actor);

    public SessionStatistics Statistics(Guid id, OperatorIdentity? actor = null)
    {
        lock (gate)
        {
            var history = Find(id);
            AccessPolicy.Read(actor ?? OperatorIdentity.Internal, history.View.RoomIds);
            return Statistics(history);
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
            if (history.View.CombatStream is not null) throw new InvalidOperationException("Use the bound ordered combat stream for this session.");
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
        var authority = previous?.Authority ?? [];
        var applyCombat = combat.Prepare(CombatBefore(previous?.View, entry, authority), entry);
        eventStore.Append(entry); // Memory advances only after the durable append succeeds.
        applyCombat();
        var events = previous?.Events ?? [];
        var commands = previous?.Commands ?? [];
        events.Add(entry);
        if (entry.Kind == SessionEventKind.ControlApplied) commands.Add(entry.Read<ControlCommand>().CommandId, entry);
        if (IsAuthority(entry)) authority.Add(view);
        sessions[entry.SessionId] = new(view, events, commands, combat, authority,
            RunningSince(previous?.View, view, previous?.RunningSinceSequence ?? 0));
        if (entry.RequestId.HasValue) requests.Add(entry.RequestId.Value, entry);
        return Snapshot(view);
    }

    private static long RunningSince(SessionView? previous, SessionView current, long runningSince) => current.State != SessionState.Running
        ? 0 : previous?.State == SessionState.Running ? runningSince : current.Sequence;

    private static void ValidateRequestId(Guid? requestId)
    {
        if (requestId == Guid.Empty) throw new ArgumentException("Request ID must be a non-empty UUID.");
    }

    private SessionEvent? Request(Guid? requestId, SessionEventKind kind, OperatorIdentity actor)
    {
        if (!requestId.HasValue || !requests.TryGetValue(requestId.Value, out var previous)) return null;
        if (previous.Kind != kind || previous.Actor != actor)
            throw new InvalidOperationException("Request ID already used for another operation or identity.");
        return previous;
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
