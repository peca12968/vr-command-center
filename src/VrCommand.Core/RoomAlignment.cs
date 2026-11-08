using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Simulation;

namespace VrCommand.Core;

public record FloorPoint([property: JsonRequired] double X, [property: JsonRequired] double Z);
public record FloorMarker(FloorPoint Room, FloorPoint Tracking);
public record RoomAlignmentRequest(int RoomId, FloorMarker[] Markers);
public record FloorMarkerResult(string Name, FloorPoint Room, FloorPoint Tracking, FloorPoint MappedRoom, double ErrorMeters);
public record RoomAlignmentReport(int Version, string Profile, int RoomId, FloorPoint RoomOrigin, double YawDegrees,
    FloorPoint Translation, double ToleranceMeters, bool WithinTolerance, FloorMarkerResult[] Markers);
public record CheckedRoomAlignmentFile(int RoomId, string Sha256);

public static class RoomAlignment
{
    public const int MaxFileBytes = 16_384;
    private static readonly JsonSerializerOptions FileOptions = new(JsonFormat.Options)
    {
        AllowDuplicateProperties = false,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        PropertyNameCaseInsensitive = false,
        NumberHandling = JsonNumberHandling.Strict,
        MaxDepth = 12
    };

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

    public static CheckedRoomAlignmentFile CheckFile(ReadOnlySpan<byte> bytes)
    {
        if (bytes.Length is 0 or > MaxFileBytes)
            throw new ArgumentException("Use a room alignment export up to 16 KiB.");
        RoomAlignmentReport? report;
        try
        {
            // Unity ignores a UTF-8 BOM when reading the JSON but hashes the original bytes.
            var json = bytes.StartsWith("\uFEFF"u8) ? bytes[3..] : bytes;
            report = JsonSerializer.Deserialize<RoomAlignmentReport>(json, FileOptions);
        }
        catch (JsonException)
        {
            throw new ArgumentException("Use a valid room alignment JSON export.");
        }
        if (report is not { Version: 1, Profile: RoomFloorFit.Profile, WithinTolerance: true, Markers.Length: 3 }
            || report.RoomId is < 1 or > SessionManager.RoomCount)
            throw new ArgumentException("Use a checked room alignment JSON export.");
        for (var i = 0; i < report.Markers.Length; i++)
            if (report.Markers[i]?.Name != "ABC"[i].ToString())
                throw new ArgumentException("Use the original A, B and C room alignment measurements.");
        var fit = Solve(new(report.RoomId, report.Markers.Select(marker => new FloorMarker(marker.Room, marker.Tracking)).ToArray()));
        if (!fit.WithinTolerance || fit.RoomOrigin != report.RoomOrigin)
            throw new ArgumentException("The exported room origin or alignment measurements do not match the arena.");
        return new(report.RoomId, Convert.ToHexStringLower(SHA256.HashData(bytes)));
    }

}
