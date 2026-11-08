using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using VrCommand.Core;

internal static class RoomAlignmentChecks
{
    internal static void Run(Action<bool, string> check)
    {
        var pairs = new FloorMarker[]
        {
            new(new(-2, -2), new(-1, -3)),
            new(new( 2, -2), new(-1,  1)),
            new(new(-2,  2), new(-5, -3))
        };
        RoomAlignmentReport Solve(params FloorMarker[] markers) => RoomAlignment.Solve(new(5, markers));
        var exact = Solve(pairs);
        check(exact.WithinTolerance && Near(exact.YawDegrees, 90) && Near(exact.Translation.X, 1) && Near(exact.Translation.Z, -3),
            "Floor alignment rotates and translates real-sized coordinates with the Unity yaw convention");
        check(exact.RoomOrigin == new FloorPoint(28, 0) && exact.Markers.All(marker => Near(marker.ErrorMeters, 0)),
            "Floor alignment uses the original room origin while marker errors remain room-local");

        var reflected = Solve(pairs[0], pairs[1], pairs[2] with { Tracking = new(3, -3) });
        check(!reflected.WithinTolerance && Near(reflected.Markers[2].ErrorMeters, 8) && reflected.Translation == exact.Translation,
            "The independent C marker rejects reflection without changing the A/B fit");
        var stretched = Solve(pairs[0], pairs[1] with { Tracking = new(-1, 1.1) }, pairs[2]);
        check(!stretched.WithinTolerance && Near(stretched.Markers[1].ErrorMeters, .1) && Near(stretched.Markers[2].ErrorMeters, 0),
            "The alignment preserves meters and reports a stretched baseline instead of rescaling it");

        check(Solve(pairs[0], pairs[1], pairs[2] with { Tracking = new(-5.05, -3) }).WithinTolerance
            && !Solve(pairs[0], pairs[1], pairs[2] with { Tracking = new(-5.051, -3) }).WithinTolerance,
            "The five-centimeter error boundary is inclusive and larger deviations are rejected");

        var nonAxis = new FloorPoint[] { new(1, 2), new(-1, 3), new(0, 0) };
        const double theta = -.71;
        var oriented = Solve(nonAxis.Select(room => new FloorMarker(room, new(
            Math.Cos(theta) * (room.X - 4) - Math.Sin(theta) * (room.Z + 2),
            Math.Sin(theta) * (room.X - 4) + Math.Cos(theta) * (room.Z + 2)))).ToArray());
        check(oriented.WithinTolerance && Near(oriented.YawDegrees, theta * 180 / Math.PI) && Near(oriented.Translation.X, 4) && Near(oriented.Translation.Z, -2),
            "A non-axis-aligned baseline preserves negative yaw and both translation components");

        check(Reject(() => Solve(pairs[0], pairs[1], pairs[2] with { Room = new(0, -2) }))
            && Reject(() => Solve(pairs[0], pairs[1] with { Tracking = pairs[0].Tracking }, pairs[2])),
            "Duplicate tracking points and collinear room markers cannot produce an alignment");
        check(Reject(() => RoomAlignment.Solve(new(6, pairs))) && Reject(() => Solve(pairs[..2]))
            && Reject(() => Solve(pairs[0] with { Room = new(6.01, 0) }, pairs[1], pairs[2]))
            && Reject(() => Solve(pairs[0] with { Tracking = new(double.NaN, 0) }, pairs[1], pairs[2])),
            "Room range, exact marker count, room footprint and finite coordinates are enforced");

        byte[] Export(RoomAlignmentReport report) => Encoding.UTF8.GetBytes(JsonSerializer.Serialize(report, JsonFormat.Options));
        var raw = Export(exact);
        byte[] bom = [0xef, 0xbb, 0xbf, .. raw, (byte)'\n'];
        var fingerprint = RoomAlignment.CheckFile(bom);
        check(fingerprint.RoomId == 5 && fingerprint.Sha256 == Convert.ToHexStringLower(SHA256.HashData(bom))
            && fingerprint.Sha256 != RoomAlignment.CheckFile(raw).Sha256,
            "Alignment file check hashes exact original UTF-8 bytes including optional BOM and final newline");
        check(Reject(() => RoomAlignment.CheckFile(Export(reflected with { WithinTolerance = true })))
            && Reject(() => RoomAlignment.CheckFile(Export(exact with { RoomOrigin = new(14, 0) }))),
            "Alignment file check recomputes the real fit and canonical origin instead of trusting the report flag");
        check(Reject(() => RoomAlignment.CheckFile(Export(exact with { Markers = [exact.Markers[1], exact.Markers[0], exact.Markers[2]] })))
            && Reject(() => RoomAlignment.CheckFile(Encoding.UTF8.GetBytes("{\"roomId\":4," + Encoding.UTF8.GetString(raw)[1..]))),
            "Alignment file check rejects reordered marker names and duplicate JSON members");
        check(Reject(() => RoomAlignment.CheckFile([])) && Reject(() => RoomAlignment.CheckFile(new byte[RoomAlignment.MaxFileBytes + 1])),
            "Alignment file check bounds the original file size");
    }

    private static bool Near(double left, double right) => Math.Abs(left - right) < 1e-8;
    private static bool Reject(Action action)
    {
        try { action(); return false; }
        catch (ArgumentException) { return true; }
    }
}
