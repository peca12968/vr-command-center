using System.Buffers.Binary;
using System.Security.Cryptography;

namespace VrCommand.Core;

public record PlayerJoinTicket(string Ticket, DateTimeOffset ExpiresAtUtc);
public record PlayerJoinClaims(Guid SessionId, Guid PlayerId, int RoomId, DateTimeOffset ExpiresAtUtc);

// Opaque, short-lived invitations: no console or game-server credential is sent to a headset.
public sealed class PlayerJoinTicketSigner
{
    private readonly byte[] key;
    private readonly TimeProvider clock;
    public PlayerJoinTicketSigner(byte[] key, TimeProvider? clock = null)
    {
        if (key is null || key.Length < 32) throw new ArgumentException("Ticket signing key requires at least 32 bytes.");
        this.key = [.. key];
        this.clock = clock ?? TimeProvider.System;
    }

    public PlayerJoinTicket Issue(Guid sessionId, Player player)
    {
        if (sessionId == Guid.Empty || player.Id == Guid.Empty || player.RoomId is < 1 or > SessionManager.RoomCount)
            throw new ArgumentException("Invalid ticket participant.");
        var expires = DateTimeOffset.FromUnixTimeSeconds(clock.GetUtcNow().AddMinutes(5).ToUnixTimeSeconds());
        var payload = new byte[58];
        payload[0] = 1;
        sessionId.TryWriteBytes(payload.AsSpan(1, 16));
        player.Id.TryWriteBytes(payload.AsSpan(17, 16));
        payload[33] = (byte)player.RoomId;
        BinaryPrimitives.WriteInt64BigEndian(payload.AsSpan(34, 8), expires.ToUnixTimeSeconds());
        RandomNumberGenerator.Fill(payload.AsSpan(42, 16));
        return new($"v1.{Encode(payload)}.{Encode(HMACSHA256.HashData(key, payload))}", expires);
    }

    public PlayerJoinClaims Validate(string ticket, Guid expectedSessionId)
    {
        if (string.IsNullOrEmpty(ticket) || ticket.Length > 256 || expectedSessionId == Guid.Empty) throw Rejected();
        var parts = ticket.Split('.');
        if (parts.Length != 3 || parts[0] != "v1") throw Rejected();
        byte[] payload;
        byte[] signature;
        try { payload = Decode(parts[1]); signature = Decode(parts[2]); }
        catch (FormatException) { throw Rejected(); }
        if (payload.Length != 58 || payload[0] != 1 || signature.Length != 32
            || !CryptographicOperations.FixedTimeEquals(signature, HMACSHA256.HashData(key, payload))) throw Rejected();
        var session = new Guid(payload.AsSpan(1, 16));
        var player = new Guid(payload.AsSpan(17, 16));
        var room = payload[33];
        var seconds = BinaryPrimitives.ReadInt64BigEndian(payload.AsSpan(34, 8));
        var now = clock.GetUtcNow().ToUnixTimeSeconds();
        if (session != expectedSessionId || player == Guid.Empty || room is < 1 or > SessionManager.RoomCount
            || seconds <= now || seconds > now + 300) throw Rejected();
        return new(session, player, room, DateTimeOffset.FromUnixTimeSeconds(seconds));
    }

    private static AccessDeniedException Rejected() => new("Player join ticket is invalid, expired or for another session.");
    private static string Encode(byte[] bytes) => Convert.ToBase64String(bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_');
    private static byte[] Decode(string value)
    {
        if (value.Any(c => !char.IsAsciiLetterOrDigit(c) && c is not ('-' or '_'))) throw new FormatException();
        var base64 = value.Replace('-', '+').Replace('_', '/');
        return Convert.FromBase64String(base64.PadRight((base64.Length + 3) / 4 * 4, '='));
    }
}
