using System.Buffers.Binary;
using System.Diagnostics;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Sockets;
using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Core;

internal static partial class LiveHardwareGateway
{
    private const int MaxBatch = 32, MaxAttempts = 1024, MaxFrameBytes = 32 * 1024;
    private const string ManagementRefused = "management-refused", ManagementInvalidResponse = "management-invalid-response";
    private static readonly TimeSpan PollInterval = TimeSpan.FromMilliseconds(150);
    private static readonly TimeSpan RequestTimeout = TimeSpan.FromMilliseconds(750);
    private static readonly TimeSpan SignalLifetime = TimeSpan.FromSeconds(2);
    private static readonly JsonSerializerOptions Wire = new(JsonFormat.Options)
    {
        AllowDuplicateProperties = false, UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        PropertyNameCaseInsensitive = false, WriteIndented = false, MaxDepth = 12
    };
    private static readonly JsonSerializerOptions HeartbeatWire = new(Wire) { RespectRequiredConstructorParameters = true };

    private sealed record SeatDevice(Guid DeviceId, [property: JsonRequired] int Seat);
    private sealed record SeatMap(int Version, string ManagementUrl, Guid SessionId, int RoomId, int MockPort, int Seconds, SeatDevice[] Devices);
    private sealed record Binding(Guid DeviceId, Guid PlayerId, Guid AdmissionId, [property: JsonRequired] int Seat);
    private sealed record Configuration(int Version, string ManagementUrl, Guid SessionId, int RoomId, int MockPort, int Seconds, Binding[] Bindings);
    private sealed record MockReply(int Version, string Kind, Guid ConnectionId, Guid? BatchId);
    private sealed record Delivery(Guid DeviceId, RoomHardwareSignal Signal);
    private sealed record Attempt(Guid ConnectionId, Guid BatchId, string Status, Delivery[] Deliveries);
    private sealed record Observation(RoomHardwareFeedback Page, long RequestStarted)
    {
        internal bool IsFresh(RoomHardwareSignal signal) => Page.CheckedAtUtc >= signal.AcceptedAtUtc
            && Page.CheckedAtUtc - signal.AcceptedAtUtc + Stopwatch.GetElapsedTime(RequestStarted) < SignalLifetime;
    }
    private sealed class MockFailure(string reason) : IOException(reason);
    private sealed class BindingMismatch : Exception { }
    private sealed class GatewayLeaseUnavailable : IOException { }
    private sealed class MockPortLeaseUnavailable : IOException { }
    private sealed class DeviceLeaseUnavailable : IOException { }

    internal static bool IsExpectedFailure(Exception error) => error is ArgumentException or InvalidDataException
        or InvalidOperationException or JsonException or IOException or UnauthorizedAccessException or AccessDeniedException
        or KeyNotFoundException or HttpRequestException or TimeoutException;

    private sealed class GatewayLeases(string directory) : IDisposable
    {
        private readonly List<FileStream> handles = [];

        // The file stays in place. Only the live OS handle owns the lease.
        internal void Hold(string name) =>
            handles.Add(new FileStream(Path.Combine(directory, name), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None));

        public void Dispose()
        {
            foreach (var handle in handles) handle.Dispose();
        }
    }

    private static T ReadInput<T>(string path) where T : class
    {
        using var file = File.OpenRead(path);
        if (file.Length is < 1 or > 8192) throw new ArgumentException("Use a bounded live rehearsal configuration.");
        var bytes = new byte[file.Length]; file.ReadExactly(bytes);
        return JsonSerializer.Deserialize<T>(bytes, Wire) ?? throw new ArgumentException("Missing configuration.");
    }

    private static void ValidateRoom(Guid sessionId, int roomId, int port, int seconds)
    {
        if (sessionId == Guid.Empty || roomId is < 1 or > 5 || port is < 1024 or > 65535 || seconds is < 1 or > 120)
            throw new ArgumentException("Use a session, one room, a mock port and a bounded rehearsal duration.");
    }

