using System.IO.Compression;
using System.Net;
using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

internal static class MixedVenueDeployment
{
    internal sealed record BundleRequest(BundleRoom[] Rooms, int PlayersPerRoom = SessionManager.PlayersPerRoom);
    internal sealed record BundleRoom(int RoomId, Guid SessionId, ExperienceMode Mode, Guid StreamId, TicketAdmission?[] Players, byte[]? AlignmentFile);
    internal sealed record CheckRequest(string Topology, CheckRoom[] Rooms, bool RequireLiveSource = false,
        int PlayersPerRoom = SessionManager.PlayersPerRoom);
    internal sealed record CheckRoom(int RoomId, Guid SessionId, ExperienceMode Mode, byte[][] ConnectionFiles, byte[]? AlignmentFile);
    internal sealed record Preview(Room[] Rooms)
    {
        public bool Ready => IsMixed(Rooms.Select(room => room.Mode)) && Rooms.All(room => room.Problem is null);
    }
    internal sealed record Room(int RoomId, Guid? SessionId, ExperienceMode? Mode, string? MissionName, ConnectionEndpoint? Endpoint,
        VrVenueTickets.Seat[] Seats, string? AlignmentSha256, string? Problem,
        [property: System.Text.Json.Serialization.JsonIgnore(Condition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)] bool? TicketSourceLive = null);
    private sealed record ReadyRoom(Room Room, SessionView Session, ConnectionEndpoint Endpoint, Player[] Players, byte[]? AlignmentFile);

    private static bool IsMixed(IEnumerable<ExperienceMode?> modes) => modes.Distinct().Count(mode => mode.HasValue) == 2;
    private static bool HasFiveRooms(IEnumerable<(int Room, Guid Session, ExperienceMode Mode, byte[]? Alignment)> rows)
    {
        var rooms = rows.OrderBy(row => row.Room).ToArray();
        return rooms.Select(row => row.Room).SequenceEqual(Enumerable.Range(1, SessionManager.RoomCount))
            && rooms.All(row => row.Session != Guid.Empty) && rooms.Select(row => row.Session).Distinct().Count() == SessionManager.RoomCount
            && IsMixed(rooms.Select(row => (ExperienceMode?)row.Mode))
            && rooms.All(row => row.Mode == ExperienceMode.VR ? row.Alignment is null
                : row.Mode == ExperienceMode.MR && row.Alignment is { Length: > 0 and <= RoomAlignment.MaxFileBytes });
    }

    internal static async Task<BundleRequest> ReadBundle(HttpRequest request, CancellationToken cancellation)
    {
        const string error = "Provide five independent rooms with both VR and MR, current admissions and the original MR alignment files.";
        var input = await DeploymentJson.Read<BundleRequest>(request, 128 * 1024, error, cancellation);
        if (!RoomTicketBundles.SupportedVenueSeatCount(input.PlayersPerRoom) || input.Rooms is not { Length: SessionManager.RoomCount }
            || input.Rooms.Any(room => room?.Players?.Length != input.PlayersPerRoom || room.StreamId == Guid.Empty)
            || !HasFiveRooms(input.Rooms.Select(room => (room.RoomId, room.SessionId, room.Mode, room.AlignmentFile))))
            throw new ArgumentException(error);
        return input;
    }

    internal static async Task<CheckRequest> ReadCheck(HttpRequest request, CancellationToken cancellation)
    {
        const string error = "Provide the five independent rooms and original connection files for the mixed venue.";
        var input = await DeploymentJson.Read<CheckRequest>(request, 180 * 1024, error, cancellation);
        if (input.Topology != "Independent" || !RoomTicketBundles.SupportedVenueSeatCount(input.PlayersPerRoom)
            || input.Rooms is not { Length: SessionManager.RoomCount }
            || input.Rooms.Any(room => room?.ConnectionFiles?.Length != input.PlayersPerRoom
                || room.ConnectionFiles.Any(file => file is not { Length: > 0 and <= 2048 }))
            || !HasFiveRooms(input.Rooms.Select(room => (room.RoomId, room.SessionId, room.Mode, room.AlignmentFile))))
            throw new ArgumentException(error);
        return input;
    }

