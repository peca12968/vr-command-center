using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Linq;

namespace VrCommand.Simulation
{
    public interface IWorldCodec
    {
        string Header(WorldRecordingHeader value);
        string Packet(WorldRecordingPacket value);
        WorldRecordingHeader ReadHeader(string value);
        WorldRecordingPacket ReadPacket(string value);
        WorldPublicationAck ReadAck(string value);
    }
    [Serializable] public sealed class WorldPublicationAck { public string type = "", error = ""; public WorldPublicationInfo info = new WorldPublicationInfo(); }
    [Serializable] public sealed class WorldPublicationInfo
    {
        public WorldRecordingHeader header = new WorldRecordingHeader();
        public long acceptedSequence, durationMilliseconds; public bool complete;
    }
    public sealed class WorldJournalRecord
    {
        public byte[] Payload { get; }
        public long NextPosition { get; }
        public WorldJournalRecord(byte[] payload, long next) { Payload = payload; NextPosition = next; }
    }
    public interface IWorldJournal : IDisposable
    {
        long Length { get; }
        WorldJournalRecord? Read(long position);
        void Append(byte[] payload);
    }
    public sealed class FileWorldJournal : IWorldJournal
    {
        public const int MaximumPayload = 1024 * 1024 - 128;
        private static readonly byte[] Magic = Encoding.ASCII.GetBytes("VRWORLD1");
        private readonly FileStream file;
        private bool fault;
        public FileWorldJournal(string path, bool createNew)
        {
            path = Path.GetFullPath(path);
            if (createNew) Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            file = new FileStream(path, createNew ? FileMode.CreateNew : FileMode.Open, FileAccess.ReadWrite, FileShare.None);
            try
            {
                if (createNew) { file.Write(Magic, 0, Magic.Length); file.Flush(true); }
                else
                {
                    var signature = new byte[Magic.Length];
                    if (file.Read(signature, 0, signature.Length) != signature.Length || !signature.SequenceEqual(Magic)) throw new InvalidDataException("Unknown world journal format.");
                }
            }
            catch { file.Dispose(); throw; }
        }
        public long Length => file.Length - Magic.Length;
        public WorldJournalRecord? Read(long position)
        {
            if (fault) throw new IOException("World journal is faulted; inspect and reopen its complete source.");
            if (position < 0 || position > Length) throw new ArgumentOutOfRangeException(nameof(position));
            if (position == Length) return null;
            file.Position = position + Magic.Length;
            try
            {
                using (var reader = new BinaryReader(file, Encoding.UTF8, true))
                {
                    var count = reader.ReadInt32();
                    if (count < 1 || count > MaximumPayload) throw new InvalidDataException("Invalid world journal record length.");
                    var payload = reader.ReadBytes(count); var digest = reader.ReadBytes(32);
                    using (var hash = SHA256.Create())
                        if (payload.Length != count || digest.Length != 32 || !hash.ComputeHash(payload).SequenceEqual(digest)) throw new InvalidDataException("World journal is torn or corrupt; no bytes were discarded.");
                    return new WorldJournalRecord(payload, file.Position - Magic.Length);
                }
            }
            catch (EndOfStreamException exception) { throw new InvalidDataException("World journal has a torn length header.", exception); }
        }
        public void Append(byte[] payload)
        {
            if (fault) throw new IOException("World journal writer is faulted.");
            if (payload == null || payload.Length < 1 || payload.Length > MaximumPayload) throw new ArgumentException("Invalid world journal payload size.");
            try
            {
                file.Position = file.Length;
                using (var hash = SHA256.Create()) using (var writer = new BinaryWriter(file, Encoding.UTF8, true))
                { writer.Write(payload.Length); writer.Write(payload); writer.Write(hash.ComputeHash(payload)); writer.Flush(); }
                file.Flush(true);
            }
            catch { fault = true; throw; }
        }
        public void Dispose() => file.Dispose();
    }
    public sealed class PendingWorldFrame
    {
        public long Sequence { get; }
        public long ThroughCombatSequence { get; }
        public string Json { get; }
        internal PendingWorldFrame(WorldRecordingPacket packet, string json) { Sequence = packet.sequence; ThroughCombatSequence = packet.throughCombatSequence; Json = json; }
    }
    // Single durable source, thread-safe against asynchronous delivery. Retains only the last and pending frame.
    public sealed class WorldOutbox : IDisposable
    {
        private readonly object gate = new object();
        private readonly IWorldJournal journal;
        private readonly IWorldCodec codec;
        private WorldRecordingPacket? last;
        private PendingWorldFrame? pending;
        private long pendingPosition, acknowledged;
        private bool complete, sealedStream;
        private readonly WorldRecordingHeader savedHeader;
        public WorldRecordingHeader Header => codec.ReadHeader(HeaderJson);
        public string HeaderJson { get; }
        public long LastSequence { get { lock (gate) return last?.sequence ?? 0; } }
        public long ThroughWorldSequence { get { lock (gate) return last?.frame.throughSequence ?? 0; } }
        public long AcknowledgedSequence { get { lock (gate) return acknowledged; } }
        public bool Complete { get { lock (gate) return complete; } }
        public bool Sealed { get { lock (gate) return sealedStream; } }

