using System.Text.Json;
using Microsoft.Data.Sqlite;
using VrCommand.Core;

namespace VrCommand.Persistence;

public record MissionRevision(Mission Mission, Guid SeriesId, int Number, Guid? PreviousId, OperatorIdentity Author);
public record MissionVersionInfo(Guid Id, Guid SeriesId, int Number, Guid? PreviousId, DateTimeOffset CreatedAtUtc, string Name, OperatorIdentity Author);
public record MissionHistory(Guid SeriesId, Guid HeadId, int HeadNumber, MissionVersionInfo[] Versions, int? NextBefore);

public sealed class SqliteMissionLibrary : IDisposable
{
    private readonly object gate = new();
    private readonly FileStream lease;
    private readonly SqliteConnection db;
    private bool disposed;

    public SqliteMissionLibrary(string directory)
    {
        Directory.CreateDirectory(directory);
        lease = new(Path.Combine(directory, ".library-writer.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        db = new(new SqliteConnectionStringBuilder { DataSource = Path.Combine(directory, "missions.db"), Pooling = false }.ToString());
        try
        {
            db.Open();
            using var version = Command("PRAGMA user_version");
            if ((long)version.ExecuteScalar()! is not (0 or 1)) throw new InvalidDataException("Unknown mission library schema.");
            using var settings = Command("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;"); settings.ExecuteNonQuery();
            using var transaction = db.BeginTransaction();
            using var schema = Command("""
                CREATE TABLE IF NOT EXISTS missions (
                  id TEXT PRIMARY KEY, series TEXT NOT NULL REFERENCES missions(id), revision INTEGER NOT NULL CHECK(revision>0),
                  previous TEXT REFERENCES missions(id), created TEXT NOT NULL, name TEXT NOT NULL, body TEXT NOT NULL,
                  author TEXT NOT NULL, request TEXT UNIQUE, UNIQUE(series,revision));
                CREATE TABLE IF NOT EXISTS library_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                PRAGMA user_version=1;
                """, transaction);
            schema.ExecuteNonQuery();
            using var marker = Command("SELECT value FROM library_metadata WHERE key='legacy_import'", transaction);
            var migration = marker.ExecuteScalar();
            if (migration is null)
            {
                using var count = Command("SELECT COUNT(*) FROM missions", transaction);
                if ((long)count.ExecuteScalar()! != 0) throw new InvalidDataException("Mission library is missing its import marker.");
                foreach (var file in Directory.EnumerateFiles(directory, "*.json"))
                {
                    if (!Guid.TryParse(Path.GetFileNameWithoutExtension(file), out var id)) continue;
                    var mission = ReadMission(File.ReadAllText(file), id);
                    Insert(new(mission, id, 1, null, OperatorIdentity.Internal), null, transaction);
                }
                using var done = Command("INSERT INTO library_metadata(key,value) VALUES('legacy_import','complete')", transaction); done.ExecuteNonQuery();
            }
            else if (!Equals(migration, "complete")) throw new InvalidDataException("Unknown mission import marker.");
            ValidateCatalog(transaction);
            transaction.Commit(); // Existing JSON files remain untouched; the catalog becomes authoritative.
        }
        catch { db.Dispose(); lease.Dispose(); throw; }
    }

    private SqliteCommand Command(string sql, SqliteTransaction? transaction = null, params (string Key, object Value)[] values)
    {
        var command = db.CreateCommand(); command.CommandText = sql; command.Transaction = transaction;
        foreach (var (key, value) in values) command.Parameters.AddWithValue(key, value);
        return command;
    }
    private static string Write<T>(T value) => JsonSerializer.Serialize(value, JsonFormat.Options);
    private static T Read<T>(string json) => JsonSerializer.Deserialize<T>(json, JsonFormat.Options) ?? throw new InvalidDataException("Missing mission library data.");
    private static Mission ReadMission(string body, Guid id)
    {
        try
        {
            var mission = Read<Mission>(body);
            if (id == Guid.Empty || mission.Id != id || mission.SchemaVersion != 1) throw new InvalidDataException("Unsupported or inconsistent mission snapshot.");
            MissionStore.Validate(mission.Definition); return mission;
        }
        catch (Exception error) when (error is JsonException or ArgumentException) { throw new InvalidDataException("Invalid mission snapshot.", error); }
    }
    private static MissionRevision ReadRevision(SqliteDataReader row)
    {
        var author = Read<OperatorIdentity>(row.GetString(6)); AccessPolicy.AuthorMission(author);
        var mission = ReadMission(row.GetString(5), Guid.Parse(row.GetString(0)));
        if (mission.CreatedAtUtc.ToString("O") != row.GetString(4)) throw new InvalidDataException("Mission creation time disagrees with catalog.");
        return new(mission, Guid.Parse(row.GetString(1)), row.GetInt32(2), row.IsDBNull(3) ? null : Guid.Parse(row.GetString(3)), author);
    }
    private const string Columns = "id,series,revision,previous,created,body,author";
    private void ValidateCatalog(SqliteTransaction transaction)
    {
        using var relation = Command("""
            SELECT COUNT(*) FROM missions m WHERE
              NOT EXISTS(SELECT 1 FROM missions root WHERE root.id=m.series AND root.series=root.id AND root.revision=1 AND root.previous IS NULL)
              OR (m.revision=1 AND (m.id<>m.series OR m.previous IS NOT NULL))
              OR (m.revision>1 AND NOT EXISTS(SELECT 1 FROM missions p WHERE p.id=m.previous AND p.series=m.series AND p.revision=m.revision-1))
            """, transaction);
        if ((long)relation.ExecuteScalar()! != 0) throw new InvalidDataException("Mission revision chain is inconsistent.");
        using var command = Command("SELECT " + Columns + ",name FROM missions", transaction); using var rows = command.ExecuteReader();
        while (rows.Read())
        {
            var revision = ReadRevision(rows);
            if (revision.Mission.Definition.Name != rows.GetString(7)) throw new InvalidDataException("Mission name disagrees with catalog.");
        }
    }
    private MissionRevision Find(Guid id, SqliteTransaction? transaction = null)
    {
        using var command = Command("SELECT " + Columns + " FROM missions WHERE id=$id", transaction, ("$id", id.ToString("D")));
        using var row = command.ExecuteReader(); if (!row.Read()) throw new KeyNotFoundException("Mission does not exist.");
        return ReadRevision(row);
    }
    public Mission Get(Guid id, OperatorIdentity? actor = null) { AccessPolicy.ReadMission(actor ?? OperatorIdentity.Internal); lock (gate) { ObjectDisposedException.ThrowIf(disposed, this); return Find(id).Mission; } }
    public MissionRevision Version(Guid id, OperatorIdentity? actor = null) { AccessPolicy.ReadMission(actor ?? OperatorIdentity.Internal); lock (gate) { ObjectDisposedException.ThrowIf(disposed, this); return Find(id); } }
    public Mission[] List(OperatorIdentity? actor = null)
    {
        AccessPolicy.ReadMission(actor ?? OperatorIdentity.Internal);
        lock (gate)
        {
            ObjectDisposedException.ThrowIf(disposed, this);
            using var command = Command("SELECT " + Columns + " FROM missions ORDER BY created DESC,id"); using var rows = command.ExecuteReader();
            var result = new List<Mission>(); while (rows.Read()) result.Add(ReadRevision(rows).Mission); return result.ToArray();
        }
    }
    public MissionRevision[] Heads(OperatorIdentity? actor = null)
    {
        AccessPolicy.ReadMission(actor ?? OperatorIdentity.Internal);
        lock (gate)
        {
            ObjectDisposedException.ThrowIf(disposed, this);
            using var command = Command("SELECT " + Columns + " FROM missions m WHERE revision=(SELECT MAX(revision) FROM missions WHERE series=m.series) ORDER BY created DESC,id");
            using var rows = command.ExecuteReader(); var result = new List<MissionRevision>(); while (rows.Read()) result.Add(ReadRevision(rows)); return result.ToArray();
        }
    }
    public MissionHistory History(Guid id, int? before = null, int limit = 20, OperatorIdentity? actor = null)
    {
        AccessPolicy.ReadMission(actor ?? OperatorIdentity.Internal);
        if (before is <= 0 || limit is < 1 or > 100) throw new ArgumentException("History before must be positive and limit must be 1–100.");
        lock (gate)
        {
            ObjectDisposedException.ThrowIf(disposed, this);
            var series = Find(id).SeriesId;
            using var head = Command("SELECT id,revision FROM missions WHERE series=$series ORDER BY revision DESC LIMIT 1", null, ("$series", series.ToString("D")));
            Guid headId; int headNumber;
            using (var row = head.ExecuteReader()) { row.Read(); headId = Guid.Parse(row.GetString(0)); headNumber = row.GetInt32(1); }
            using var command = Command("SELECT id,revision,previous,created,name,author FROM missions WHERE series=$series AND revision<$before ORDER BY revision DESC LIMIT $limit", null,
                ("$series", series.ToString("D")), ("$before", (long?)before ?? (long)int.MaxValue + 1), ("$limit", limit + 1));
            using var rows = command.ExecuteReader(); var result = new List<MissionVersionInfo>();
            while (rows.Read()) result.Add(new(Guid.Parse(rows.GetString(0)), series, rows.GetInt32(1), rows.IsDBNull(2) ? null : Guid.Parse(rows.GetString(2)),
                DateTimeOffset.Parse(rows.GetString(3)), rows.GetString(4), Read<OperatorIdentity>(rows.GetString(5))));
            var more = result.Count > limit; if (more) result.RemoveAt(result.Count - 1);
            return new(series, headId, headNumber, result.ToArray(), more ? result[^1].Number : null);
        }
    }
    public Mission Create(MissionDraft draft, OperatorIdentity actor, Guid? requestId = null) => Save(null, draft, actor, requestId);
    public Mission Revise(Guid previousId, MissionDraft draft, OperatorIdentity actor, Guid requestId)
    {
        if (previousId == Guid.Empty || requestId == Guid.Empty) throw new ArgumentException("Revision requires nonempty previous mission and request IDs.");
        return Save(previousId, draft, actor, requestId);
    }
    private Mission Save(Guid? previousId, MissionDraft draft, OperatorIdentity actor, Guid? requestId)
    {
        AccessPolicy.AuthorMission(actor); MissionStore.Validate(draft);
        if (requestId == Guid.Empty) throw new ArgumentException("Mission request ID cannot be empty.");
        var definition = Write(draft); var author = Write(actor);
        lock (gate)
        {
            ObjectDisposedException.ThrowIf(disposed, this);
            using var transaction = db.BeginTransaction();
            if (requestId is not null)
            {
                using var replay = Command("SELECT " + Columns + " FROM missions WHERE request=$request", transaction, ("$request", requestId.Value.ToString("D")));
                using var row = replay.ExecuteReader();
                if (row.Read())
                {
                    var saved = ReadRevision(row);
                    if (saved.PreviousId != previousId || Write(saved.Mission.Definition) != definition || Write(saved.Author) != author)
                        throw new InvalidOperationException("Mission request ID already identifies a different author or operation.");
                    return saved.Mission; // Confirm accepted history even if a newer revision now exists.
                }
            }
            var id = Guid.NewGuid(); var series = id; var number = 1;
            if (previousId is not null)
            {
                var previous = Find(previousId.Value, transaction); series = previous.SeriesId;
                using var next = Command("SELECT MAX(revision) FROM missions WHERE series=$series", transaction, ("$series", series.ToString("D")));
                if ((long)next.ExecuteScalar()! != previous.Number) throw new InvalidOperationException("This mission has a newer revision. Preserve the draft and load the latest version or save a separate mission.");
                if (previous.Number == int.MaxValue) throw new InvalidOperationException("Mission revision number is exhausted.");
                number = previous.Number + 1;
            }
            var mission = new Mission(id, 1, DateTimeOffset.UtcNow, Read<MissionDraft>(definition));
            Insert(new(mission, series, number, previousId, actor), requestId, transaction); transaction.Commit();
            return mission;
        }
    }
    private void Insert(MissionRevision revision, Guid? requestId, SqliteTransaction transaction)
    {
        var mission = revision.Mission;
        using var command = Command("INSERT INTO missions(id,series,revision,previous,created,name,body,author,request) VALUES($id,$series,$revision,$previous,$created,$name,$body,$author,$request)", transaction,
            ("$id", mission.Id.ToString("D")), ("$series", revision.SeriesId.ToString("D")), ("$revision", revision.Number),
            ("$previous", (object?)revision.PreviousId?.ToString("D") ?? DBNull.Value), ("$created", mission.CreatedAtUtc.ToString("O")),
            ("$name", mission.Definition.Name), ("$body", Write(mission)), ("$author", Write(revision.Author)), ("$request", (object?)requestId?.ToString("D") ?? DBNull.Value));
        command.ExecuteNonQuery();
    }
    public void Dispose() { lock (gate) { if (disposed) return; disposed = true; db.Dispose(); lease.Dispose(); } }
}
