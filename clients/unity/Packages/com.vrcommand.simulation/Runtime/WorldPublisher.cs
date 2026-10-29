using System;
using System.IO;
using System.Net.WebSockets;
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
        private readonly ClientWebSocket socket = new ClientWebSocket();
        private readonly Uri uri;
        public WorldWebSocket(string managementBase, Guid session, string token)
        {
            if (!Uri.TryCreate(managementBase, UriKind.Absolute, out var address) || (address.Scheme != "http" && address.Scheme != "https")
                || address.Query != "" || address.Fragment != "" || address.UserInfo != "" || session == Guid.Empty || string.IsNullOrWhiteSpace(token))
                throw new ArgumentException("Invalid world publication address or server identity.");
            var target = new Uri(managementBase.TrimEnd('/') + "/api/sessions/" + session.ToString("D") + "/world/publish");
            uri = new UriBuilder(target) { Scheme = target.Scheme == "https" ? "wss" : "ws" }.Uri;
            socket.Options.SetRequestHeader("Authorization", "Bearer " + token);
        }
        public async Task Connect(CancellationToken cancellation)
        {
            try { await socket.ConnectAsync(uri, cancellation).ConfigureAwait(false); }
            catch (WebSocketException exception) { throw new WorldConnectionInterrupted("World connection failed.", exception); }
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
        public void Dispose() => socket.Dispose();
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
