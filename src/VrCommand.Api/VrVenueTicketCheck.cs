using System.Net;
using System.Text.Json.Serialization;
using VrCommand.Core;

namespace VrCommand.Api;

internal static partial class VrVenueTickets
{
    internal sealed record CheckRequest(string Topology, CheckRoom[] Rooms, bool RequireLiveSource = false, bool AllowLoopback = false,
        int PlayersPerRoom = SessionManager.PlayersPerRoom);
    internal sealed record CheckRoom(int RoomId, Guid SessionId, byte[][] ConnectionFiles);
    internal sealed record SeatResult(int RoomId, int Seat, string Status, HeadsetKind? Headset = null);
    internal sealed record CheckResult(string Topology, bool AllMatched, SeatResult[] Seats,
        [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] bool? LiveSourceVerified);
    internal sealed record SeatFile(byte[] ConnectionFile);
    internal sealed record SeatFileResult(string Status, int RoomId, int Seat, DateTimeOffset? ExpiresAtUtc, string? Address, int? Port);
    private sealed record Connection(string? Role, string? Address, int Port, string? JoinTicket);

    internal static async Task<SeatFile> ReadSeatFile(HttpRequest request, CancellationToken cancellation)
    {
        const string message = "Provide one original VR connection file of at most 2 KiB.";
        var file = await DeploymentJson.Read<SeatFile>(request, 3 * 1024, message, cancellation);
        if (file.ConnectionFile is not { Length: > 0 and <= 2048 }) throw new ArgumentException(message);
        return file;
    }

    internal static async Task<CheckRequest> ReadCheck(HttpRequest request, CancellationToken cancellation)
    {
        const string message = "Provide five rooms with 1, 2 or 5 original VR connection files each.";
        var files = await DeploymentJson.Read<CheckRequest>(request, 72 * 1024, message, cancellation);
        if (files.Topology is not ("Linked" or "Independent") || !SupportedSeatCount(files.PlayersPerRoom)
            || files.Rooms is not { Length: SessionManager.RoomCount }
            || files.Rooms.Any(room => room is not { RoomId: >= 1 and <= SessionManager.RoomCount }
                || room.ConnectionFiles?.Length != files.PlayersPerRoom
                || room.SessionId == Guid.Empty || room.ConnectionFiles.Any(file => file is not { Length: > 0 and <= 2048 }))
            || files.Rooms.Select(room => room.RoomId).Distinct().Count() != SessionManager.RoomCount
            || files.Rooms.Select(room => room.SessionId).Distinct().Count() != (files.Topology == "Linked" ? 1 : SessionManager.RoomCount))
            throw new ArgumentException(message);
        return files;
    }

    internal static CheckResult Check(CheckRequest input, WorldRecordings worlds, OperatorIdentity actor, PlayerJoinTicketSigner signer)
    {
        var sources = worlds.ReadVenueSources(null, actor, requireLiveCapture: input.RequireLiveSource);
        var plan = Plan(sources, input.PlayersPerRoom);
        var seats = new List<SeatResult>(SessionManager.MaxPlayers);
        foreach (var room in input.Rooms.OrderBy(room => room.RoomId))
        {
            var current = plan.Rooms[room.RoomId - 1];
            for (var seat = 0; seat < input.PlayersPerRoom; seat++)
            {
                SeatResult result;
                if (current.SessionId != room.SessionId || plan.Topology?.ToString() != input.Topology)
                    result = new(room.RoomId, seat, "session-unavailable");
                else if (current.Endpoint is not { } endpoint || current.Problem == "vr-venue-endpoint-reused"
                    || (input.RequireLiveSource && !input.AllowLoopback && IPAddress.IsLoopback(IPAddress.Parse(endpoint.Address))))
                    result = new(room.RoomId, seat, "endpoint-mismatch");
                else if (current.Problem == "vr-venue-roster-reused" || (input.PlayersPerRoom != SessionManager.PlayersPerRoom
                    && current.Problem == "vr-venue-roster-incomplete"))
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

    internal static SeatFileResult CheckSeatFile(Guid sessionId, Player player, SeatFile file, ConnectionEndpoint? endpoint,
        bool sourceLive, PlayerJoinTicketSigner signer)
    {
        var (status, expires) = InspectConnection(sessionId, player, file.ConnectionFile, endpoint, signer);
        if (status == "matched") status = endpoint is null ? "endpoint-unpublished" : sourceLive ? status : "source-stale";
        return new(status, player.RoomId, player.Seat, status == "matched" ? expires : null, endpoint?.Address, endpoint?.Port);
    }

    internal static SeatResult CheckConnection(Guid sessionId, Player player, byte[] json, ConnectionEndpoint endpoint, PlayerJoinTicketSigner signer)
    {
        var (status, _) = InspectConnection(sessionId, player, json, endpoint, signer);
        return new(player.RoomId, player.Seat, status, status == "matched" ? player.Headset : null);
    }

    private static (string Status, DateTimeOffset? ExpiresAtUtc) InspectConnection(Guid sessionId, Player player, byte[] json,
        ConnectionEndpoint? endpoint, PlayerJoinTicketSigner signer)
    {
        var config = DeploymentJson.Connection<Connection>(json);
        if (config is not { Role: "Client", JoinTicket.Length: > 0 } || !ConnectionDestination.IsValid(config.Address, config.Port))
            return ("connection-invalid", null);
        if (endpoint is not null && (config.Address != endpoint.Address || config.Port != endpoint.Port)) return ("endpoint-mismatch", null);
        PlayerJoinClaims claims;
        try { claims = signer.Validate(config.JoinTicket, sessionId); }
        catch (AccessDeniedException) { return ("ticket-invalid", null); }
        if (claims.RoomId != player.RoomId || claims.Seat != player.Seat) return ("wrong-seat", null);
        if (claims.PlayerId != player.Id || claims.AdmissionId != player.AdmissionId) return ("admission-changed", null);
        return ("matched", claims.ExpiresAtUtc);
    }
}
