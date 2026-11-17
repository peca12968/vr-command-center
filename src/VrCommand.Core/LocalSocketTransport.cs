using System.Net;
using System.Net.Sockets;

namespace VrCommand.Core;

public static class LocalSocketTransport
{
    public static async ValueTask<Stream> Connect(EndPoint endpoint, CancellationToken cancellation)
    {
        var socket = new Socket(endpoint.AddressFamily, SocketType.Stream, ProtocolType.Unspecified);
        try
        {
            await socket.ConnectAsync(endpoint, cancellation);
            return new NetworkStream(socket, ownsSocket: true);
        }
        catch
        {
            socket.Dispose();
            throw;
        }
    }
}
