using System.IO.Compression;
using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

internal sealed class VrVenueTicketConflict(int roomId, string code) : InvalidOperationException("Reload the current VR venue before issuing tickets.")
{
    public int RoomId { get; } = roomId;
    public string Code { get; } = code;
}

internal static class VrVenueTickets
{
    internal sealed record Request(SessionMode Topology, RoomFence[] Rooms);
    internal sealed record RoomFence(int RoomId, Guid SessionId, Guid StreamId, TicketAdmission?[] Players);
    internal sealed record Seat(int Number, Guid PlayerId, Guid AdmissionId, string Name);
    internal sealed record Room(int RoomId, Guid? SessionId, string? MissionName, ConnectionEndpoint? Endpoint, Seat[] Seats, string? Problem);
    internal sealed record Preview(SessionMode? Topology, Room[] Rooms)
    {
        public bool Ready => Topology is not null && Rooms.All(room => room.Problem is null);
    }

    internal static Preview Read(WorldRecordings worlds, OperatorIdentity actor) => Plan(worlds.ReadVenueSources(null, actor));

    private static Preview Plan(Dictionary<Guid, (SessionView Session, ConnectionEndpoint? Endpoint)> sources)
    {
        var modes = sources.Values.Where(source => source.Session.Environment.Mode == ExperienceMode.VR)
            .Select(source => source.Session.Mode).Distinct().ToArray();
        var topology = modes.Length == 1 ? modes[0] : (SessionMode?)null;
        var endpoints = new HashSet<(string Address, int Port)>();
        var players = new HashSet<Guid>();
        var admissions = new HashSet<Guid>();
        var rooms = Enumerable.Range(1, SessionManager.RoomCount).Select(roomId =>
        {
            var (session, endpoint) = sources.Values.SingleOrDefault(source => source.Session.RoomIds.Contains(roomId));
            if (session is null || session.Environment.Mode != ExperienceMode.VR)
                return new Room(roomId, null, null, null, [], "vr-venue-session-missing");
            var seats = session.Players.Where(player => player.RoomId == roomId).OrderBy(player => player.Seat)
                .Select(player => new Seat(player.Seat + 1, player.Id, player.AdmissionId, player.Name)).ToArray();
            var problem = topology is null ? "vr-venue-topology-changed"
                : endpoint is null ? "vr-venue-endpoint-missing"
                : topology == SessionMode.Independent && !endpoints.Add((endpoint.Address, endpoint.Port)) ? "vr-venue-endpoint-reused"
                : seats.Length != SessionManager.PlayersPerRoom ? "vr-venue-roster-incomplete"
                : seats.Any(seat => !players.Add(seat.PlayerId) || !admissions.Add(seat.AdmissionId)) ? "vr-venue-roster-reused"
                : null;
            return new Room(roomId, session.Id, session.Mission.Definition.Name, endpoint, seats, problem);
        }).ToArray();
        return new(topology, rooms);
    }

    internal static async Task<Request> ReadRequest(HttpRequest request, CancellationToken cancellation)
    {
        const string error = "Provide the current VR session, source and all five admissions for each of the five rooms.";
        var input = await MrDeploymentCheck.ReadJson<Request>(request, 8192, error, cancellation);
        if (input.Topology is not (SessionMode.Independent or SessionMode.Linked)
            || input.Rooms is not { Length: SessionManager.RoomCount }
            || input.Rooms.Any(room => room is not { RoomId: >= 1 and <= SessionManager.RoomCount, Players.Length: SessionManager.PlayersPerRoom }
                || room.SessionId == Guid.Empty || room.StreamId == Guid.Empty)
            || input.Rooms.Select(room => room.RoomId).Distinct().Count() != SessionManager.RoomCount
            || input.Rooms.Select(room => room.SessionId).Distinct().Count() != (input.Topology == SessionMode.Linked ? 1 : SessionManager.RoomCount))
            throw new ArgumentException(error);
        return input;
    }

    internal static byte[] Create(Request request, WorldRecordings worlds, OperatorIdentity actor, PlayerJoinTicketSigner signer)
    {
        var sources = worlds.ReadVenueSources(null, actor);
        var preview = Plan(sources);
        var verified = request.Rooms.OrderBy(room => room.RoomId).Select(input =>
        {
            var room = preview.Rooms[input.RoomId - 1];
            if (room.SessionId != input.SessionId) throw new VrVenueTicketConflict(room.RoomId, "vr-venue-session-changed");
            if (preview.Topology != request.Topology) throw new VrVenueTicketConflict(room.RoomId, "vr-venue-topology-changed");
            if (room.Problem is { } problem) throw new VrVenueTicketConflict(room.RoomId, problem);
            if (room.Endpoint is not { } endpoint || endpoint.StreamId != input.StreamId)
                throw new VrVenueTicketConflict(room.RoomId, "vr-venue-source-changed");
            var session = sources[input.SessionId].Session;
            Player[] seats;
            try { seats = RoomTicketBundles.ValidateAdmissions(session, room.RoomId, input.Players); }
            catch (InvalidOperationException) { throw new VrVenueTicketConflict(room.RoomId, "vr-venue-roster-changed"); }
            return (Room: room, Session: session, Endpoint: endpoint, Seats: seats);
        }).ToArray();

        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            var manifest = verified.Select(item => new
            {
                roomId = item.Room.RoomId, sessionId = item.Session.Id, item.Endpoint.Address, item.Endpoint.Port,
                ticketsZip = FormattableString.Invariant($"room-{item.Room.RoomId:00}-connections.zip"),
                seats = item.Room.Seats.Select(seat => new { seat = seat.Number, seat.Name })
            }).ToArray();
            using (var entry = archive.CreateEntry("venue.json").Open())
                JsonSerializer.Serialize(entry, new { version = 1, mode = "VR", topology = request.Topology, rooms = manifest }, JsonFormat.Options);
            for (var index = 0; index < verified.Length; index++)
            {
                var item = verified[index];
                using var entry = archive.CreateEntry(manifest[index].ticketsZip, CompressionLevel.NoCompression).Open();
                entry.Write(RoomTicketBundles.Encode(item.Session, item.Room.RoomId, item.Seats, item.Endpoint.Address, item.Endpoint.Port, signer));
            }
        }
        return output.ToArray();
    }
}
