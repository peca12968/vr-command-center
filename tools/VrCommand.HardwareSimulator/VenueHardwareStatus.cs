using System.Diagnostics;
using System.Text.Json;
using VrCommand.Core;

internal static partial class LiveHardwareGateway
{
    private static readonly TimeSpan HeartbeatInterval = TimeSpan.FromMilliseconds(500);
    private static readonly TimeSpan HeartbeatLifetime = TimeSpan.FromSeconds(3);
    private static readonly TimeSpan ReadRetryLimit = TimeSpan.FromMilliseconds(25);

    private sealed record GatewayProgress(string Phase, int Connections, int Attachments, int ManagementFaults,
        int MockFaults, int Dropped, int Acknowledged, int Batches);
    private sealed record GatewaySnapshot(int Version, Guid SessionId, int RoomId, Guid RunId, int Sequence,
        DateTimeOffset ObservedAtUtc, GatewayProgress Progress, string? Termination, string? Fault, bool PhysicalDeliveryConfirmed);

    private static string RoomStatusName(int roomId) => FormattableString.Invariant($"room-{roomId:00}.status.json");

    private static bool WindowsSharingConflict(IOException error) => OperatingSystem.IsWindows()
        && error.HResult is unchecked((int)0x80070020) or unchecked((int)0x80070021);

    private sealed class GatewayHeartbeat : IDisposable
    {
        private readonly Configuration config;
        private readonly string path;
        private readonly FileStream lease;
        private readonly Guid runId = Guid.NewGuid();
        private GatewaySnapshot? prior;
        private (GatewayProgress Progress, string? Termination, string? Fault)? pending;
        private long lastWrite;

