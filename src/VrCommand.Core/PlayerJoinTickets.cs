using System.Buffers.Binary;
using System.Security.Cryptography;

namespace VrCommand.Core;

public record PlayerJoinTicket(string Ticket, DateTimeOffset ExpiresAtUtc);
public record PlayerJoinClaims(Guid SessionId, Guid PlayerId, int RoomId, DateTimeOffset ExpiresAtUtc, Guid AdmissionId, int Seat);
public record PlayerAdmission(Guid SessionId, Guid PlayerId, int RoomId, int Seat, Guid AdmissionId, long ThroughSequence, DateTimeOffset ExpiresAtUtc);

public sealed partial class SessionManager
{
    // Call only after the signer verified the ticket. Resolves one current, atomic roster observation.
    public PlayerAdmission ResolveAdmission(PlayerJoinClaims claims, OperatorIdentity actor)
    {
        AccessPolicy.ReportCombat(actor);
        lock (gate)
        {
            var session = Find(claims.SessionId).View; AccessPolicy.Read(actor, session.RoomIds);
            var player = session.Players.SingleOrDefault(player => player.Id == claims.PlayerId);
            if (session.State == SessionState.Ended || player is null || player.AdmissionId != claims.AdmissionId || claims.AdmissionId == Guid.Empty
                || player.RoomId != claims.RoomId || player.Seat != claims.Seat)
                throw new AccessDeniedException("Player ticket no longer matches the current admission.");
            return new(session.Id, player.Id, player.RoomId, player.Seat, player.AdmissionId, session.Sequence, claims.ExpiresAtUtc);
        }
    }
}

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
        if (sessionId == Guid.Empty || player.Id == Guid.Empty || player.AdmissionId == Guid.Empty || player.Seat is < 0 or >= SessionManager.PlayersPerRoom
            || player.RoomId is < 1 or > SessionManager.RoomCount)
            throw new ArgumentException("Invalid ticket participant.");
        var expires = DateTimeOffset.FromUnixTimeSeconds(clock.GetUtcNow().AddMinutes(5).ToUnixTimeSeconds());
        var payload = new byte[75];
        payload[0] = 2;
        sessionId.TryWriteBytes(payload.AsSpan(1, 16));
        player.Id.TryWriteBytes(payload.AsSpan(17, 16));
        player.AdmissionId.TryWriteBytes(payload.AsSpan(33, 16));
        payload[49] = (byte)player.RoomId; payload[50] = (byte)player.Seat;
        BinaryPrimitives.WriteInt64BigEndian(payload.AsSpan(51, 8), expires.ToUnixTimeSeconds());
        RandomNumberGenerator.Fill(payload.AsSpan(59, 16));
        return new($"v2.{Encode(payload)}.{Encode(HMACSHA256.HashData(key, payload))}", expires);
    }

    public PlayerJoinClaims Validate(string ticket, Guid expectedSessionId)
    {
        if (string.IsNullOrEmpty(ticket) || ticket.Length > 256 || expectedSessionId == Guid.Empty) throw Rejected();
        var parts = ticket.Split('.');
        if (parts.Length != 3 || parts[0] != "v2") throw Rejected();
        byte[] payload;
        byte[] signature;
        try { payload = Decode(parts[1]); signature = Decode(parts[2]); }
        catch (FormatException) { throw Rejected(); }
        if (payload.Length != 75 || payload[0] != 2 || signature.Length != 32
            || !CryptographicOperations.FixedTimeEquals(signature, HMACSHA256.HashData(key, payload))) throw Rejected();
        var session = new Guid(payload.AsSpan(1, 16));
        var player = new Guid(payload.AsSpan(17, 16));
        var admission = new Guid(payload.AsSpan(33, 16));
        var room = payload[49]; var seat = payload[50];
        var seconds = BinaryPrimitives.ReadInt64BigEndian(payload.AsSpan(51, 8));
        var now = clock.GetUtcNow().ToUnixTimeSeconds();
        if (session != expectedSessionId || player == Guid.Empty || admission == Guid.Empty || seat >= SessionManager.PlayersPerRoom || room is < 1 or > SessionManager.RoomCount
            || seconds <= now || seconds > now + 300) throw Rejected();
        return new(session, player, room, DateTimeOffset.FromUnixTimeSeconds(seconds), admission, seat);
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