    private static HttpClient CreateManagementClient(string origin, string keyVariable = "VR_COMMAND_ROOM_KEY")
    {
        if (!Uri.TryCreate(origin, UriKind.Absolute, out var api) || api.UserInfo.Length != 0 || api.Query.Length != 0
            || api.Fragment.Length != 0 || api.AbsolutePath != "/" || !(api.Scheme == "https" || api.Scheme == "http" && api.Host == "127.0.0.1"))
            throw new ArgumentException("Use an HTTPS management origin or 127.0.0.1 HTTP.");
        var key = Environment.GetEnvironmentVariable(keyVariable);
        if (string.IsNullOrWhiteSpace(key) || key.Length > 512 || key.Any(c => c <= 32 || c >= 127)) throw new ArgumentException("Set the required operator key in the environment.");

        var client = new HttpClient(new SocketsHttpHandler { AllowAutoRedirect = false, UseProxy = false })
            { BaseAddress = api, Timeout = Timeout.InfiniteTimeSpan };
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", key);
        return client;
    }

    private static async Task VerifyIdentity(HttpClient client, int roomId)
    {
        var identity = await Get<OperatorIdentity>(client, "/api/me", CancellationToken.None);
        if (identity.Role != OperatorRole.RoomController || identity.RoomId != roomId)
            throw new AccessDeniedException("This rehearsal requires the matching room controller.");
    }

    internal static async Task<int> BindRoom(string input, string output)
    {
        var map = ReadInput<SeatMap>(input);
        ValidateRoom(map.SessionId, map.RoomId, map.MockPort, map.Seconds);
        if (map.Version != 1) throw new ArgumentException("Use version 1 seat maps.");
        ValidateDevices(map.Devices);
        var config = new Configuration(2, map.ManagementUrl, map.SessionId, map.RoomId, map.MockPort, map.Seconds, []);
        using var client = CreateManagementClient(map.ManagementUrl);
        await VerifyIdentity(client, map.RoomId);
        var page = (await Read(client, FeedbackRoute(config), config, null, CancellationToken.None)).Page;
        if (page.State == SessionState.Ended) throw new InvalidOperationException("The rehearsal session has ended.");
        var bindings = ResolveBindings(map.Devices, page.Bindings!);
        using var destination = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        JsonSerializer.Serialize(destination, config with { Bindings = bindings }, JsonFormat.Options);
        destination.Flush(true);
        Console.WriteLine(JsonSerializer.Serialize(new { complete = true, config.SessionId, config.RoomId, boundSeats = bindings.Length }, Wire));
        return 0;
    }

    private static void ValidateDevices(SeatDevice[] devices)
    {
        if (devices is not { Length: >= 1 and <= 5 }
            || devices.Any(device => device is null || device.DeviceId == Guid.Empty || device.Seat is < 0 or > 4)
            || devices.Select(device => device.Seat).Distinct().Count() != devices.Length
            || devices.Select(device => device.DeviceId).Distinct().Count() != devices.Length)
            throw new ArgumentException("Use unique seats and device IDs.");
    }

    private static Binding[] ResolveBindings(SeatDevice[] devices, RoomHardwareSeat[] seats)
    {
        var roster = seats.ToDictionary(binding => binding.Seat);
        return devices.OrderBy(device => device.Seat).Select(device =>
        {
            if (!roster.TryGetValue(device.Seat, out var seat)) throw new InvalidOperationException("A mapped seat has no current admission.");
            return new Binding(device.DeviceId, seat.PlayerId, seat.AdmissionId, seat.Seat);
        }).ToArray();
    }

    private static RoomHardwareSeat[] ValidateBindingRoster(RoomHardwareSeat[]? seats)
    {
        if (seats is not { Length: <= 5 } || seats.Any(seat => seat is null || seat.PlayerId == Guid.Empty || seat.AdmissionId == Guid.Empty || seat.Seat is < 0 or > 4)
            || seats.Select(seat => seat.Seat).Distinct().Count() != seats.Length
            || seats.Select(seat => seat.PlayerId).Distinct().Count() != seats.Length
            || seats.Select(seat => seat.AdmissionId).Distinct().Count() != seats.Length)
            throw new InvalidDataException("Invalid feedback binding roster.");
        return seats;
    }

    private static string FeedbackRoute(Configuration config) => $"/api/sessions/{config.SessionId:D}/rooms/{config.RoomId}/hardware-feedback";

    private static (Guid Stream, long Since)? ActiveEpoch(RoomHardwareFeedback page) =>
        page.State == SessionState.Running && page.ResetReason != "inactive"
        && page.StreamId is { } stream && stream != Guid.Empty && page.RunningSinceSequence is > 0 and var since
            ? (stream, since) : null;

