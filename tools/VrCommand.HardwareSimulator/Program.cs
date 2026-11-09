using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Core;

var live = args.Length != 0 && args[0] == "--live";
try
{
    if (args.Length != 4 || args[0] is not ("--input" or "--live") || args[2] != "--output")
        throw new ArgumentException("Use --input or --live <configuration.json> --output <new-report.json>");
    var input = Path.GetFullPath(args[1]); var output = Path.GetFullPath(args[3]);
    if (!input.EndsWith(".json", StringComparison.OrdinalIgnoreCase) || !output.EndsWith(".json", StringComparison.OrdinalIgnoreCase)
        || string.Equals(input, output, StringComparison.OrdinalIgnoreCase) || File.Exists(output)) throw new ArgumentException("Use separate JSON input and a new output file.");
    if (live) return await LiveHardwareGateway.Run(input, output);
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
    Console.Error.WriteLine((live ? "Live hardware rehearsal rejected: " : "Offline hardware simulation rejected: ") + error.GetType().Name);
    return 1;
}
