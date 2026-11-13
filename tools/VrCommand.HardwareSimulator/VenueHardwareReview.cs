using System.Security.Cryptography;
using System.Text.Json;
using VrCommand.Core;

internal static partial class LiveHardwareGateway
{
    private const int MaxRoomReportBytes = 32 * 1024 * 1024;
    private sealed record RoomRunReport(int Version, bool Complete, bool SimulatedHardwareOnly, bool PhysicalDeliveryConfirmed,
        Guid SessionId, int RoomId, string Termination, int Connections, int Attachments, int ManagementFaults,
        int MockFaults, int Dropped, int Acknowledged, Attempt[] Attempts);
    private sealed record RoomRunReview(int RoomId, Guid SessionId, int ExitCode, string? Termination, string? Error,
        int? Acknowledged, int? Cancelled, int? MockFailed);

    private static byte[] ReadReportBytes(string path, int maximum)
    {
        using var file = File.OpenRead(path);
        if (file.Length is < 1 || file.Length > maximum) throw new InvalidDataException("Report size is out of bounds.");
        var bytes = new byte[file.Length];
        file.ReadExactly(bytes);
        if (file.ReadByte() != -1) throw new InvalidDataException("Report changed during reading.");
        return bytes;
    }

    private static string ReportHash(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    internal static int ReviewVenueRun(string manifestPath, string directory)
    {
        var manifest = ReadVenueManifest(manifestPath, out var manifestHash);
        var report = JsonSerializer.Deserialize<VenueRunReport>(ReadReportBytes(Path.Combine(directory, "venue-report.json"), 8192), HeartbeatWire);
        if (report is not { Version: 2, SimulatedHardwareOnly: true, PhysicalDeliveryConfirmed: false, Rooms.Length: SessionManager.RoomCount }
            || report.Mode != manifest.Mode || report.BindingManifestSha256 != manifestHash
            || report.Complete != report.Rooms.All(room => room?.ExitCode == 0))
            throw new InvalidDataException("Venue report does not match the original binding manifest.");

        var rooms = report.Rooms.Zip(manifest.Rooms, ReviewRoom).ToArray();
        Console.WriteLine(JsonSerializer.Serialize(new { version = 1, verified = true, rehearsalComplete = report.Complete,
            report.Mode, report.BindingManifestSha256, simulatedHardwareOnly = true, physicalDeliveryConfirmed = false, rooms }, Wire));
        return 0;

        RoomRunReview ReviewRoom(VenueRunResult row, VenueBindingRoom binding)
        {
            if (row is null || row.RoomId != binding.RoomId || row.SessionId != binding.SessionId || row.ExitCode is not (0 or 1))
                throw new InvalidDataException("Venue room result does not match the original room.");
            var fileName = FormattableString.Invariant($"room-{row.RoomId:00}-report.json");
            var path = Path.Combine(directory, fileName);
            if (row.Report is null)
            {
                if (row.ExitCode != 1 || row.Error is not { Length: > 0 and <= 64 } || !row.Error.All(char.IsAsciiLetterOrDigit)
                    || row.Sha256 is not null || row.Bytes is not null)
                    throw new InvalidDataException("Unexpected room report for a room with a recorded error.");
                return new(row.RoomId, row.SessionId, row.ExitCode, null, row.Error, null, null, null);
            }
            if (row.Report != fileName || row.Error is not null) throw new InvalidDataException("Unexpected room report file name.");
            var bytes = ReadReportBytes(path, MaxRoomReportBytes);
            if (row.Bytes != bytes.Length || row.Sha256 != ReportHash(bytes)) throw new InvalidDataException("Room report bytes do not match.");
            var room = JsonSerializer.Deserialize<RoomRunReport>(bytes, HeartbeatWire);
            if (room is not { Version: 1, SimulatedHardwareOnly: true, PhysicalDeliveryConfirmed: false, Attempts.Length: <= MaxAttempts }
                || room.RoomId != row.RoomId || room.SessionId != row.SessionId || room.Complete != (row.ExitCode == 0)
                || room is not { Connections: >= 0, Attachments: >= 0, ManagementFaults: >= 0, MockFaults: >= 0, Dropped: >= 0 }
                || room.Attachments > room.Connections
                || room.Termination is not ("duration" or "ended" or OperatorStop or OperatorRoomStop or "attempt-limit"
                    or "binding-mismatch" or ManagementRefused or ManagementInvalidResponse)
                || room.Complete != (room.Attachments > 0 && room.Termination is ("duration" or "ended" or OperatorStop or OperatorRoomStop))
                || room.Attempts.Any(attempt => attempt is null || attempt.Deliveries is not { Length: >= 1 and <= MaxBatch }
                    || attempt.ConnectionId == Guid.Empty || attempt.BatchId == Guid.Empty
                    || attempt.Deliveries.Any(delivery => delivery is null || delivery.DeviceId == Guid.Empty || delivery.Signal is null)
                    || attempt.Status is not ("simulated-acknowledged" or "cancelled" or "mock-timeout" or "mock-disconnected" or "mock-invalid-reply")))
                throw new InvalidDataException("Room report does not match the venue result.");
            var acknowledged = Count("simulated-acknowledged");
            var cancelled = Count("cancelled");
            if (acknowledged != room.Acknowledged) throw new InvalidDataException("Room acknowledgement count does not match.");
            return new(row.RoomId, row.SessionId, row.ExitCode, room.Termination, null, acknowledged, cancelled,
                room.Attempts.Sum(attempt => attempt.Deliveries.Length) - acknowledged - cancelled);

            int Count(string status) => room.Attempts.Where(attempt => attempt.Status == status).Sum(attempt => attempt.Deliveries.Length);
        }
    }
}
