using System.Text.Json;
using Microsoft.Data.Sqlite;
using VrCommand.Core;

namespace VrCommand.Persistence;

public sealed class SqliteSessionEventStore : ISessionEventStore, IDisposable
{
    private readonly FileStream lease;
    private readonly SqliteConnection connection;
    private bool disposed;
    public string DatabasePath { get; }

    public SqliteSessionEventStore(string directory)
    {
        directory = Path.GetFullPath(directory);
        Directory.CreateDirectory(directory);
        DatabasePath = Path.Combine(directory, "events.db");
        lease = new FileStream(Path.Combine(directory, ".writer.lock"), FileMode.OpenOrCreate,
            FileAccess.ReadWrite, FileShare.None);
        SqliteConnection? initializing = null;
        try
        {
            initializing = new(new SqliteConnectionStringBuilder { DataSource = DatabasePath, Pooling = false }.ToString());
            initializing.Open();
            connection = initializing;
            using var version = connection.CreateCommand();
            version.CommandText = "PRAGMA user_version";
            if ((long)version.ExecuteScalar()! is not (0 or 1))
                throw new InvalidDataException("Unknown SQLite event-store schema.");
            using var setup = connection.CreateCommand();
            setup.CommandText = "PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;";
            setup.ExecuteNonQuery();
            InitializeAndImport(directory);
        }
        catch
        {
            initializing?.Dispose();
            lease.Dispose();
            throw;
        }
    }

    private void InitializeAndImport(string directory)
    {
        using var transaction = connection.BeginTransaction();
        using var schema = connection.CreateCommand();
        schema.Transaction = transaction;
        schema.CommandText = """
            CREATE TABLE IF NOT EXISTS session_events (
                session_id TEXT NOT NULL,
                sequence INTEGER NOT NULL CHECK(sequence > 0),
                event_id TEXT NOT NULL UNIQUE,
                envelope TEXT NOT NULL,
                PRIMARY KEY(session_id, sequence));
            CREATE TABLE IF NOT EXISTS store_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            PRAGMA user_version=1;
            """;
        schema.ExecuteNonQuery();
        using var marker = connection.CreateCommand();
        marker.Transaction = transaction;
        marker.CommandText = "SELECT value FROM store_metadata WHERE key='legacy_import_v1'";
        var migration = marker.ExecuteScalar();
        if (migration is null)
        {
            using var count = connection.CreateCommand();
            count.Transaction = transaction;
            count.CommandText = "SELECT COUNT(*) FROM session_events";
            if ((long)count.ExecuteScalar()! != 0) throw new InvalidDataException("Existing store has no migration marker.");
            var legacy = FileSessionEventStore.ReadLegacy(directory);
            var staging = new MemorySessionEventStore();
            foreach (var events in legacy) staging.Seed(events[0].SessionId, events);
            _ = new SessionManager(staging); // Validate all histories and room conflicts before importing any row.
            foreach (var events in legacy)
                foreach (var entry in events) Insert(transaction, entry);
            marker.CommandText = "INSERT INTO store_metadata(key,value) VALUES('legacy_import_v1','complete')";
            marker.ExecuteNonQuery();
        }
        else if (!Equals(migration, "complete")) throw new InvalidDataException("Unknown migration marker.");
        transaction.Commit(); // Original JSON files remain untouched as migration backups.
    }

    public SessionEvent[][] Load()
    {
        ObjectDisposedException.ThrowIf(disposed, this);
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT session_id,sequence,event_id,envelope FROM session_events ORDER BY session_id,sequence";
        using var reader = command.ExecuteReader();
        var streams = new Dictionary<Guid, List<SessionEvent>>();
        while (reader.Read())
        {
            var entry = JsonSerializer.Deserialize<SessionEvent>(reader.GetString(3), JsonFormat.Options)
                ?? throw new InvalidDataException("Invalid event envelope.");
            if (entry.SessionId.ToString("D") != reader.GetString(0) || entry.Sequence != reader.GetInt64(1)
                || entry.EventId.ToString("D") != reader.GetString(2))
                throw new InvalidDataException("Stored envelope does not match its row identity.");
            if (!streams.TryGetValue(entry.SessionId, out var stream)) streams[entry.SessionId] = stream = [];
            stream.Add(entry);
        }
        return streams.Values.Select(events => events.ToArray()).ToArray();
    }

    public void Append(SessionEvent entry)
    {
        ObjectDisposedException.ThrowIf(disposed, this);
        using var transaction = connection.BeginTransaction();
        using var last = connection.CreateCommand();
        last.Transaction = transaction;
        last.CommandText = "SELECT COALESCE(MAX(sequence),0) FROM session_events WHERE session_id=$session";
        last.Parameters.AddWithValue("$session", entry.SessionId.ToString("D"));
        if (entry.Sequence != (long)last.ExecuteScalar()! + 1)
            throw new InvalidOperationException("Unexpected storage sequence; reload the session.");
        Insert(transaction, entry);
        transaction.Commit();
    }

    private void Insert(SqliteTransaction transaction, SessionEvent entry)
    {
        using var insert = connection.CreateCommand();
        insert.Transaction = transaction;
        insert.CommandText = "INSERT INTO session_events(session_id,sequence,event_id,envelope) VALUES($session,$sequence,$event,$envelope)";
        insert.Parameters.AddWithValue("$session", entry.SessionId.ToString("D"));
        insert.Parameters.AddWithValue("$sequence", entry.Sequence);
        insert.Parameters.AddWithValue("$event", entry.EventId.ToString("D"));
        insert.Parameters.AddWithValue("$envelope", JsonSerializer.Serialize(entry, JsonFormat.Options));
        insert.ExecuteNonQuery();
    }

    public void Dispose()
    {
        if (disposed) return;
        connection.Dispose();
        lease.Dispose();
        disposed = true;
    }
}
