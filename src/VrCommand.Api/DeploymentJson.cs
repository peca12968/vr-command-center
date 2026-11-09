using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Core;

namespace VrCommand.Api;

internal static class DeploymentJson
{
    private static readonly JsonSerializerOptions Options = new(JsonFormat.Options)
    {
        AllowDuplicateProperties = false,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        PropertyNameCaseInsensitive = false,
        NumberHandling = JsonNumberHandling.Strict,
        MaxDepth = 5
    };

    internal static async Task<T> Read<T>(HttpRequest request, int limit, string message, CancellationToken cancellation) where T : class
    {
        if (request.ContentLength is 0 || request.ContentLength > limit) throw new ArgumentException(message);
        var buffer = new byte[limit + 1];
        var length = await request.Body.ReadAtLeastAsync(buffer, buffer.Length, throwOnEndOfStream: false, cancellation);
        if (length > limit) throw new ArgumentException(message);
        try { return JsonSerializer.Deserialize<T>(buffer.AsSpan(0, length), Options) ?? throw new ArgumentException(message); }
        catch (JsonException) { throw new ArgumentException(message); }
    }

    internal static T? Connection<T>(ReadOnlySpan<byte> json) where T : class
    {
        if (json.StartsWith("\uFEFF"u8)) json = json[3..];
        try { return JsonSerializer.Deserialize<T>(json, Options); }
        catch (JsonException) { return null; }
    }
}
