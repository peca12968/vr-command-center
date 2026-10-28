using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

public record CameraView(double[] Target, double Theta, double Phi, double Radius);
public record CameraBookmarkDraft(string Name, CameraView View);
public record CameraBookmark(Guid Id, string Name, CameraView View, DateTimeOffset CreatedAtUtc, bool Deleted);

public sealed partial class WorldRecordings
{
    private string BookmarkOwner(Guid id, OperatorIdentity actor)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role is not (OperatorRole.Master or OperatorRole.RoomController))
            throw new AccessDeniedException("Camera bookmarks require an operator identity.");
        Info(id, actor); // Check current room scope and recording existence on every request.
        return JsonSerializer.Serialize(actor, JsonFormat.Options);
    }

    public CameraBookmark[] Bookmarks(Guid id, OperatorIdentity actor)
    {
        var owner = BookmarkOwner(id, actor);
        lock (gate)
        {
            using var command = Command("SELECT id,body,created,deleted FROM camera_bookmarks WHERE session=$session AND owner=$owner AND deleted=0 ORDER BY created,id",
                ("$session", id.ToString("D")), ("$owner", owner));
            using var rows = command.ExecuteReader(); var result = new List<CameraBookmark>();
            while (rows.Read()) result.Add(ReadBookmark(rows.GetString(0), rows.GetString(1), rows.GetString(2), rows.GetInt64(3) != 0));
            return result.ToArray();
        }
    }

    public CameraBookmark SaveBookmark(Guid id, Guid bookmarkId, CameraBookmarkDraft draft, OperatorIdentity actor)
    {
        var owner = BookmarkOwner(id, actor);
        if (bookmarkId == Guid.Empty || draft is null || string.IsNullOrWhiteSpace(draft.Name)
            || draft.Name.Length > 60 || draft.Name != draft.Name.Trim() || draft.Name.Any(char.IsControl))
            throw new ArgumentException("Provide a bookmark ID and a name of 1–60 characters without surrounding whitespace or control characters.");
        var view = draft.View;
        if (view is null || view.Target is null || view.Target.Length != 3 || view.Target.Any(x => !double.IsFinite(x) || Math.Abs(x) > 120)
            || !double.IsFinite(view.Theta) || view.Theta is < -Math.PI or > Math.PI
            || !double.IsFinite(view.Phi) || view.Phi is < .06 or > 1.5
            || !double.IsFinite(view.Radius) || view.Radius is < 2 or > 240)
            throw new ArgumentException("Camera target must be within ±120 metres, azimuth ±pi, elevation .06–1.5 and distance 2–240 metres.");
        var body = WorldJson.Write(draft);
        lock (gate)
        {
            using (var existing = Command("SELECT body,created,deleted FROM camera_bookmarks WHERE session=$session AND owner=$owner AND id=$id",
                ("$session", id.ToString("D")), ("$owner", owner), ("$id", bookmarkId.ToString("D"))))
            {
                using var row = existing.ExecuteReader();
                if (row.Read())
                {
                    if (row.GetString(0) != body) throw new InvalidOperationException("Bookmark ID already identifies a different camera position.");
                    return ReadBookmark(bookmarkId.ToString("D"), body, row.GetString(1), row.GetInt64(2) != 0);
                }
            }
            using var count = Command("SELECT COUNT(*) FROM camera_bookmarks WHERE session=$session AND owner=$owner AND deleted=0",
                ("$session", id.ToString("D")), ("$owner", owner));
            if ((long)count.ExecuteScalar()! >= 24) throw new InvalidOperationException("This operator already has 24 camera positions for this recording. Remove one before saving another.");
            var created = DateTimeOffset.UtcNow.ToString("O");
            using var insert = Command("INSERT INTO camera_bookmarks(session,owner,id,body,created) VALUES($session,$owner,$id,$body,$created)",
                ("$session", id.ToString("D")), ("$owner", owner), ("$id", bookmarkId.ToString("D")), ("$body", body), ("$created", created));
            insert.ExecuteNonQuery(); return ReadBookmark(bookmarkId.ToString("D"), body, created, false);
        }
    }

    public void DeleteBookmark(Guid id, Guid bookmarkId, OperatorIdentity actor)
    {
        var owner = BookmarkOwner(id, actor);
        lock (gate)
        {
            // Retain the immutable body so a late save retry cannot resurrect a removed position.
            using var remove = Command("UPDATE camera_bookmarks SET deleted=1 WHERE session=$session AND owner=$owner AND id=$id",
                ("$session", id.ToString("D")), ("$owner", owner), ("$id", bookmarkId.ToString("D")));
            if (remove.ExecuteNonQuery() == 0) throw new KeyNotFoundException("No camera position for this operator and recording.");
        }
    }

    private static CameraBookmark ReadBookmark(string id, string body, string created, bool deleted)
    {
        var draft = WorldJson.Read<CameraBookmarkDraft>(body);
        return new(Guid.Parse(id), draft.Name, draft.View, DateTimeOffset.Parse(created), deleted);
    }
}