    private static GatewayLeases AcquireGatewayLeases(Configuration config)
    {
        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData, Environment.SpecialFolderOption.DoNotVerify);
        if (!Path.IsPathFullyQualified(local)) throw new GatewayLeaseUnavailable();
        var directory = Path.Combine(local, "VrCommand", "HardwareGatewayLeases");
        var leases = new GatewayLeases(directory);
        try
        {
            try
            {
                Directory.CreateDirectory(directory);
                leases.Hold(FormattableString.Invariant($"{config.SessionId:N}-{config.RoomId}.lock"));
            }
            catch (IOException) { throw new GatewayLeaseUnavailable(); }
            try { leases.Hold(FormattableString.Invariant($"mock-port-{config.MockPort}.lock")); }
            catch (IOException) { throw new MockPortLeaseUnavailable(); }
            try
            {
                foreach (var device in config.Bindings.Select(binding => binding.DeviceId).Order())
                    leases.Hold($"device-{device:N}.lock");
            }
            catch (IOException) { throw new DeviceLeaseUnavailable(); }
            return leases;
        }
        catch
        {
            leases.Dispose();
            throw;
        }
    }

    private static Configuration ReadConfiguration(string input)
    {
        var config = ReadInput<Configuration>(input);
        ValidateRoom(config.SessionId, config.RoomId, config.MockPort, config.Seconds);
        if (config.Version is not (1 or 2)
            || config.Bindings is not { Length: >= 1 and <= 5 } || config.Bindings.Any(b => b is null || b.DeviceId == Guid.Empty
                || b.PlayerId == Guid.Empty || b.AdmissionId == Guid.Empty || b.Seat is < 0 or > 4)
            || config.Bindings.Select(b => b.Seat).Distinct().Count() != config.Bindings.Length
            || config.Bindings.Select(b => b.PlayerId).Distinct().Count() != config.Bindings.Length
            || config.Bindings.Select(b => b.DeviceId).Distinct().Count() != config.Bindings.Length
            || config.Bindings.Select(b => b.AdmissionId).Distinct().Count() != config.Bindings.Length)
            throw new ArgumentException("Use one room and unique seat, device, player and admission bindings.");
        return config;
    }

    internal static async Task<int> Run(string input, string output, string? stopFile, bool statusEnabled, string? statusDirectory)
    {
        var config = ReadConfiguration(input);
        using var client = CreateManagementClient(config.ManagementUrl);
        await VerifyIdentity(client, config.RoomId);
        using var leases = AcquireGatewayLeases(config);
        return await RunRoom(config, client, input, output, stopFile, statusEnabled, statusDirectory);
    }

    private static async Task<int> RunRoom(Configuration config, HttpClient client, string input, string output,
        string? stopFile, bool statusEnabled, string? statusDirectory, bool writeSummary = true)
    {
        using var heartbeat = statusDirectory is null ? null : new GatewayHeartbeat(statusDirectory, config, input, output, stopFile);

        var bindings = config.Bindings.ToDictionary(b => (b.PlayerId, b.AdmissionId, b.Seat));
        var route = FeedbackRoute(config);
        var attempts = new List<Attempt>();
        int connections = 0, attachments = 0, managementFaults = 0, mockFaults = 0, dropped = 0, acknowledged = 0;
        var termination = "duration";
        var statusSequence = 0;
        GatewayProgress? prior = null;
        void PublishStatus(string phase, string? reason = null, string? fault = null)
        {
            if (!statusEnabled && heartbeat is null) return;
            var progress = new GatewayProgress(phase, connections, attachments, managementFaults, mockFaults, dropped, acknowledged, attempts.Count);
            heartbeat?.Publish(progress, reason, fault);
            if (!statusEnabled || progress == prior) return;
            prior = progress;
            Console.WriteLine(JsonSerializer.Serialize(new { version = 1, kind = "gateway-status", config.RoomId,
                sequence = ++statusSequence, observedAtUtc = DateTimeOffset.UtcNow, phase,
                connections, attachments, managementFaults, mockFaults, dropped, acknowledged, batches = attempts.Count,
                termination = reason, fault, simulatedHardwareOnly = true, physicalDeliveryConfirmed = false }, Wire));
        }
        using var duration = new CancellationTokenSource(TimeSpan.FromSeconds(config.Seconds));
        using var operatorStop = new CancellationTokenSource();
        using var run = CancellationTokenSource.CreateLinkedTokenSource(duration.Token, operatorStop.Token);
        var watch = stopFile is null ? Task.CompletedTask : WatchForStop(stopFile, operatorStop, run.Token);
        try
        {
            PublishStatus("checking-management");
            while (!run.IsCancellationRequested)
            {
                try
                {
                    var page = (await Read(client, route, config, null, run.Token)).Page;
                    if (page.State == SessionState.Ended)
                    {
                        termination = "ended";
                        break;
                    }
                    if (ActiveEpoch(page) is not { } epoch)
                    {
                        PublishStatus(page.State == SessionState.Paused ? "paused" : page.State == SessionState.Running ? "waiting-source" : "waiting-mission");
                        await Task.Delay(PollInterval, run.Token);
                        continue;
                    }
                    PublishStatus("connecting");
                    using var mock = new TcpClient(AddressFamily.InterNetwork);
                    var connection = Guid.NewGuid();
                    await Connect(mock, config.MockPort, run.Token);
                    var wire = mock.GetStream();
                    await Exchange(wire, new { version = 1, kind = "hello", mode = "simulation", connectionId = connection, config.RoomId },
                        "ready", connection, null, run.Token);
                    connections++;
                    page = (await Read(client, route, config, null, run.Token)).Page;
                    if (ActiveEpoch(page) == epoch)
                    {
                        attachments++;
                        PublishStatus("active");
                    }
                    while (ActiveEpoch(page) == epoch)
                    {
                        await Task.Delay(PollInterval, run.Token);
                        var after = page.ThroughSequence;
                        var current = await Read(client, route, config, after, run.Token);
                        page = current.Page;
                        if (ActiveEpoch(page) != epoch) break;
                        if (page.ResetReason is not null) { heartbeat?.Refresh(); continue; }
                        var deliveries = page.Signals.Where(current.IsFresh).Select(signal =>
                        {
                            bindings.TryGetValue((signal.PlayerId, signal.AdmissionId, signal.Seat), out var binding);
                            return binding is null ? null : new Delivery(binding.DeviceId, signal);
                        }).OfType<Delivery>().ToArray();
                        dropped += page.Signals.Length - deliveries.Length;
                        if (deliveries.Length == 0) { PublishStatus("active"); continue; }
                        if (deliveries.Length > MaxBatch) { dropped += deliveries.Length; PublishStatus("active"); continue; }
                        if (attempts.Count >= MaxAttempts) { termination = "attempt-limit"; break; }

                        var batch = Guid.NewGuid();
                        var status = "cancelled";
                        PublishStatus("awaiting-ack");
                        try
                        {
                            var invalid = await ExchangeFeedback(wire, client, route, config, after, page, deliveries, connection, batch, run.Token);
                            if (invalid is not null)
                            {
                                page = invalid;
                                break;
                            }
                            status = "simulated-acknowledged";
                            acknowledged += deliveries.Length;
                        }
                        catch (MockFailure failure) { status = failure.Message; throw; }
                        finally { attempts.Add(new(connection, batch, status, deliveries)); }
                        PublishStatus("active");
                    }
                    if (page.State == SessionState.Ended)
                    {
                        termination = "ended";
                        break;
                    }
                    if (termination == "attempt-limit") break;
                    PublishStatus("checking-management");
                }
                catch (MockFailure failure) { mockFaults++; PublishStatus("mock-unavailable", fault: failure.Message); }
                catch (Exception failure) when (failure is HttpRequestException or TimeoutException || failure is IOException && failure is not InvalidDataException)
                { managementFaults++; PublishStatus("management-unavailable"); }
                await Task.Delay(PollInterval, run.Token);
            }
        }
        catch (BindingMismatch) { termination = "binding-mismatch"; }
        catch (AccessDeniedException) { managementFaults++; termination = ManagementRefused; }
        catch (Exception failure) when (failure is InvalidDataException or JsonException)
        { managementFaults++; termination = ManagementInvalidResponse; }
        catch (OperationCanceledException) when (run.IsCancellationRequested) { }
        finally
        {
            run.Cancel();
            await watch;
        }

        if (termination == "duration" && operatorStop.IsCancellationRequested) termination = "operator-stop";

        var complete = attachments > 0 && termination is ("duration" or "ended" or "operator-stop");
        using (var destination = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        {
            JsonSerializer.Serialize(destination, new { version = 1, complete, simulatedHardwareOnly = true, physicalDeliveryConfirmed = false,
                config.SessionId, config.RoomId, termination, connections, attachments, managementFaults, mockFaults, dropped, acknowledged, attempts }, JsonFormat.Options);
            destination.Flush(true);
        }
        PublishStatus("stopped", termination);
        if (writeSummary)
            Console.WriteLine(JsonSerializer.Serialize(new { complete, simulatedHardwareOnly = true, physicalDeliveryConfirmed = false, acknowledged }, Wire));
        return complete ? 0 : 1;
    }

    private static async Task WatchForStop(string path, CancellationTokenSource operatorStop, CancellationToken run)
    {
        try
        {
            while (!run.IsCancellationRequested)
            {
                if (File.Exists(path))
                {
                    operatorStop.Cancel();
                    return;
                }
                await Task.Delay(PollInterval, run);
            }
        }
        catch (OperationCanceledException) when (run.IsCancellationRequested) { }
    }

    // Monitor the authority while the peer holds the batch, and read it again after an ACK.
    // Cancelling the exchange joins its socket read before the caller closes and replaces the connection.
    private static async Task<RoomHardwareFeedback?> ExchangeFeedback(NetworkStream wire, HttpClient client, string route, Configuration config,
        long after, RoomHardwareFeedback page, Delivery[] deliveries, Guid connection, Guid batch, CancellationToken run)
    {
        using var pending = CancellationTokenSource.CreateLinkedTokenSource(run);
        var receipt = Exchange(wire, new { version = 1, kind = "feedback", mode = "simulation", connectionId = connection,
            batchId = batch, config.RoomId, page.StreamId, page.RunningSinceSequence, signals = deliveries }, "ack", connection, batch, pending.Token);

        bool StillEligible(Observation observed) => observed.Page.State == SessionState.Running && observed.Page.ResetReason is null
            && observed.Page.StreamId == page.StreamId && observed.Page.RunningSinceSequence == page.RunningSinceSequence
            && deliveries.All(item => observed.IsFresh(item.Signal) && observed.Page.Signals.Contains(item.Signal));
        try
        {
            while (await Task.WhenAny(receipt, Task.Delay(PollInterval, pending.Token)) != receipt)
            {
                var observation = await Read(client, route, config, after, pending.Token);
                if (receipt.IsFaulted || receipt.IsCanceled) await receipt;
                if (!StillEligible(observation)) return observation.Page;
            }
            await receipt;
            var confirmed = await Read(client, route, config, after, pending.Token);
            run.ThrowIfCancellationRequested();
            return StillEligible(confirmed) ? null : confirmed.Page;
        }
        finally
        {
            pending.Cancel();
            try { await receipt; }
            catch (Exception error) when (error is OperationCanceledException or MockFailure) { /* A terminal path already owns the outcome. */ }
        }
    }

    private static async Task<T> Get<T>(HttpClient client, string path, CancellationToken run) where T : class
    {
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(run); deadline.CancelAfter(RequestTimeout);
        try
        {
            using var response = await client.GetAsync(path, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
            if (response.StatusCode is HttpStatusCode.Unauthorized or HttpStatusCode.Forbidden) throw new AccessDeniedException("Room identity refused.");
            if (response.StatusCode is HttpStatusCode.BadGateway or HttpStatusCode.ServiceUnavailable or HttpStatusCode.GatewayTimeout)
                throw new HttpRequestException("Management service temporarily unavailable.");
            if (!response.IsSuccessStatusCode) throw new InvalidDataException("Management response failed.");
            using var body = await response.Content.ReadAsStreamAsync(deadline.Token);
            const int limit = 192 * 1024;
            var buffer = new byte[limit + 1];
            var count = await body.ReadAtLeastAsync(buffer, buffer.Length, throwOnEndOfStream: false, deadline.Token);
            if (count > limit) throw new InvalidDataException("Management response too large.");
            return JsonSerializer.Deserialize<T>(buffer.AsSpan(0, count), Wire) ?? throw new InvalidDataException("Missing management response.");
        }
        catch (OperationCanceledException) when (!run.IsCancellationRequested) { throw new TimeoutException(); }
    }

    private static async Task<Observation> Read(HttpClient client, string route, Configuration config, long? after, CancellationToken run)
    {
        var started = Stopwatch.GetTimestamp();
        var query = config.Version == 2 ? "?includeBindings=true" : "";
        if (after.HasValue) query += (query.Length == 0 ? "?" : "&") + FormattableString.Invariant($"after={after}");
        var page = await Get<RoomHardwareFeedback>(client, route + query, run);
        if (page.Version != config.Version || (page.Version == 1 && page.Bindings is not null)
            || page.RoomId != config.RoomId || page.SessionId != config.SessionId || page.ThroughSequence < 1
            || page.ThroughSequence < after || !Enum.IsDefined(page.State) || page.CheckedAtUtc == default
            || (after.HasValue ? page.ResetReason is not (null or "inactive" or "backlog") : page.ResetReason != "attached")
            || page.Signals is not { Length: <= 256 } || (page.ResetReason is not null && page.Signals.Length != 0)
            || (page.ResetReason is null && (page.State != SessionState.Running || page.StreamId is null || page.StreamId == Guid.Empty
                || page.RunningSinceSequence is null or < 1 || page.RunningSinceSequence > page.ThroughSequence)))
            throw new InvalidDataException("Unexpected feedback cursor, room or phase.");
        if (config.Version == 2)
        {
            var seats = ValidateBindingRoster(page.Bindings);
            if (page.State != SessionState.Ended && config.Bindings.Any(binding => !seats.Contains(new RoomHardwareSeat(binding.PlayerId, binding.AdmissionId, binding.Seat))))
                throw new BindingMismatch();
        }
        var last = after ?? 0;
        foreach (var signal in page.Signals)
        {
            if (signal is null || signal.EventSequence <= last || signal.EventSequence > page.ThroughSequence
                || signal.ObservedSequence < page.RunningSinceSequence || signal.ObservedSequence >= signal.EventSequence || signal.StreamSequence < 1
                || signal.EventId == Guid.Empty || signal.ReportId == Guid.Empty || signal.PlayerId == Guid.Empty || signal.AdmissionId == Guid.Empty
                || signal.Seat is < 0 or > 4 || signal.Kind is not (CombatKind.ShotFired or CombatKind.PlayerDamaged)
                || signal.Damage != (signal.Kind == CombatKind.ShotFired ? 0 : Math.Clamp(signal.Damage, 1, 1000)))
                throw new InvalidDataException("Invalid feedback signal.");
            last = signal.EventSequence;
        }
        return new(page, started);
    }

    private static async Task Connect(TcpClient mock, int port, CancellationToken run)
    {
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(run); deadline.CancelAfter(RequestTimeout);
        try { await mock.ConnectAsync(IPAddress.Loopback, port, deadline.Token); }
        catch (SocketException) { throw new MockFailure("mock-disconnected"); }
        catch (OperationCanceledException) when (!run.IsCancellationRequested) { throw new MockFailure("mock-timeout"); }
    }

    private static async Task Exchange(NetworkStream wire, object message, string kind, Guid connection, Guid? batch, CancellationToken run)
    {
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(run); deadline.CancelAfter(RequestTimeout);
        var frame = JsonSerializer.SerializeToUtf8Bytes(message, Wire);
        if (frame.Length > MaxFrameBytes) throw new InvalidDataException("Mock request too large.");
        var size = new byte[4]; BinaryPrimitives.WriteInt32BigEndian(size, frame.Length);
        MockReply? reply;
        try
        {
            await wire.WriteAsync(size, deadline.Token);
            await wire.WriteAsync(frame, deadline.Token);
            await wire.ReadExactlyAsync(size, deadline.Token);
            var length = BinaryPrimitives.ReadInt32BigEndian(size);
            if (length is < 1 or > MaxFrameBytes) throw new MockFailure("mock-invalid-reply");
            var payload = new byte[length]; await wire.ReadExactlyAsync(payload, deadline.Token);
            reply = JsonSerializer.Deserialize<MockReply>(payload, Wire);
        }
        catch (IOException failure) when (failure is not MockFailure) { throw new MockFailure("mock-disconnected"); }
        catch (JsonException) { throw new MockFailure("mock-invalid-reply"); }
        catch (OperationCanceledException) when (!run.IsCancellationRequested) { throw new MockFailure("mock-timeout"); }
        if (reply is null || reply.Version != 1 || reply.Kind != kind || reply.ConnectionId != connection || reply.BatchId != batch)
            throw new MockFailure("mock-invalid-reply");
    }
}
