namespace VrCommand.Core;

public enum CombatKind { Unspecified, ShotFired, ShotHit, EnemyEliminated, PlayerDamaged }
public enum CombatOrigin { Unspecified, Simulation, GameServer }
public record CombatReport(Guid ReportId, CombatKind Kind, CombatOrigin Origin, Guid PlayerId,
    Guid? ShotId = null, Guid? EnemyId = null, int Damage = 0);
public record PlayerStatistics(Guid PlayerId, string Name, int RoomId, long AmmoUsed = 0,
    long ShotsHit = 0, long Kills = 0, long HitsReceived = 0, long DamageTaken = 0, int Health = 100)
{
    public decimal AccuracyPercent => AmmoUsed == 0 ? 0 : decimal.Round(100m * ShotsHit / AmmoUsed, 2);

    public PlayerStatistics ApplyDamage(int damage)
    {
        var loss = Math.Min(damage, Health);
        return this with { HitsReceived = checked(HitsReceived + 1), DamageTaken = checked(DamageTaken + loss), Health = Health - loss };
    }
}
public record SessionStatistics(Guid SessionId, long ThroughSequence, CombatOrigin? Origin, PlayerStatistics[] Players, bool PendingTelemetry = false);
public record CombatReceipt(Guid ReportId, long AppliedAtSequence, bool Duplicate, SessionStatistics Statistics);

// Incremental projection. A prepared change is applied only after its event has committed to storage.
internal sealed class CombatLedger
{
    private record Shot(Guid PlayerId, Guid FiredReportId, Guid? EnemyId = null, Guid? HitReportId = null, Guid? KillReportId = null);
    private readonly Dictionary<Guid, Shot> shots = [];
    private readonly HashSet<Guid> eliminated = [];
    private readonly Dictionary<Guid, PlayerStatistics> players = [];
    private readonly Dictionary<Guid, SessionEvent> reports = [];
    private CombatOrigin? origin;

    internal static void Validate(CombatReport report)
    {
        ArgumentNullException.ThrowIfNull(report);
        if (report.ReportId == Guid.Empty || report.PlayerId == Guid.Empty
            || !Enum.IsDefined(report.Kind) || report.Kind == CombatKind.Unspecified
            || !Enum.IsDefined(report.Origin) || report.Origin == CombatOrigin.Unspecified)
            throw new ArgumentException("Report ID, player, combat kind and explicit origin are required.");
        if (report.Kind == CombatKind.PlayerDamaged)
        {
            if (report.ShotId is not null || report.EnemyId is not null || report.Damage is < 1 or > 1000)
                throw new ArgumentException("PlayerDamaged requires damage 1–1000 and no shot/enemy fields.");
        }
        else
        {
            if (report.ShotId is null || report.ShotId == Guid.Empty || report.Damage != 0)
                throw new ArgumentException("Shot reports require a shot ID and zero player damage.");
            if (report.Kind == CombatKind.ShotFired ? report.EnemyId is not null
                : report.EnemyId is null || report.EnemyId == Guid.Empty)
                throw new ArgumentException("Only hit/elimination reports require an enemy ID.");
        }
    }

    internal SessionEvent? Find(Guid reportId) => reports.GetValueOrDefault(reportId);
    internal SessionEvent[] ShotReports(Guid shotId) => shots.TryGetValue(shotId, out var shot)
        ? new Guid?[] { shot.FiredReportId, shot.HitReportId, shot.KillReportId }.OfType<Guid>().Select(id => reports[id]).ToArray() : [];
    internal SessionStatistics Snapshot(Guid sessionId, long sequence) => new(sessionId, sequence, origin,
        players.Values.OrderBy(p => p.RoomId).ThenBy(p => p.PlayerId).ToArray());

    internal Action Prepare(SessionView? before, SessionEvent entry)
    {
        if (entry.Kind == SessionEventKind.PlayerJoined)
        {
            var joined = entry.Read<Player>();
            return () => players[joined.Id] = new(joined.Id, joined.Name, joined.RoomId);
        }
        if (entry.Kind is not (SessionEventKind.CombatRecorded or SessionEventKind.StreamCombatRecorded)) return static () => { };
        if (before is null || before.State != SessionState.Running)
            throw new InvalidOperationException("New combat reports require a running session.");
        var report = entry.Kind == SessionEventKind.StreamCombatRecorded ? entry.Read<StreamCombatRecord>().Report : entry.Read<CombatReport>();
        Validate(report);
        if (reports.ContainsKey(report.ReportId)) throw new InvalidDataException("Repeated combat report ID in history.");
        if (origin.HasValue && origin != report.Origin)
            throw new InvalidOperationException("Simulation and game-server data cannot be mixed in one session.");
        if (!players.TryGetValue(report.PlayerId, out var statistic))
            throw new ArgumentException("Combat player never joined this session.");
        if (report.Kind is CombatKind.ShotFired or CombatKind.PlayerDamaged)
        {
            if (!before.Players.Any(p => p.Id == report.PlayerId) || statistic.Health == 0)
                throw new InvalidOperationException("Firing and damage require an active, living player.");
        }
        var shot = report.ShotId.HasValue ? shots.GetValueOrDefault(report.ShotId.Value) : null;
        switch (report.Kind)
        {
            case CombatKind.ShotFired:
                if (shot is not null) throw new InvalidOperationException("Shot ID already exists.");
                statistic = statistic with { AmmoUsed = checked(statistic.AmmoUsed + 1) };
                break;
            case CombatKind.ShotHit:
                if (shot is null || shot.PlayerId != report.PlayerId || shot.EnemyId is not null)
                    throw new InvalidOperationException("Hit requires this player's previously fired, unscored shot.");
                if (eliminated.Contains(report.EnemyId!.Value)) throw new InvalidOperationException("Enemy was already eliminated.");
                statistic = statistic with { ShotsHit = checked(statistic.ShotsHit + 1) };
                break;
            case CombatKind.EnemyEliminated:
                if (shot is null || shot.PlayerId != report.PlayerId || shot.EnemyId != report.EnemyId)
                    throw new InvalidOperationException("Elimination must reference a confirmed hit on the same enemy.");
                if (eliminated.Contains(report.EnemyId!.Value)) throw new InvalidOperationException("Enemy elimination already credited.");
                statistic = statistic with { Kills = checked(statistic.Kills + 1) };
                break;
            case CombatKind.PlayerDamaged:
                statistic = statistic.ApplyDamage(report.Damage);
                break;
        }
        return () =>
        {
            origin ??= report.Origin;
            players[report.PlayerId] = statistic;
            reports.Add(report.ReportId, entry);
            if (report.Kind == CombatKind.ShotFired) shots.Add(report.ShotId!.Value, new(report.PlayerId, report.ReportId));
            if (report.Kind == CombatKind.ShotHit)
                shots[report.ShotId!.Value] = shot! with { EnemyId = report.EnemyId, HitReportId = report.ReportId };
            if (report.Kind == CombatKind.EnemyEliminated)
            {
                eliminated.Add(report.EnemyId!.Value);
                shots[report.ShotId!.Value] = shot! with { KillReportId = report.ReportId };
            }
        };
    }
}
