using System.Globalization;
using System.IO.Compression;
using System.Text;
using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

public static class FinalReportCsv
{
    public static string FileName(Guid sessionId) => $"vr-command-report-v1-{sessionId:D}.csv";

    public static string FileName(Guid sessionId, int? roomId) =>
        roomId is int room ? FormattableString.Invariant($"vr-command-report-v1-{sessionId:D}-room-{room:00}.csv")
            : FileName(sessionId);

    internal static byte[] EncodeBundle(FinalSessionReport report)
    {
        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            WriteCsv(archive, report);
            foreach (var room in report.RoomIds) WriteCsv(archive, report.ForRoom(room));
        }
        return output.ToArray();
    }

    internal static byte[] EncodeVenueBundle(FinalVenueReport venue)
    {
        var sessions = venue.Sessions.Select(session =>
        {
            var rooms = session.Report.RoomIds.Select(session.Report.ForRoom);
            return (Session: session, Files: (session.Report.Mode == SessionMode.Linked ? rooms.Prepend(session.Report) : rooms).ToArray());
        }).ToArray();
        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            using (var manifest = OpenEntry(archive, "manifest.json"))
                JsonSerializer.Serialize(manifest, new
                {
                    schemaVersion = 1,
                    venue.RequestId,
                    venue.RecordedAtUtc,
                    sessions = sessions.Select(item => new
                    {
                        item.Session.Report.SessionId,
                        item.Session.Report.RoomIds,
                        item.Session.AppliedAtSequence,
                        item.Session.Report.ThroughSequence,
                        files = item.Files.Select(file => new { roomId = file.ReportRoomId, name = FileName(file.SessionId, file.ReportRoomId) })
                    })
                }, JsonFormat.Options);
            foreach (var item in sessions)
                foreach (var file in item.Files) WriteCsv(archive, file);
        }
        return output.ToArray();
    }

    private static void WriteCsv(ZipArchive archive, FinalSessionReport report)
    {
        using var stream = OpenEntry(archive, FileName(report.SessionId, report.ReportRoomId));
        stream.Write(Encode(report));
    }

    private static Stream OpenEntry(ZipArchive archive, string name)
    {
        var entry = archive.CreateEntry(name);
        // CSV records the source timestamps. The ZIP adds no export timestamp.
        entry.LastWriteTime = new DateTimeOffset(1980, 1, 1, 0, 0, 0, TimeSpan.Zero);
        return entry.Open();
    }

    public static byte[] Encode(FinalSessionReport report)
    {
        var csv = new StringBuilder("\uFEFF");
        string[] columns = ["reportVersion", "rowType", "sessionId", "missionId", "missionName", "sessionMode", "roomIds",
            "createdAtUtc", "startedAtUtc", "endedAtUtc", "plannedDurationSeconds", "throughSequence", "origin",
            "streamId", "finalStreamSequence", "playerId", "playerName", "playerRoomId", "ammoUsed", "shotsHit",
            "kills", "damageTaken", "hitsReceived", "accuracyPercent", "health"];
        Row(report.ReportRoomId.HasValue ? [.. columns, "reportRoomId"] : columns);
        // A session with no historical players still exports its identity and completion boundary.
        if (report.Players.Length == 0) PlayerRow(null);
        else foreach (var player in report.Players) PlayerRow(player);
        return Encoding.UTF8.GetBytes(csv.ToString());

        void PlayerRow(PlayerStatistics? player)
        {
            object?[] fields = [
                report.ReportVersion, player is null ? "Session" : "Player", report.SessionId, report.MissionId,
                Text(report.MissionName), report.Mode, string.Join('|', report.RoomIds),
                report.CreatedAtUtc.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                report.StartedAtUtc?.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                report.EndedAtUtc.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                report.PlannedDurationSeconds, report.ThroughSequence, report.Origin?.ToString() ?? "None",
                report.StreamId, report.FinalStreamSequence, player?.PlayerId, player is null ? null : Text(player.Name),
                player?.RoomId, player?.AmmoUsed, player?.ShotsHit, player?.Kills, player?.DamageTaken,
                player?.HitsReceived, player?.AccuracyPercent, player?.Health];
            Row(report.ReportRoomId is int room ? [.. fields, room] : fields);
        }

        void Row(params object?[] cells)
        {
            csv.AppendJoin(',', cells.Select(cell => "\"" +
                (Convert.ToString(cell, CultureInfo.InvariantCulture) ?? "").Replace("\"", "\"\"") + "\""));
            csv.Append("\r\n");
        }
    }

    private static string Text(string value)
    {
        // Quoting alone does not stop a spreadsheet from evaluating a formula.
        // Preserve the original text after an explicit apostrophe; JSON/statistics are untouched.
        var first = value.AsSpan().TrimStart();
        return value.Any(char.IsControl) || first.Length > 0 && "=+-@".Contains(first[0]) ? "'" + value : value;
    }
}
