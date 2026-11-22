using System.Text.Json;
using Microsoft.Data.Sqlite;
using VrCommand.Core;
using VrCommand.Simulation;

namespace VrCommand.Api;

public sealed record ReplayClipDraft(Guid StreamId, string Name, long StartFrame, long EndFrame);
public sealed record ReplayClip(Guid Id, Guid StreamId, string Name, long StartFrame, long EndFrame,
    long StartMilliseconds, long EndMilliseconds, DateTimeOffset CreatedAtUtc, bool Deleted);
public sealed record ReplayClipList(Guid SessionId, Guid StreamId, ReplayClip[] Clips);
public sealed record ReplayFrameMark(long Sequence, long ElapsedMilliseconds);
public sealed record ReplayFrameContext(string SessionId, string StreamId, long ThroughFrame,
    ReplayFrameMark Center, ReplayFrameMark Start, ReplayFrameMark End);

public sealed partial class WorldRecordings
{
    private const string ClipSelect = """
        SELECT clip.id,clip.name,clip.first_frame,clip.last_frame,start.elapsed,finish.elapsed,clip.created,clip.deleted
        FROM replay_clips clip
        JOIN world_frames start ON start.session=clip.session AND start.sequence=clip.first_frame
        JOIN world_frames finish ON finish.session=clip.session AND finish.sequence=clip.last_frame
        WHERE clip.session=$session
        """;

    private WorldRecordingInfo ReplayClipRecording(Guid id, OperatorIdentity actor, bool write)
    {
        AccessPolicy.Validate(actor);
        if (write ? actor.Role != OperatorRole.Master : actor.Role is not (OperatorRole.Master or OperatorRole.RoomController))
            throw new AccessDeniedException("Only the master may change shared replay clips. Readers must have operator access.");
        return Info(id, actor);
    }

    public ReplayClipList ReplayClips(Guid id, OperatorIdentity actor)
    {
        var stream = Guid.Parse(ReplayClipRecording(id, actor, write: false).Header.streamId);
        lock (gate)
        {
            using var command = Command(ClipSelect + " AND clip.deleted=0 ORDER BY clip.created,clip.id", ("$session", id.ToString("D")));
            using var rows = command.ExecuteReader();
            var clips = new List<ReplayClip>();
            while (rows.Read()) clips.Add(ReadClip(rows, stream));
            return new(id, stream, clips.ToArray());
        }
    }

    public ReplayFrameContext FrameContext(Guid id, long centerFrame, long throughFrame, OperatorIdentity actor, CancellationToken cancellation)
    {
        const int windowMilliseconds = 5000;
        var info = ReplayClipRecording(id, actor, write: false);
        if (centerFrame < 1 || centerFrame > throughFrame)
            throw new ArgumentException("Use a positive center frame within the saved range.");
        if (throughFrame > info.AcceptedSequence)
            throw new KeyNotFoundException("No saved world frame with this sequence.");

        var session = id.ToString("D");
        lock (gate)
        {
            var center = ReadMark("""
                SELECT sequence, elapsed FROM world_frames WHERE session=$session AND sequence=$center
                """, ("$center", centerFrame));
            var start = ReadMark("""
                SELECT sequence, elapsed FROM world_frames
                WHERE session=$session AND sequence BETWEEN $first AND $center AND elapsed >= $time
                ORDER BY sequence LIMIT 1
                """, ("$first", Math.Max(1, centerFrame - 149)), ("$center", centerFrame),
                ("$time", center.ElapsedMilliseconds - windowMilliseconds));
            var end = ReadMark("""
                SELECT sequence, elapsed FROM world_frames
                WHERE session=$session AND sequence BETWEEN $center AND $last AND elapsed <= $time
                ORDER BY sequence DESC LIMIT 1
                """, ("$center", centerFrame), ("$last", Math.Min(throughFrame, centerFrame + 150)),
                ("$time", center.ElapsedMilliseconds + windowMilliseconds));
            return new(info.Header.sessionId, info.Header.streamId, throughFrame, center, start, end);
        }

        ReplayFrameMark ReadMark(string query, params (string Name, object Value)[] parameters)
        {
            cancellation.ThrowIfCancellationRequested();
            using var command = Command(query, [("$session", session), .. parameters]);
            using var row = command.ExecuteReader();
            if (!row.Read()) throw new InvalidDataException("Saved world frame sequence has a gap.");
            return new(row.GetInt64(0), row.GetInt64(1));
        }
    }

