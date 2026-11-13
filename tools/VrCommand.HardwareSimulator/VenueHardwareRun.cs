using System.Text.Json;
using VrCommand.Core;

internal static partial class LiveHardwareGateway
{
    private sealed record VenueRunResult(int RoomId, Guid SessionId, int ExitCode, string? Report, string? Error, string? Sha256, int? Bytes)
    {
        public string? ConfigurationSha256 { get; init; }
    }
    private sealed record VenueRunReport(int Version, bool Complete, SessionMode Mode, bool SimulatedHardwareOnly,
        bool PhysicalDeliveryConfirmed, string BindingManifestSha256, VenueRunResult[] Rooms);

    internal static async Task<int> RunVenue(string manifestPath, string output, string stopFile)
    {
        var parent = Path.GetDirectoryName(output);
        if (parent is null || !Directory.Exists(parent) || Path.Exists(output) || Path.Exists(stopFile)
            || !Directory.Exists(Path.GetDirectoryName(stopFile)) || string.Equals(output, stopFile, StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Use a new output directory and a separate absent stop marker with existing parents.");

        var manifest = ReadVenueManifest(manifestPath, out var bindingManifestSha256);
        var configs = manifest.Rooms.Select(room =>
        {
            var path = Path.Combine(Path.GetDirectoryName(manifestPath)!, room.Configuration);
            var config = ReadVenueConfiguration(path, room, out var sha256);
            return (Path: path, Config: config, Sha256: sha256);
        }).ToArray();
        var bindings = configs.SelectMany(entry => entry.Config.Bindings).ToArray();
        if (configs.Select(entry => entry.Config.ManagementUrl).Distinct(StringComparer.Ordinal).Count() != 1
            || configs.Select(entry => entry.Config.Seconds).Distinct().Count() != 1
            || configs.Select(entry => entry.Config.MockPort).Distinct().Count() != configs.Length
            || bindings.Select(binding => binding.DeviceId).Distinct().Count() != bindings.Length
            || bindings.Select(binding => binding.PlayerId).Distinct().Count() != bindings.Length
            || bindings.Select(binding => binding.AdmissionId).Distinct().Count() != bindings.Length)
            throw new InvalidDataException("Expected one management origin and duration with distinct room resources.");

        var clients = new List<HttpClient>(configs.Length);
        var leases = new List<GatewayLeases>(configs.Length);
        try
        {
            foreach (var entry in configs)
                clients.Add(CreateManagementClient(entry.Config.ManagementUrl,
                    FormattableString.Invariant($"VR_COMMAND_ROOM_{entry.Config.RoomId}_KEY")));
            await Task.WhenAll(configs.Select((entry, index) => VerifyIdentity(clients[index], entry.Config.RoomId)));
            try
            {
                await Task.WhenAll(configs.Select(async (entry, index) =>
                {
                    var current = await Read(clients[index], FeedbackRoute(entry.Config), entry.Config, null, CancellationToken.None);
                    if (current.Page.State == SessionState.Ended) throw new InvalidOperationException("A venue session has already ended.");
                }));
            }
            catch (BindingMismatch)
            {
                throw new InvalidOperationException("A configured venue admission is no longer current.");
            }
            foreach (var entry in configs) leases.Add(AcquireGatewayLeases(entry.Config));

            var staging = Directory.CreateDirectory(Path.Combine(parent, $".vr-venue-live-{Guid.NewGuid():N}")).FullName;
            try { Directory.Move(staging, output); }
            finally { if (Directory.Exists(staging)) Directory.Delete(staging); }

            var rooms = await Task.WhenAll(configs.Select(async (entry, index) =>
                (await RunVenueRoom(entry.Config, clients[index], entry.Path, output, stopFile, leases[index]))
                with { ConfigurationSha256 = entry.Sha256 }));
            var complete = rooms.All(room => room.ExitCode == 0);
            var report = new VenueRunReport(3, complete, manifest.Mode, true, false, bindingManifestSha256, rooms);
            var stagedReport = Path.Combine(output, "venue-report.tmp");
            using (var file = new FileStream(stagedReport, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                JsonSerializer.Serialize(file, report, Wire);
                file.Flush(true);
            }
            File.Move(stagedReport, Path.Combine(output, "venue-report.json"));
            Console.WriteLine(JsonSerializer.Serialize(report, Wire));
            return complete ? 0 : 1;
        }
        finally
        {
            foreach (var lease in leases) lease.Dispose();
            foreach (var client in clients) client.Dispose();
        }
    }

    private static async Task<VenueRunResult> RunVenueRoom(Configuration config, HttpClient client, string input, string directory,
        string stopFile, GatewayLeases leases)
    {
        var fileName = FormattableString.Invariant($"room-{config.RoomId:00}-report.json");
        var output = Path.Combine(directory, fileName);
        var roomStop = Path.Combine(directory, FormattableString.Invariant($"room-{config.RoomId:00}.stop"));
        try
        {
            var exit = await RunRoom(config, client, input, output, stopFile, statusEnabled: false, statusDirectory: directory,
                writeSummary: false, roomStopFile: roomStop, roomLeases: leases);
            var bytes = ReadReportBytes(output, MaxRoomReportBytes);
            return new(config.RoomId, config.SessionId, exit, fileName, null, ReportHash(bytes), bytes.Length);
        }
        catch (Exception error) when (IsExpectedFailure(error))
        {
            return new(config.RoomId, config.SessionId, 1, null, error.GetType().Name, null, null);
        }
        finally { leases.Dispose(); }
    }
}
