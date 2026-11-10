using System.Net;
using System.Text.Json.Serialization;
using VrCommand.Core;

namespace VrCommand.Api;

internal static partial class VrVenueTickets
{
    internal sealed record CheckRequest(string Topology, CheckRoom[] Rooms, bool RequireLiveSource = false);
    internal sealed record CheckRoom(int RoomId, Guid SessionId, byte[][] ConnectionFiles);
    internal sealed record SeatResult(int RoomId, int Seat, string Status, HeadsetKind? Headset = null);
    internal sealed record CheckResult(string Topology, bool AllMatched, SeatResult[] Seats,
        [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] bool? LiveSourceVerified);
    private sealed record Connection(string? Role, string? Address, int Port, string? JoinTicket);

    internal static async Task<CheckRequest> ReadCheck(HttpRequest request, CancellationToken cancellation)
    {
        const string message = "Provide five rooms with five original VR connection files each.";
        var files = await DeploymentJson.Read<CheckRequest>(request, 72 * 1024, message, cancellation);
        if (files.Topology is not ("Linked" or "Independent") || files.Rooms is not { Length: SessionManager.RoomCount }
            || files.Rooms.Any(room => room is not { RoomId: >= 1 and <= SessionManager.RoomCount, ConnectionFiles.Length: SessionManager.PlayersPerRoom }
                || room.SessionId == Guid.Empty || room.ConnectionFiles.Any(file => file is not { Length: > 0 and <= 2048 }))
            || files.Rooms.Select(room => room.RoomId).Distinct().Count() != SessionManager.RoomCount
            || files.Rooms.Select(room => room.SessionId).Distinct().Count() != (files.Topology == "Linked" ? 1 : SessionManager.RoomCount))
            throw new ArgumentException(message);
        return files;
    }

    internal static CheckResult Check(CheckRequest input, WorldRecordings worlds, OperatorIdentity actor, PlayerJoinTicketSigner signer)
    {
        var sources = worlds.ReadVenueSources(null, actor, requireLiveCapture: input.RequireLiveSource);
        var plan = Plan(sources);
        var seats = new List<SeatResult>(SessionManager.MaxPlayers);
        foreach (var room in input.Rooms.OrderBy(room => room.RoomId))
        {
            var current = plan.Rooms[room.RoomId - 1];
            for (var seat = 0; seat < SessionManager.PlayersPerRoom; seat++)
            {
                SeatResult result;
                if (current.SessionId != room.SessionId || plan.Topology?.ToString() != input.Topology)
                    result = new(room.RoomId, seat, "session-unavailable");
                else if (current.Endpoint is not { } endpoint || current.Problem == "vr-venue-endpoint-reused"
                    || (input.RequireLiveSource && IPAddress.IsLoopback(IPAddress.Parse(endpoint.Address))))
                    result = new(room.RoomId, seat, "endpoint-mismatch");
                else if (current.Problem == "vr-venue-roster-reused")
                    result = new(room.RoomId, seat, "venue-unavailable");
                else if (input.RequireLiveSource && current.TicketSourceLive != true)
                    result = new(room.RoomId, seat, "source-stale");
                else
                {
                    var player = sources[room.SessionId].Session.Players.SingleOrDefault(player => player.RoomId == room.RoomId && player.Seat == seat);
                    result = player is null ? new(room.RoomId, seat, "seat-unavailable")
                        : CheckConnection(room.SessionId, player, room.ConnectionFiles[seat], endpoint, signer);
                }
                seats.Add(result);
            }
        }
        var matched = seats.All(seat => seat.Status == "matched");
        return new(input.Topology, matched, [.. seats], input.RequireLiveSource ? matched : null);
    }

    internal static SeatResult CheckConnection(Guid sessionId, Player player, byte[] json, ConnectionEndpoint endpoint, PlayerJoinTicketSigner signer)
    {
        SeatResult Status(string value) => new(player.RoomId, player.Seat, value);
        var config = DeploymentJson.Connection<Connection>(json);
        if (config is not { Role: "Client", JoinTicket.Length: > 0 } || !ConnectionDestination.IsValid(config.Address, config.Port))
            return Status("connection-invalid");
        if (config.Address != endpoint.Address || config.Port != endpoint.Port) return Status("endpoint-mismatch");
        PlayerJoinClaims claims;
        try { claims = signer.Validate(config.JoinTicket, sessionId); }
        catch (AccessDeniedException) { return Status("ticket-invalid"); }
        if (claims.RoomId != player.RoomId || claims.Seat != player.Seat) return Status("wrong-seat");
        if (claims.PlayerId != player.Id || claims.AdmissionId != player.AdmissionId) return Status("admission-changed");
        return new(player.RoomId, player.Seat, "matched", player.Headset);
    }
}
