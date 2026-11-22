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

    public static string FileName(Guid sessionId, Guid playerId) => $"vr-command-report-v1-{sessionId:D}-player-{playerId:D}.csv";

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

    internal static byte[] EncodeVenueBundle(FinalVenueReport venue, bool includeScores)
    {
        const string scoresName = "scores.csv";
        var sessions = venue.Sessions.Select(session =>
        {
            var rooms = session.Report.RoomIds.Select(session.Report.ForRoom);
            return (Session: session, Files: (session.Report.Mode == SessionMode.Linked ? rooms.Prepend(session.Report) : rooms).ToArray());
        }).ToArray();
        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            var manifestData = new Dictionary<string, object>
            {
                ["schemaVersion"] = 1,
                ["requestId"] = venue.RequestId,
                ["recordedAtUtc"] = venue.RecordedAtUtc,
                ["sessions"] = sessions.Select(item => new
                {
                    item.Session.Report.SessionId,
                    item.Session.Report.RoomIds,
                    item.Session.AppliedAtSequence,
                    item.Session.Report.ThroughSequence,
                    files = item.Files.Select(file => new { roomId = file.ReportRoomId, name = FileName(file.SessionId, file.ReportRoomId) })
                })
            };
            if (includeScores) manifestData["scoresFile"] = scoresName;
            using (var manifest = OpenEntry(archive, "manifest.json"))
                JsonSerializer.Serialize(manifest, manifestData, JsonFormat.Options);
            foreach (var item in sessions)
                foreach (var file in item.Files) WriteCsv(archive, file);
            if (includeScores)
            {
                using var scores = OpenEntry(archive, scoresName);
                scores.Write(EncodeVenueScores(VenueBattleScores.From(venue)));
            }
        }
        return output.ToArray();
    }

    internal static byte[] EncodeVenueScores(VenueBattleScores scores)
    {
        var csv = new StringBuilder("\uFEFF");
        CsvReportRows.Append(csv, "reportVersion", "rowType", "requestId", "sessionId", "roomId", "players", "ammoUsed",
            "shotsHit", "kills", "hitsReceived", "damageTaken", "accuracyPercent");
        foreach (var room in scores.Rooms) WriteRow("Room", room.SessionId, room.RoomId, room.Totals);
        WriteRow("Total", null, null, scores.Total);
        return Encoding.UTF8.GetBytes(csv.ToString());

        void WriteRow(string type, Guid? sessionId, int? roomId, VenueBattleTotals totals) =>
            CsvReportRows.Append(csv, 1, type, scores.RequestId, sessionId, roomId, totals.Players, totals.AmmoUsed,
                totals.ShotsHit, totals.Kills, totals.HitsReceived, totals.DamageTaken,
                totals.AccuracyPercent.ToString("0.##", CultureInfo.InvariantCulture));
    }

    internal static byte[] EncodeVenuePlayerReports(FinalVenueReport venue)
    {
        var index = new StringBuilder("\uFEFF");
        CsvReportRows.Append(index, "requestId", "sessionId", "roomId", "playerId", "playerName", "file");
        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            foreach (var session in venue.Sessions)
            {
                var report = session.Report;
                foreach (var player in report.Players.OrderBy(p => p.RoomId).ThenBy(p => p.PlayerId))
                {
                    var file = FormattableString.Invariant($"room-{player.RoomId:00}/{FileName(report.SessionId, player.PlayerId)}");
                    using var entry = OpenEntry(archive, file);
                    entry.Write(Encode(report with { Players = [player] }));
                    CsvReportRows.Append(index, venue.RequestId, report.SessionId, player.RoomId, player.PlayerId,
                        CsvReportRows.Text(player.Name), file);
                }
            }
            using var list = OpenEntry(archive, "index.csv");
            list.Write(Encoding.UTF8.GetBytes(index.ToString()));
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
                CsvReportRows.Text(report.MissionName), report.Mode, string.Join('|', report.RoomIds),
                report.CreatedAtUtc.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                report.StartedAtUtc?.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                report.EndedAtUtc.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                report.PlannedDurationSeconds, report.ThroughSequence, report.Origin?.ToString() ?? "None",
                report.StreamId, report.FinalStreamSequence, player?.PlayerId, player is null ? null : CsvReportRows.Text(player.Name),
                player?.RoomId, player?.AmmoUsed, player?.ShotsHit, player?.Kills, player?.DamageTaken,
                player?.HitsReceived, player?.AccuracyPercent, player?.Health];
            Row(report.ReportRoomId is int room ? [.. fields, room] : fields);
        }

        void Row(params object?[] cells) => CsvReportRows.Append(csv, cells);
    }
}

internal static class CsvReportRows
{
    internal static void Append(StringBuilder csv, params object?[] cells)
    {
        csv.AppendJoin(',', cells.Select(cell => "\"" +
            (Convert.ToString(cell, CultureInfo.InvariantCulture) ?? "").Replace("\"", "\"\"") + "\""));
        csv.Append("\r\n");
    }

    internal static string Text(string value)
    {
        // Quoting alone does not stop a spreadsheet from evaluating a formula.
        // Preserve the original text after an explicit apostrophe; JSON/statistics are untouched.
        var first = value.AsSpan().TrimStart();
        return value.Any(char.IsControl) || first.Length > 0 && "=+-@".Contains(first[0]) ? "'" + value : value;
    }
}