    internal static Preview Read(WorldRecordings worlds, OperatorIdentity actor, int playersPerRoom)
    {
        if (!RoomTicketBundles.SupportedVenueSeatCount(playersPerRoom)) throw new ArgumentException("Use 1, 2 or 5 players per room.");
        return Plan(worlds.ReadVenueSources(null, actor), playersPerRoom);
    }

    private static Preview Plan(Dictionary<Guid, (SessionView Session, ConnectionEndpoint? Endpoint, bool? TicketSourceLive)> sources,
        int playersPerRoom)
    {
        var endpoints = new HashSet<(string, int)>();
        var players = new HashSet<Guid>();
        var admissions = new HashSet<Guid>();
        return new(Enumerable.Range(1, SessionManager.RoomCount).Select(roomId =>
        {
            var (session, endpoint, ticketSourceLive) = sources.Values.SingleOrDefault(source => source.Session.RoomIds.Contains(roomId));
            if (session?.Mode != SessionMode.Independent) return new Room(roomId, null, null, null, null, [], null, "venue-session-changed");
            var mode = session.Environment.Mode;
            var alignment = mode == ExperienceMode.MR ? session.RoomAlignment?.ForRoom(roomId) : null;
            var roster = session.Players.Where(player => player.RoomId == roomId).OrderBy(player => player.Seat).ToArray();
            var seats = roster.Select(player => new VrVenueTickets.Seat(player.Seat + 1, player.Id, player.AdmissionId, player.Name)).ToArray();
            var problem = endpoint is null ? "venue-endpoint-missing"
                : IPAddress.IsLoopback(IPAddress.Parse(endpoint.Address)) ? "venue-endpoint-loopback"
                : !endpoints.Add((endpoint.Address, endpoint.Port)) ? "venue-endpoint-reused"
                : mode == ExperienceMode.MR && alignment is null ? "venue-alignment-unlocked"
                : !RoomTicketBundles.HasFirstSeats(roster, playersPerRoom)
                    || (mode == ExperienceMode.MR && roster.Any(player => player.Headset != HeadsetKind.Quest3)) ? "venue-roster-changed"
                : seats.Any(seat => !players.Add(seat.PlayerId) || !admissions.Add(seat.AdmissionId)) ? "venue-roster-reused"
                : ticketSourceLive == false ? "venue-endpoint-stale" : null;
            return new Room(roomId, session.Id, mode, session.Mission.Definition.Name, endpoint, seats, alignment, problem, ticketSourceLive);
        }).ToArray());
    }

