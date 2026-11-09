using System.Buffers.Binary;
using System.Diagnostics;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Sockets;
using System.Text.Json;
using System.Text.Json.Serialization;
using VrCommand.Core;

internal static class LiveHardwareGateway
{
    private const int MaxBatch = 32, MaxAttempts = 1024, MaxFrameBytes = 32 * 1024;
    private static readonly TimeSpan PollInterval = TimeSpan.FromMilliseconds(150);
    private static readonly TimeSpan RequestTimeout = TimeSpan.FromMilliseconds(750);
    private static readonly TimeSpan SignalLifetime = TimeSpan.FromSeconds(2);
    private static readonly JsonSerializerOptions Wire = new(JsonFormat.Options)
    {
        AllowDuplicateProperties = false, UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        PropertyNameCaseInsensitive = false, WriteIndented = false, MaxDepth = 12
    };

    private sealed record Binding(Guid DeviceId, Guid PlayerId, Guid AdmissionId, int Seat);
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

    internal static async Task<int> Run(string input, string output)
    {
        using var file = File.OpenRead(input);
        if (file.Length is < 1 or > 8192) throw new ArgumentException("Use a bounded live rehearsal configuration.");
        var bytes = new byte[file.Length]; file.ReadExactly(bytes);
        var config = JsonSerializer.Deserialize<Configuration>(bytes, Wire) ?? throw new ArgumentException("Missing configuration.");
        if (config.Version != 1 || config.SessionId == Guid.Empty || config.RoomId is < 1 or > 5
            || config.MockPort is < 1024 or > 65535 || config.Seconds is < 1 or > 120
            || config.Bindings is not { Length: >= 1 and <= 5 } || config.Bindings.Any(b => b is null || b.DeviceId == Guid.Empty
                || b.PlayerId == Guid.Empty || b.AdmissionId == Guid.Empty || b.Seat is < 0 or > 4)
            || config.Bindings.Select(b => b.Seat).Distinct().Count() != config.Bindings.Length
            || config.Bindings.Select(b => b.PlayerId).Distinct().Count() != config.Bindings.Length
            || config.Bindings.Select(b => b.DeviceId).Distinct().Count() != config.Bindings.Length
            || config.Bindings.Select(b => b.AdmissionId).Distinct().Count() != config.Bindings.Length)
            throw new ArgumentException("Use one room and unique seat, device, player and admission bindings.");
        if (!Uri.TryCreate(config.ManagementUrl, UriKind.Absolute, out var api) || api.UserInfo.Length != 0 || api.Query.Length != 0
            || api.Fragment.Length != 0 || api.AbsolutePath != "/" || !(api.Scheme == "https" || api.Scheme == "http" && api.Host == "127.0.0.1"))
            throw new ArgumentException("Use an HTTPS management origin or 127.0.0.1 HTTP.");
        var key = Environment.GetEnvironmentVariable("VR_COMMAND_ROOM_KEY");
        if (string.IsNullOrWhiteSpace(key) || key.Length > 512 || key.Any(c => c <= 32 || c >= 127)) throw new ArgumentException("Set the room operator key in the environment.");

        using var client = new HttpClient(new SocketsHttpHandler { AllowAutoRedirect = false, UseProxy = false })
            { BaseAddress = api, Timeout = Timeout.InfiniteTimeSpan };
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", key);
        var identity = await Get<OperatorIdentity>(client, "/api/me", CancellationToken.None);
        if (identity.Role != OperatorRole.RoomController || identity.RoomId != config.RoomId)
            throw new AccessDeniedException("This rehearsal requires the matching room controller.");

        var bindings = config.Bindings.ToDictionary(b => (b.PlayerId, b.AdmissionId, b.Seat));
        var route = $"/api/sessions/{config.SessionId:D}/rooms/{config.RoomId}/hardware-feedback";
        var attempts = new List<Attempt>();
        int connections = 0, attachments = 0, managementFaults = 0, mockFaults = 0, dropped = 0;
        var termination = "duration";
        using var run = new CancellationTokenSource(TimeSpan.FromSeconds(config.Seconds));
        try
        {
            while (!run.IsCancellationRequested)
            {
                using var mock = new TcpClient(AddressFamily.InterNetwork);
                var connection = Guid.NewGuid();
                try
                {
                    await Connect(mock, config.MockPort, run.Token);
                    var wire = mock.GetStream();
                    await Exchange(wire, new { version = 1, kind = "hello", mode = "simulation", connectionId = connection, config.RoomId },
                        "ready", connection, null, run.Token);
                    connections++;
                    var page = (await Read(client, route, config, null, run.Token)).Page;
                    attachments++;
                    var reattach = false;
                    while (page.State != SessionState.Ended)
                    {
                        await Task.Delay(PollInterval, run.Token);
                        var after = page.ThroughSequence;
                        var current = await Read(client, route, config, after, run.Token);
                        page = current.Page;
                        if (page.ResetReason is not null) continue;
                        var deliveries = page.Signals.Where(current.IsFresh).Select(signal =>
                        {
                            bindings.TryGetValue((signal.PlayerId, signal.AdmissionId, signal.Seat), out var binding);
                            return binding is null ? null : new Delivery(binding.DeviceId, signal);
                        }).OfType<Delivery>().ToArray();
                        dropped += page.Signals.Length - deliveries.Length;
                        if (deliveries.Length == 0) continue;
                        if (deliveries.Length > MaxBatch) { dropped += deliveries.Length; continue; }
                        if (attempts.Count >= MaxAttempts) { termination = "attempt-limit"; break; }

                        var batch = Guid.NewGuid();
                        var status = "cancelled";
                        try
                        {
                            await Exchange(wire, new { version = 1, kind = "feedback", mode = "simulation", connectionId = connection,
                                batchId = batch, config.RoomId, page.StreamId, page.RunningSinceSequence, signals = deliveries }, "ack", connection, batch, run.Token);
                            var verified = await Read(client, route, config, after, run.Token);
                            if (verified.Page.State == SessionState.Running && verified.Page.ResetReason is null
                                && verified.Page.StreamId == page.StreamId && verified.Page.RunningSinceSequence == page.RunningSinceSequence
                                && deliveries.All(item => verified.IsFresh(item.Signal) && verified.Page.Signals.Contains(item.Signal)))
                                status = "simulated-acknowledged";
                            else if (verified.Page.State == SessionState.Ended) page = verified.Page;
                            else reattach = true;
                        }
                        catch (MockFailure failure) { status = failure.Message; throw; }
                        finally { attempts.Add(new(connection, batch, status, deliveries)); }
                        if (reattach) break;
                    }
                    if (reattach) continue;
                    if (page.State == SessionState.Ended) termination = "ended";
                    break;
                }
                catch (MockFailure) { mockFaults++; }
                catch (Exception failure) when (failure is HttpRequestException or TimeoutException || failure is IOException && failure is not InvalidDataException) { managementFaults++; }
                await Task.Delay(PollInterval, run.Token);
            }
        }
        catch (OperationCanceledException) when (run.IsCancellationRequested) { }

        var complete = attachments > 0 && termination != "attempt-limit";
        var acknowledged = attempts.Where(item => item.Status == "simulated-acknowledged").Sum(item => item.Deliveries.Length);
        using var destination = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        JsonSerializer.Serialize(destination, new { version = 1, complete, simulatedHardwareOnly = true, physicalDeliveryConfirmed = false,
            config.SessionId, config.RoomId, termination, connections, attachments, managementFaults, mockFaults, dropped, acknowledged, attempts }, JsonFormat.Options);
        destination.Flush(true);
        Console.WriteLine(JsonSerializer.Serialize(new { complete, simulatedHardwareOnly = true, physicalDeliveryConfirmed = false, acknowledged }, Wire));
        return complete ? 0 : 1;
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
        var page = await Get<RoomHardwareFeedback>(client, after.HasValue ? FormattableString.Invariant($"{route}?after={after}") : route, run);
        if (page.Version != 1 || page.RoomId != config.RoomId || page.SessionId != config.SessionId || page.ThroughSequence < 1
            || page.ThroughSequence < after || !Enum.IsDefined(page.State) || page.CheckedAtUtc == default
            || (after.HasValue ? page.ResetReason is not (null or "inactive" or "backlog") : page.ResetReason != "attached")
            || page.Signals is not { Length: <= 256 } || (page.ResetReason is not null && page.Signals.Length != 0)
            || (page.ResetReason is null && (page.State != SessionState.Running || page.StreamId is null || page.StreamId == Guid.Empty
                || page.RunningSinceSequence is null or < 1 || page.RunningSinceSequence > page.ThroughSequence)))
            throw new InvalidDataException("Unexpected feedback cursor, room or phase.");
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
