using System.Text.Json.Serialization;
using VrCommand.Simulation;

namespace VrCommand.Core;

public record FloorPoint([property: JsonRequired] double X, [property: JsonRequired] double Z);
public record FloorMarker(FloorPoint Room, FloorPoint Tracking);
public record RoomAlignmentRequest(int RoomId, FloorMarker[] Markers);
public record FloorMarkerResult(string Name, FloorPoint Room, FloorPoint Tracking, FloorPoint MappedRoom, double ErrorMeters);
public record RoomAlignmentReport(int Version, string Profile, int RoomId, FloorPoint RoomOrigin, double YawDegrees,
    FloorPoint Translation, double ToleranceMeters, bool WithinTolerance, FloorMarkerResult[] Markers);

public static class RoomAlignment
{
    private const double MinimumSpacing = .5, Tolerance = .05, ComparisonEpsilon = 1e-9;

    public static RoomAlignmentReport Solve(RoomAlignmentRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (request.RoomId is < 1 or > SessionManager.RoomCount || request.Markers is not { Length: 3 }
            || request.Markers.Any(marker => marker is null || !InRange(marker.Room, ArenaLayout.RoomHalfSize) || !InRange(marker.Tracking, 100)))
            throw new ArgumentException("Provide three finite floor marker pairs for one room. Room coordinates must be inside its 12 m footprint.");

        var (a, b, c) = (request.Markers[0], request.Markers[1], request.Markers[2]);
        var room = Difference(b.Room, a.Room);
        var tracking = Difference(b.Tracking, a.Tracking);
        var roomLength = Length(room);
        if (roomLength < MinimumSpacing || Length(tracking) < MinimumSpacing)
            throw new ArgumentException("Markers A and B must be at least 0.5 m apart in both coordinate spaces.");

        var third = Difference(c.Room, a.Room);
        var perpendicularDistance = Math.Abs(room.X * third.Z - room.Z * third.X) / roomLength;
        if (perpendicularDistance < MinimumSpacing)
            throw new ArgumentException("Room marker C must be at least 0.5 m away from the line through A and B.");

        // Unity yaw rotates +Z towards +X. Fit A/B, then check C without fitting it.
        var yaw = Math.Atan2(tracking.Z, tracking.X) - Math.Atan2(room.Z, room.X);
        var cosine = Math.Cos(yaw);
        var sine = Math.Sin(yaw);
        FloorPoint Rotate(FloorPoint point) => new(cosine * point.X + sine * point.Z, -sine * point.X + cosine * point.Z);
        var translation = Difference(a.Room, Rotate(a.Tracking));
        FloorMarkerResult Measure(string name, FloorMarker marker)
        {
            var rotated = Rotate(marker.Tracking);
            var mapped = new FloorPoint(rotated.X + translation.X, rotated.Z + translation.Z);
            return new(name, marker.Room, marker.Tracking, mapped, Length(Difference(mapped, marker.Room)));
        }

        var results = new[] { Measure("A", a), Measure("B", b), Measure("C", c) };
        var origin = ArenaWorld.RoomOrigin(request.RoomId);
        return new(1, "room-floor-alignment-v1", request.RoomId, new(origin.X, origin.Z), Math.IEEERemainder(yaw * 180 / Math.PI, 360),
            translation, Tolerance, results.All(marker => marker.ErrorMeters <= Tolerance + ComparisonEpsilon), results);
    }

    private static bool InRange(FloorPoint? point, double bound) => point is not null
        && Math.Abs(point.X) <= bound && Math.Abs(point.Z) <= bound;
    private static FloorPoint Difference(FloorPoint point, FloorPoint origin) => new(point.X - origin.X, point.Z - origin.Z);
    private static double Length(FloorPoint point) => Math.Sqrt(point.X * point.X + point.Z * point.Z);
}
