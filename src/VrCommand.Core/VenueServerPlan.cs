namespace VrCommand.Core;

public record VenueServerPlanRoom(int RoomId, Guid? SessionId, long? SessionSequence,
    Guid? MissionId, string? MissionName, ExperienceMode? ExperienceMode, string State);
public record VenueServerPlan(SessionMode? Topology, bool Ready, VenueServerPlanRoom[] Rooms);

public sealed partial class SessionManager
{
    public Dictionary<Guid, SessionView> ReadVenueLaunchSessions(Guid[] sessionIds, OperatorIdentity actor)
    {
        RequireVenueMaster(actor);
        lock (gate)
        {
            var result = new Dictionary<Guid, SessionView>();
            foreach (var id in sessionIds)
                if (sessions.TryGetValue(id, out var history)) result.Add(id, Snapshot(history.View));
            return result;
        }
    }

    public VenueServerPlan ReadVenueServerPlan(OperatorIdentity actor)
    {
        RequireVenueMaster(actor);
        var active = List(false, actor);
        var rooms = Enumerable.Range(1, RoomCount).Select(roomId =>
        {
            var session = active.SingleOrDefault(candidate => candidate.RoomIds.Contains(roomId));
            if (session is null) return new VenueServerPlanRoom(roomId, null, null, null, null, null, "missing-session");
            var state = session.State != SessionState.Preparing ? "not-preparing"
                : session.CombatStream is not null ? "source-bound"
                : session.Environment.Mode == ExperienceMode.MR && session.RoomAlignment?.ForRoom(roomId) is null ? "alignment-unlocked"
                : "ready";
            return new VenueServerPlanRoom(roomId, session.Id, session.Sequence, session.Mission.Id,
                session.Mission.Definition.Name, session.Environment.Mode, state);
        }).ToArray();
        SessionMode? topology = null;
        if (rooms.All(room => room.SessionId.HasValue))
        {
            if (active.Length == RoomCount && active.All(session => session.Mode == SessionMode.Independent))
                topology = SessionMode.Independent;
            else if (active is [{ Mode: SessionMode.Linked }])
                topology = SessionMode.Linked;
        }
        return new(topology, topology.HasValue && rooms.All(room => room.State == "ready"), rooms);
    }
}