    public ReplayClip SaveReplayClip(Guid id, Guid clipId, ReplayClipDraft draft, OperatorIdentity actor)
    {
        var recording = ReplayClipRecording(id, actor, write: true);
        if (draft is null || clipId == Guid.Empty || draft.StreamId == Guid.Empty || string.IsNullOrWhiteSpace(draft.Name)
            || draft.Name.Length > 60 || draft.Name != draft.Name.Trim() || draft.Name.Any(char.IsControl)
            || draft.StartFrame < 1 || draft.EndFrame <= draft.StartFrame)
            throw new ArgumentException("Provide a clip ID, recording stream, name of 1–60 characters, and ordered positive frame bounds.");
        if (draft.StreamId != Guid.Parse(recording.Header.streamId)) throw new InvalidOperationException("Replay clip recording stream differs.");
        if (draft.EndFrame > recording.AcceptedSequence) throw new ArgumentException("Both replay clip bounds must already be saved.");
        var session = id.ToString("D");
        var key = clipId.ToString("D");
        lock (gate)
        {
            var existing = FindClip(session, key, draft.StreamId);
            if (existing is not null)
            {
                if (existing.Name != draft.Name || existing.StartFrame != draft.StartFrame || existing.EndFrame != draft.EndFrame)
                    throw new InvalidOperationException("Clip ID already identifies a different replay clip.");
                return existing;
            }
            using var count = Command("SELECT COUNT(*) FROM replay_clips WHERE session=$session AND deleted=0", ("$session", session));
            if ((long)count.ExecuteScalar()! >= 24) throw new InvalidOperationException("This recording already has 24 shared replay clips.");
            using var insert = Command("""
                INSERT INTO replay_clips(session,id,name,first_frame,last_frame,created)
                VALUES($session,$id,$name,$first,$last,$created)
                """, ("$session", session), ("$id", key), ("$name", draft.Name), ("$first", draft.StartFrame),
                ("$last", draft.EndFrame), ("$created", DateTimeOffset.UtcNow.ToString("O")));
            insert.ExecuteNonQuery();
            return FindClip(session, key, draft.StreamId)!;
        }
    }

    public void DeleteReplayClip(Guid id, Guid clipId, OperatorIdentity actor)
    {
        ReplayClipRecording(id, actor, write: true);
        lock (gate)
        {
            // Keep the range and name so a delayed PUT cannot recreate a removed clip.
            using var remove = Command("UPDATE replay_clips SET deleted=1 WHERE session=$session AND id=$id",
                ("$session", id.ToString("D")), ("$id", clipId.ToString("D")));
            if (remove.ExecuteNonQuery() == 0) throw new KeyNotFoundException("No shared clip for this recording.");
        }
    }

    private sealed class ReplayPartTooLargeException() : InvalidOperationException("Player replay exceeds 8 MiB.") { }
    private const int PlayerReplayFramesPerFile = 300;
    private const int PlayerReplayFilesPerSet = 24;

    public byte[] ExportPlayerReplay(Guid id, Guid clipId, int? roomId, OperatorIdentity actor, CancellationToken cancellation)
        => PlayerReplayParts(id, clipId, roomId, actor, cancellation, split: false).Single().Data;

