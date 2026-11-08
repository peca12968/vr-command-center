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
    public static RoomAlignmentReport Solve(RoomAlignmentRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (request.RoomId is < 1 or > SessionManager.RoomCount || request.Markers is not { Length: 3 }
            || request.Markers.Any(marker => marker is null || marker.Room is null || marker.Tracking is null))
            throw new ArgumentException("Provide three finite floor marker pairs for one room. Room coordinates must be inside its 12 m footprint.");

        var room = request.Markers.Select(marker => new FloorXZ(marker.Room.X, marker.Room.Z)).ToArray();
        var tracking = request.Markers.Select(marker => new FloorXZ(marker.Tracking.X, marker.Tracking.Z)).ToArray();
        var fit = RoomFloorFit.Solve(room, tracking, out var transform);
        if (fit == FloorFitResult.InvalidPoints)
            throw new ArgumentException("Provide three finite floor marker pairs for one room. Room coordinates must be inside its 12 m footprint.");
        if (fit == FloorFitResult.ShortBaseline)
            throw new ArgumentException("Markers A and B must be at least 0.5 m apart in both coordinate spaces.");
        if (fit == FloorFitResult.NarrowReference)
            throw new ArgumentException("Room marker C must be at least 0.5 m away from the line through A and B.");
        var results = new FloorMarkerResult[3];
        for (var i = 0; i < results.Length; i++)
        {
            var mapped = transform.Map(tracking[i]);
            var marker = request.Markers[i];
            results[i] = new("ABC"[i].ToString(), marker.Room, marker.Tracking, new(mapped.X, mapped.Z), (mapped - room[i]).Length);
        }
        var origin = ArenaWorld.RoomOrigin(request.RoomId);
        return new(1, RoomFloorFit.Profile, request.RoomId, new(origin.X, origin.Z), transform.YawDegrees,
            new(transform.Translation.X, transform.Translation.Z), RoomFloorFit.Tolerance, fit == FloorFitResult.Valid, results);
    }

}
