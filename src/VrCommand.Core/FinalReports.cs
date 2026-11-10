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

public record FinalVenueSessionReport(long AppliedAtSequence, FinalSessionReport Report);
public record FinalVenueReport(Guid RequestId, DateTimeOffset RecordedAtUtc, FinalVenueSessionReport[] Sessions);
public sealed class VenueReportsNotReadyException(int[] roomIds) : InvalidOperationException("Some sessions still await their final combat reports.")
{
    public int[] RoomIds { get; } = roomIds;
}

public sealed partial class SessionManager
{
    public FinalVenueReport FinalVenueReports(Guid requestId, OperatorIdentity actor)
    {
        RequireVenueMaster(actor);
        lock (gate)
        {
            var entries = EndEntries(requestId);
            var sessions = entries.Select(entry => (Entry: entry, Session: Find(entry.SessionId).View))
                .OrderBy(item => item.Session.RoomIds[0]).ToArray();
            var waiting = sessions.Where(item => !CanExportFinalReport(item.Session)).SelectMany(item => item.Session.RoomIds).ToArray();
            if (waiting.Length > 0) throw new VenueReportsNotReadyException(waiting);
            return new(requestId, entries[0].RecordedAtUtc,
                sessions.Select(item => new FinalVenueSessionReport(item.Entry.Sequence, FinalReport(item.Session.Id, actor))).ToArray());
        }
    }

    public FinalSessionReport FinalReport(Guid id, OperatorIdentity actor) => FinalReport(id, actor, null);

    public FinalSessionReport FinalPlayerReport(Guid id, Guid playerId, OperatorIdentity actor)
    {
        var report = FinalReport(id, actor);
        var player = report.Players.SingleOrDefault(row => row.PlayerId == playerId
            && (actor.Role != OperatorRole.RoomController || row.RoomId == actor.RoomId))
            ?? throw new KeyNotFoundException("No final report for this player.");
        return report with { Players = [player] };
    }


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
            if (!CanExportFinalReport(session) || session.EndedAtUtc is not { } endedAt)
                throw new InvalidOperationException("End the session and seal all combat reports before exporting a final report.");
            var statistics = Statistics(history);
            var report = new FinalSessionReport(1, id, session.Mission.Id, session.Mission.Definition.Name, session.Mode,
                [.. session.RoomIds], session.CreatedAtUtc, session.StartedAtUtc, endedAt,
                session.Mission.Definition.DurationSeconds, statistics.ThroughSequence,
                statistics.Origin ?? session.CombatStream?.Origin, session.CombatStream?.StreamId,
                session.CombatStream?.AcceptedSequence, statistics.Players);
            return roomId is int reportRoom ? report.ForRoom(reportRoom) : report;
        }
    }

    private static bool CanExportFinalReport(SessionView session) => session.State == SessionState.Ended && session.EndedAtUtc is not null
        && session.CombatStream is not { Sealed: false };
}
