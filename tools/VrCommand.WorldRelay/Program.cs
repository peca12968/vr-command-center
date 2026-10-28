using System.Net.Http.Json;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using VrCommand.Core;
using VrCommand.Simulation;

var options = args.Chunk(2).ToArray();
if (options.Any(pair => pair.Length != 2 || pair[0] is not ("--recording" or "--world-journal" or "--combat-journal" or "--demo-room" or "--seconds" or "--environment-demo" or "--base-url" or "--key-file"))
    || options.Select(pair => pair[0]).Distinct().Count() != options.Length) throw new ArgumentException("Use named value pairs: --recording or --world-journal, optional --combat-journal, --demo-room, --seconds, --environment-demo, --base-url, --key-file.");
var values = options.ToDictionary(pair => pair[0], pair => pair[1]);
if (!bool.TryParse(values.GetValueOrDefault("--environment-demo", "false"), out var environmentDemo) || (values.ContainsKey("--environment-demo") && !values.ContainsKey("--demo-room")))
    throw new ArgumentException("--environment-demo requires true/false and a new --demo-room simulation.");
if (values.ContainsKey("--recording") == values.ContainsKey("--world-journal")) throw new ArgumentException("Choose exactly one of --recording (legacy NDJSON) or --world-journal (shared binary source).");
var binary = values.ContainsKey("--world-journal");
var path = Path.GetFullPath(values.GetValueOrDefault(binary ? "--world-journal" : "--recording")!);
var combatPath = Path.GetFullPath(values.GetValueOrDefault("--combat-journal", path + ".combat"));
var codec = new SystemWorldCodec();
var root = new DirectoryInfo(Environment.CurrentDirectory);
while (!File.Exists(Path.Combine(root.FullName, "VrCommand.slnx"))) root = root.Parent ?? throw new InvalidOperationException("Run from the repository.");
using var keys = JsonDocument.Parse(File.ReadAllText(values.GetValueOrDefault("--key-file", Path.Combine(root.FullName, "data/operator-keys.local.json"))).TrimStart('\uFEFF'));
using var http = new HttpClient { BaseAddress = new Uri(values.GetValueOrDefault("--base-url", "http://127.0.0.1:5080")), Timeout = TimeSpan.FromSeconds(10) };
http.DefaultRequestHeaders.Authorization = new("Bearer", keys.RootElement.GetProperty("OperatorKeys").GetProperty("GameServer").GetString());
var json = new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true, IgnoreReadOnlyProperties = false, WriteIndented = false };
string Write(object value) => JsonSerializer.Serialize(value, json);
async Task<T> Post<T>(HttpClient client, string route, object body)
{
    using var response = await client.PostAsJsonAsync(route, body, JsonFormat.Options); response.EnsureSuccessStatusCode();
    return (await response.Content.ReadFromJsonAsync<T>(JsonFormat.Options))!;
}
async Task Deliver(TelemetryOutbox queue)
{
    var route = "/api/sessions/" + queue.SessionId + "/combat-stream";
    await Post<CombatStreamView>(http, route, new OpenCombatStream(queue.StreamId, Enum.Parse<CombatOrigin>(queue.Origin)));
    while (queue.Pending is not null)
    {
        var batch = queue.PendingBatch(); using var response = await http.PostAsync(route + "/batch", new StringContent(TelemetryOutbox.BatchJson(batch), Encoding.UTF8, "application/json"));
        response.EnsureSuccessStatusCode(); var receipt = (await response.Content.ReadFromJsonAsync<StreamReceipt>(JsonFormat.Options))!;
        if (receipt.StreamId != queue.StreamId || receipt.AcceptedSequence < batch[^1].StreamSequence) throw new InvalidDataException("Invalid combat acknowledgment.");
        queue.AcknowledgeThrough(batch[^1].StreamSequence, batch[^1].ReportId);
    }
    if (queue.Complete && !queue.Sealed)
    {
        var receipt = await Post<CombatStreamView>(http, route + "/seal", new SealCombatStream(queue.StreamId, queue.LastSequence));
        if (!receipt.Sealed || receipt.AcceptedSequence != queue.LastSequence) throw new InvalidDataException("Invalid combat seal.");
        queue.MarkSealed();
    }
}
async Task<ClientWebSocket> Connect(Guid session)
{
    var socket = new ClientWebSocket(); socket.Options.SetRequestHeader("Authorization", http.DefaultRequestHeaders.Authorization!.ToString());
    var uri = new UriBuilder(http.BaseAddress!) { Scheme = http.BaseAddress!.Scheme == "https" ? "wss" : "ws", Path = "/api/sessions/" + session + "/world/publish" };
    try { await socket.ConnectAsync(uri.Uri, CancellationToken.None); return socket; } catch { socket.Dispose(); throw; }
}
async Task<JsonElement> Send(ClientWebSocket socket, string message)
{
    using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
    await socket.SendAsync(Encoding.UTF8.GetBytes(message), WebSocketMessageType.Text, true, timeout.Token);
    using var body = new MemoryStream(); var bytes = new byte[16384]; WebSocketReceiveResult result;
    do
    {
        result = await socket.ReceiveAsync(bytes, timeout.Token);
        if (result.MessageType != WebSocketMessageType.Text || body.Length + result.Count > 1024 * 1024) throw new InvalidDataException("Missing bounded world acknowledgment.");
        body.Write(bytes, 0, result.Count);
    } while (!result.EndOfMessage);
    using var response = JsonDocument.Parse(body.ToArray());
    if (response.RootElement.GetProperty("type").GetString() != "ack") throw new InvalidDataException(response.RootElement.ToString());
    var info = response.RootElement.GetProperty("info"); using var sent = JsonDocument.Parse(message);
    var type = sent.RootElement.GetProperty("type").GetString();
    if (type == "header")
        foreach (var field in new[] { "sessionId", "streamId", "origin" })
            if (info.GetProperty("header").GetProperty(field).GetString() != sent.RootElement.GetProperty("payload").GetProperty(field).GetString()) throw new InvalidDataException("World receipt identity mismatch.");
    if (type == "frame" && info.GetProperty("acceptedSequence").GetInt64() < sent.RootElement.GetProperty("payload").GetProperty("sequence").GetInt64()) throw new InvalidDataException("World receipt has not accepted this frame.");
    if (type == "seal" && (!info.GetProperty("complete").GetBoolean() || info.GetProperty("acceptedSequence").GetInt64() != sent.RootElement.GetProperty("finalSequence").GetInt64())) throw new InvalidDataException("World seal receipt mismatch.");
    return info.Clone();
}

