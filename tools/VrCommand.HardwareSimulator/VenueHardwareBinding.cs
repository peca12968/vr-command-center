using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Core;

internal static partial class LiveHardwareGateway
{
    private sealed record VenueMap(int Version, string ManagementUrl, [property: JsonRequired] SessionMode Mode, int Seconds, VenueRoomMap[] Rooms);
    private sealed record VenueRoomMap(int RoomId, Guid SessionId, int MockPort, SeatDevice[] Devices);
    private sealed record VenueBindingManifest(int Version, [property: JsonRequired] SessionMode Mode, VenueBindingRoom[] Rooms);
    private sealed record VenueBindingRoom(int RoomId, Guid SessionId, long SessionSequence, string Configuration, int BoundSeats);

    private static VenueBindingManifest ReadVenueManifest(string path)
    {
        var manifest = ReadInput<VenueBindingManifest>(path);
        if (manifest.Version != 1 || !Enum.IsDefined(manifest.Mode) || manifest.Rooms is not { Length: SessionManager.RoomCount }
            || manifest.Rooms.Any(room => room is null || room.SessionId == Guid.Empty || room.SessionSequence < 1 || room.BoundSeats is < 1 or > 5
                || room.Configuration != FormattableString.Invariant($"room-{room.RoomId:00}.json"))
            || !manifest.Rooms.Select(room => room.RoomId).SequenceEqual(Enumerable.Range(1, SessionManager.RoomCount))
            || manifest.Rooms.Select(room => room.SessionId).Distinct().Count() != (manifest.Mode == SessionMode.Linked ? 1 : SessionManager.RoomCount))
            throw new InvalidDataException("Unexpected venue binding manifest.");
        return manifest;
    }

    internal static async Task<int> BindVenue(string input, string output)
    {
        var parent = Path.GetDirectoryName(output);
        if (parent is null || !Directory.Exists(parent) || Directory.Exists(output) || File.Exists(output))
            throw new ArgumentException("Use a new venue output directory within an existing directory.");

        var map = ReadInput<VenueMap>(input);
        if (map.Version != 1 || !Enum.IsDefined(map.Mode) || map.Rooms is not { Length: SessionManager.RoomCount }
            || map.Rooms.Any(room => room is null)
            || !map.Rooms.Select(room => room.RoomId).Order().SequenceEqual(Enumerable.Range(1, SessionManager.RoomCount)))
            throw new ArgumentException("Use a version 1 map for exactly five rooms.");
        foreach (var room in map.Rooms)
        {
            ValidateRoom(room.SessionId, room.RoomId, room.MockPort, map.Seconds);
            ValidateDevices(room.Devices);
        }
        var devices = map.Rooms.SelectMany(room => room.Devices).ToArray();
        if (map.Rooms.Select(room => room.MockPort).Distinct().Count() != SessionManager.RoomCount
            || map.Rooms.Select(room => room.SessionId).Distinct().Count() != (map.Mode == SessionMode.Linked ? 1 : SessionManager.RoomCount)
            || devices.Select(device => device.DeviceId).Distinct().Count() != devices.Length)
            throw new ArgumentException("Use the expected topology and unique mock ports and device IDs across all five rooms.");

        using var client = CreateManagementClient(map.ManagementUrl, "VR_COMMAND_MASTER_KEY");
        var snapshot = await Get<VenueHardwareBindings>(client, "/api/venue/hardware-bindings", CancellationToken.None);
        if (snapshot.Version != 1 || snapshot.Mode != map.Mode || snapshot.Rooms is not { Length: SessionManager.RoomCount }
            || snapshot.Rooms.Any(room => room is null || room.SessionSequence < 1)
            || !snapshot.Rooms.Select(room => room.RoomId).SequenceEqual(Enumerable.Range(1, SessionManager.RoomCount)))
            throw new InvalidDataException("Unexpected venue binding snapshot.");
        var entries = map.Rooms.OrderBy(room => room.RoomId).Zip(snapshot.Rooms, (room, current) =>
        {
            if (room.SessionId != current.SessionId) throw new InvalidOperationException("A room belongs to a different session.");
            var bindings = ResolveBindings(room.Devices, ValidateBindingRoster(current.Bindings));
            return (Configuration: new Configuration(2, map.ManagementUrl, room.SessionId, room.RoomId, room.MockPort, map.Seconds, bindings),
                current.SessionSequence, FileName: FormattableString.Invariant($"room-{room.RoomId:00}.json"));
        }).ToArray();
        var bindingsAcrossRooms = entries.SelectMany(entry => entry.Configuration.Bindings).ToArray();
        if (bindingsAcrossRooms.Select(binding => binding.PlayerId).Distinct().Count() != devices.Length
            || bindingsAcrossRooms.Select(binding => binding.AdmissionId).Distinct().Count() != devices.Length)
            throw new InvalidDataException("The snapshot repeats a player or admission across rooms.");

        var manifest = new VenueBindingManifest(1, map.Mode, entries.Select(entry => new VenueBindingRoom(
            entry.Configuration.RoomId, entry.Configuration.SessionId, entry.SessionSequence, entry.FileName,
            entry.Configuration.Bindings.Length)).ToArray());
        const string manifestName = "venue-bindings.json";
        var staging = Directory.CreateDirectory(Path.Combine(parent, $".vr-venue-bindings-{Guid.NewGuid():N}")).FullName;
        try
        {
            foreach (var entry in entries) Write(entry.FileName, entry.Configuration);
            Write(manifestName, manifest);
            Directory.Move(staging, output);
        }
        finally
        {
            if (Directory.Exists(staging))
            {
                foreach (var entry in entries) File.Delete(Path.Combine(staging, entry.FileName));
                File.Delete(Path.Combine(staging, manifestName));
                Directory.Delete(staging);
            }
        }
        Console.WriteLine(JsonSerializer.Serialize(new { complete = true, mode = map.Mode, rooms = entries.Length, boundSeats = devices.Length }, Wire));
        return 0;

        void Write<T>(string fileName, T value)
        {
            using var file = new FileStream(Path.Combine(staging, fileName), FileMode.CreateNew, FileAccess.Write, FileShare.None);
            JsonSerializer.Serialize(file, value, JsonFormat.Options);
            file.Flush(true);
        }
    }
}
