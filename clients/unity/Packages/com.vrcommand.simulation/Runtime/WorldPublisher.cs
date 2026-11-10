using System;
using System.IO;
using System.Linq;
using System.Net.Sockets;
using System.Net.WebSockets;
using System.Net.Security;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace VrCommand.Simulation
{
    public interface IWorldConnection : IDisposable
    {
        Task Connect(CancellationToken cancellation);
        Task<string> Exchange(string message, CancellationToken cancellation);
    }
    public sealed class WorldWebSocket : IWorldConnection
    {
        private WebSocket socket = default!;
        private TcpClient transport = default!;
        private readonly Uri uri;
        private readonly string certificatePin;
        private readonly string token;
        public WorldWebSocket(string managementBase, Guid session, string token, string certificateSha256 = "")
        {
            if (!Uri.TryCreate(managementBase, UriKind.Absolute, out var address) || (address.Scheme != "http" && address.Scheme != "https")
                || address.Query != "" || address.Fragment != "" || address.UserInfo != "" || session == Guid.Empty || string.IsNullOrWhiteSpace(token))
                throw new ArgumentException("Invalid world publication address or server identity.");
            var target = new Uri(managementBase.TrimEnd('/') + "/api/sessions/" + session.ToString("D") + "/world/publish");
            uri = new UriBuilder(target) { Scheme = target.Scheme == "https" ? "wss" : "ws" }.Uri;
            certificatePin = certificateSha256;
            this.token = token;
            if (string.IsNullOrEmpty(certificatePin))
            {
                var platform = new ClientWebSocket();
                platform.Options.SetRequestHeader("Authorization", "Bearer " + token);
                socket = platform;
            }
            else if (uri.Scheme != "wss" || !ManagementCertificatePin.IsValid(certificatePin) || token.Any(c => c <= 32 || c >= 127))
                throw new ArgumentException("Invalid pinned world publication settings.");
        }
        public async Task Connect(CancellationToken cancellation)
        {
            try
            {
                if (string.IsNullOrEmpty(certificatePin))
                    await ((ClientWebSocket)socket).ConnectAsync(uri, cancellation).ConfigureAwait(false);
                else
                {
                    transport = new TcpClient();
                    socket = await PinnedWorldUpgrade.Connect(transport, uri, token, certificatePin, cancellation).ConfigureAwait(false);
                }
            }
            catch (Exception exception) when (exception is WebSocketException || exception is IOException
                || exception is AuthenticationException || exception is SocketException || exception is ObjectDisposedException)
            {
                cancellation.ThrowIfCancellationRequested();
                throw new WorldConnectionInterrupted("World connection failed.", exception);
            }
        }
        public async Task<string> Exchange(string message, CancellationToken cancellation)
        {
            var bytes = Encoding.UTF8.GetBytes(message);
            if (bytes.Length > 1024 * 1024) throw new InvalidDataException("World message exceeds 1 MiB.");
            try { return await ExchangeBytes(bytes, cancellation).ConfigureAwait(false); }
            catch (Exception exception) when (exception is WebSocketException || exception is IOException)
            { throw new WorldConnectionInterrupted("World acknowledgment connection was interrupted.", exception); }
        }
        private async Task<string> ExchangeBytes(byte[] bytes, CancellationToken cancellation)
        {
            await socket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, cancellation).ConfigureAwait(false);
            using (var body = new MemoryStream())
            {
                var block = new byte[16384]; WebSocketReceiveResult result;
                do
                {
                    result = await socket.ReceiveAsync(new ArraySegment<byte>(block), cancellation).ConfigureAwait(false);
                    if (result.MessageType == WebSocketMessageType.Close) throw new IOException("Connection closed before the acknowledgment.");
                    if (result.MessageType != WebSocketMessageType.Text || body.Length + result.Count > 1024 * 1024) throw new WorldPublicationRejected("Missing bounded text world acknowledgment.");
                    body.Write(block, 0, result.Count);
                } while (!result.EndOfMessage);
                return new UTF8Encoding(false, true).GetString(body.ToArray());
            }
        }
        public void Dispose() { socket?.Dispose(); transport?.Dispose(); }
    }

    // Unity's Mono ClientWebSocket does not consume its per-socket certificate callback.
    // Establish pinned TLS and the RFC 6455 upgrade here, then use framework WebSocket framing.
    internal static class PinnedWorldUpgrade
    {
        private const string Magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

        internal static async Task<WebSocket> Connect(TcpClient client, Uri uri, string token, string pin, CancellationToken cancellation)
        {
            using (cancellation.Register(client.Dispose))
            {
                await client.ConnectAsync(uri.IdnHost, uri.Port).ConfigureAwait(false);
                var tls = new SslStream(client.GetStream(), false, (sender, certificate, chain, errors) =>
                    certificate != null && ManagementCertificatePin.Matches(certificate.GetRawCertData(), pin));
                try
                {
                    await tls.AuthenticateAsClientAsync(uri.IdnHost, null, SslProtocols.Tls12, false).ConfigureAwait(false);
                    cancellation.ThrowIfCancellationRequested();
                    var challenge = new byte[16];
                    using (var random = RandomNumberGenerator.Create()) random.GetBytes(challenge);
                    var key = Convert.ToBase64String(challenge);
                    var request = Encoding.ASCII.GetBytes("GET " + uri.PathAndQuery + " HTTP/1.1\r\nHost: " + uri.Authority
                        + "\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: "
                        + key + "\r\nAuthorization: Bearer " + token + "\r\n\r\n");
                    await tls.WriteAsync(request, 0, request.Length, cancellation).ConfigureAwait(false);
                    await ValidateResponse(tls, key, cancellation).ConfigureAwait(false);
                    return WebSocket.CreateFromStream(tls, false, null, TimeSpan.FromSeconds(30));
                }
                catch { tls.Dispose(); throw; }
            }
        }

        private static async Task ValidateResponse(Stream stream, string key, CancellationToken cancellation)
        {
            // Read precisely through the header terminator so the first frame stays on the stream.
            var buffer = new byte[8192];
            for (var index = 0; index < buffer.Length; index++)
            {
                if (await stream.ReadAsync(buffer, index, 1, cancellation).ConfigureAwait(false) != 1)
                    throw new IOException("World WebSocket upgrade ended before response headers.");
                if (index < 3 || buffer[index] != 10 || buffer[index - 1] != 13 || buffer[index - 2] != 10 || buffer[index - 3] != 13)
                    continue;
                var lines = Encoding.ASCII.GetString(buffer, 0, index + 1).Split(new[] { "\r\n" }, StringSplitOptions.None);
                if (!IsUpgrade(lines, key)) throw new IOException("World WebSocket upgrade was refused.");
                return;
            }
            throw new IOException("World WebSocket upgrade headers exceed the limit.");
        }

        private static bool IsUpgrade(string[] lines, string key)
        {
            if (lines[0] != "HTTP/1.1 101" && !lines[0].StartsWith("HTTP/1.1 101 ", StringComparison.Ordinal)) return false;
            var headers = lines.Skip(1);
            string ReadSingle(string name)
            {
                var matches = headers.Where(line => line.StartsWith(name + ":", StringComparison.OrdinalIgnoreCase)).ToArray();
                return matches.Length == 1 ? matches[0].Substring(name.Length + 1).Trim() : "";
            }
            using (var sha = SHA1.Create())
            {
                var accept = Convert.ToBase64String(sha.ComputeHash(Encoding.ASCII.GetBytes(key + Magic)));
                return ReadSingle("Sec-WebSocket-Accept") == accept
                    && ReadSingle("Upgrade").Equals("websocket", StringComparison.OrdinalIgnoreCase)
                    && ReadSingle("Connection").Split(',').Any(value => value.Trim().Equals("upgrade", StringComparison.OrdinalIgnoreCase))
                    && !headers.Any(line => line.StartsWith("Sec-WebSocket-Extensions:", StringComparison.OrdinalIgnoreCase)
                        || line.StartsWith("Sec-WebSocket-Protocol:", StringComparison.OrdinalIgnoreCase));
            }
        }
    }

    public static class ManagementCertificatePin
    {
        public static bool IsValid(string value)
        {
            if (value == null || value.Length != 64) return false;
            foreach (var c in value)
                if (!(c >= '0' && c <= '9' || c >= 'a' && c <= 'f')) return false;
            return true;
        }

        public static bool Matches(byte[] certificateData, string expected)
        {
            if (certificateData == null || !IsValid(expected)) return false;
            try
            {
                // Unity can supply PEM or DER. Compare the parsed leaf DER in both cases.
                using (var hash = SHA256.Create())
                using (var certificate = new X509Certificate2(certificateData))
                {
                    var now = DateTime.UtcNow;
                    return certificate.NotBefore.ToUniversalTime() <= now && now < certificate.NotAfter.ToUniversalTime()
                        && BitConverter.ToString(hash.ComputeHash(certificate.RawData)).Replace("-", "").ToLowerInvariant() == expected;
                }
            }
            catch (CryptographicException) { return false; }
        }
    }
    public sealed class WorldPublicationRejected : Exception { public WorldPublicationRejected(string message) : base(message) { } }
    public sealed class WorldConnectionInterrupted : IOException { public WorldConnectionInterrupted(string message, Exception inner) : base(message, inner) { } }
    // One outstanding frame. The combat acknowledgment is a dependency, not an inferred network success.
    public sealed class WorldPublisher : IDisposable
    {
        private readonly WorldOutbox source;
        private readonly IWorldCodec codec;
        private readonly IWorldConnection connection;
        private bool attached; private int busy;
        public WorldPublisher(WorldOutbox source, IWorldCodec codec, IWorldConnection connection)
        { this.source = source; this.codec = codec; this.connection = connection; }
        public async Task<bool> Deliver(long combatAcknowledged, bool combatSealed, CancellationToken cancellation)
        {
            if (Interlocked.CompareExchange(ref busy, 1, 0) != 0) throw new InvalidOperationException("World publication already has an outstanding operation.");
            try
            {
                if (!attached)
                {
                    await connection.Connect(cancellation).ConfigureAwait(false);
                    var info = Read(await connection.Exchange("{\"type\":\"header\",\"payload\":" + source.HeaderJson + "}", cancellation).ConfigureAwait(false));
                    if (info.header == null || info.header.sessionId != source.Header.sessionId || info.header.streamId != source.Header.streamId
                        || info.header.origin != source.Header.origin || info.acceptedSequence < 0 || info.acceptedSequence > source.LastSequence)
                        throw new WorldPublicationRejected("World attachment receipt disagrees with the saved source.");
                    attached = true;
                }
                var pending = source.Pending;
                if (pending != null)
                {
                    if (pending.ThroughCombatSequence > combatAcknowledged) return false;
                    var info = Read(await connection.Exchange("{\"type\":\"frame\",\"payload\":" + pending.Json + "}", cancellation).ConfigureAwait(false));
                    if (info.acceptedSequence < pending.Sequence || info.acceptedSequence > source.LastSequence) throw new WorldPublicationRejected("World receipt has not accepted the saved frame.");
                    source.Acknowledge(pending.Sequence); return true;
                }
                if (source.Complete && !source.Sealed && combatSealed)
                {
                    var sequence = source.LastSequence.ToString(System.Globalization.CultureInfo.InvariantCulture);
                    var info = Read(await connection.Exchange("{\"type\":\"seal\",\"finalSequence\":" + sequence + "}", cancellation).ConfigureAwait(false));
                    if (!info.complete || info.acceptedSequence != source.LastSequence) throw new WorldPublicationRejected("World seal receipt disagrees with its final source boundary.");
                    source.MarkSealed(); return true;
                }
                return false;
            }
            finally { Volatile.Write(ref busy, 0); }
        }
        private WorldPublicationInfo Read(string json)
        {
            WorldPublicationAck ack;
            try { ack = codec.ReadAck(json); }
            catch (Exception exception) when (exception is ArgumentException || exception is InvalidOperationException || exception is FormatException)
            { throw new WorldPublicationRejected("Unrecognized world receipt."); }
            if (ack == null || ack.type != "ack" || ack.info == null) throw new WorldPublicationRejected(ack?.error ?? "Missing world receipt.");
            return ack.info;
        }
        public void Dispose() => connection.Dispose();
    }
}
