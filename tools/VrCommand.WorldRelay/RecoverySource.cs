using System.Text.Json;
using VrCommand.Core;
using VrCommand.Simulation;

internal sealed class RecoveryRejected(string reason) : Exception(reason);

internal sealed record RecoverySource(Guid SessionId, string Origin, Uri Api, string Key, string Directory)
{
    internal static RecoverySource Read(string configPath)
    {
        using var input = File.OpenRead(configPath);
        if (input.Length is < 1 or > 8192) throw new RecoveryRejected("invalid-server-config");
        var bytes = new byte[(int)input.Length];
        input.ReadExactly(bytes);
        var start = bytes.AsSpan().StartsWith("\uFEFF"u8) ? 3 : 0;
        using var document = JsonDocument.Parse(bytes.AsMemory(start), new JsonDocumentOptions { MaxDepth = 4 });
        var config = document.RootElement;
        if (config.ValueKind != JsonValueKind.Object
            || config.EnumerateObject().Select(field => field.Name).Distinct(StringComparer.Ordinal).Count() != config.EnumerateObject().Count()
            || config.GetProperty("role").GetString() != "Server"
            || !Guid.TryParseExact(config.GetProperty("sessionId").GetString(), "D", out var id) || id == Guid.Empty
            || !Uri.TryCreate(config.GetProperty("managementApiUrl").GetString(), UriKind.Absolute, out var api)
            || api.Scheme is not ("http" or "https") || api.AbsolutePath != "/" || api.UserInfo != "" || api.Query != "" || api.Fragment != ""
            || config.GetProperty("gameServerKey").GetString() is not { Length: >= 16 and <= 256 } key || key.Any(char.IsWhiteSpace)
            || config.GetProperty("telemetryOrigin").GetString() is not ("Simulation" or "GameServer")
            || config.GetProperty("telemetryDirectory").GetString() is not { } directory || !Path.IsPathFullyQualified(directory))
            throw new RecoveryRejected("invalid-server-config");
        return new(id, config.GetProperty("telemetryOrigin").GetString()!, api, key, directory);
    }

    internal FileStream OpenOriginal(string suffix) =>
        new(Path.Combine(Directory, SessionId.ToString("D") + suffix), FileMode.Open, FileAccess.Read, FileShare.None);

    internal static void Copy(FileStream input, string destination)
    {
        using var output = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        input.CopyTo(output);
        output.Flush(flushToDisk: true);
    }

    internal void CheckJournals(TelemetryOutbox combat, WorldOutbox world, WorldRecordingHeader header)
    {
        if (combat.SessionId != SessionId || combat.Origin != Origin
            || header.sessionId != SessionId.ToString("D") || header.streamId != combat.StreamId.ToString("D") || header.origin != Origin
            || (world.Complete && !combat.Complete))
            throw new RecoveryRejected("journal-identity-or-completion-mismatch");
    }
}
