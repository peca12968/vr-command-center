using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Core;

var live = args.Length != 0 && args[0] == "--live";
var bind = args.Length != 0 && args[0] == "--bind-room";
var bindVenue = args.Length != 0 && args[0] == "--bind-venue";
try
{
    if (args.Length < 4 || (!live && args.Length != 4) || args[0] is not ("--input" or "--live" or "--bind-room" or "--bind-venue") || args[2] != "--output")
        throw new ArgumentException("Use --input, --live, --bind-room or --bind-venue <input.json> --output <new-path>.");
    var input = Path.GetFullPath(args[1]); var output = Path.GetFullPath(args[3]);
    if (!input.EndsWith(".json", StringComparison.OrdinalIgnoreCase) || (!bindVenue && !output.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
        || string.Equals(input, output, StringComparison.OrdinalIgnoreCase) || File.Exists(output)) throw new ArgumentException("Use separate JSON input and a new output file.");
    if (bindVenue) return await LiveHardwareGateway.BindVenue(input, Path.TrimEndingDirectorySeparator(output));
    string? stopFile = null;
    var status = false;
    for (var index = 4; index < args.Length; index++)
    {
        switch (args[index])
        {
            case "--status" when !status:
                status = true;
                break;
            case "--stop-file" when stopFile is null && index + 1 < args.Length && !args[index + 1].StartsWith("--", StringComparison.Ordinal):
                stopFile = Path.GetFullPath(args[++index]);
                break;
            default:
                throw new ArgumentException("Use each live option at most once and provide a stop marker path.");
        }
    }
    if (stopFile is not null && (string.Equals(stopFile, input, StringComparison.OrdinalIgnoreCase)
        || string.Equals(stopFile, output, StringComparison.OrdinalIgnoreCase) || File.Exists(stopFile)
        || Directory.Exists(stopFile) || !Directory.Exists(Path.GetDirectoryName(stopFile))))
        throw new ArgumentException("Use a separate, absent stop marker in an existing directory.");
    if (live) return await LiveHardwareGateway.Run(input, output, stopFile, status);
    if (bind) return await LiveHardwareGateway.BindRoom(input, output);
    using var source = new FileStream(input, FileMode.Open, FileAccess.Read, FileShare.Read);
    if (source.Length is < 1 or > 8 * 1024 * 1024) throw new ArgumentException("Input exceeds the offline simulation limit.");
    var bytes = new byte[source.Length]; source.ReadExactly(bytes);
    var options = new JsonSerializerOptions(JsonFormat.Options) { UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow };
    var request = JsonSerializer.Deserialize<HardwareSimulationInput>(bytes, options) ?? throw new ArgumentException("Missing simulation input.");
    var report = HardwareFeedbackSimulation.Run(request); var payload = JsonSerializer.SerializeToUtf8Bytes(report, JsonFormat.Options);
    if (payload.Length > 64 * 1024 * 1024) throw new ArgumentException("Report exceeds the offline simulation limit.");
    using (var destination = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None)) { destination.Write(payload); destination.Flush(true); }
    Console.WriteLine(JsonSerializer.Serialize(new { complete = true, simulatedHardwareOnly = true, physicalDeliveryConfirmed = false, inputSteps = report.InputSteps }, JsonFormat.Options));
    return 0;
}
catch (Exception error) when (error is ArgumentException or InvalidDataException or InvalidOperationException or JsonException or IOException or UnauthorizedAccessException or AccessDeniedException or KeyNotFoundException or HttpRequestException or TimeoutException)
{
    // Never echo untrusted input, payloads or credentials into diagnostics.
    var message = args.FirstOrDefault() switch
    {
        "--live" => "Live hardware rehearsal rejected: ",
        "--bind-room" => "Room hardware binding rejected: ",
        "--bind-venue" => "Venue hardware binding rejected: ",
        _ => "Offline hardware simulation rejected: "
    };
    Console.Error.WriteLine(message + error.GetType().Name);
    return 1;
}
