using Microsoft.Data.Sqlite;
using VrCommand.Core;

namespace VrCommand.Api;

public sealed record ReplayClipDraft(Guid StreamId, string Name, long StartFrame, long EndFrame);
public sealed record ReplayClip(Guid Id, Guid StreamId, string Name, long StartFrame, long EndFrame,
    long StartMilliseconds, long EndMilliseconds, DateTimeOffset CreatedAtUtc, bool Deleted);
public sealed record ReplayClipList(Guid SessionId, Guid StreamId, ReplayClip[] Clips);

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
