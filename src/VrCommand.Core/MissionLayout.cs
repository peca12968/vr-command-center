using VrCommand.Simulation;

namespace VrCommand.Core;

public record MissionLayoutRequest(ExperienceMode ExperienceMode, SessionMode Mode, int EnemyCount, PropPlacement[] Props);
public record LayoutSpawn(int Seat, float X, float Z);
public record MissionLayoutReport(int Version, string Profile, string RulesVersion, SessionMode Mode, bool Applies, bool? CanStart,
    float RoomHalfSize, float PlayerRadius, LayoutSpawn[] Spawns, int? EnemyCapacityPerRoom, int RequestedEnemiesPerRoom,
    int TotalIssueCount, bool Truncated, ArenaLayoutIssue[] Issues, int[] InvalidProps);

public sealed class MissionLayoutRejectedException(MissionLayoutReport report) : ArgumentException("VR layout is not startable; inspect the layout report and save a corrected mission revision.")
{ public MissionLayoutReport Report { get; } = report; }

public static class MissionLayout
{
    public static MissionLayoutReport Inspect(MissionDraft definition, SessionMode mode) => Inspect(new(definition.Environment.Mode, mode, definition.Enemies.Count, definition.Props));
    public static MissionLayoutReport Inspect(MissionLayoutRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (!Enum.IsDefined(request.ExperienceMode) || !Enum.IsDefined(request.Mode) || request.EnemyCount is < 0 or > 100
            || request.Props is null || request.Props.Length > 500) throw new ArgumentException("Invalid layout request.");
        var spawns = Enumerable.Range(0, 5).Select(seat => { var point = ArenaSession.Spawn(3, seat); return new LayoutSpawn(seat, point.X, point.Z); }).ToArray();
        if (request.ExperienceMode != ExperienceMode.VR)
            return new(ArenaLayout.Version, "vr-room-v1", "0.8.0", request.Mode, false, null, ArenaLayout.RoomHalfSize, ArenaWalkSurface.Radius,
                spawns, null, 0, 0, false, [], []);
        var props = request.Props.Select(prop => prop is null ? null! : new ManagedProp { assetId = prop.AssetId,
            position = prop.Position is null ? null! : new ManagedPosition { x = prop.Position.X, y = prop.Position.Y, z = prop.Position.Z }, yawDegrees = prop.YawDegrees }).ToArray();
        var result = ArenaLayout.Inspect(props, request.EnemyCount, request.Mode == SessionMode.Linked ? 5 : 1);
        return new(ArenaLayout.Version, "vr-room-v1", "0.8.0", request.Mode, true, result.Valid, ArenaLayout.RoomHalfSize, ArenaWalkSurface.Radius,
            spawns, result.EnemyCapacityPerRoom, result.RequestedEnemiesPerRoom, result.IssueCount, result.Truncated, result.Issues, result.InvalidProps);
    }
    internal static void RequireNewStart(MissionDraft definition, SessionMode mode)
    {
        var report = Inspect(definition, mode);
        if (report.CanStart == false) throw new MissionLayoutRejectedException(report);
    }
}
