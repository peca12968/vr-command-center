namespace VrCommand.Core;

// A final combat ledger, not a claim that a world recording or physical device was verified.
public record FinalSessionReport(int ReportVersion, Guid SessionId, Guid MissionId, string MissionName,
    SessionMode Mode, int[] RoomIds, DateTimeOffset CreatedAtUtc, DateTimeOffset? StartedAtUtc,
    DateTimeOffset EndedAtUtc, int PlannedDurationSeconds, long ThroughSequence, CombatOrigin? Origin,
    Guid? StreamId, long? FinalStreamSequence, PlayerStatistics[] Players)
{
    public int? ReportRoomId { get; init; }

    public FinalSessionReport ForRoom(int roomId)
    {
        if (!RoomIds.Contains(roomId)) throw new ArgumentException("Report room is outside the session.");
        return this with { ReportRoomId = roomId, Players = Players.Where(player => player.RoomId == roomId).ToArray() };
    }
}

public sealed partial class SessionManager
{
    public FinalSessionReport FinalReport(Guid id, OperatorIdentity actor) => FinalReport(id, actor, null);

    public FinalSessionReport FinalReport(Guid id, OperatorIdentity actor, int? roomId)
    {
        ArgumentNullException.ThrowIfNull(actor);
        lock (gate)
        {
            var history = Find(id);
            AccessPolicy.Read(actor, history.View.RoomIds);
            if (actor.Role == OperatorRole.GameServer)
                throw new AccessDeniedException("Final report export requires an operator identity.");
            var session = history.View;
            if (roomId is int room)
            {
                if (room is < 1 or > RoomCount) throw new ArgumentException("Invalid report room.");
                AccessPolicy.Read(actor, [room]);
                if (!session.RoomIds.Contains(room)) throw new ArgumentException("Report room is outside the session.");
            }
            var statistics = Statistics(history);
            if (session.State != SessionState.Ended || session.EndedAtUtc is null || statistics.PendingTelemetry)
                throw new InvalidOperationException("End the session and seal all combat reports before exporting a final report.");
            var report = new FinalSessionReport(1, id, session.Mission.Id, session.Mission.Definition.Name, session.Mode,
                [.. session.RoomIds], session.CreatedAtUtc, session.StartedAtUtc, session.EndedAtUtc.Value,
                session.Mission.Definition.DurationSeconds, statistics.ThroughSequence,
                statistics.Origin ?? session.CombatStream?.Origin, session.CombatStream?.StreamId,
                session.CombatStream?.AcceptedSequence, statistics.Players);
            return roomId is int reportRoom ? report.ForRoom(reportRoom) : report;
        }
    }
}
