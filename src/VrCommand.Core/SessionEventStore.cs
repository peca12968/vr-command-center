using System.Text.Json;

namespace VrCommand.Core;

public interface ISessionEventStore
{
    SessionEvent[][] Load();
    void Save(Guid sessionId, SessionEvent[] events);
}

public sealed class MemorySessionEventStore : ISessionEventStore
{
    private readonly Dictionary<Guid, SessionEvent[]> streams = [];
    public SessionEvent[][] Load() => streams.Values.Select(events => events.ToArray()).ToArray();
    public void Save(Guid sessionId, SessionEvent[] events) => streams[sessionId] = [.. events];
}

// A single process per directory; file replacement is for low-frequency management events.
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
        return Directory.EnumerateFiles(directory, "*.json")
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
    }

    public void Save(Guid sessionId, SessionEvent[] events)
    {
        ObjectDisposedException.ThrowIf(disposed, this);
        var destination = Path.Combine(directory, $"{sessionId:D}.json");
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
