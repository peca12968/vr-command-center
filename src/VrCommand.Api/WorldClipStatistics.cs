using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

public record WorldClipStatistics(string SessionId, string StreamId, long FromFrame, long ThroughFrame,
    int? RoomId, Guid? PlayerId, WorldClipPlayerStatistics[] Players);

public record WorldClipPlayerStatistics(Guid PlayerId, string Name, int RoomId, int AmmoUsed, int ShotsHit,
    int Kills, int HitsReceived, int DamageTaken, int MatchedShots)
{
    public decimal? AccuracyPercent => AmmoUsed == 0 ? null : decimal.Round(100m * MatchedShots / AmmoUsed, 2);
}

public sealed partial class WorldRecordings
{
    private sealed class ClipPlayer(PlayerStatistics identity)
    {
        internal PlayerStatistics Identity = identity;
        internal readonly HashSet<string> Fired = new(StringComparer.Ordinal);
        internal int Hits, Kills, HitsReceived, DamageTaken, MatchedShots;
    }

    public WorldClipStatistics ClipStatistics(Guid id, long from, long through, int? room, Guid? playerId,
        OperatorIdentity actor, CancellationToken cancellation)
    {
        if (actor.Role is not (OperatorRole.Master or OperatorRole.RoomController))
            throw new AccessDeniedException("Replay clip statistics require a control desk.");
        if (actor.Role == OperatorRole.RoomController)
        {
            if (room.HasValue && room != actor.RoomId) throw new AccessDeniedException("Select your own room for clip statistics.");
            room = actor.RoomId;
        }
        if (from < 1 || through < from || through - from >= 300)
            throw new ArgumentException("Select up to 300 saved frames in order.");
        var info = Info(id, actor);
        ValidateEventScope(info, through, room, null, playerId);
        var players = new Dictionary<(Guid PlayerId, int RoomId), ClipPlayer>();
        var cursor = from - 1;
        while (cursor < through)
        {
            var candidates = ReadEventCandidates(id, cursor, through, reverse: false, scoped: true, cancellation);
            if (candidates.Count == 0) throw new InvalidDataException("Saved world frame sequence has a gap.");
            foreach (var candidate in candidates)
            {
                cancellation.ThrowIfCancellationRequested();
                if (candidate.Sequence != ++cursor) throw new InvalidDataException("Saved world frame sequence has a gap.");
                if (candidate.Statistics is null) continue;
                var identities = WorldJson.Read<PlayerStatistics[]>(candidate.Statistics).ToDictionary(player => player.PlayerId);
                using var events = JsonDocument.Parse(candidate.Events);
                foreach (var entry in events.RootElement.EnumerateArray())
                {
                    var kind = entry.GetProperty("kind").GetString();
                    if (kind is not ("ShotFired" or "ShotHit" or "EnemyEliminated" or "PlayerDamaged")) continue;
                    var player = entry.GetProperty("playerId").GetGuid();
                    if (playerId.HasValue && playerId.Value != player) continue;
                    if (!identities.TryGetValue(player, out var identity)) throw new InvalidDataException("Recorded combat has no player statistics.");
                    if (room.HasValue && identity.RoomId != room.Value) continue;
                    var key = (player, identity.RoomId);
                    if (!players.TryGetValue(key, out var row)) players.Add(key, row = new(identity));
                    row.Identity = identity;
                    switch (kind)
                    {
                        case "ShotFired": row.Fired.Add(entry.GetProperty("shotId").GetString()!); break;
                        case "ShotHit":
                            row.Hits++;
                            if (row.Fired.Contains(entry.GetProperty("shotId").GetString()!)) row.MatchedShots++;
                            break;
                        case "EnemyEliminated": row.Kills++; break;
                        case "PlayerDamaged": row.HitsReceived++; row.DamageTaken += entry.GetProperty("damage").GetInt32(); break;
                    }
                }
            }
        }
        return new(info.Header.sessionId, info.Header.streamId, from, through, room, playerId,
            players.Values.OrderBy(row => row.Identity.RoomId).ThenBy(row => row.Identity.PlayerId)
                .Select(row => new WorldClipPlayerStatistics(row.Identity.PlayerId, row.Identity.Name, row.Identity.RoomId,
                    row.Fired.Count, row.Hits, row.Kills, row.HitsReceived, row.DamageTaken, row.MatchedShots)).ToArray());
    }
}
