using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Data.Sqlite;
using VrCommand.Core;
using VrCommand.Simulation;

namespace VrCommand.Api;

public static class WorldJson
{
    public static JsonSerializerOptions Options { get; } = new(JsonFormat.Options)
    {
        IncludeFields = true, WriteIndented = false,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow, MaxDepth = 32
    };
    public static string Write<T>(T value) => JsonSerializer.Serialize(value, Options);
    public static T Read<T>(string value)
    {
        var result = JsonSerializer.Deserialize<T>(value, Options) ?? throw new ArgumentException("Missing world data.");
        if (result is WorldRecordingPacket packet) WorldRecordingValidation.NormalizeLegacyPresentation(packet);
        return result;
    }
}

public record WorldRecordingInfo(WorldRecordingHeader Header, long AcceptedSequence, long DurationMilliseconds, bool Complete, DateTimeOffset UpdatedAtUtc, string MissionName, DateTimeOffset? CapturedAtUtc)
{
    public required Guid MissionId { get; init; }
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public DebriefReceiptView? DebriefReceipts { get; init; }
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public WorldTrackedVrStart? TrackedVrStart { get; init; }
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? ObserverRoomId { get; init; }
}
public record WorldFrameView(WorldRecordingPacket Packet, PlayerStatistics[] Statistics)
{
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? ObserverRoomId { get; init; }
}
public record WorldRecordingPage(WorldRecordingInfo[] Recordings, WorldRecordingInfo[] Pinned, Guid? NextBefore);

// Indexed, append-only frames are read on demand; startup never loads an entire world recording.
// This instance shares the session store's process lease and uses its own synchronous SQLite transactions.
public sealed partial class WorldRecordings : IDisposable
{
    private const int RecordingListBatchSize = 128;
    private readonly record struct RecordingRow(string Header, long Accepted, long Duration, bool Complete, string Updated)
    {
        internal static RecordingRow Read(SqliteDataReader row) =>
            new(row.GetString(0), row.GetInt64(1), row.GetInt64(2), row.GetInt64(3) != 0, row.GetString(4));

        internal WorldRecordingInfo ToInfo(Mission mission)
        {
            var header = WorldJson.Read<WorldRecordingHeader>(Header);
            var captured = header.captureStartedAtUtc == "" ? (DateTimeOffset?)null
                : DateTimeOffset.ParseExact(header.captureStartedAtUtc, "O", System.Globalization.CultureInfo.InvariantCulture).AddMilliseconds(Duration);
            return new(header, Accepted, Duration, Complete, DateTimeOffset.Parse(Updated), mission.Definition.Name, captured) { MissionId = mission.Id };
        }
    }

    private readonly object gate = new();
    private readonly SqliteConnection db;
    private readonly SessionManager manager;
    private readonly TimeProvider readinessClock;

