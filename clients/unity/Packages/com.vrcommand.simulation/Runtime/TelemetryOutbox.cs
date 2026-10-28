using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;

namespace VrCommand.Simulation
{
    public interface ITelemetryJournal : IDisposable { byte[][] Load(); void Append(byte[] frame); }

    // One writer, checksummed frames, one durable flush per capture batch. A torn/corrupt tail fails closed.
    public sealed class FileTelemetryJournal : ITelemetryJournal
    {
        private readonly FileStream file;
        private bool failed;
        public FileTelemetryJournal(string path)
        {
            path = Path.GetFullPath(path); Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            file = new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        }
        public byte[][] Load()
        {
            if (failed) throw new IOException("Journal writer is faulted; inspect its complete file before recovery.");
            file.Position = 0; var frames = new List<byte[]>();
            try
            {
                using (var reader = new BinaryReader(file, System.Text.Encoding.UTF8, true))
                    while (file.Position < file.Length)
                    {
                        var length = reader.ReadInt32();
                        if (length < 1 || length > 65536) throw new InvalidDataException("Unsupported telemetry frame length.");
                        var frame = reader.ReadBytes(length); var checksum = reader.ReadBytes(32);
                        using (var hash = SHA256.Create())
                            if (frame.Length != length || checksum.Length != 32 || !hash.ComputeHash(frame).SequenceEqual(checksum))
                                throw new InvalidDataException("Telemetry journal has a torn or corrupt frame; no data was discarded.");
                        frames.Add(frame);
                    }
            }
            catch (EndOfStreamException exception) { throw new InvalidDataException("Telemetry journal has a torn frame header.", exception); }
            return frames.ToArray();
        }
        public void Append(byte[] frame)
        {
            if (failed) throw new IOException("Journal writer is faulted.");
            if (frame.Length < 1 || frame.Length > 65536) throw new ArgumentException("Invalid frame size.");
            try
            {
                file.Position = file.Length;
                using (var hash = SHA256.Create()) using (var writer = new BinaryWriter(file, System.Text.Encoding.UTF8, true))
                { writer.Write(frame.Length); writer.Write(frame); writer.Write(hash.ComputeHash(frame)); writer.Flush(); }
                file.Flush(true);
            }
            catch { failed = true; throw; }
        }
        public void Dispose() => file.Dispose();
    }

    public sealed class TelemetryRecord
    {
        public Guid StreamId { get; }
        public long StreamSequence { get; }
        public long ObservedSequence { get; }
        public Guid ReportId { get; }
        public WorldEventKind Kind { get; }
        public Guid PlayerId { get; }
        public Guid ShotId { get; }
        public Guid EnemyId { get; }
        public int Damage { get; }
        public string Origin { get; }
        internal TelemetryRecord(Guid stream, long sequence, long observed, Guid report, WorldEventKind kind, Guid player, Guid shot, Guid enemy, int damage, string origin)
        {
            if (sequence < 1 || observed < 1 || report == Guid.Empty || player == Guid.Empty || !Combat(kind)
                || (kind == WorldEventKind.PlayerDamaged ? shot != Guid.Empty || enemy != Guid.Empty || damage < 1 || damage > 1000
                    : shot == Guid.Empty || damage != 0 || (kind == WorldEventKind.ShotFired ? enemy != Guid.Empty : enemy == Guid.Empty)))
                throw new InvalidDataException("Invalid queued combat report.");
            StreamId = stream; StreamSequence = sequence; ObservedSequence = observed; ReportId = report; Kind = kind; PlayerId = player;
            ShotId = shot; EnemyId = enemy; Damage = damage; Origin = origin;
        }
        internal static bool Combat(WorldEventKind kind) => kind == WorldEventKind.ShotFired || kind == WorldEventKind.ShotHit
            || kind == WorldEventKind.EnemyEliminated || kind == WorldEventKind.PlayerDamaged;
        // Values are validated UUIDs, enums and integers. Omit absent GUID fields (JsonUtility emits empty strings).
        public string ToJson() => "{\"streamId\":\"" + StreamId.ToString("D") + "\",\"streamSequence\":" + StreamSequence.ToString(CultureInfo.InvariantCulture)
            + ",\"observedSequence\":" + ObservedSequence.ToString(CultureInfo.InvariantCulture) + ",\"report\":{\"reportId\":\"" + ReportId.ToString("D")
            + "\",\"kind\":\"" + Kind + "\",\"origin\":\"" + Origin + "\",\"playerId\":\"" + PlayerId.ToString("D") + "\""
            + (ShotId == Guid.Empty ? "" : ",\"shotId\":\"" + ShotId.ToString("D") + "\"")
            + (EnemyId == Guid.Empty ? "" : ",\"enemyId\":\"" + EnemyId.ToString("D") + "\"")
            + ",\"damage\":" + Damage.ToString(CultureInfo.InvariantCulture) + "}}";
    }