    public IEnumerable<(byte[] Data, string Suffix, long LastFrame, long ClipEnd)> PlayerReplayParts(Guid id, Guid clipId, int? roomId,
        OperatorIdentity actor, CancellationToken cancellation, bool split = true, long? fromFrame = null)
    {
        var recording = ReplayClipRecording(id, actor, write: true);
        if (!recording.Complete) throw new InvalidOperationException("Seal the recording before exporting a player replay.");
        var header = recording.Header;
        if (roomId.HasValue && !header.roomIds.Contains(roomId.Value))
            throw new ArgumentException("Select a room within this recording.");
        var session = id.ToString("D");
        ReplayClip clip;
        lock (gate)
        {
            var saved = FindClip(session, clipId.ToString("D"), Guid.Parse(header.streamId));
            if (saved is null || saved.Deleted) throw new KeyNotFoundException("No shared clip for this recording.");
            clip = saved;
        }
        if (!split && clip.EndFrame - clip.StartFrame >= PlayerReplayFramesPerFile)
            throw new InvalidOperationException("Player replay is limited to 300 saved frames.");
        if (fromFrame.HasValue && (fromFrame < clip.StartFrame || fromFrame >= clip.EndFrame))
            throw new ArgumentException("分冊起點須在保存片段內，並至少包含兩格。");
        if (!fromFrame.HasValue && clip.EndFrame - clip.StartFrame >= PlayerReplayFilesPerSet * PlayerReplayFramesPerFile)
            throw new InvalidOperationException("每份回放 ZIP 最多 7,200 格，請縮小片段範圍。");
        Dictionary<string, int>? propRooms = null;
        if (roomId is int room)
        {
            propRooms = header.props.ToDictionary(prop => prop.id, prop => prop.roomId, StringComparer.Ordinal);
            header.roomIds = [room];
            header.props = header.props.Where(prop => prop.roomId == room).ToArray();
        }
        return ReadParts();

        IEnumerable<(byte[] Data, string Suffix, long LastFrame, long ClipEnd)> ReadParts()
        {
            long first = fromFrame ?? clip.StartFrame;
            int files = 0, bytes = 0;
            while (first < clip.EndFrame)
            {
                if (fromFrame.HasValue && files == PlayerReplayFilesPerSet) yield break;
                var remaining = clip.EndFrame - first + 1;
                var count = (int)Math.Min(remaining, PlayerReplayFramesPerFile);
                byte[] data;
                while (true)
                {
                    cancellation.ThrowIfCancellationRequested();
                    if (remaining - count == 1 && count > 2) count--; // Each file needs at least two frames.
                    try
                    {
                        data = WritePlayerReplayRange(id, actor, recording, clip, first, first + count - 1, roomId, propRooms, cancellation);
                        break;
                    }
                    catch (ReplayPartTooLargeException) when (split && count > 2) { count = Math.Max(2, count / 2); }
                }
                // A pair of overlapping two-frame files may be required for the last three dense frames.
                // Keep both in one volume so its successor can always start at the very next frame.
                if (fromFrame.HasValue && files > 0 && remaining == 3 && count == 2) yield break;
                if (++files > PlayerReplayFilesPerSet || (bytes += data.Length) > 64 * 1024 * 1024)
                {
                    if (fromFrame.HasValue) yield break;
                    throw new InvalidOperationException("片段超過播放器一次可開啟的 24 份檔案或 64 MiB，請縮小片段範圍。");
                }
                long last = first + count - 1;
                yield return (data, first == clip.StartFrame && last == clip.EndFrame ? "" : FormattableString.Invariant($"-frames-{first:D6}-{last:D6}"), last, clip.EndFrame);
                if (last == clip.EndFrame) yield break;
                first = Math.Min(last + 1, clip.EndFrame - 1);
            }
        }
    }

    private byte[] WritePlayerReplayRange(Guid id, OperatorIdentity actor, WorldRecordingInfo recording,
        ReplayClip clip, long first, long last, int? roomId, Dictionary<string, int>? propRooms, CancellationToken cancellation)
    {
        const int maxBytes = 8 * 1024 * 1024;
        var header = recording.Header;
        using var output = new MemoryStream();
        using var json = new Utf8JsonWriter(output);
        lock (gate)
        {
            RecordedEnemy[] previousEnemies = roomId.HasValue ? Frame(id, first - 1, actor)?.Packet.frame.enemies ?? [] : [];
            json.WriteStartObject();
            json.WriteNumber("playerReplayVersion", roomId.HasValue ? 2 : 1);
            if (roomId.HasValue) json.WriteNumber("roomId", roomId.Value);
            json.WriteString("missionName", recording.MissionName);
            json.WriteString("clipName", clip.Name);
            json.WriteNumber("startFrame", first);
            json.WriteNumber("endFrame", last);
            json.WritePropertyName("header");
            JsonSerializer.Serialize(json, header, WorldJson.Options);
            json.WriteStartArray("packets");
            var linkedExport = roomId is null && header.roomIds.Length > 1;
            var eventRooms = new Dictionary<string, int>(StringComparer.Ordinal);
            using var command = Command("""
                SELECT packet, statistics
                FROM world_frames WHERE session=$session AND sequence BETWEEN $first AND $last ORDER BY sequence
                """, ("$session", id.ToString("D")), ("$first", first), ("$last", last));
            using var rows = command.ExecuteReader();
            var expected = first;
            while (rows.Read())
            {
                cancellation.ThrowIfCancellationRequested();
                var packet = WorldJson.Read<WorldRecordingPacket>(rows.GetString(0));
                if (packet.sequence != expected++) throw new InvalidOperationException("Replay clip has a missing saved frame.");
                if (roomId is int selectedRoom)
                {
                    var statistics = WorldJson.Read<PlayerStatistics[]>(rows.GetString(1));
                    JsonSerializer.Serialize(json, ProjectReplayRoom(packet, statistics, previousEnemies, propRooms!, selectedRoom), WorldJson.Options);
                    previousEnemies = packet.frame.enemies;
                }
                else
                {
                    if (linkedExport && packet.events.Length > 0)
                    {
                        var visible = packet.frame.players.Select(player => player.id).ToHashSet(StringComparer.Ordinal);
                        var missing = packet.events.Where(entry => !visible.Contains(entry.playerId)).ToArray();
                        if (missing.Length > 0)
                        {
                            var rooms = WorldJson.Read<PlayerStatistics[]>(rows.GetString(1))
                                .ToDictionary(row => row.PlayerId.ToString("D"), row => row.RoomId);
                            foreach (var entry in missing)
                                if (rooms.TryGetValue(entry.playerId, out var roomNumber))
                                    eventRooms.Add(entry.eventId, roomNumber);
                        }
                    }
                    JsonSerializer.Serialize(json, packet, WorldJson.Options);
                }
                json.Flush();
                if (output.Length > maxBytes - 2) throw new ReplayPartTooLargeException();
            }
            if (expected - 1 != last) throw new InvalidOperationException("Replay clip has a missing saved frame.");
            json.WriteEndArray();
            if (eventRooms.Count > 0)
            {
                json.WritePropertyName("eventRooms");
                JsonSerializer.Serialize(json, eventRooms, WorldJson.Options);
            }
        }
        json.WriteEndObject();
        json.Flush();
        if (output.Length > maxBytes) throw new ReplayPartTooLargeException();
        return output.ToArray();
    }