if (!values.TryGetValue("--demo-room", out var roomValue))
{
    using var queue = TelemetryOutbox.OpenExisting(combatPath);
    if (binary)
    {
        using var saved = WorldOutbox.Recover(path, codec); var header = saved.Header;
        if (header.sessionId != queue.SessionId.ToString("D") || header.streamId != queue.StreamId.ToString("D") || header.origin != queue.Origin) throw new InvalidDataException("World and combat source identities disagree.");
        await Deliver(queue);
        using var publisher = new WorldPublisher(saved, codec, new WorldWebSocket(http.BaseAddress!.ToString(), queue.SessionId, http.DefaultRequestHeaders.Authorization!.Parameter!));
        while (saved.Pending != null || (saved.Complete && !saved.Sealed))
        {
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            if (!await publisher.Deliver(queue.AcknowledgedSequence, queue.Sealed, timeout.Token)) break;
        }
        Console.WriteLine(Write(new { sessionId = queue.SessionId, frames = saved.LastSequence, acknowledged = saved.AcknowledgedSequence, complete = saved.Sealed, origin = header.origin })); return;
    }
    await Deliver(queue);
    using var socket = await Connect(queue.SessionId);
    // Exclusive source lease. Read one line at a time, retain no unbounded frame collection.
    using var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.None);
    using var reader = new StreamReader(file); long frames = 0; var complete = false;
    while (await reader.ReadLineAsync() is { } line)
    {
        if (line.Length > 1024 * 1024) throw new InvalidDataException("Oversized source frame.");
        using var message = JsonDocument.Parse(line);
        var ack = await Send(socket, line); complete = ack.GetProperty("complete").GetBoolean();
        if (message.RootElement.GetProperty("type").GetString() == "frame") frames++;
    }
    Console.WriteLine(Write(new { sessionId = queue.SessionId, frames, complete, origin = "Simulation" })); return;
}
var room = int.Parse(roomValue); var seconds = int.Parse(values.GetValueOrDefault("--seconds", "3"));
if (room is < 1 or > 5 || seconds is < 1 or > 60 || File.Exists(path) || File.Exists(combatPath)) throw new ArgumentException("Demo requires a free room 1–5, 1–60 seconds, and new output files.");
using var master = new HttpClient { BaseAddress = http.BaseAddress, Timeout = http.Timeout };
master.DefaultRequestHeaders.Authorization = new("Bearer", keys.RootElement.GetProperty("OperatorKeys").GetProperty("Master").GetString());
if ((await master.GetFromJsonAsync<RoomView[]>("/api/rooms", JsonFormat.Options))!.Single(entry => entry.Id == room).SessionId.HasValue) throw new InvalidOperationException("Room is occupied; no existing session changed.");
var mission = await Post<Mission>(master, "/api/missions", new MissionDraft("World recording simulation", "Synthetic tracked rig; no headset attached", 900,
    environmentDemo ? new(ExperienceMode.VR, Weather.Storm, TimeOfDay.Night, true) : new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(1, EnemyBehavior.Hold, true),
    [new("sandbag", new(2, 0, 1), 15), new("barrel", new(3, 0, 3), 0)]));