        public static WorldOutbox Create(string path, WorldRecordingHeader header, IWorldCodec codec)
        {
            var detached = codec.ReadHeader(codec.Header(header));
            if (detached.captureStartedAtUtc == "") detached.captureStartedAtUtc = DateTimeOffset.UtcNow.ToString("O", System.Globalization.CultureInfo.InvariantCulture);
            return new WorldOutbox(new FileWorldJournal(path, true), codec, detached);
        }
        public static WorldOutbox Recover(string path, IWorldCodec codec) => new WorldOutbox(new FileWorldJournal(path, false), codec, null);
        public WorldOutbox(IWorldJournal journal, IWorldCodec codec, WorldRecordingHeader? header)
        {
            this.journal = journal; this.codec = codec;
            try
            {
                if (journal.Length == 0)
                {
                    if (header == null) throw new InvalidDataException("World source has no recording header.");
                    WorldRecordingValidation.Header(header);
                    var json = codec.Header(header); journal.Append(Text(0, json));
                }
                var first = journal.Read(0) ?? throw new InvalidDataException("Missing recording header.");
                if (first.Payload[0] != 0) throw new InvalidDataException("World source must start with its header.");
                HeaderJson = Decode(first.Payload); savedHeader = codec.ReadHeader(HeaderJson); WorldRecordingValidation.Header(savedHeader);
                if (header != null && codec.Header(header) != HeaderJson) throw new InvalidDataException("World source header identity changed.");
                pendingPosition = first.NextPosition; var position = first.NextPosition;
                WorldJournalRecord? row;
                while ((row = journal.Read(position)) != null)
                {
                    var tag = row.Payload[0];
                    if (tag == 1)
                    {
                        if (complete) throw new InvalidDataException("World source contains a frame after completion.");
                        var packet = codec.ReadPacket(Decode(row.Payload)); WorldRecordingValidation.Packet(savedHeader, packet, last);
                        if (last?.frame.phase == "Ended" || packet.observedSequence < (last?.observedSequence ?? 1)) throw new InvalidDataException("World source resumes or rewinds a terminal frame.");
                        last = packet;
                    }
                    else if (tag >= 2 && tag <= 4)
                    {
                        var sequence = Number(row.Payload);
                        if (tag == 2)
                        {
                            if (sequence != acknowledged + 1 || sequence > (last?.sequence ?? 0) || sealedStream) throw new InvalidDataException("Invalid durable world receipt.");
                            acknowledged = sequence;
                        }
                        else if (tag == 3)
                        {
                            if (complete || last?.frame.phase != "Ended" || sequence != last.sequence) throw new InvalidDataException("Invalid world completion intent.");
                            complete = true;
                        }
                        else
                        {
                            if (!complete || sealedStream || sequence != acknowledged || sequence != last!.sequence) throw new InvalidDataException("Invalid final world receipt.");
                            sealedStream = true;
                        }
                    }
                    else throw new InvalidDataException("Unknown world source operation.");
                    position = row.NextPosition;
                }
            }
            catch { journal.Dispose(); throw; }
        }
        public void Append(WorldRecordingPacket packet)
        {
            lock (gate)
            {
                if (complete || last?.frame.phase == "Ended" || (last?.sequence ?? 0) >= 1000000) throw new InvalidOperationException("World source is terminal or full.");
                WorldRecordingValidation.Packet(savedHeader, packet, last);
                if (packet.observedSequence < (last?.observedSequence ?? 1)) throw new InvalidOperationException("World observation cannot rewind.");
                var json = codec.Packet(packet); var detached = codec.ReadPacket(json);
                WorldRecordingValidation.Packet(savedHeader, detached, last);
                journal.Append(Text(1, json)); last = detached;
            }
        }
        public PendingWorldFrame? Pending
        {
            get
            {
                lock (gate)
                {
                    if (pending != null) return pending;
                    WorldJournalRecord? row;
                    while ((row = journal.Read(pendingPosition)) != null)
                    {
                        pendingPosition = row.NextPosition;
                        if (row.Payload[0] != 1) continue;
                        var json = Decode(row.Payload); var packet = codec.ReadPacket(json);
                        if (packet.sequence <= acknowledged) continue;
                        if (packet.sequence != acknowledged + 1) throw new InvalidDataException("World pending sequence gap.");
                        pending = new PendingWorldFrame(packet, json); return pending;
                    }
                    return null;
                }
            }
        }
        public void Acknowledge(long sequence)
        {
            lock (gate)
            {
                if (sequence == acknowledged) return;
                if (Pending?.Sequence != sequence || sequence != acknowledged + 1) throw new InvalidOperationException("Acknowledge the exact pending world frame.");
                journal.Append(Integer(2, sequence)); acknowledged = sequence; pending = null;
            }
        }
        public void Finish()
        {
            lock (gate)
            {
                if (complete) return;
                if (last?.frame.phase != "Ended") throw new InvalidOperationException("Persist the final Ended world frame before completion.");
                journal.Append(Integer(3, last.sequence)); complete = true;
            }
        }
        public void MarkSealed()
        {
            lock (gate)
            {
                if (sealedStream) return;
                if (!complete || acknowledged != last!.sequence) throw new InvalidOperationException("Deliver every completed world frame before accepting its seal.");
                journal.Append(Integer(4, acknowledged)); sealedStream = true;
            }
        }
        private static byte[] Text(byte tag, string value)
        {
            var text = Encoding.UTF8.GetBytes(value); var result = new byte[text.Length + 1]; result[0] = tag; Array.Copy(text, 0, result, 1, text.Length); return result;
        }
        private static string Decode(byte[] payload) => new UTF8Encoding(false, true).GetString(payload, 1, payload.Length - 1);
        private static byte[] Integer(byte tag, long value)
        {
            using (var buffer = new MemoryStream()) using (var writer = new BinaryWriter(buffer)) { writer.Write(tag); writer.Write(value); return buffer.ToArray(); }
        }
        private static long Number(byte[] payload)
        {
            if (payload.Length != 9) throw new InvalidDataException("Invalid world source receipt size.");
            using (var reader = new BinaryReader(new MemoryStream(payload))) { reader.ReadByte(); return reader.ReadInt64(); }
        }
        public void Dispose() { lock (gate) journal.Dispose(); }
    }
}
