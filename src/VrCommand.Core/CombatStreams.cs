using System.Text.Json.Serialization;

namespace VrCommand.Core;

public record OpenCombatStream(Guid StreamId, CombatOrigin Origin, int MissionClockVersion = 0,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)] int RoomEnemyPolicyVersion = 0,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? ExpectedSequence = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? VenueLaunchId = null);
public record CombatStreamView(Guid StreamId, CombatOrigin Origin, OperatorIdentity Owner, long AcceptedSequence = 0, bool Sealed = false, int MissionClockVersion = 0,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)] int RoomEnemyPolicyVersion = 0,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] long? ExpectedSequence = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? VenueLaunchId = null);
public record VenueStreamCandidate(Guid SessionId, Guid StreamId, CombatOrigin Origin, long ExpectedSequence);
public record VenueStreamBatch(int Version, Guid LaunchId, SessionMode Topology, VenueStreamCandidate[] Servers);
public record VenueStreamSource(Guid SessionId, CombatStreamView Stream);
public record VenueStreamBatchReceipt(int Version, Guid LaunchId, SessionMode Topology, VenueStreamSource[] Servers);
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
                || open.MissionClockVersion is < 0 or > 1 || open.RoomEnemyPolicyVersion is < 0 or > 1
                || (open.VenueLaunchId.HasValue && (open.VenueLaunchId == Guid.Empty || open.ExpectedSequence is null or < 1))
                || ((open.MissionClockVersion != 0 || open.RoomEnemyPolicyVersion != 0 || open.ExpectedSequence.HasValue) && entry.SchemaVersion < 7))
                throw new ArgumentException("A stream requires a non-empty ID and explicit origin.");
            if (current.State != SessionState.Preparing || current.CombatStream is not null)
                throw new InvalidOperationException("Attach one combat stream while preparing, before combat begins.");
            if (open.ExpectedSequence is long expected && expected != current.Sequence)
                throw new InvalidOperationException("Session changed after the launch plan was reviewed.");
            return current with { CombatStream = new(open.StreamId, open.Origin, actor, MissionClockVersion: open.MissionClockVersion,
                RoomEnemyPolicyVersion: open.RoomEnemyPolicyVersion, ExpectedSequence: open.ExpectedSequence, VenueLaunchId: open.VenueLaunchId) };
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
            return Snapshot(ObserveAuthority(history.Authority, sequence) ?? throw new InvalidOperationException("No administrative observation."));
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

    public StreamCombatRecord[] CombatShotWitnesses(Guid id, Guid shotId, OperatorIdentity actor)
    {
        lock (gate)
        {
            var history = Find(id); AccessPolicy.Read(actor, history.View.RoomIds);
            return history.Combat.ShotReports(shotId).Where(entry => entry.Kind == SessionEventKind.StreamCombatRecorded)
                .Select(entry => entry.Read<StreamCombatRecord>()).ToArray();
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
    public CombatStreamView OpenGuardedStream(Guid id, OpenCombatStream request, OperatorIdentity actor)
    {
        ArgumentNullException.ThrowIfNull(request);
        AccessPolicy.ReportCombat(actor);
        if (request.ExpectedSequence is null or < 1) throw new ArgumentException("A positive expected session sequence is required.");
        return OpenStream(id, request, actor);
    }

    public CombatStreamView OpenStream(Guid id, OpenCombatStream request, OperatorIdentity? actor = null)
    {
        ArgumentNullException.ThrowIfNull(request);
        actor ??= OperatorIdentity.Internal; AccessPolicy.ReportCombat(actor);
        if (request.VenueLaunchId.HasValue) throw new ArgumentException("A venue launch ID requires batch attachment.");
        lock (gate)
        {
            var history = Find(id);
            if (history.View.CombatStream is { } existing)
            {
                if (!MatchesOpening(existing, request, actor))
                    throw new InvalidOperationException("A different stream or owner is already attached.");
                return existing;
            }
            return Commit(history, StreamOpening(history, request, actor)).CombatStream!;
        }
    }

    public VenueStreamBatchReceipt OpenVenueStreams(VenueStreamBatch request, OperatorIdentity actor)
    {
        ArgumentNullException.ThrowIfNull(request);
        AccessPolicy.ReportCombat(actor);
        if (request.Version != 1 || request.LaunchId == Guid.Empty || request.Topology is not (SessionMode.Linked or SessionMode.Independent)
            || request.Servers is null || request.Servers.Length != (request.Topology == SessionMode.Linked ? 1 : RoomCount)
            || request.Servers.Any(row => row is null || row.SessionId == Guid.Empty || row.StreamId == Guid.Empty || row.ExpectedSequence < 1)
            || request.Servers.Select(row => row.SessionId).Distinct().Count() != request.Servers.Length
            || request.Servers.Select(row => row.StreamId).Distinct().Count() != request.Servers.Length)
            throw new ArgumentException("Provide one distinct source for each original venue session.");

        lock (gate)
        {
            var targets = request.Servers.Select(row => (History: Find(row.SessionId),
                Open: new OpenCombatStream(row.StreamId, row.Origin, 1, 1, row.ExpectedSequence, request.LaunchId)))
                .OrderBy(target => target.History.View.RoomIds[0]).ToArray();
            if (targets.Any(target => target.History.View.Mode != request.Topology)
                || !targets.SelectMany(target => target.History.View.RoomIds).Order().SequenceEqual(Enumerable.Range(1, RoomCount)))
                throw new InvalidOperationException("The original sessions do not cover the selected venue topology.");

            var attached = sessions.Values.Count(history => history.View.CombatStream?.VenueLaunchId == request.LaunchId);
            if (attached != 0)
            {
                if (attached != targets.Length || targets.Any(target => target.History.View.CombatStream is not { } stream
                    || !MatchesOpening(stream, target.Open, actor)))
                    throw new InvalidOperationException("The venue launch ID already has different sources.");
                return VenueSourceReceipt(request, targets.Select(target => target.History.View));
            }
            if (eventStore is not IAtomicSessionEventStore store)
                throw new InvalidOperationException("Venue attachment requires a transactional session store.");

            var entries = targets.Select(target => StreamOpening(target.History, target.Open, actor)).ToArray();
            var views = entries.Select((entry, index) => SessionProjection.Apply(targets[index].History.View, entry)).ToArray();
            store.AppendBatch(entries);
            for (var index = 0; index < targets.Length; index++)
            {
                var history = targets[index].History;
                RememberCommitted(history, entries[index], views[index], history.Combat, history.Authority);
            }
            return VenueSourceReceipt(request, views);
        }
    }

    private static VenueStreamBatchReceipt VenueSourceReceipt(VenueStreamBatch request, IEnumerable<SessionView> views) =>
        new(1, request.LaunchId, request.Topology, views.Select(view => new VenueStreamSource(view.Id, view.CombatStream!)).ToArray());

    private static bool MatchesOpening(CombatStreamView stream, OpenCombatStream request, OperatorIdentity actor) =>
        stream.StreamId == request.StreamId && stream.Origin == request.Origin && stream.Owner == actor
        && stream.MissionClockVersion == request.MissionClockVersion && stream.RoomEnemyPolicyVersion == request.RoomEnemyPolicyVersion
        && stream.ExpectedSequence == request.ExpectedSequence && stream.VenueLaunchId == request.VenueLaunchId;

    private static SessionEvent StreamOpening(History history, OpenCombatStream request, OperatorIdentity actor)
    {
        if (history.View.Environment.Mode == ExperienceMode.MR && request.Origin != CombatOrigin.GameServer)
            throw new InvalidOperationException("MR sessions require a GameServer combat stream.");
        return SessionEvent.Create(history.View.Id, history.View.Sequence + 1, SessionEventKind.CombatStreamOpened, request, actor);
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
        var observed = ObserveAuthority(authority, record.ObservedSequence);
        if (observed?.State != SessionState.Running)
            throw new InvalidOperationException("Combat must reference a management snapshot observed while Running.");
        return observed;
    }

    private static SessionView? ObserveAuthority(List<SessionView> authority, long sequence)
    {
        var low = 0; var high = authority.Count - 1; SessionView? observed = null;
        while (low <= high)
        {
            var middle = low + (high - low) / 2;
            if (authority[middle].Sequence <= sequence) { observed = authority[middle]; low = middle + 1; }
            else high = middle - 1;
        }
        return observed;
    }
}