    public WorldRecordings(string directory, SessionManager manager, TimeProvider? clock = null)
    {
        this.manager = manager;
        readinessClock = clock ?? TimeProvider.System;
        db = new(new SqliteConnectionStringBuilder { DataSource = Path.Combine(directory, "worlds.db"), Pooling = false }.ToString());
        try
        {
            db.Open();
            using var version = Command("PRAGMA user_version");
            if ((long)version.ExecuteScalar()! is not (0 or 1)) throw new InvalidDataException("Unknown world archive schema.");
            using var setup = Command("""
                PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS recordings (
                  session TEXT PRIMARY KEY, header TEXT NOT NULL, accepted INTEGER NOT NULL DEFAULT 0,
                  duration INTEGER NOT NULL DEFAULT 0, complete INTEGER NOT NULL DEFAULT 0, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS world_frames (
                  session TEXT NOT NULL REFERENCES recordings(session), sequence INTEGER NOT NULL,
                  elapsed INTEGER NOT NULL, packet TEXT NOT NULL, statistics TEXT NOT NULL,
                  PRIMARY KEY(session, sequence));
                CREATE INDEX IF NOT EXISTS world_time ON world_frames(session, elapsed, sequence);
                CREATE TABLE IF NOT EXISTS world_event_ids (
                  session TEXT NOT NULL REFERENCES recordings(session), event TEXT NOT NULL, PRIMARY KEY(session, event));
                CREATE TABLE IF NOT EXISTS camera_bookmarks (
                  session TEXT NOT NULL REFERENCES recordings(session), owner TEXT NOT NULL, id TEXT NOT NULL,
                  body TEXT NOT NULL, created TEXT NOT NULL, deleted INTEGER NOT NULL DEFAULT 0,
                  PRIMARY KEY(session, owner, id));
                CREATE TABLE IF NOT EXISTS replay_clips (
                  session TEXT NOT NULL REFERENCES recordings(session), id TEXT NOT NULL, name TEXT NOT NULL,
                  first_frame INTEGER NOT NULL, last_frame INTEGER NOT NULL,
                  created TEXT NOT NULL, deleted INTEGER NOT NULL DEFAULT 0,
                  PRIMARY KEY(session, id),
                  FOREIGN KEY(session, first_frame) REFERENCES world_frames(session, sequence),
                  FOREIGN KEY(session, last_frame) REFERENCES world_frames(session, sequence));
                CREATE TABLE IF NOT EXISTS connection_endpoints (
                  session TEXT PRIMARY KEY REFERENCES recordings(session), stream TEXT NOT NULL,
                  owner TEXT NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS managed_connection_endpoints (
                  session TEXT PRIMARY KEY REFERENCES connection_endpoints(session));
                CREATE TABLE IF NOT EXISTS debrief_receipts (
                  session TEXT NOT NULL REFERENCES recordings(session), admission TEXT NOT NULL,
                  PRIMARY KEY(session, admission));
                PRAGMA user_version=1;
                """);
            setup.ExecuteNonQuery();
        }
        catch { db.Dispose(); throw; }
    }

    private SqliteCommand Command(string sql, params (string Key, object Value)[] parameters)
    {
        var command = db.CreateCommand(); command.CommandText = sql;
        foreach (var (key, value) in parameters) command.Parameters.AddWithValue(key, value);
        return command;
    }

    private SessionView Owner(Guid id, OperatorIdentity actor)
    {
        AccessPolicy.ReportCombat(actor);
        var view = manager.Get(id, actor);
        if (view.CombatStream is null) throw new InvalidOperationException("Attach the combat stream first.");
        if (view.CombatStream.Owner != actor) throw new AccessDeniedException("World publisher must own the combat stream.");
        return view;
    }

