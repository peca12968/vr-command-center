namespace VrCommand.Core;

public enum SessionMode { Independent, Linked }
public enum HeadsetKind { ViveXr, Quest3 }
public record Player(Guid Id, string Name, int RoomId, HeadsetKind Headset);
public record SessionView(Guid Id, SessionMode Mode, int[] RoomIds, Mission Mission,
    DateTimeOffset StartedAtUtc, Player[] Players);
public record RoomView(int Id, int Capacity, Guid? SessionId, int PlayerCount);

// Control-plane prototype only. This does not run a combat simulation or track physical presence.
public sealed class SessionManager
{
    public const int RoomCount = 5;
    public const int PlayersPerRoom = 5;
    public const int MaxPlayers = RoomCount * PlayersPerRoom;
    private readonly object gate = new();
    private readonly Dictionary<Guid, SessionView> sessions = [];

    public SessionView Start(SessionMode mode, int[] roomIds, Mission mission)
    {
        ArgumentNullException.ThrowIfNull(roomIds);
        ArgumentNullException.ThrowIfNull(mission);
        MissionStore.Validate(mission.Definition);
        if (!Enum.IsDefined(mode)) throw new ArgumentException("Invalid session mode.");
        var expected = mode == SessionMode.Independent ? 1 : RoomCount;
        if (roomIds.Length != expected || roomIds.Distinct().Count() != expected
            || roomIds.Any(id => id < 1 || id > RoomCount))
            throw new ArgumentException("Independent mode requires one room; linked mode requires rooms 1–5.");
        lock (gate)
        {
            if (sessions.Values.Any(s => s.RoomIds.Intersect(roomIds).Any()))
                throw new InvalidOperationException("A requested room is already in use.");
            var session = new SessionView(Guid.NewGuid(), mode, roomIds.Order().ToArray(),
                CloneMission(mission), DateTimeOffset.UtcNow, []);
            sessions.Add(session.Id, session);
            return Snapshot(session);
        }
    }

    public SessionView Get(Guid id)
    {
        lock (gate) return Snapshot(Find(id));
    }

    public SessionView Join(Guid sessionId, Guid playerId, string name, int roomId, HeadsetKind headset)
    {
        if (playerId == Guid.Empty || string.IsNullOrWhiteSpace(name) || name.Length > 80
            || !Enum.IsDefined(headset)) throw new ArgumentException("Invalid player details.");
        lock (gate)
        {
            var session = Find(sessionId);
            if (!session.RoomIds.Contains(roomId)) throw new ArgumentException("Room is outside this session.");
            if (sessions.Values.Any(s => s.Players.Any(p => p.Id == playerId)))
                throw new InvalidOperationException("Player already belongs to a session.");
            if (session.Players.Count(p => p.RoomId == roomId) >= PlayersPerRoom
                || sessions.Values.Sum(s => s.Players.Length) >= MaxPlayers)
                throw new InvalidOperationException("Player capacity reached.");
            var updated = session with { Players = [.. session.Players, new(playerId, name, roomId, headset)] };
            sessions[sessionId] = updated;
            return Snapshot(updated);
        }
    }

    public void Leave(Guid sessionId, Guid playerId)
    {
        lock (gate)
        {
            var session = Find(sessionId);
            if (!session.Players.Any(p => p.Id == playerId)) throw new KeyNotFoundException("Player does not exist.");
            sessions[sessionId] = session with { Players = session.Players.Where(p => p.Id != playerId).ToArray() };
        }
    }

    public void End(Guid id)
    {
        lock (gate)
        {
            Find(id);
            sessions.Remove(id);
        }
    }

    public RoomView[] Rooms()
    {
        lock (gate)
        {
            return Enumerable.Range(1, RoomCount).Select(id =>
            {
                var session = sessions.Values.SingleOrDefault(s => s.RoomIds.Contains(id));
                return new RoomView(id, PlayersPerRoom, session?.Id, session?.Players.Count(p => p.RoomId == id) ?? 0);
            }).ToArray();
        }
    }

    private SessionView Find(Guid id) => sessions.TryGetValue(id, out var session)
        ? session : throw new KeyNotFoundException("Session does not exist.");
    private static Mission CloneMission(Mission mission) => mission with
    {
        Definition = mission.Definition with { Props = [.. mission.Definition.Props] }
    };
    private static SessionView Snapshot(SessionView session) => session with
    {
        RoomIds = [.. session.RoomIds], Players = [.. session.Players], Mission = CloneMission(session.Mission)
    };
}