    public sealed class TelemetryOutbox : IDisposable
    {
        private readonly ITelemetryJournal journal;
        private readonly List<TelemetryRecord> records = new List<TelemetryRecord>();
        private readonly HashSet<Guid> reportIds = new HashSet<Guid>();
        private long worldCursor;
        public Guid SessionId { get; }
        public Guid StreamId { get; }
        public string Origin { get; }
        public long LastSequence => records.Count;
        public long AcknowledgedSequence { get; private set; }
        public bool Complete { get; private set; }
        public bool Sealed { get; private set; }
        public TelemetryRecord? Pending => AcknowledgedSequence < records.Count ? records[(int)AcknowledgedSequence] : null;
        public TelemetryRecord[] PendingBatch(int limit = 128)
        { if (limit < 1 || limit > 128) throw new ArgumentException("Batch limit is 1–128."); return records.Skip((int)AcknowledgedSequence).Take(limit).ToArray(); }
        public static string BatchJson(TelemetryRecord[] batch) => "[" + string.Join(",", batch.Select(record => record.ToJson())) + "]";

        public static TelemetryOutbox OpenFile(string path, Guid session, string origin)
        {
            var journal = new FileTelemetryJournal(path);
            try
            {
                var frames = journal.Load(); var stream = frames.Length == 0 ? System.Guid.NewGuid() : Header(frames[0]).Stream;
                return new TelemetryOutbox(journal, session, stream, origin);
            }
            catch { journal.Dispose(); throw; }
        }
        public static TelemetryOutbox OpenExisting(string path)
        {
            if (!File.Exists(path)) throw new FileNotFoundException("Telemetry journal is missing.", path);
            var journal = new FileTelemetryJournal(path);
            try
            {
                var frames = journal.Load(); if (frames.Length == 0) throw new InvalidDataException("Telemetry journal has no identity.");
                var header = Header(frames[0]); return new TelemetryOutbox(journal, header.Session, header.Stream, header.Origin);
            }
            catch { journal.Dispose(); throw; }
        }
        public TelemetryOutbox(ITelemetryJournal journal, Guid session, Guid stream, string origin)
        {
            if (session == System.Guid.Empty || stream == System.Guid.Empty || (origin != "Simulation" && origin != "GameServer")) throw new ArgumentException("Invalid telemetry identity.");
            this.journal = journal; SessionId = session; StreamId = stream; Origin = origin;
            var frames = journal.Load();
            if (frames.Length == 0) journal.Append(Frame(writer => { writer.Write((byte)1); writer.Write(1); Guid(writer, session); Guid(writer, stream); writer.Write(origin); }));
            else
            {
                var identity = Header(frames[0]);
                if (identity.Session != session || identity.Stream != stream || identity.Origin != origin) throw new InvalidDataException("Telemetry identity does not match its file.");
                foreach (var frame in frames.Skip(1)) Apply(frame);
            }
        }
        private static (Guid Session, Guid Stream, string Origin) Header(byte[] frame)
        {
            using (var reader = Reader(frame))
            {
                if (reader.ReadByte() != 1 || reader.ReadInt32() != 1) throw new InvalidDataException("Unsupported telemetry journal version.");
                var session = Guid(reader); var stream = Guid(reader); var origin = reader.ReadString(); End(reader);
                return (session, stream, origin);
            }
        }
        public void Capture(ArenaWorld world, long observedSequence)
        {
            if (Complete && world.EventSequence == worldCursor) return;
            if (Complete || world.EventSequence < worldCursor) throw new InvalidOperationException("Cannot append to completed or replaced combat world.");
            while (true)
            {
                var events = world.Events(worldCursor); if (events.Length == 0) return;
                var next = new List<TelemetryRecord>();
                foreach (var entry in events.Where(entry => TelemetryRecord.Combat(entry.Kind)))
                {
                    if (reportIds.Contains(entry.EventId)) throw new InvalidDataException("World report identity was already queued.");
                    next.Add(new TelemetryRecord(StreamId, records.Count + next.Count + 1L, observedSequence, entry.EventId, entry.Kind,
                        entry.PlayerId, entry.ShotId ?? System.Guid.Empty, entry.Kind == WorldEventKind.PlayerDamaged ? System.Guid.Empty : entry.EnemyId ?? System.Guid.Empty, entry.Damage, Origin));
                }
                if (next.Count != 0)
                {
                    var frame = Frame(writer => { writer.Write((byte)2); writer.Write(next.Count); foreach (var record in next) Write(writer, record); });
                    journal.Append(frame); Apply(frame); // Publish/acknowledge gameplay only after this durable write.
                }
                worldCursor = events[events.Length - 1].Sequence;
            }
        }
        public void Finish(ArenaWorld world)
        {
            if (Complete) return;
            if (world.Phase != WorldPhase.Ended || world.EventSequence != worldCursor)
                throw new InvalidOperationException("Stop the world and persist its full tail before completing the journal.");
            Commit(Frame(writer => { writer.Write((byte)3); writer.Write(LastSequence); }));
        }
        public void Acknowledge(long sequence, System.Guid report)
        {
            if (sequence >= 1 && sequence <= AcknowledgedSequence && records[(int)sequence - 1].ReportId == report) return;
            if (sequence != AcknowledgedSequence + 1 || sequence > records.Count || records[(int)sequence - 1].ReportId != report)
                throw new InvalidOperationException("Receipt does not acknowledge the next queued report.");
            AcknowledgeThrough(sequence, report);
        }
        public void AcknowledgeThrough(long sequence, System.Guid report)
        {
            if (sequence >= 1 && sequence <= AcknowledgedSequence && records[(int)sequence - 1].ReportId == report) return;
            if (sequence <= AcknowledgedSequence || sequence > records.Count || records[(int)sequence - 1].ReportId != report)
                throw new InvalidOperationException("Cumulative receipt does not match the queued prefix.");
            Commit(Frame(writer => { writer.Write((byte)4); writer.Write(sequence); Guid(writer, report); }));
        }
        public void MarkSealed()
        {
            if (Sealed) return;
            if (!Complete || AcknowledgedSequence != LastSequence) throw new InvalidOperationException("Journal is not fully delivered and complete.");
            Commit(Frame(writer => writer.Write((byte)5)));
        }
        private void Commit(byte[] frame) { journal.Append(frame); Apply(frame); }
        private void Apply(byte[] frame)
        {
            using (var reader = Reader(frame))
            {
                switch (reader.ReadByte())
                {
                    case 2:
                        if (Complete) throw new InvalidDataException("Report appears after journal completion.");
                        var count = reader.ReadInt32(); if (count < 1 || count > 500) throw new InvalidDataException("Invalid telemetry batch.");
                        for (var index = 0; index < count; index++)
                        {
                            var record = Read(reader);
                            if (record.StreamSequence != records.Count + 1L || !reportIds.Add(record.ReportId)) throw new InvalidDataException("Telemetry report order or identity is inconsistent.");
                            records.Add(record);
                        }
                        break;
                    case 3:
                        if (Complete || reader.ReadInt64() != LastSequence) throw new InvalidDataException("Invalid journal completion boundary.");
                        Complete = true; break;
                    case 4:
                        var sequence = reader.ReadInt64(); var report = Guid(reader);
                        if (Sealed || sequence <= AcknowledgedSequence || sequence > records.Count || records[(int)sequence - 1].ReportId != report)
                            throw new InvalidDataException("Invalid persisted telemetry acknowledgment.");
                        AcknowledgedSequence = sequence; break;
                    case 5:
                        if (Sealed || !Complete || AcknowledgedSequence != LastSequence) throw new InvalidDataException("Invalid persisted seal.");
                        Sealed = true; break;
                    default: throw new InvalidDataException("Unknown telemetry journal operation.");
                }
                End(reader);
            }
        }
        private static byte[] Frame(Action<BinaryWriter> write)
        { using (var stream = new MemoryStream()) { using (var writer = new BinaryWriter(stream, System.Text.Encoding.UTF8, true)) write(writer); return stream.ToArray(); } }
        private static BinaryReader Reader(byte[] bytes) => new BinaryReader(new MemoryStream(bytes, false));
        private static void End(BinaryReader reader) { if (reader.BaseStream.Position != reader.BaseStream.Length) throw new InvalidDataException("Unexpected journal frame content."); }
        private static void Guid(BinaryWriter writer, System.Guid id) => writer.Write(id.ToByteArray());
        private static System.Guid Guid(BinaryReader reader)
        { var bytes = reader.ReadBytes(16); if (bytes.Length != 16) throw new InvalidDataException("Truncated telemetry UUID."); return new System.Guid(bytes); }
        private static void Write(BinaryWriter writer, TelemetryRecord record)
        {
            writer.Write(record.StreamSequence); writer.Write(record.ObservedSequence); Guid(writer, record.ReportId); writer.Write((byte)record.Kind);
            Guid(writer, record.PlayerId); Guid(writer, record.ShotId); Guid(writer, record.EnemyId); writer.Write(record.Damage);
        }
        private TelemetryRecord Read(BinaryReader reader) => new TelemetryRecord(StreamId, reader.ReadInt64(), reader.ReadInt64(), Guid(reader),
            (WorldEventKind)reader.ReadByte(), Guid(reader), Guid(reader), Guid(reader), reader.ReadInt32(), Origin);
        public void Dispose() => journal.Dispose();
    }
}