    public WorldRecordingInfo Open(Guid id, WorldRecordingHeader header, OperatorIdentity actor)
    {
        var view = Owner(id, actor); WorldRecordingValidation.Header(header);
        if (header.sessionId != id.ToString("D") || header.streamId != view.CombatStream!.StreamId.ToString("D")
            || header.origin != view.CombatStream.Origin.ToString() || header.missionClockVersion != view.CombatStream.MissionClockVersion
            || (header.missionClockVersion == 1 && header.missionDurationSeconds != view.Mission.Definition.DurationSeconds))
            throw new InvalidOperationException("World and combat stream identities or clock capabilities disagree.");
        // Rebuild only canonical mission geometry, not a running or recovered world.
        var bridge = new ArenaSession();
        var source = JsonSerializer.Serialize(view with { State = SessionState.Preparing }, JsonFormat.Options);
        var management = JsonSerializer.Deserialize<ManagementSnapshot>(source, new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true })!;
        bridge.Apply(management);
        var expected = WorldRecordingHeader.Create(id, view.CombatStream.StreamId, header.origin, view.RoomIds, bridge.Props, header.captureStartedAtUtc, header.environmentVersion, header.assetSet, header.enemyPresentationVersion, header.weaponPresentationVersion, header.enemyFireVersion, header.playerFireVersion, header.combatAudioVersion, header.playerPresentationVersion, header.missionClockVersion, header.missionDurationSeconds);
        expected.reinforcementVersion = header.reinforcementVersion;
        if (bridge.IsMixedReality) expected.calibration = WorldRecordingHeader.QuestMixedRealityProfile;
        var json = WorldJson.Write(header);
        lock (gate)
        {
            using var existing = Command("SELECT header FROM recordings WHERE session=$id", ("$id", id.ToString("D")));
            if (existing.ExecuteScalar() is string saved)
            {
                if (WorldJson.Write(WorldJson.Read<WorldRecordingHeader>(saved)) != json) throw new InvalidOperationException("Recording header is immutable.");
                return Info(id, actor);
            }
            if (json != WorldJson.Write(expected)) throw new InvalidOperationException("Recording profile and geometry must match the session's canonical mission.");
            using var insert = Command("INSERT INTO recordings(session,header,updated) VALUES($id,$header,$updated)",
                ("$id", id.ToString("D")), ("$header", json), ("$updated", DateTimeOffset.UtcNow.ToString("O")));
            insert.ExecuteNonQuery(); return Info(id, actor);
        }
    }

    public WorldRecordingInfo Info(Guid id, OperatorIdentity actor)
    {
        var session = manager.Get(id, actor);
        RecordingRow recording;
        lock (gate)
        {
            using var command = Command("SELECT header,accepted,duration,complete,updated FROM recordings WHERE session=$id", ("$id", id.ToString("D")));
            using var row = command.ExecuteReader();
            if (!row.Read()) throw new KeyNotFoundException("No world recording for this session.");
            recording = RecordingRow.Read(row);
        }
        return recording.ToInfo(session.Mission);
    }

    public WorldRecordingInfo[] List(OperatorIdentity actor, CancellationToken cancellation = default)
    {
        cancellation.ThrowIfCancellationRequested();
        return ReadRecordings(manager.List(true, actor), cancellation).ToArray();
    }

    public WorldRecordingPage Page(OperatorIdentity actor, int limit, Guid? before, Guid[] include, CancellationToken cancellation)
    {
        if (limit is < 1 or > 50 || before == Guid.Empty || include.Length > 6 || include.Contains(Guid.Empty))
            throw new ArgumentException("Use a page size from 1 to 50 and at most six nonempty recording IDs.");
        cancellation.ThrowIfCancellationRequested();
        var sessions = manager.List(true, actor);
        var start = 0;
        if (before is Guid cursor)
        {
            var index = Array.FindIndex(sessions, session => session.Id == cursor);
            if (index < 0 || !ReadRecordings([sessions[index]], cancellation).Any())
                throw new KeyNotFoundException("No world recording for the requested cursor.");
            start = index + 1;
        }
        var page = ReadRecordings(sessions.Skip(start), cancellation, limit + 1).Take(limit + 1).ToArray();
        var recordings = page.Take(limit).ToArray();
        var returned = recordings.Select(row => Guid.Parse(row.Header.sessionId)).ToHashSet();
        var requested = include.ToHashSet();
        var pinned = ReadRecordings(sessions.Where(session => !returned.Contains(session.Id)
            && (requested.Contains(session.Id) || (before is null && session.State != SessionState.Ended))), cancellation).ToArray();
        return new(recordings, pinned, page.Length > limit ? Guid.Parse(recordings[^1].Header.sessionId) : null);
    }

    private IEnumerable<WorldRecordingInfo> ReadRecordings(IEnumerable<SessionView> sessions, CancellationToken cancellation,
        int batchSize = RecordingListBatchSize)
    {
        cancellation.ThrowIfCancellationRequested();
        foreach (var batch in sessions.Chunk(batchSize))
        {
            cancellation.ThrowIfCancellationRequested();
            var ids = batch.Select(session => session.Id.ToString("D")).ToArray();
            var encoded = WorldJson.Write(ids);
            var recordings = new Dictionary<string, RecordingRow>(batch.Length, StringComparer.Ordinal);
            lock (gate)
            {
                cancellation.ThrowIfCancellationRequested();
                using var command = Command("""
                    SELECT r.header,r.accepted,r.duration,r.complete,r.updated,r.session
                    FROM json_each($ids) wanted CROSS JOIN recordings r WHERE r.session=wanted.value
                    """, ("$ids", encoded));
                using var rows = command.ExecuteReader();
                while (rows.Read())
                {
                    cancellation.ThrowIfCancellationRequested();
                    recordings.Add(rows.GetString(5), RecordingRow.Read(rows));
                }
            }
            for (var index = 0; index < batch.Length; index++)
            {
                cancellation.ThrowIfCancellationRequested();
                if (recordings.TryGetValue(ids[index], out var recording))
                    yield return recording.ToInfo(batch[index].Mission);
            }
        }
    }

    public WorldFrameView? Frame(Guid id, long sequence, OperatorIdentity actor)
    {
        manager.Get(id, actor);
        lock (gate)
        {
            using var command = Command("SELECT packet,statistics FROM world_frames WHERE session=$id AND sequence=$seq", ("$id", id.ToString("D")), ("$seq", sequence));
            using var row = command.ExecuteReader();
            if (!row.Read()) return null;
            var statistics = WorldJson.Read<PlayerStatistics[]>(row.GetString(1));
            // Older projections could add the full final hit even though the saved health was already capped at zero.
            for (var index = 0; index < statistics.Length; index++)
                if (statistics[index] is { Health: 0, DamageTaken: > 100 } player)
                    statistics[index] = player with { DamageTaken = 100 };
            return new(WorldJson.Read<WorldRecordingPacket>(row.GetString(0)), statistics);
        }
    }

    public long Seek(Guid id, long milliseconds, OperatorIdentity actor)
    {
        manager.Get(id, actor);
        if (milliseconds < 0) throw new ArgumentException("Seek time must be nonnegative.");
        lock (gate)
        {
            using var command = Command("SELECT sequence FROM world_frames WHERE session=$id AND elapsed <= $time ORDER BY elapsed DESC,sequence DESC LIMIT 1",
                ("$id", id.ToString("D")), ("$time", milliseconds));
            return command.ExecuteScalar() is long sequence ? sequence : 1;
        }
    }

    public WorldRecordingInfo Append(Guid id, WorldRecordingPacket packet, OperatorIdentity actor)
    {
        Owner(id, actor);
        lock (gate)
        {
            var info = Info(id, actor); var json = WorldJson.Write(packet);
            if (packet.sequence <= info.AcceptedSequence)
            {
                var accepted = Frame(id, packet.sequence, actor);
                if (accepted is null || WorldJson.Write(accepted.Packet) != json) throw new InvalidOperationException("Frame sequence already has different content.");
                return info;
            }
            if (info.Complete || info.AcceptedSequence >= 1000000) throw new InvalidOperationException("Recording is closed or at its frame limit.");
            var previous = Frame(id, info.AcceptedSequence, actor);
            WorldRecordingValidation.Packet(info.Header, packet, previous?.Packet);
            if (previous?.Packet.frame.phase == "Ended" || packet.observedSequence < (previous?.Packet.observedSequence ?? 1)) throw new InvalidOperationException("Recording cannot resume or rewind management.");
            var observed = manager.Observed(id, packet.observedSequence, actor);
            if (packet.frame.phase != observed.State.ToString() && !(packet.suspended && packet.frame.phase == "Paused" && observed.State == SessionState.Running))
                throw new InvalidOperationException("Recorded phase disagrees with its management observation.");
            if (packet.frame.behavior != observed.Enemies.Behavior.ToString() || packet.frame.autoAttack != observed.Enemies.AutoAttack
                || packet.weather != observed.Environment.Weather.ToString() || packet.lightning != observed.Environment.Lightning
                || packet.frame.night != (observed.Environment.TimeOfDay == TimeOfDay.Night)
                || packet.frame.visibility != (observed.Environment.Weather is Weather.Fog or Weather.Storm ? observed.Environment.Weather.ToString() : "Clear"))
                throw new InvalidOperationException("Recorded policy disagrees with its management observation.");
            var roomPolicies = packet.frame.roomEnemyPolicies ?? [];
            if (!roomPolicies.Select(policy => (policy.roomId, policy.behavior, policy.autoAttack)).SequenceEqual(
                (observed.RoomEnemyPolicies ?? []).Select(policy => (policy.RoomId, policy.Behavior.ToString(), policy.AutoAttack))))
                throw new InvalidOperationException("Recorded room enemy policy disagrees with its management observation.");
            if (observed.Players.Any(player => !packet.frame.players.Any(body => body.id == player.Id.ToString("D") && body.roomId == player.RoomId)))
                throw new InvalidOperationException("Recording must include every admitted player body.");
            RequireEnemyRoster(info.Header, observed.Enemies.Count, packet.frame);
            var stats = (previous?.Statistics ?? []).ToDictionary(player => player.PlayerId);
            foreach (var player in observed.Players)
                stats[player.Id] = stats.TryGetValue(player.Id, out var existingPlayer)
                    ? existingPlayer with { Name = player.Name, RoomId = player.RoomId }
                    : new(player.Id, player.Name, player.RoomId);
            var through = previous?.Packet.throughCombatSequence ?? 0;
            foreach (var entry in packet.events)
            {
                if (!Enum.TryParse<CombatKind>(entry.kind, out var kind)) continue;
                var witness = manager.CombatWitness(id, Guid.Parse(entry.eventId), actor);
                var report = witness.Report;
                if (witness.StreamId.ToString("D") != info.Header.streamId || witness.StreamSequence != ++through || witness.ObservedSequence > packet.observedSequence
                    || report.Origin.ToString() != info.Header.origin || report.Kind != kind || report.PlayerId.ToString("D") != entry.playerId
                    || report.Damage != entry.damage || (report.ShotId?.ToString("D") ?? "") != entry.shotId
                    || (kind != CombatKind.PlayerDamaged && (report.EnemyId?.ToString("D") ?? "") != entry.enemyId))
                    throw new InvalidOperationException("Recorded event disagrees with its durable combat report.");
                if (!stats.TryGetValue(report.PlayerId, out var player))
                {
                    var admitted = manager.Statistics(id, actor).Players.Single(value => value.PlayerId == report.PlayerId);
                    player = new(admitted.PlayerId, admitted.Name, admitted.RoomId);
                }
                stats[report.PlayerId] = kind switch
                {
                    CombatKind.ShotFired => player with { AmmoUsed = player.AmmoUsed + 1 },
                    CombatKind.ShotHit => player with { ShotsHit = player.ShotsHit + 1 },
                    CombatKind.EnemyEliminated => player with { Kills = player.Kills + 1 },
                    CombatKind.PlayerDamaged => player.ApplyDamage(report.Damage),
                    _ => throw new InvalidOperationException("Unknown recorded combat event.")
                };
            }
            if (through != packet.throughCombatSequence) throw new InvalidOperationException("Combat boundary mismatch.");
            foreach (var player in packet.frame.players)
            {
                if (info.Header.calibration == WorldRecordingHeader.QuestMixedRealityProfile && player.connected && player.rig.kind != "Tracked")
                    throw new InvalidOperationException("Connected MR player bodies require tracked rigs.");
                var playerId = Guid.Parse(player.id);
                if (!stats.TryGetValue(playerId, out var statistic) || statistic.RoomId != player.roomId || statistic.Health != player.health
                    || (player.connected && !observed.Players.Any(admitted => admitted.Id == playerId && admitted.RoomId == player.roomId)))
                    throw new InvalidOperationException("Recorded player health or admission disagrees with accepted history.");
                if (player.magazine + player.reserve != 120 - statistic.AmmoUsed) throw new InvalidOperationException("Recorded ammunition disagrees with combat reports.");
            }
            using var transaction = db.BeginTransaction();
            using var insert = Command("INSERT INTO world_frames(session,sequence,elapsed,packet,statistics) VALUES($id,$seq,$elapsed,$packet,$stats)",
                ("$id", id.ToString("D")), ("$seq", packet.sequence), ("$elapsed", packet.elapsedMilliseconds), ("$packet", json),
                ("$stats", WorldJson.Write(stats.Values.OrderBy(player => player.RoomId).ThenBy(player => player.PlayerId).ToArray())));
            insert.Transaction = transaction; insert.ExecuteNonQuery();
            foreach (var entry in packet.events)
            {
                using var unique = Command("INSERT INTO world_event_ids(session,event) VALUES($id,$event)", ("$id", id.ToString("D")), ("$event", entry.eventId));
                unique.Transaction = transaction;
                try { unique.ExecuteNonQuery(); } catch (SqliteException exception) when (exception.SqliteErrorCode == 19) { throw new InvalidOperationException("Duplicate recorded event ID."); }
            }
            using var update = Command("UPDATE recordings SET accepted=$seq,duration=$elapsed,updated=$updated WHERE session=$id",
                ("$seq", packet.sequence), ("$elapsed", packet.elapsedMilliseconds), ("$updated", DateTimeOffset.UtcNow.ToString("O")), ("$id", id.ToString("D")));
            update.Transaction = transaction; update.ExecuteNonQuery(); transaction.Commit(); return Info(id, actor);
        }
    }

    private static void RequireEnemyRoster(WorldRecordingHeader header, int target, RecordedFrame frame)
    {
        if ((header.reinforcementVersion == 0 || frame.phase == "Preparing") && frame.enemies.Length != target)
            throw new InvalidOperationException("Recorded enemy roster disagrees with management.");
        if (header.reinforcementVersion == 0) return;
        var rooms = header.roomIds.Order().ToArray();
        for (var index = 0; index < rooms.Length; index++)
        {
            var room = rooms[index];
            var limit = target / rooms.Length + (index < target % rooms.Length ? 1 : 0);
            if (frame.enemies.Count(enemy => enemy.roomId == room) > limit)
                throw new InvalidOperationException("Recorded enemy roster exceeds its room's reinforcement target.");
        }
    }

    public WorldRecordingInfo Seal(Guid id, long finalSequence, OperatorIdentity actor)
    {
        var view = Owner(id, actor);
        lock (gate)
        {
            var info = Info(id, actor); var last = Frame(id, info.AcceptedSequence, actor);
            if (finalSequence != info.AcceptedSequence || last?.Packet.frame.phase != "Ended" || view.State != SessionState.Ended
                || view.CombatStream is not { Sealed: true } stream || stream.AcceptedSequence != last.Packet.throughCombatSequence)
                throw new InvalidOperationException("Final Ended frame and sealed combat boundary are required.");
            var expected = manager.Statistics(id, actor).Players;
            foreach (var player in expected)
            {
                var recorded = last.Statistics.SingleOrDefault(value => value.PlayerId == player.PlayerId) ?? new(player.PlayerId, player.Name, player.RoomId);
                if (recorded != player) throw new InvalidOperationException("Final recording statistics disagree with accepted combat history.");
            }
            using var update = Command("UPDATE recordings SET complete=1 WHERE session=$id", ("$id", id.ToString("D")));
            update.ExecuteNonQuery(); return Info(id, actor);
        }
    }
    public void Dispose() => db.Dispose();
}
