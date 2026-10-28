using System.Text.Json;
using VrCommand.Core;
using VrCommand.Simulation;

internal sealed class SystemWorldCodec : IWorldCodec
{
    private static readonly JsonSerializerOptions Json = new(JsonFormat.Options) { IncludeFields = true, WriteIndented = false };
    public string Header(WorldRecordingHeader value) => JsonSerializer.Serialize(value, Json);
    public string Packet(WorldRecordingPacket value) => JsonSerializer.Serialize(value, Json);
    public WorldRecordingHeader ReadHeader(string value) => Read<WorldRecordingHeader>(value);
    public WorldRecordingPacket ReadPacket(string value) => Read<WorldRecordingPacket>(value);
    public WorldPublicationAck ReadAck(string value) => Read<WorldPublicationAck>(value);
    private static T Read<T>(string value)
    {
        try { return JsonSerializer.Deserialize<T>(value, Json) ?? throw new ArgumentException("Missing world JSON."); }
        catch (JsonException) { throw new ArgumentException("Invalid world JSON."); }
    }
}
