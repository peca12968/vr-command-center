using VrCommand.Core;

namespace VrCommand.Api;

internal sealed record VenueLaunchReviewRequest(int Version, Guid InstanceId, Guid LaunchId, SessionMode Topology,
    VenueLaunchReviewTarget?[]? Servers);
internal sealed record VenueLaunchReviewTarget(Guid SessionId, int[]? RoomIds, Guid? StreamId, VenueLaunchReviewUdp? Udp);
internal sealed record VenueLaunchReviewUdp(string BindAddress, int Port);
internal sealed record VenueLaunchReviewRow(Guid SessionId, int[] RoomIds, SessionState? Phase, string SourceState, Guid? StreamId,
    string EndpointState, string? EndpointAddress, int? EndpointPort, bool? AddressMatched, bool? RecentSource);
internal sealed record VenueLaunchReview(int Version, Guid LaunchId, SessionMode Topology, bool InstanceVerified,
    DateTimeOffset ObservedAtUtc, VenueLaunchReviewRow[] Servers);
internal sealed class VenueLaunchInstanceMismatchException()
    : InvalidOperationException("The launch report belongs to a different control instance.");

public sealed partial class WorldRecordings
{
    internal VenueLaunchReview ReadVenueLaunch(VenueLaunchReviewRequest request, OperatorIdentity actor, Guid? instanceId)
    {
        if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Launch review requires the master operator.");
        if (request is not { Version: 1, Servers: { } rows } || request.InstanceId == Guid.Empty || request.LaunchId == Guid.Empty
            || request.Topology is not (SessionMode.Independent or SessionMode.Linked)
            || rows.Length != (request.Topology == SessionMode.Linked ? 1 : SessionManager.RoomCount))
            throw new ArgumentException("Provide one original Linked session or all five Independent sessions.");
        var roomCount = request.Topology == SessionMode.Linked ? SessionManager.RoomCount : 1;
        if (rows.Any(row => row is null || row.SessionId == Guid.Empty || row.StreamId == Guid.Empty
            || row.RoomIds?.Length != roomCount
            || (row.Udp is { } udp && (row.StreamId is null
                || !ConnectionDestination.IsValid(udp.BindAddress == "0.0.0.0" ? "127.0.0.1" : udp.BindAddress, udp.Port)))))
            throw new ArgumentException("A launch review requires the original rooms and valid UDP evidence.");
        var targets = rows.OfType<VenueLaunchReviewTarget>()
            .Select(row => row with { RoomIds = row.RoomIds!.Order().ToArray() }).OrderBy(row => row.RoomIds![0]).ToArray();
        if (targets.Select(row => row.SessionId).Distinct().Count() != targets.Length
            || !targets.SelectMany(row => row.RoomIds!).SequenceEqual(Enumerable.Range(1, SessionManager.RoomCount)))
            throw new ArgumentException("The launch review must identify the five original rooms exactly once.");
        if (instanceId is Guid known && known != request.InstanceId) throw new VenueLaunchInstanceMismatchException();

        lock (gate)
        {
            var original = manager.ReadVenueLaunchSessions(targets.Select(row => row.SessionId).ToArray(), actor);
            var observed = readinessClock.GetUtcNow();
            return new(1, request.LaunchId, request.Topology, instanceId.HasValue, observed, targets.Select(target =>
                ReviewLaunchTarget(target, original.GetValueOrDefault(target.SessionId), request.Topology, request.LaunchId)).ToArray());
        }
    }

    private VenueLaunchReviewRow ReviewLaunchTarget(VenueLaunchReviewTarget target, SessionView? session, SessionMode topology, Guid launchId)
    {
        VenueLaunchReviewRow Status(string source, SessionState? phase = null) =>
            new(target.SessionId, target.RoomIds!, phase, source, null, "not-checked", null, null, null, null);
        if (session is null) return Status("missing-session");
        if (session.Mode != topology || !session.RoomIds.Order().SequenceEqual(target.RoomIds!)) return Status("room-mismatch");
        if (session.CombatStream is not { } stream) return Status("unbound", session.State);
        if (stream.VenueLaunchId != launchId || (target.StreamId is Guid id && stream.StreamId != id))
            return Status("different-source", session.State);

        var endpoint = EndpointRow(session);
        if (endpoint is null)
            return Status("original-source", session.State) with { StreamId = stream.StreamId, EndpointState = "not-published" };
        bool? addressMatched = target.Udp is { BindAddress: not "0.0.0.0" } udp ? udp.BindAddress == endpoint.Address : null;
        var mismatch = addressMatched == false || (target.Udp is { } bound && bound.Port != endpoint.Port);
        return new(target.SessionId, target.RoomIds!, session.State, "original-source", stream.StreamId,
            mismatch ? "endpoint-mismatch" : "published", endpoint.Address, endpoint.Port, addressMatched,
            session.State == SessionState.Ended ? null : TicketSourceLive(session, includeLegacy: true));
    }
}
