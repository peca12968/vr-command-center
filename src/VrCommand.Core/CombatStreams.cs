namespace VrCommand.Core;

public record OpenCombatStream(Guid StreamId, CombatOrigin Origin, int MissionClockVersion = 0);
public record CombatStreamView(Guid StreamId, CombatOrigin Origin, OperatorIdentity Owner, long AcceptedSequence = 0, bool Sealed = false, int MissionClockVersion = 0);
public record StreamCombatRecord(Guid StreamId, long StreamSequence, long ObservedSequence, CombatReport Report);
public record SealCombatStream(Guid StreamId, long FinalSequence);
public record StreamReceipt(Guid StreamId, long AcceptedSequence, bool Duplicate, SessionStatistics Statistics);

internal static class CombatStreamProjection
{
    internal static SessionView Apply(SessionView current, SessionEvent entry)
    {
        var actor = entry.Actor!;
        AccessPolicy.ReportCombat(actor);
        if (entry.Kind == SessionEventKind.CombatStreamOpened)
        {
            var open = entry.Read<OpenCombatStream>();
            if (open.StreamId == Guid.Empty || open.Origin == CombatOrigin.Unspecified || !Enum.IsDefined(open.Origin)
                || open.MissionClockVersion is < 0 or > 1 || (open.MissionClockVersion != 0 && entry.SchemaVersion < 7))
                throw new ArgumentException("A stream requires a non-empty ID and explicit origin.");
            if (current.State != SessionState.Preparing || current.CombatStream is not null)
                throw new InvalidOperationException("Attach one combat stream while preparing, before combat begins.");
            return current with { CombatStream = new(open.StreamId, open.Origin, actor, MissionClockVersion: open.MissionClockVersion) };
        }
        var stream = current.CombatStream ?? throw new InvalidOperationException("No combat stream is attached.");
        if (stream.Owner != actor) throw new AccessDeniedException("Combat stream belongs to another server identity.");
        if (stream.Sealed) throw new InvalidOperationException("Combat stream is sealed.");
        if (entry.Kind == SessionEventKind.CombatStreamSealed)
        {
            var seal = entry.Read<SealCombatStream>();
            if (current.State != SessionState.Ended || seal.StreamId != stream.StreamId || seal.FinalSequence != stream.AcceptedSequence)
                throw new InvalidOperationException("End the session and deliver every ordered report before sealing its final sequence.");
            return current with { CombatStream = stream with { Sealed = true } };
        }
        var record = entry.Read<StreamCombatRecord>();
        CombatLedger.Validate(record.Report);
        if (current.State == SessionState.Preparing || record.StreamId != stream.StreamId || record.Report.Origin != stream.Origin
            || record.StreamSequence != stream.AcceptedSequence + 1 || record.ObservedSequence < 1 || record.ObservedSequence > current.Sequence)
            throw new InvalidOperationException("Stream ID, origin, order or observed management sequence is invalid.");
        return current with { CombatStream = stream with { AcceptedSequence = record.StreamSequence } };
    }
}

public sealed partial class SessionManager
{
    // Read a sparse administrative view without replaying high-volume combat reports.
    public SessionView Observed(Guid id, long sequence, OperatorIdentity actor)
    {
        lock (gate)
        {
            var history = Find(id); AccessPolicy.Read(actor, history.View.RoomIds);
            if (sequence < 1 || sequence > history.View.Sequence) throw new ArgumentException("Observation is outside accepted history.");
            var low = 0; var high = history.Authority.Count - 1; SessionView? observed = null;
            while (low <= high)
            {
                var middle = low + (high - low) / 2;
                if (history.Authority[middle].Sequence <= sequence) { observed = history.Authority[middle]; low = middle + 1; }
                else high = middle - 1;
            }
            return Snapshot(observed ?? throw new InvalidOperationException("No administrative observation."));
        }
    }

    public StreamCombatRecord CombatWitness(Guid id, Guid reportId, OperatorIdentity actor)
    {
        lock (gate)
        {
            var history = Find(id); AccessPolicy.Read(actor, history.View.RoomIds);
            var entry = history.Combat.Find(reportId);
            if (entry?.Kind != SessionEventKind.StreamCombatRecorded) throw new InvalidOperationException("Deliver the matching combat report before its world frame.");
            return entry.Read<StreamCombatRecord>();
        }
    }