    private static object ProjectReplayRoom(WorldRecordingPacket packet, PlayerStatistics[] statistics, RecordedEnemy[] previousEnemies,
        Dictionary<string, int> propRooms, int roomId)
    {
        var events = RoomCombatEvents(packet, statistics, previousEnemies, propRooms, roomId)
            .Select(entry => new { entry.eventId, entry.tick, entry.kind, entry.playerId, entry.shotId, entry.enemyId, entry.damage,
                entry.hasRay, entry.origin, entry.direction, entry.distance, entry.hit, entry.targetId });
        var frame = packet.frame;
        var roomPolicy = frame.roomEnemyPolicies?.SingleOrDefault(policy => policy.roomId == roomId);
        return new
        {
            packet.sequence, packet.elapsedMilliseconds, packet.suspended, packet.weather, packet.lightning,
            frame = new
            {
                frame.tick, frame.phase, behavior = roomPolicy?.behavior ?? frame.behavior,
                autoAttack = roomPolicy?.autoAttack ?? frame.autoAttack, frame.night, frame.visibility,
                players = frame.players.Where(player => player.roomId == roomId),
                enemies = frame.enemies.Where(enemy => enemy.roomId == roomId)
            },
            events
        };
    }

    private static RecordedEvent[] RoomCombatEvents(WorldRecordingPacket packet, PlayerStatistics[] statistics,
        RecordedEnemy[] previousEnemies, IReadOnlyDictionary<string, int> propRooms, int roomId)
    {
        if (packet.events.Length == 0) return [];
        // Saved player statistics include departures. An enemy removed since the previous frame can still have an event in this packet.
        var players = statistics.ToDictionary(row => row.PlayerId.ToString("D"), row => row.RoomId, StringComparer.Ordinal);
        var enemies = previousEnemies.Concat(packet.frame.enemies).GroupBy(enemy => enemy.id, StringComparer.Ordinal)
            .ToDictionary(group => group.Key, group => group.Last().roomId, StringComparer.Ordinal);
        var roomX = ArenaWorld.RoomOrigin(roomId).X;
        bool LocalTarget(string id)
        {
            var player = players.GetValueOrDefault(id);
            var enemy = enemies.GetValueOrDefault(id);
            var prop = propRooms.GetValueOrDefault(id);
            return (player == roomId || enemy == roomId || prop == roomId)
                && (player == 0 || player == roomId) && (enemy == 0 || enemy == roomId) && (prop == 0 || prop == roomId);
        }

        return packet.events.Where(entry => players.GetValueOrDefault(entry.playerId) == roomId
            && (entry.enemyId.Length == 0 || enemies.GetValueOrDefault(entry.enemyId) == roomId)
            && (entry.targetId.Length == 0 || LocalTarget(entry.targetId))
            && (!entry.hasRay || (Math.Abs(entry.origin.x - roomX) <= 6.01f && Math.Abs(entry.origin.z) <= 6.01f))).ToArray();
    }

    private ReplayClip? FindClip(string session, string id, Guid stream)
    {
        using var command = Command(ClipSelect + " AND clip.id=$id", ("$session", session), ("$id", id));
        using var row = command.ExecuteReader();
        return row.Read() ? ReadClip(row, stream) : null;
    }

    private static ReplayClip ReadClip(SqliteDataReader row, Guid stream) => new(Guid.Parse(row.GetString(0)),
        stream, row.GetString(1), row.GetInt64(2), row.GetInt64(3), row.GetInt64(4), row.GetInt64(5),
        DateTimeOffset.Parse(row.GetString(6)), row.GetInt64(7) != 0);
}
