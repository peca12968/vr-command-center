using System.Text.Json;

namespace VrCommand.Core;

public interface ISessionEventStore
{
    SessionEvent[][] Load();
    void Append(SessionEvent entry);
}

public interface IAtomicSessionEventStore : ISessionEventStore
{
    void AppendBatch(SessionEvent[] entries);
}

public sealed class MemorySessionEventStore : IAtomicSessionEventStore
{
    private readonly Dictionary<Guid, List<SessionEvent>> streams = [];
    public SessionEvent[][] Load() => streams.Values.Select(events => events.ToArray()).ToArray();
    public void Append(SessionEvent entry)
    {
        var existing = streams.TryGetValue(entry.SessionId, out var events);
        events ??= [];
        if (entry.Sequence != events.Count + 1) throw new InvalidOperationException("Unexpected storage sequence.");
        if (!existing) streams.Add(entry.SessionId, events);
        events.Add(entry);
    }
    public void Seed(Guid sessionId, SessionEvent[] events) => streams[sessionId] = [.. events];

    public void AppendBatch(SessionEvent[] entries)
    {
        if (entries.Length == 0) throw new InvalidOperationException("An atomic batch requires events.");
        var through = new Dictionary<Guid, long>();
        foreach (var entry in entries)
        {
            var prior = through.GetValueOrDefault(entry.SessionId, streams.GetValueOrDefault(entry.SessionId)?.Count ?? 0);
            if (entry.Sequence != prior + 1) throw new InvalidOperationException("Unexpected storage sequence in the batch.");
            through[entry.SessionId] = entry.Sequence;
        }
        foreach (var entry in entries) Append(entry);
    }
}

// Legacy JSON compatibility adapter. The HTTP service uses the transactional SQLite store.
public sealed class FileSessionEventStore : ISessionEventStore, IDisposable
{
    private readonly string directory;
    private readonly FileStream lease;
    private bool disposed;

    public FileSessionEventStore(string directory)
    {
        this.directory = Path.GetFullPath(directory);
        Directory.CreateDirectory(this.directory);
        lease = new FileStream(Path.Combine(this.directory, ".writer.lock"), FileMode.OpenOrCreate,
            FileAccess.ReadWrite, FileShare.None);
    }

    public SessionEvent[][] Load()
    {
        ObjectDisposedException.ThrowIf(disposed, this);
        return ReadLegacy(directory);
    }

    public static SessionEvent[][] ReadLegacy(string directory) => !Directory.Exists(directory) ? [] :
        Directory.EnumerateFiles(directory, "*.json")
        .Select(path =>
        {
            if (!Guid.TryParse(Path.GetFileNameWithoutExtension(path), out var id))
                throw new InvalidDataException($"Unexpected session history filename: {Path.GetFileName(path)}");
            var entries = JsonSerializer.Deserialize<SessionEvent[]>(File.ReadAllText(path), JsonFormat.Options)
                ?? throw new InvalidDataException("Invalid session history file.");
            if (entries.Length == 0 || entries.Any(entry => entry is null || entry.SessionId != id))
                throw new InvalidDataException("Session history identity does not match its filename.");
            return entries;
        }).ToArray();

    public void Append(SessionEvent entry)
    {
        ObjectDisposedException.ThrowIf(disposed, this);
        var previous = Load().SingleOrDefault(events => events[0].SessionId == entry.SessionId) ?? [];
        if (entry.Sequence != previous.Length + 1) throw new InvalidOperationException("Unexpected storage sequence.");
        SessionEvent[] events = [.. previous, entry];
        var destination = Path.Combine(directory, $"{entry.SessionId:D}.json");
        var temporary = destination + ".tmp";
        try
        {
            using (var stream = new FileStream(temporary, FileMode.Create, FileAccess.Write, FileShare.None))
            {
                JsonSerializer.Serialize(stream, events, JsonFormat.Options);
                stream.Flush(flushToDisk: true);
            }
            File.Move(temporary, destination, overwrite: true);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }

    public void Dispose()
    {
        lease.Dispose();
        disposed = true;
    }
}
