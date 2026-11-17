using System.Net.WebSockets;
using System.Text;
using VrCommand.Simulation;

internal sealed class LocalWorldConnection : IWorldConnection
{
    private readonly HttpClient client;
    private readonly Uri uri;
    private readonly ClientWebSocket socket = new();

    internal LocalWorldConnection(HttpClient client, Guid session)
    {
        this.client = client;
        uri = new UriBuilder(client.BaseAddress!) { Scheme = "ws", Path = "/api/sessions/" + session + "/world/publish" }.Uri;
        socket.Options.SetRequestHeader("Authorization", client.DefaultRequestHeaders.Authorization!.ToString());
    }

    public async Task Connect(CancellationToken cancellation)
    {
        try { await socket.ConnectAsync(uri, client, cancellation); }
        catch (Exception error) when (error is WebSocketException or IOException)
        {
            cancellation.ThrowIfCancellationRequested();
            throw new WorldConnectionInterrupted("Local world connection failed.", error);
        }
    }

    public async Task<string> Exchange(string message, CancellationToken cancellation)
    {
        var bytes = Encoding.UTF8.GetBytes(message);
        if (bytes.Length > 1024 * 1024) throw new InvalidDataException("World message exceeds 1 MiB.");
        try
        {
            await socket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, cancellation);
            using var body = new MemoryStream();
            var block = new byte[16384];
            WebSocketReceiveResult result;
            do
            {
                result = await socket.ReceiveAsync(new ArraySegment<byte>(block), cancellation);
                if (result.MessageType == WebSocketMessageType.Close) throw new IOException("Local world connection closed before the acknowledgment.");
                if (result.MessageType != WebSocketMessageType.Text || body.Length + result.Count > 1024 * 1024)
                    throw new WorldPublicationRejected("Missing bounded text world acknowledgment.");
                body.Write(block, 0, result.Count);
            } while (!result.EndOfMessage);
            return new UTF8Encoding(false, true).GetString(body.ToArray());
        }
        catch (Exception error) when (error is WebSocketException or IOException)
        {
            throw new WorldConnectionInterrupted("Local world acknowledgment was interrupted.", error);
        }
    }

    public void Dispose() => socket.Dispose();
}
