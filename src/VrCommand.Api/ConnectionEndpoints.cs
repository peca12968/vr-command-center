using System.Net;
using System.Net.Sockets;
using System.Text.Json;
using Microsoft.Data.Sqlite;
using VrCommand.Core;

namespace VrCommand.Api;

public record ConnectionEndpointDraft(int Version, Guid StreamId, string Address, int Port);
public record ConnectionEndpoint(int Version, Guid SessionId, Guid StreamId, string Address, int Port, DateTimeOffset CreatedAtUtc, bool SessionEnded);
public record VenueEndpointTarget(Guid SessionId, ConnectionEndpointDraft Endpoint);
public record VenueEndpointBatch(int Version, SessionMode Topology, VenueEndpointTarget?[]? Servers);
public record VenueEndpointReceipt(int Version, SessionMode Topology, ConnectionEndpoint[] Servers);

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

    internal Dictionary<Guid, (SessionView Session, ConnectionEndpoint? Endpoint)> ReadVenueSources(Guid[]? ids, OperatorIdentity actor)
    {
        if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Venue exports require the master operator.");
        lock (gate)
            return manager.List(false, actor).Where(session => ids is null || ids.Contains(session.Id))
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
            return InsertEndpoint(session, draft, actor, DateTimeOffset.UtcNow);
        }
    }

    public VenueEndpointReceipt PublishVenueEndpoints(VenueEndpointBatch batch, OperatorIdentity actor)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role != OperatorRole.GameServer) throw new AccessDeniedException("Only the owning game source may publish venue endpoints.");
        if (batch is not { Version: 1, Servers: { } rows } || !Enum.IsDefined(batch.Topology)
            || rows.Length != (batch.Topology == SessionMode.Linked ? 1 : SessionManager.RoomCount)
            || rows.Any(row => row is null || row.SessionId == Guid.Empty))
            throw new ArgumentException("Provide one Linked source or all five Independent sources.");
        var targets = rows.OfType<VenueEndpointTarget>().ToArray();
        foreach (var row in targets) ValidateEndpoint(row.Endpoint);
        if (targets.Select(row => row.SessionId).Distinct().Count() != targets.Length
            || targets.Select(row => row.Endpoint.StreamId).Distinct().Count() != targets.Length
            || targets.Select(row => row.Endpoint.Address).Distinct(StringComparer.Ordinal).Count() != 1
            || targets.Select(row => row.Endpoint.Port).Distinct().Count() != targets.Length)
            throw new ArgumentException("Venue endpoints require distinct sessions, sources and UDP ports at one IPv4 address.");

        lock (gate)
        {
            var sources = targets.Select(row =>
            {
                var session = Owner(row.SessionId, actor);
                var world = Info(row.SessionId, actor);
                if (row.Endpoint.StreamId != session.CombatStream!.StreamId
                    || world.Header.streamId != row.Endpoint.StreamId.ToString("D"))
                    throw new InvalidOperationException("Venue endpoint must identify the original attached game source and world.");
                return (Session: session, row.Endpoint, Existing: EndpointRow(session));
            }).OrderBy(source => source.Session.RoomIds[0]).ToArray();
            if (sources.Any(source => source.Session.Mode != batch.Topology)
                || !sources.SelectMany(source => source.Session.RoomIds).SequenceEqual(Enumerable.Range(1, SessionManager.RoomCount)))
                throw new InvalidOperationException("The original sources must cover the five venue rooms exactly once.");
            if (sources.All(source => source.Existing is { } existing && existing.Address == source.Endpoint.Address
                    && existing.Port == source.Endpoint.Port))
                return new(1, batch.Topology, sources.Select(source => source.Existing!).ToArray());
            if (sources.Any(source => source.Existing is not null || source.Session.State != SessionState.Preparing))
                throw new InvalidOperationException("New venue endpoints require all sources to be Preparing and unpublished.");

            using var transaction = db.BeginTransaction();
            var now = DateTimeOffset.UtcNow;
            var published = sources.Select(source => InsertEndpoint(source.Session, source.Endpoint, actor, now, transaction)).ToArray();
            transaction.Commit();
            return new(1, batch.Topology, published);
        }
    }

    private ConnectionEndpoint InsertEndpoint(SessionView session, ConnectionEndpointDraft draft, OperatorIdentity actor,
        DateTimeOffset created, SqliteTransaction? transaction = null)
    {
        using var insert = Command("INSERT INTO connection_endpoints(session,stream,owner,body,created) VALUES($id,$stream,$owner,$body,$created)",
            ("$id", session.Id.ToString("D")), ("$stream", draft.StreamId.ToString("D")), ("$owner", JsonSerializer.Serialize(actor, JsonFormat.Options)),
            ("$body", WorldJson.Write(draft)), ("$created", created.ToString("O")));
        insert.Transaction = transaction;
        insert.ExecuteNonQuery();
        return new(1, session.Id, draft.StreamId, draft.Address, draft.Port, created, session.State == SessionState.Ended);
    }
}
