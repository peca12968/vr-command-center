namespace VrCommand.Core;

// A final combat ledger, not a claim that a world recording or physical device was verified.
public record FinalSessionReport(int ReportVersion, Guid SessionId, Guid MissionId, string MissionName,
    SessionMode Mode, int[] RoomIds, DateTimeOffset CreatedAtUtc, DateTimeOffset? StartedAtUtc,
    DateTimeOffset EndedAtUtc, int PlannedDurationSeconds, long ThroughSequence, CombatOrigin? Origin,
    Guid? StreamId, long? FinalStreamSequence, PlayerStatistics[] Players);

public sealed partial class SessionManager
{
    public FinalSessionReport FinalReport(Guid id, OperatorIdentity actor)
    {
        ArgumentNullException.ThrowIfNull(actor);
        lock (gate)
        {
            var history = Find(id);
            AccessPolicy.Read(actor, history.View.RoomIds);
            if (actor.Role == OperatorRole.GameServer)
                throw new AccessDeniedException("Final report export requires an operator identity.");
            var session = history.View;
            var statistics = Statistics(history);
            if (session.State != SessionState.Ended || session.EndedAtUtc is null || statistics.PendingTelemetry)
                throw new InvalidOperationException("End the session and seal all combat reports before exporting a final report.");
            return new(1, id, session.Mission.Id, session.Mission.Definition.Name, session.Mode,
                [.. session.RoomIds], session.CreatedAtUtc, session.StartedAtUtc, session.EndedAtUtc.Value,
                session.Mission.Definition.DurationSeconds, statistics.ThroughSequence,
                statistics.Origin ?? session.CombatStream?.Origin, session.CombatStream?.StreamId,
                session.CombatStream?.AcceptedSequence, statistics.Players);
        }
    }
}