    // Each row remains its own durable event. Retrying a partially committed batch deduplicates its accepted prefix.
    public StreamReceipt ReportStreamBatch(Guid id, StreamCombatRecord[] records, OperatorIdentity? actor = null)
    {
        actor ??= OperatorIdentity.Internal; AccessPolicy.ReportCombat(actor);
        if (records is null || records.Length is < 1 or > 128 || records.Any(record => record is null))
            throw new ArgumentException("Send 1–128 ordered stream reports.");
        lock (gate)
        {
            StreamReceipt? receipt = null; var duplicate = true;
            foreach (var record in records) { receipt = ReportStream(id, record, actor); duplicate &= receipt.Duplicate; }
            return receipt! with { Duplicate = duplicate };
        }
    }
    public CombatStreamView OpenStream(Guid id, OpenCombatStream request, OperatorIdentity? actor = null)
    {
        ArgumentNullException.ThrowIfNull(request);
        actor ??= OperatorIdentity.Internal; AccessPolicy.ReportCombat(actor);
        lock (gate)
        {
            var history = Find(id);
            if (history.View.CombatStream is { } existing)
            {
                if (existing.StreamId != request.StreamId || existing.Origin != request.Origin || existing.Owner != actor || existing.MissionClockVersion != request.MissionClockVersion)
                    throw new InvalidOperationException("A different stream or owner is already attached.");
                return existing;
            }
            return Commit(history, SessionEvent.Create(id, history.View.Sequence + 1, SessionEventKind.CombatStreamOpened, request, actor)).CombatStream!;
        }
    }

    public StreamReceipt ReportStream(Guid id, StreamCombatRecord record, OperatorIdentity? actor = null)
    {
        ArgumentNullException.ThrowIfNull(record);
        actor ??= OperatorIdentity.Internal; AccessPolicy.ReportCombat(actor); CombatLedger.Validate(record.Report);
        lock (gate)
        {
            var history = Find(id);
            var stream = history.View.CombatStream ?? throw new InvalidOperationException("No combat stream is attached.");
            if (stream.Owner != actor) throw new AccessDeniedException("Combat stream belongs to another server identity.");
            var previous = history.Combat.Find(record.Report.ReportId);
            if (previous is not null)
            {
                if (previous.Kind != SessionEventKind.StreamCombatRecorded || previous.Read<StreamCombatRecord>() != record || previous.Actor != actor)
                    throw new InvalidOperationException("Report ID already has different stream content.");
                return new(stream.StreamId, stream.AcceptedSequence, true, Statistics(history));
            }
            Commit(history, SessionEvent.Create(id, history.View.Sequence + 1, SessionEventKind.StreamCombatRecorded, record, actor));
            var updated = Find(id);
            return new(stream.StreamId, updated.View.CombatStream!.AcceptedSequence, false, Statistics(updated));
        }
    }

    public CombatStreamView SealStream(Guid id, SealCombatStream request, OperatorIdentity? actor = null)
    {
        ArgumentNullException.ThrowIfNull(request);
        actor ??= OperatorIdentity.Internal; AccessPolicy.ReportCombat(actor);
        lock (gate)
        {
            var history = Find(id);
            var stream = history.View.CombatStream ?? throw new InvalidOperationException("No combat stream is attached.");
            if (stream.Owner != actor) throw new AccessDeniedException("Combat stream belongs to another server identity.");
            if (stream.Sealed && stream.StreamId == request.StreamId && stream.AcceptedSequence == request.FinalSequence) return stream;
            return Commit(history, SessionEvent.Create(id, history.View.Sequence + 1, SessionEventKind.CombatStreamSealed, request, actor)).CombatStream!;
        }
    }

    private static bool IsAuthority(SessionEvent entry) => entry.Kind is not (SessionEventKind.CombatRecorded or SessionEventKind.StreamCombatRecorded);
    private static SessionStatistics Statistics(History history) => history.Combat.Snapshot(history.View.Id, history.View.Sequence)
        with { PendingTelemetry = history.View.State == SessionState.Ended && history.View.CombatStream is { Sealed: false } };

    // Sparse administrative snapshots avoid replaying the entire combat log for every delayed report.
    private static SessionView? CombatBefore(SessionView? current, SessionEvent entry, List<SessionView> authority)
    {
        if (entry.Kind != SessionEventKind.StreamCombatRecorded) return current;
        var record = entry.Read<StreamCombatRecord>();
        if (current is null || record.ObservedSequence < 1 || record.ObservedSequence > current.Sequence)
            throw new InvalidOperationException("Observed sequence is not in this session's accepted history.");
        var low = 0; var high = authority.Count - 1; SessionView? observed = null;
        while (low <= high)
        {
            var middle = low + (high - low) / 2;
            if (authority[middle].Sequence <= record.ObservedSequence) { observed = authority[middle]; low = middle + 1; }
            else high = middle - 1;
        }
        if (observed?.State != SessionState.Running)
            throw new InvalidOperationException("Combat must reference a management snapshot observed while Running.");
        return observed;
    }
}