var session = await Post<SessionView>(master, "/api/sessions", new { missionId = mission.Id, mode = "Independent", roomIds = new[] { room } });
var route = "/api/sessions/" + session.Id;
try
{
    var player = Guid.NewGuid(); await Post<SessionView>(master, route + "/players", new { playerId = player, name = "World Simulation", roomId = room, headset = "Quest3" });
    Directory.CreateDirectory(Path.GetDirectoryName(path)!);
    using var queue = TelemetryOutbox.OpenFile(combatPath, session.Id, "Simulation"); await Deliver(queue);
    var bridge = new ArenaSession(); ManagementSnapshot management = null!;
    async Task Refresh() { management = (await http.GetFromJsonAsync<ManagementSnapshot>(route, json))!; bridge.Apply(management); }
    await Refresh();
    var elapsed = System.Diagnostics.Stopwatch.StartNew();
    var header = WorldRecordingHeader.Create(session.Id, queue.StreamId, "Simulation", session.RoomIds, bridge.Props,
        DateTimeOffset.UtcNow.ToString("O", System.Globalization.CultureInfo.InvariantCulture));
    using var saved = binary ? WorldOutbox.Create(path, header, codec) : null;
    using var publisher = binary ? new WorldPublisher(saved!, codec, new WorldWebSocket(http.BaseAddress!.ToString(), session.Id, http.DefaultRequestHeaders.Authorization!.Parameter!)) : null;
    using var source = binary ? null : new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None);
    using var socket = binary ? null : await Connect(session.Id);
    async Task SaveSend(object message)
    {
        var line = Write(message);
        if (binary)
        {
            using var payload = JsonDocument.Parse(line); var type = payload.RootElement.GetProperty("type").GetString();
            if (type == "frame") saved!.Append(codec.ReadPacket(payload.RootElement.GetProperty("payload").GetRawText()));
            else if (type == "seal") saved!.Finish();
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            await publisher!.Deliver(queue.AcknowledgedSequence, queue.Sealed, timeout.Token); return;
        }
        var bytes = Encoding.UTF8.GetBytes(line + "\n"); source!.Write(bytes); source.Flush(true);
        await Send(socket!, line);
    }
    await SaveSend(new { type = "header", payload = header });
    long sequence = 0, worldCursor = 0;
    RecordedRig Rig(Guid id)
    {
        var body = bridge.World.PlayerSnapshot(id);
        return body.Connected ? new RecordedRig { kind = "Simulated", left = new RecordedVector(body.Head + new Vec3(-.25f, -.35f, .2f)), right = new RecordedVector(body.Muzzle) } : new RecordedRig();
    }
    async Task Capture()
    {
        queue.Capture(bridge.World, management.sequence); await Deliver(queue);
        var packet = WorldRecordingPacket.Capture(bridge.World, ++sequence, sequence == 1 ? 0 : elapsed.ElapsedMilliseconds,
            management.sequence, queue.LastSequence, worldCursor, Rig, management.environment.weather, management.environment.lightning);
        await SaveSend(new { type = "frame", payload = packet }); worldCursor = bridge.World.EventSequence;
    }
    await Capture();
    if (!bridge.Connect(1, player, room, 0, (await http.GetFromJsonAsync<SessionView>(route, JsonFormat.Options))!.Players.Single().AdmissionId)) throw new InvalidOperationException("Simulation binding failed.");
    var head = ArenaSession.Spawn(room, 0); var target = bridge.World.Snapshot().Enemies[0].Feet + new Vec3(0, .9f, 0);
    await Post<CommandReceipt>(master, route + "/commands", new ControlCommand(Guid.NewGuid(), ControlAction.Begin)); await Refresh();
    for (var tick = 0; tick < seconds * 20; tick++)
    {
        var time = tick * .05; bridge.Pose(1, head, head, (target - head).Normalized(), time);
        if (tick is 0 or 4) bridge.Weapon(1, (ulong)(tick + 1), false, time);
        bridge.Tick(time); await Capture(); await Task.Delay(50);
    }
    await Post<CommandReceipt>(master, route + "/commands", new ControlCommand(Guid.NewGuid(), ControlAction.Pause)); await Refresh(); await Capture();
    await Task.Delay(250);
    await Post<CommandReceipt>(master, route + "/commands", new ControlCommand(Guid.NewGuid(), ControlAction.SetEnvironment,
        new(ExperienceMode.VR, Weather.Storm, TimeOfDay.Night, true))); await Refresh(); await Capture();
    await Post<CommandReceipt>(master, route + "/commands", new ControlCommand(Guid.NewGuid(), ControlAction.End)); await Refresh();
    queue.Finish(bridge.World); await Deliver(queue); await Capture();
    await SaveSend(new { type = "seal", finalSequence = sequence });
    if (binary && !saved!.Sealed) throw new InvalidDataException("Shared source has not confirmed the final world seal.");
    Console.WriteLine(Write(new { sessionId = session.Id, frames = sequence, complete = true, origin = "Simulation", recording = path }));
}
catch
{
    try { await Post<CommandReceipt>(master, route + "/commands", new ControlCommand(Guid.NewGuid(), ControlAction.End)); } catch { }
    throw;
}