    internal static byte[] Create(BundleRequest input, WorldRecordings worlds, OperatorIdentity actor, PlayerJoinTicketSigner signer)
    {
        var sources = worlds.ReadVenueSources(null, actor);
        var plan = Plan(sources, input.PlayersPerRoom);
        var ready = input.Rooms.OrderBy(room => room.RoomId).Select(wanted =>
        {
            MrVenueBundleConflict Conflict(string code) => new(wanted.RoomId, code, "Reload the current mixed venue before issuing tickets.");
            var room = plan.Rooms[wanted.RoomId - 1];
            if (room.SessionId != wanted.SessionId || room.Mode != wanted.Mode) throw Conflict("venue-session-changed");
            if (room.Problem is { } problem) throw Conflict(problem);
            if (room.Endpoint is not { } endpoint || endpoint.StreamId != wanted.StreamId) throw Conflict("venue-source-changed");
            if (wanted.Mode == ExperienceMode.MR && (MrDeploymentCheck.ReadAlignment(wanted.AlignmentFile!) is not { } alignment
                || alignment.RoomId != wanted.RoomId || alignment.Sha256 != room.AlignmentSha256))
                throw Conflict("venue-alignment-mismatch");
            var session = sources[wanted.SessionId].Session;
            Player[] players;
            try { players = RoomTicketBundles.ValidateAdmissions(session, wanted.RoomId, wanted.Players); }
            catch (InvalidOperationException) { throw Conflict("venue-roster-changed"); }
            return new ReadyRoom(room, session, endpoint, players, wanted.AlignmentFile);
        }).ToArray();

        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            var manifest = ready.Select(row => new ManifestRoom(row.Room.RoomId, row.Session.Id, row.Room.Mode!.Value, row.Endpoint.Address, row.Endpoint.Port,
                FormattableString.Invariant($"room-{row.Room.RoomId:00}-connections.zip"),
                row.AlignmentFile is null ? null : FormattableString.Invariant($"room-{row.Room.RoomId:00}-alignment.json"))).ToArray();
            using (var entry = archive.CreateEntry("venue.json").Open())
            {
                if (input.PlayersPerRoom == SessionManager.PlayersPerRoom)
                    JsonSerializer.Serialize(entry, new { version = 2, mode = "Mixed", topology = "Independent", rooms = manifest }, JsonFormat.Options);
                else
                    JsonSerializer.Serialize(entry, new { version = 2, mode = "Mixed", topology = "Independent",
                        playersPerRoom = input.PlayersPerRoom, rooms = manifest }, JsonFormat.Options);
            }
            for (var index = 0; index < ready.Length; index++)
            {
                var row = ready[index];
                if (row.AlignmentFile is { } bytes)
                {
                    using var file = archive.CreateEntry(manifest[index].AlignmentFile!).Open();
                    file.Write(bytes);
                }
                using var tickets = archive.CreateEntry(manifest[index].TicketsZip, CompressionLevel.NoCompression).Open();
                tickets.Write(RoomTicketBundles.Encode(row.Session, row.Room.RoomId, row.Players, row.Endpoint.Address, row.Endpoint.Port, signer));
            }
        }
        return output.ToArray();
    }

    private sealed record ManifestRoom(int RoomId, Guid SessionId, ExperienceMode Mode, string Address, int Port, string TicketsZip,
        [property: System.Text.Json.Serialization.JsonIgnore(Condition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)] string? AlignmentFile);

    internal static VrVenueTickets.CheckResult Check(CheckRequest input, WorldRecordings worlds, OperatorIdentity actor, PlayerJoinTicketSigner signer)
    {
        var sources = worlds.ReadVenueSources(null, actor, requireLiveCapture: input.RequireLiveSource);
        var plan = Plan(sources, input.PlayersPerRoom);
        var results = new List<VrVenueTickets.SeatResult>(SessionManager.MaxPlayers);
        foreach (var wanted in input.Rooms.OrderBy(room => room.RoomId))
        {
            var room = plan.Rooms[wanted.RoomId - 1];
            var alignment = wanted.AlignmentFile is { } bytes ? MrDeploymentCheck.ReadAlignment(bytes) : null;
            for (var seat = 0; seat < input.PlayersPerRoom; seat++)
            {
                VrVenueTickets.SeatResult Status(string status) => new(wanted.RoomId, seat, status);
                var result = room.SessionId != wanted.SessionId || room.Mode != wanted.Mode ? Status("session-unavailable")
                    : room.Endpoint is null || room.Problem is "venue-endpoint-loopback" or "venue-endpoint-reused" ? Status("endpoint-mismatch")
                    : room.Problem == "venue-alignment-unlocked" ? Status("alignment-not-locked")
                    : room.Problem == "venue-roster-reused" || (input.PlayersPerRoom != SessionManager.PlayersPerRoom
                        && room.Problem == "venue-roster-changed") ? Status("venue-unavailable")
                    : input.RequireLiveSource && room.TicketSourceLive != true ? Status("source-stale")
                    : VerifySeat(sources[wanted.SessionId].Session, room, wanted.ConnectionFiles[seat], seat, alignment, signer);
                results.Add(result);
            }
        }
        var matched = results.All(seat => seat.Status == "matched");
        return new(input.Topology, matched, [.. results], input.RequireLiveSource ? matched : null);
    }

    private static VrVenueTickets.SeatResult VerifySeat(SessionView session, Room room, byte[] json, int seat,
        CheckedRoomAlignmentFile? alignment, PlayerJoinTicketSigner signer)
    {
        var player = session.Players.SingleOrDefault(player => player.RoomId == room.RoomId && player.Seat == seat);
        if (player is null || (room.Mode == ExperienceMode.MR && player.Headset != HeadsetKind.Quest3))
            return new(room.RoomId, seat, "seat-unavailable");
        if (room.Mode == ExperienceMode.VR) return VrVenueTickets.CheckConnection(session.Id, player, json, room.Endpoint!, signer);
        var verified = MrDeploymentCheck.CheckFiles(session.Id, player, json, alignment, room.AlignmentSha256!, signer, room.Endpoint);
        return new(room.RoomId, seat, verified.Status, verified.Status == "matched" ? player.Headset : null);
    }
}
