using System.Globalization;
using System.Text;
using VrCommand.Core;

namespace VrCommand.Api;

public static class FinalReportCsv
{
    public static string FileName(Guid sessionId) => $"vr-command-report-v1-{sessionId:D}.csv";

    public static byte[] Encode(FinalSessionReport report)
    {
        var csv = new StringBuilder("\uFEFF");
        Row("reportVersion", "rowType", "sessionId", "missionId", "missionName", "sessionMode", "roomIds",
            "createdAtUtc", "startedAtUtc", "endedAtUtc", "plannedDurationSeconds", "throughSequence", "origin",
            "streamId", "finalStreamSequence", "playerId", "playerName", "playerRoomId", "ammoUsed", "shotsHit",
            "kills", "damageTaken", "hitsReceived", "accuracyPercent", "health");
        // A session with no historical players still exports its identity and completion boundary.
        if (report.Players.Length == 0) PlayerRow(null);
        else foreach (var player in report.Players) PlayerRow(player);
        return Encoding.UTF8.GetBytes(csv.ToString());

        void PlayerRow(PlayerStatistics? player) => Row(
            report.ReportVersion, player is null ? "Session" : "Player", report.SessionId, report.MissionId,
            Text(report.MissionName), report.Mode, string.Join('|', report.RoomIds),
            report.CreatedAtUtc.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
            report.StartedAtUtc?.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
            report.EndedAtUtc.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
            report.PlannedDurationSeconds, report.ThroughSequence, report.Origin?.ToString() ?? "None",
            report.StreamId, report.FinalStreamSequence, player?.PlayerId, player is null ? null : Text(player.Name),
            player?.RoomId, player?.AmmoUsed, player?.ShotsHit, player?.Kills, player?.DamageTaken,
            player?.HitsReceived, player?.AccuracyPercent, player?.Health);

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
