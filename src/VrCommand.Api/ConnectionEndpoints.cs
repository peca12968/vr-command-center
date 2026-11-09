using System.Net;
using System.Net.Sockets;
using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

public record ConnectionEndpointDraft(int Version, Guid StreamId, string Address, int Port);
public record ConnectionEndpoint(int Version, Guid SessionId, Guid StreamId, string Address, int Port, DateTimeOffset CreatedAtUtc, bool SessionEnded);

internal static class ConnectionDestination
{
    public static bool IsValid(string? value, int port) => IPAddress.TryParse(value, out var address)
        && address.AddressFamily == AddressFamily.InterNetwork && address.ToString() == value
        && address.GetAddressBytes()[0] is > 0 and < 224 && port is >= 1024 and <= 65535;
}

public sealed partial class WorldRecordings
{
    private static void ValidateEndpoint(ConnectionEndpointDraft draft)
    {
        if (draft is null || draft.Version != 1 || draft.StreamId == Guid.Empty || !ConnectionDestination.IsValid(draft.Address, draft.Port))
            throw new ArgumentException("Endpoint v1 requires its stream, a canonical unicast IPv4 address and port 1024–65535.");
    }
    private ConnectionEndpoint? EndpointRow(SessionView session)
    {
        using var command = Command("SELECT stream,owner,body,created FROM connection_endpoints WHERE session=$id", ("$id", session.Id.ToString("D")));
        using var row = command.ExecuteReader(); if (!row.Read()) return null;
        var draft = WorldJson.Read<ConnectionEndpointDraft>(row.GetString(2)); ValidateEndpoint(draft);
        if (session.CombatStream is null || row.GetString(0) != session.CombatStream.StreamId.ToString("D") || draft.StreamId != session.CombatStream.StreamId
            || row.GetString(1) != JsonSerializer.Serialize(session.CombatStream.Owner, JsonFormat.Options))
            throw new InvalidDataException("Published endpoint does not match its combat source.");
        return new(1, session.Id, draft.StreamId, draft.Address, draft.Port, DateTimeOffset.Parse(row.GetString(3)), session.State == SessionState.Ended);
    }
    public ConnectionEndpoint ConnectionEndpoint(Guid id, OperatorIdentity actor)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role is not (OperatorRole.Master or OperatorRole.RoomController)) throw new AccessDeniedException("Connection settings require a control-desk identity.");
        lock (gate) return EndpointRow(manager.Get(id, actor)) ?? throw new KeyNotFoundException("The game source has not published connection settings.");
    }

    internal Dictionary<Guid, (SessionView Session, ConnectionEndpoint? Endpoint)> ReadVenueSources(Guid[] ids, OperatorIdentity actor)
    {
        if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue exports require the master operator.");
        lock (gate)
            return manager.List(false, actor).Where(session => ids.Contains(session.Id))
                .ToDictionary(session => session.Id, session => (session, EndpointRow(session)));
    }
    public ConnectionEndpoint PublishEndpoint(Guid id, ConnectionEndpointDraft draft, OperatorIdentity actor)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role != OperatorRole.GameServer) throw new AccessDeniedException("Only the owning game source may publish connection settings.");
        lock (gate)
        {
            var session = Owner(id, actor); Info(id, actor); ValidateEndpoint(draft);
            if (draft.StreamId != session.CombatStream!.StreamId) throw new InvalidOperationException("Endpoint must identify the attached combat stream.");
            var existing = EndpointRow(session);
            if (existing is not null)
            {
                if (existing.Address != draft.Address || existing.Port != draft.Port) throw new InvalidOperationException("Connection settings are immutable for this source; create a new session to change its endpoint.");
                return existing;
            }
            using var insert = Command("INSERT INTO connection_endpoints(session,stream,owner,body,created) VALUES($id,$stream,$owner,$body,$created)",
                ("$id", id.ToString("D")), ("$stream", draft.StreamId.ToString("D")), ("$owner", JsonSerializer.Serialize(actor, JsonFormat.Options)),
                ("$body", WorldJson.Write(draft)), ("$created", DateTimeOffset.UtcNow.ToString("O")));
            insert.ExecuteNonQuery(); return EndpointRow(session)!;
        }
    }
}
