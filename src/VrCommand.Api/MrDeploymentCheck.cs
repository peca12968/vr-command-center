using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Core;

namespace VrCommand.Api;

internal static class MrDeploymentCheck
{
    private const int MaxConnectionBytes = 2048;
    private const int MaxRequestBytes = 25 * 1024;
    private static readonly JsonSerializerOptions FileOptions = new(JsonFormat.Options)
    {
        AllowDuplicateProperties = false,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        PropertyNameCaseInsensitive = false,
        NumberHandling = JsonNumberHandling.Strict,
        MaxDepth = 4
    };

    internal sealed record Files(byte[] ConnectionFile, byte[] AlignmentFile);
    internal sealed record Result(string Status, int RoomId, int Seat, DateTimeOffset? ExpiresAtUtc = null);
    internal sealed record VenueFiles(string Topology, VenueRoom[] Rooms);
    internal sealed record VenueRoom(int RoomId, Guid SessionId, byte[][] ConnectionFiles, byte[] AlignmentFile);
    internal sealed record VenueResult(string Topology, bool AllMatched, Result[] Seats);
    private sealed record Connection(string? Role, string? Address, int Port, string? JoinTicket, string? RoomAlignmentSha256);

    internal static async Task<Files> ReadFiles(HttpRequest request, CancellationToken cancellation)
    {
        const string message = "Provide the original connection and alignment files within their size limits.";
        var files = await ReadJson<Files>(request, MaxRequestBytes, message, cancellation);
        if (!ValidConnection(files.ConnectionFile) || !ValidAlignment(files.AlignmentFile)) throw new ArgumentException(message);
        return files;
    }

    internal static async Task<VenueFiles> ReadVenue(HttpRequest request, CancellationToken cancellation)
    {
        const string message = "Provide five rooms with five original connection files and one alignment file each, in a Linked or Independent venue.";
        var files = await ReadJson<VenueFiles>(request, 180 * 1024, message, cancellation);
        if (files.Topology is not ("Linked" or "Independent") || files.Rooms is not { Length: SessionManager.RoomCount }
            || files.Rooms.Any(room => room is not { RoomId: >= 1 and <= SessionManager.RoomCount, ConnectionFiles.Length: SessionManager.PlayersPerRoom }
                || room.SessionId == Guid.Empty || !ValidAlignment(room.AlignmentFile) || room.ConnectionFiles.Any(file => !ValidConnection(file)))
            || files.Rooms.Select(room => room.RoomId).Distinct().Count() != SessionManager.RoomCount
            || files.Rooms.Select(room => room.SessionId).Distinct().Count() != (files.Topology == "Linked" ? 1 : SessionManager.RoomCount))
            throw new ArgumentException(message);
        return files;
    }

    private static bool ValidConnection(byte[]? bytes) => bytes is { Length: > 0 and <= MaxConnectionBytes };
    private static bool ValidAlignment(byte[]? bytes) => bytes is { Length: > 0 and <= RoomAlignment.MaxFileBytes };

    private static async Task<T> ReadJson<T>(HttpRequest request, int limit, string message, CancellationToken cancellation) where T : class
    {
        if (request.ContentLength is 0 || request.ContentLength > limit) throw new ArgumentException(message);
        var buffer = new byte[limit + 1];
        var length = await request.Body.ReadAtLeastAsync(buffer, buffer.Length, throwOnEndOfStream: false, cancellation);
        if (length > limit) throw new ArgumentException(message);
        try { return JsonSerializer.Deserialize<T>(buffer.AsSpan(0, length), FileOptions) ?? throw new ArgumentException(message); }
        catch (JsonException) { throw new ArgumentException(message); }
    }

    internal static Result Check(SessionView session, Player player, Files files, PlayerJoinTicketSigner signer)
    {
        if (session.State == SessionState.Ended || session.Environment.Mode != ExperienceMode.MR || player.Headset != HeadsetKind.Quest3)
            throw new InvalidOperationException("Deployment checks require a current Quest 3 seat in an active MR session.");
        var hash = session.RoomAlignment?.ForRoom(player.RoomId) ?? throw new MixedRealityAlignmentRequiredException();
        return CheckFiles(session.Id, player, files.ConnectionFile, ReadAlignment(files.AlignmentFile), hash, signer);
    }

    internal static VenueResult CheckVenue(VenueFiles files, SessionView[] snapshot, PlayerJoinTicketSigner signer)
    {
        var mode = files.Topology == "Linked" ? SessionMode.Linked : SessionMode.Independent;
        var results = new List<Result>(SessionManager.RoomCount * SessionManager.PlayersPerRoom);
        foreach (var room in files.Rooms.OrderBy(room => room.RoomId))
        {
            var session = snapshot.SingleOrDefault(view => view.Id == room.SessionId && view.State != SessionState.Ended
                && view.Mode == mode && view.Environment.Mode == ExperienceMode.MR && view.RoomIds.Contains(room.RoomId));
            var hash = session?.RoomAlignment?.ForRoom(room.RoomId);
            var alignment = hash is null ? null : ReadAlignment(room.AlignmentFile);
            for (var seat = 0; seat < SessionManager.PlayersPerRoom; seat++)
            {
                var player = session?.Players.SingleOrDefault(player => player.RoomId == room.RoomId && player.Seat == seat && player.Headset == HeadsetKind.Quest3);
                if (session is null) results.Add(new("session-unavailable", room.RoomId, seat));
                else if (hash is null) results.Add(new("alignment-not-locked", room.RoomId, seat));
                else if (player is null) results.Add(new("seat-unavailable", room.RoomId, seat));
                else results.Add(CheckFiles(session.Id, player, room.ConnectionFiles[seat], alignment, hash, signer));
            }
        }
        return new(files.Topology, results.All(result => result.Status == "matched"), [.. results]);
    }

    private static CheckedRoomAlignmentFile? ReadAlignment(byte[] file)
    {
        try { return RoomAlignment.CheckFile(file); }
        catch (ArgumentException) { return null; }
    }

    private static Result CheckFiles(Guid sessionId, Player player, ReadOnlySpan<byte> json, CheckedRoomAlignmentFile? alignment, string hash, PlayerJoinTicketSigner signer)
    {
        Result Status(string value, DateTimeOffset? expires = null) => new(value, player.RoomId, player.Seat, expires);

        Connection? config;
        if (json.StartsWith("\uFEFF"u8)) json = json[3..];
        try { config = JsonSerializer.Deserialize<Connection>(json, FileOptions); }
        catch (JsonException) { return Status("connection-invalid"); }
        if (config is not { Role: "Client", JoinTicket.Length: > 0 } || !ConnectionDestination.IsValid(config.Address, config.Port))
            return Status("connection-invalid");

        PlayerJoinClaims claims;
        try { claims = signer.Validate(config.JoinTicket, sessionId); }
        catch (AccessDeniedException) { return Status("ticket-invalid"); }
        if (claims.RoomId != player.RoomId || claims.Seat != player.Seat) return Status("wrong-seat");
        if (claims.PlayerId != player.Id || claims.AdmissionId != player.AdmissionId) return Status("admission-changed");
        if (config.RoomAlignmentSha256 != hash) return Status("connection-hash-mismatch");

        if (alignment is null) return Status("alignment-invalid");
        if (alignment.RoomId != player.RoomId) return Status("alignment-wrong-room");
        if (alignment.Sha256 != hash) return Status("alignment-hash-mismatch");
        return Status("matched", claims.ExpiresAtUtc);
    }
}
