using System.Text;

namespace VrCommand.Api;

internal static class ClipStatisticsCsv
{
    internal static string FileName(WorldClipStatistics report)
    {
        var room = report.RoomId is int roomId ? FormattableString.Invariant($"-room-{roomId:00}") : "";
        var player = report.PlayerId is Guid playerId ? $"-player-{playerId:D}" : "";
        return FormattableString.Invariant($"vr-command-clip-statistics-v1-{report.SessionId}-{report.FromFrame}-{report.ThroughFrame}{room}{player}.csv");
    }

    internal static byte[] Encode(WorldClipStatistics report)
    {
        var csv = new StringBuilder("\uFEFF");
        CsvReportRows.Append(csv, "reportVersion", "rowType", "sessionId", "streamId", "fromFrame", "throughFrame",
            "reportRoomId", "reportPlayerId", "playerId", "playerName", "playerRoomId", "ammoUsed", "shotsHit", "matchedShots",
            "kills", "hitsReceived", "damageTaken", "accuracyPercent");
        if (report.Players.Length == 0) AppendPlayer(null);
        else foreach (var player in report.Players) AppendPlayer(player);
        return Encoding.UTF8.GetBytes(csv.ToString());

        void AppendPlayer(WorldClipPlayerStatistics? player) => CsvReportRows.Append(csv,
            1, player is null ? "Clip" : "Player", report.SessionId, report.StreamId, report.FromFrame, report.ThroughFrame,
            report.RoomId, report.PlayerId, player?.PlayerId, player is null ? null : CsvReportRows.Text(player.Name),
            player?.RoomId, player?.AmmoUsed, player?.ShotsHit, player?.MatchedShots, player?.Kills, player?.HitsReceived,
            player?.DamageTaken, player?.AccuracyPercent);
    }
}