        internal GatewayHeartbeat(string directory, Configuration config, string input, string output, string? stopFile)
        {
            if (!Directory.Exists(directory)) throw new ArgumentException("Use an existing status directory.");
            this.config = config;
            path = Path.Combine(directory, RoomStatusName(config.RoomId));
            var leasePath = path + ".lock";
            if (new[] { input, output, stopFile }.Any(other => string.Equals(path, other, StringComparison.OrdinalIgnoreCase)
                || string.Equals(leasePath, other, StringComparison.OrdinalIgnoreCase)))
                throw new ArgumentException("Use separate status, configuration, report and stop paths.");
            lease = new FileStream(leasePath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        }

        internal void Refresh()
        {
            if (pending is { } retry) Publish(retry.Progress, retry.Termination, retry.Fault);
            else if (prior is { } snapshot) Publish(snapshot.Progress, snapshot.Termination, snapshot.Fault);
        }

        internal void Publish(GatewayProgress progress, string? termination, string? fault)
        {
            if (prior is { } snapshot && progress == snapshot.Progress && termination == snapshot.Termination && fault == snapshot.Fault
                && Stopwatch.GetElapsedTime(lastWrite) < HeartbeatInterval)
            {
                pending = null;
                return;
            }

            var next = new GatewaySnapshot(1, config.SessionId, config.RoomId, runId, (prior?.Sequence ?? 0) + 1,
                DateTimeOffset.UtcNow, progress, termination, fault, false);
            var staging = path + $".{runId:N}.tmp";
            var created = false;
            try
            {
                using (var file = new FileStream(staging, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    created = true;
                    JsonSerializer.Serialize(file, next, HeartbeatWire);
                }
                if (!TryPublishFile(staging, termination is not null))
                {
                    pending = (progress, termination, fault);
                    return;
                }
                created = false;
                pending = null;
                prior = next;
                lastWrite = Stopwatch.GetTimestamp();
            }
            catch (IOException error)
            {
                throw new InvalidOperationException("Unable to publish the room status.", error);
            }
            finally { if (created) File.Delete(staging); }
        }

        private bool TryPublishFile(string staging, bool terminal)
        {
            var started = Stopwatch.GetTimestamp();
            while (true)
            {
                try
                {
                    // ReplaceFile can update a destination held with delete sharing.
                    if (File.Exists(path)) File.Replace(staging, path, null);
                    else File.Move(staging, path);
                    return true;
                }
                catch (IOException error) when (WindowsSharingConflict(error))
                {
                    // Keep the network path moving. The stopped gateway can wait briefly after writing its report.
                    if (!terminal) return false;
                    if (Stopwatch.GetElapsedTime(started) >= HeartbeatInterval) throw;
                    Thread.Sleep(10);
                }
            }
        }

        public void Dispose() => lease.Dispose();
    }

    internal static int ReadVenueStatus(string manifestPath, string directory)
    {
        if (!Directory.Exists(directory)) throw new ArgumentException("Use an existing status directory.");
        var manifest = ReadVenueManifest(manifestPath);

        var rooms = manifest.Rooms.Select(room =>
        {
            var (state, status) = ReadRoomStatus(Path.Combine(directory, RoomStatusName(room.RoomId)), room);
            return new { room.RoomId, room.SessionId, state, status };
        }).ToArray();
        Console.WriteLine(JsonSerializer.Serialize(new { version = 1, manifest.Mode, rooms, physicalDeliveryConfirmed = false }, Wire));
        return 0;
    }

    private static (string State, GatewaySnapshot? Status) ReadRoomStatus(string path, VenueBindingRoom room)
    {
        try
        {
            var status = JsonSerializer.Deserialize<GatewaySnapshot>(ReadStatusBytes(path), HeartbeatWire);
            if (status is not { Version: 1, Sequence: > 0, PhysicalDeliveryConfirmed: false, Progress: { } progress }
                || status.RunId == Guid.Empty || status.SessionId == Guid.Empty || status.ObservedAtUtc == default
                || progress is not { Connections: >= 0, Attachments: >= 0, ManagementFaults: >= 0, MockFaults: >= 0, Dropped: >= 0, Acknowledged: >= 0, Batches: >= 0 }
                || progress.Phase is not ("checking-management" or "paused" or "waiting-source" or "waiting-mission" or "connecting"
                    or "active" or "awaiting-ack" or "mock-unavailable" or "management-unavailable" or "stopped")
                || (progress.Phase == "stopped" ? status.Termination is not ("duration" or "ended" or "attempt-limit"
                    or "binding-mismatch" or OperatorStop or OperatorRoomStop or ManagementRefused or ManagementInvalidResponse) : status.Termination is not null)
                || (progress.Phase switch
                {
                    "mock-unavailable" => status.Fault is not ("mock-disconnected" or "mock-timeout" or "mock-invalid-reply"),
                    "management-unavailable" => status.Fault is not (null or ManagementTimeout or ManagementTransport or ManagementServiceUnavailable),
                    _ => status.Fault is not null
                }))
                return ("invalid", null);
            if (status.RoomId != room.RoomId || status.SessionId != room.SessionId) return ("mismatch", null);
            var age = DateTimeOffset.UtcNow - status.ObservedAtUtc;
            if (age < TimeSpan.Zero) return ("invalid", null);
            if (progress.Phase == "stopped") return ("stopped", status);
            return age >= HeartbeatLifetime ? ("stale", null) : ("current", status);
        }
        catch (FileNotFoundException) { return ("waiting", null); }
        catch (Exception error) when (error is JsonException or IOException or UnauthorizedAccessException) { return ("invalid", null); }
    }

    private static byte[] ReadStatusBytes(string path)
    {
        var started = Stopwatch.GetTimestamp();
        while (true)
        {
            try
            {
                using var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                return ReadReportBytes(file, file.Length, 8192);
            }
            catch (IOException error) when (OperatingSystem.IsWindows()
                && (error is FileNotFoundException || WindowsSharingConflict(error))
                && Stopwatch.GetElapsedTime(started) < ReadRetryLimit)
            {
                Thread.Sleep(5);
            }
        }
    }
}
