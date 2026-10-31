using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace VrCommand.Simulation
{
    // Captured != durable. Only WorldOutbox.State authorizes publication / seal.
    public sealed class QueuedWorldRecorder : IDisposable
    {
        public const int MaximumFrames = 32, MaximumBytes = 8 * 1024 * 1024;
        private readonly object gate = new object();
        private readonly Queue<Entry> queue = new Queue<Entry>();
        private readonly SemaphoreSlim wake = new SemaphoreSlim(0);
        private readonly WorldOutbox source;
        private readonly IWorldCodec codec;
        private readonly WorldRecordingHeader header;
        private readonly int frameLimit, byteLimit;
        private WorldRecordingPacket? captured;
        private Exception? failure;
        private int count, bytes, disposed;
        private bool accepting = true;
        private sealed class Entry
        {
            internal readonly string Json; internal readonly int Bytes;
            internal Entry(string json, int bytes) { Json = json; Bytes = bytes; }
        }
        public Task Completion { get; }
        public long CapturedSequence { get { lock(gate) return captured?.sequence ?? 0; } }
        public long CapturedThroughWorldSequence { get { lock(gate) return captured?.frame.throughSequence ?? 0; } }
        public bool EndQueued { get { lock(gate) return captured?.frame.phase == "Ended"; } }
        public bool Faulted { get { lock(gate) return failure != null; } }
        public int PendingFrames { get { lock(gate) return count; } }
        public int PendingBytes { get { lock(gate) return bytes; } }
        public QueuedWorldRecorder(WorldOutbox source, IWorldCodec codec, int frameLimit = MaximumFrames, int byteLimit = MaximumBytes)
        {
            if (frameLimit < 1 || frameLimit > MaximumFrames || byteLimit < 1 || byteLimit > MaximumBytes) throw new ArgumentOutOfRangeException();
            if (source.LastSequence != 0 || source.Complete) throw new InvalidOperationException("Queued capture requires a new empty world, not engine recovery.");
            this.source = source; this.codec = codec; header = source.Header; this.frameLimit = frameLimit; this.byteLimit = byteLimit;
            Completion = Task.Run(Drain);
        }
        public void Enqueue(WorldRecordingPacket packet)
        {
            // Caller-owned mutable DTOs never cross threads. Codec uses plain DTOs only.
            var json = codec.Packet(packet); var detached = codec.ReadPacket(json); var size = Encoding.UTF8.GetByteCount(json);
            if (size > FileWorldJournal.MaximumPayload - 1) throw new ArgumentException("World frame exceeds the journal record bound.");
            lock(gate)
            {
                if (failure != null) throw new IOException("World writer failed; recover its persisted source.", failure);
                if (!accepting || captured?.frame.phase == "Ended") throw new InvalidOperationException("World capture is stopped or terminal.");
                WorldRecordingValidation.Packet(header, detached, captured);
                if (detached.observedSequence < (captured?.observedSequence ?? 1)) throw new ArgumentException("World observation cannot rewind.");
                if (count == frameLimit || size > byteLimit - bytes)
                {
                    failure = new InvalidOperationException("World persistence queue is full; pause and recover source.");
                    accepting = false; wake.Release(); throw failure;
                }
                queue.Enqueue(new Entry(json, size)); count++; bytes += size; captured = detached;
                wake.Release();
            }
        }
        private async Task Drain()
        {
            while (true)
            {
                await wake.WaitAsync().ConfigureAwait(false);
                Entry entry;
                lock(gate)
                {
                    if (queue.Count == 0) { if (!accepting) return; else continue; }
                    entry = queue.Dequeue();
                }
                try
                {
                    var packet = codec.ReadPacket(entry.Json); source.Append(packet);
                    if (packet.frame.phase == "Ended") source.Finish();
                }
                catch (Exception error) { lock(gate) { failure = error; accepting = false; } return; }
                lock(gate) { count--; bytes -= entry.Bytes; }
            }
        }
        public void Stop()
        {
            lock(gate) { if (!accepting) return; accepting = false; wake.Release(); }
        }
        public void Dispose()
        {
            if (Interlocked.Exchange(ref disposed, 1) != 0) return;
            Stop(); Completion.ContinueWith(_ => wake.Dispose(), TaskScheduler.Default);
        }
    }
}
