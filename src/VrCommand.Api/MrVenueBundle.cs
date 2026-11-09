using System.IO.Compression;
using System.Net;
using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

internal sealed class MrVenueBundleConflict(int roomId, string code, string message) : InvalidOperationException(message)
{
    public int RoomId { get; } = roomId;
    public string Code { get; } = code;
}

internal static class MrVenueBundle
{
    internal sealed record Request(string Topology, Room[] Rooms);
    internal sealed record Room(int RoomId, Guid SessionId, TicketAdmission?[] Players, byte[] AlignmentFile);
    private sealed record ReadyRoom(Room Input, SessionView Session, ConnectionEndpoint Endpoint, Player[] Players);

    internal static async Task<Request> Read(HttpRequest request, CancellationToken cancellation)
    {
        const string message = "Provide five MR rooms with their current admissions and original alignment files.";
        var input = await DeploymentJson.Read<Request>(request, 128 * 1024, message, cancellation);
        if (input.Topology is not ("Linked" or "Independent") || input.Rooms is not { Length: SessionManager.RoomCount }
            || input.Rooms.Any(room => room is not { RoomId: >= 1 and <= SessionManager.RoomCount,
                Players.Length: SessionManager.PlayersPerRoom, AlignmentFile.Length: > 0 and <= RoomAlignment.MaxFileBytes }
                || room.SessionId == Guid.Empty)
            || input.Rooms.Select(room => room.RoomId).Distinct().Count() != SessionManager.RoomCount
            || input.Rooms.Select(room => room.SessionId).Distinct().Count() != (input.Topology == "Linked" ? 1 : SessionManager.RoomCount))
            throw new ArgumentException(message);
        return input;
    }

    internal static byte[] Create(Request request, WorldRecordings worlds, OperatorIdentity actor, PlayerJoinTicketSigner signer)
    {
        var mode = request.Topology == "Linked" ? SessionMode.Linked : SessionMode.Independent;
        var sources = worlds.ReadVenueSources(request.Rooms.Select(room => room.SessionId).Distinct().ToArray(), actor);
        var rooms = request.Rooms.OrderBy(room => room.RoomId).Select(room => Validate(room, mode, sources)).ToArray();
        var endpoints = new HashSet<(string, int)>();
        var players = new HashSet<Guid>();
        var admissions = new HashSet<Guid>();
        foreach (var room in rooms)
        {
            if (mode == SessionMode.Independent && !endpoints.Add((room.Endpoint.Address, room.Endpoint.Port)))
                throw new MrVenueBundleConflict(room.Input.RoomId, "venue-endpoint-reused", "Independent rooms must publish distinct endpoints.");
            if (room.Players.Any(player => !players.Add(player.Id) || !admissions.Add(player.AdmissionId)))
                throw new MrVenueBundleConflict(room.Input.RoomId, "venue-roster-reused", "The venue requires 25 distinct players and admissions.");
        }

        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            var manifest = rooms.Select(room => new
            {
                roomId = room.Input.RoomId, sessionId = room.Session.Id,
                ticketsZip = FormattableString.Invariant($"room-{room.Input.RoomId:00}-connections.zip"),
                alignmentFile = FormattableString.Invariant($"room-{room.Input.RoomId:00}-alignment.json")
            }).ToArray();
            using (var entry = archive.CreateEntry("venue.json").Open())
                JsonSerializer.Serialize(entry, new { version = 1, topology = request.Topology, rooms = manifest });
            for (var index = 0; index < rooms.Length; index++)
            {
                var room = rooms[index];
                using (var file = archive.CreateEntry(manifest[index].alignmentFile).Open()) file.Write(room.Input.AlignmentFile);
                var bundle = RoomTicketBundles.Encode(room.Session, room.Input.RoomId, room.Players, room.Endpoint.Address, room.Endpoint.Port, signer);
                using var tickets = archive.CreateEntry(manifest[index].ticketsZip).Open();
                tickets.Write(bundle);
            }
        }
        return output.ToArray();
    }

    private static ReadyRoom Validate(Room room, SessionMode mode, Dictionary<Guid, (SessionView Session, ConnectionEndpoint? Endpoint)> sources)
    {
        MrVenueBundleConflict Conflict(string code, string message) => new(room.RoomId, code, message);
        if (!sources.TryGetValue(room.SessionId, out var source) || source.Session.Mode != mode
            || source.Session.Environment.Mode != ExperienceMode.MR || !source.Session.RoomIds.Contains(room.RoomId))
            throw Conflict("venue-session-changed", "The selected MR session is unavailable for this room.");
        var hash = source.Session.RoomAlignment?.ForRoom(room.RoomId);
        if (hash is null) throw Conflict("venue-alignment-unlocked", "Lock the room alignment before exporting.");
        CheckedRoomAlignmentFile alignment;
        try { alignment = RoomAlignment.CheckFile(room.AlignmentFile); }
        catch (ArgumentException) { throw Conflict("venue-alignment-mismatch", "The original locked alignment file is required."); }
        if (alignment.RoomId != room.RoomId || alignment.Sha256 != hash)
            throw Conflict("venue-alignment-mismatch", "The original locked alignment file is required.");
        if (source.Endpoint is null) throw Conflict("venue-endpoint-missing", "Start the game server so it can publish its endpoint.");
        if (IPAddress.IsLoopback(IPAddress.Parse(source.Endpoint.Address)))
            throw Conflict("venue-endpoint-loopback", "The published loopback endpoint is only usable on the server computer.");
        Player[] players;
        try { players = RoomTicketBundles.ValidateAdmissions(source.Session, room.RoomId, room.Players); }
        catch (InvalidOperationException) { throw Conflict("venue-roster-changed", "Reload the current room roster before exporting."); }
        if (players.Any(player => player.Headset != HeadsetKind.Quest3))
            throw Conflict("venue-roster-changed", "All five seats must be current Quest 3 admissions.");
        return new(room, source.Session, source.Endpoint, players);
    }
}
