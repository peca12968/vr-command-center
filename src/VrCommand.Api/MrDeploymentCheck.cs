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
    private sealed record Connection(string? Role, string? Address, int Port, string? JoinTicket, string? RoomAlignmentSha256);

    internal static async Task<Files> ReadFiles(HttpRequest request, CancellationToken cancellation)
    {
        const string message = "Provide the original connection and alignment files within their size limits.";
        if (request.ContentLength is 0 or > MaxRequestBytes) throw new ArgumentException(message);
        var buffer = new byte[MaxRequestBytes + 1];
        var length = await request.Body.ReadAtLeastAsync(buffer, buffer.Length, throwOnEndOfStream: false, cancellation);
        if (length > MaxRequestBytes) throw new ArgumentException(message);
        Files? files;
        try { files = JsonSerializer.Deserialize<Files>(buffer.AsSpan(0, length), FileOptions); }
        catch (JsonException) { throw new ArgumentException(message); }
        if (files is not { ConnectionFile.Length: > 0 and <= MaxConnectionBytes, AlignmentFile.Length: > 0 and <= RoomAlignment.MaxFileBytes })
            throw new ArgumentException(message);
        return files;
    }

    internal static Result Check(SessionView session, Player player, Files files, PlayerJoinTicketSigner signer)
    {
        if (session.State == SessionState.Ended || session.Environment.Mode != ExperienceMode.MR || player.Headset != HeadsetKind.Quest3)
            throw new InvalidOperationException("Deployment checks require a current Quest 3 seat in an active MR session.");
        var hash = session.RoomAlignment?.ForRoom(player.RoomId) ?? throw new MixedRealityAlignmentRequiredException();
        Result Status(string value, DateTimeOffset? expires = null) => new(value, player.RoomId, player.Seat, expires);

        Connection? config;
        var json = files.ConnectionFile.AsSpan();
        if (json.StartsWith("\uFEFF"u8)) json = json[3..];
        try { config = JsonSerializer.Deserialize<Connection>(json, FileOptions); }
        catch (JsonException) { return Status("connection-invalid"); }
        if (config is not { Role: "Client", JoinTicket.Length: > 0 } || !ConnectionDestination.IsValid(config.Address, config.Port))
            return Status("connection-invalid");

        PlayerJoinClaims claims;
        try { claims = signer.Validate(config.JoinTicket, session.Id); }
        catch (AccessDeniedException) { return Status("ticket-invalid"); }
        if (claims.RoomId != player.RoomId || claims.Seat != player.Seat) return Status("wrong-seat");
        if (claims.PlayerId != player.Id || claims.AdmissionId != player.AdmissionId) return Status("admission-changed");
        if (config.RoomAlignmentSha256 != hash) return Status("connection-hash-mismatch");

        CheckedRoomAlignmentFile alignment;
        try { alignment = RoomAlignment.CheckFile(files.AlignmentFile); }
        catch (ArgumentException) { return Status("alignment-invalid"); }
        if (alignment.RoomId != player.RoomId) return Status("alignment-wrong-room");
        if (alignment.Sha256 != hash) return Status("alignment-hash-mismatch");
        return Status("matched", claims.ExpiresAtUtc);
    }
}
