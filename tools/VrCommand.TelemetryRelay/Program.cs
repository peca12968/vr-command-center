using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using VrCommand.Core;
using VrCommand.Simulation;

var pairs = args.Chunk(2).ToArray();
if (pairs.Any(pair => pair.Length != 2 || pair[0] is not ("--journal" or "--base-url" or "--key-file" or "--demo-room"))
    || pairs.Select(pair => pair[0]).Distinct().Count() != pairs.Length) throw new ArgumentException("Use --journal, --base-url, --key-file and optional --demo-room as value pairs.");
var options = pairs.ToDictionary(pair => pair[0], pair => pair[1]);
var journalPath = Path.GetFullPath(options.GetValueOrDefault("--journal") ?? throw new ArgumentException("--journal is required."));
var root = new DirectoryInfo(Environment.CurrentDirectory);
while (!File.Exists(Path.Combine(root.FullName, "VrCommand.slnx"))) root = root.Parent ?? throw new InvalidOperationException("Run from the repository.");
using var keys = JsonDocument.Parse(File.ReadAllText(options.GetValueOrDefault("--key-file", Path.Combine(root.FullName, "data/operator-keys.local.json"))).TrimStart('\uFEFF'));
using var http = new HttpClient { BaseAddress = new Uri(options.GetValueOrDefault("--base-url", "http://127.0.0.1:5080")), Timeout = TimeSpan.FromSeconds(10) };
http.DefaultRequestHeaders.Authorization = new("Bearer", keys.RootElement.GetProperty("OperatorKeys").GetProperty("GameServer").GetString());
if (options.TryGetValue("--demo-room", out var value))
{
    var room = int.Parse(value); if (room is < 1 or > 5 || File.Exists(journalPath)) throw new ArgumentException("Demo needs room 1–5 and a new journal path.");
    using var master = new HttpClient { BaseAddress = http.BaseAddress, Timeout = http.Timeout };
    master.DefaultRequestHeaders.Authorization = new("Bearer", keys.RootElement.GetProperty("OperatorKeys").GetProperty("Master").GetString());
    var rooms = await master.GetFromJsonAsync<RoomView[]>("/api/rooms", JsonFormat.Options);
    if (rooms!.Single(entry => entry.Id == room).SessionId.HasValue) throw new InvalidOperationException("Room is occupied; no existing session changed.");
    var mission = await Post<Mission>(master, "/api/missions", new MissionDraft("Outbox recovery simulation", "No headset attached", 900,
        new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(1, EnemyBehavior.Hold, true), []));
    var session = await Post<SessionView>(master, "/api/sessions", new { missionId = mission.Id, mode = "Independent", roomIds = new[] { room } });
    var path = "/api/sessions/" + session.Id;
    try
    {
        var player = Guid.NewGuid(); await Post<SessionView>(master, path + "/players", new { playerId = player, name = "Outbox Simulation", roomId = room, headset = "Quest3" });
        using var queue = TelemetryOutbox.OpenFile(journalPath, session.Id, "Simulation");
        await Post<CombatStreamView>(http, path + "/combat-stream", new OpenCombatStream(queue.StreamId, CombatOrigin.Simulation));
        var jsonOptions = new JsonSerializerOptions(JsonFormat.Options) { IncludeFields = true };
        var bridge = new ArenaSession();
        async Task Refresh() => bridge.Apply((await http.GetFromJsonAsync<ManagementSnapshot>(path, jsonOptions))!);
        await Refresh(); if (!bridge.Connect(1, player, room, 0, (await http.GetFromJsonAsync<SessionView>(path, JsonFormat.Options))!.Players.Single().AdmissionId)) throw new InvalidOperationException("Simulation binding failed.");
        var head = ArenaSession.Spawn(room, 0); var target = bridge.World.Snapshot().Enemies[0].Feet + new Vec3(0, .9f, 0);
        bridge.Pose(1, head, head, (target - head).Normalized(), 0);
        await Post<CommandReceipt>(master, path + "/commands", new ControlCommand(Guid.NewGuid(), ControlAction.Begin)); await Refresh();
        var observed = (await http.GetFromJsonAsync<SessionView>(path, JsonFormat.Options))!.Sequence;
        if (!bridge.Weapon(1, 1, false, 0)) throw new InvalidOperationException("First simulated shot failed."); queue.Capture(bridge.World, observed);
        for (var tick = 1; tick <= 4; tick++) { bridge.Tick(tick * .05); queue.Capture(bridge.World, observed); }
        if (!bridge.Weapon(1, 2, false, .2)) throw new InvalidOperationException("Second simulated shot failed."); queue.Capture(bridge.World, observed);
        await Post<CommandReceipt>(master, path + "/commands", new ControlCommand(Guid.NewGuid(), ControlAction.End)); await Refresh(); queue.Finish(bridge.World);
        var statistics = await http.GetFromJsonAsync<SessionStatistics>(path + "/statistics", JsonFormat.Options);
        using var firstReport = JsonDocument.Parse(queue.Pending!.ToJson());
        Console.WriteLine(JsonSerializer.Serialize(new { sessionId = session.Id, journal = journalPath, origin = "Simulation", queuedReports = queue.LastSequence,
            pendingTelemetry = statistics!.PendingTelemetry, firstReport = firstReport.RootElement }, JsonFormat.Options));
    }
    catch
    {
        try { await Post<CommandReceipt>(master, path + "/commands", new ControlCommand(Guid.NewGuid(), ControlAction.End)); } catch { }
        throw;
    }
    return;
}
using (var queue = TelemetryOutbox.OpenExisting(journalPath))
{
    var path = "/api/sessions/" + queue.SessionId;
    var attached = await Post<CombatStreamView>(http, path + "/combat-stream", new OpenCombatStream(queue.StreamId, Enum.Parse<CombatOrigin>(queue.Origin)));
    if (attached.StreamId != queue.StreamId || attached.Origin.ToString() != queue.Origin) throw new InvalidDataException("Server stream identity mismatch.");
    while (queue.Pending is not null)
    {
        var batch = queue.PendingBatch();
        var receipt = await PostJson<StreamReceipt>(http, path + "/combat-stream/batch", TelemetryOutbox.BatchJson(batch));
        if (receipt.StreamId != queue.StreamId || receipt.AcceptedSequence < batch[^1].StreamSequence) throw new InvalidDataException("Invalid stream receipt.");
        queue.AcknowledgeThrough(batch[^1].StreamSequence, batch[^1].ReportId);
    }
    if (queue.Complete && !queue.Sealed)
    {
        var seal = await Post<CombatStreamView>(http, path + "/combat-stream/seal", new SealCombatStream(queue.StreamId, queue.LastSequence));
        if (!seal.Sealed || seal.AcceptedSequence != queue.LastSequence || seal.StreamId != queue.StreamId) throw new InvalidDataException("Invalid seal receipt.");
        queue.MarkSealed();
    }
    var statistics = await http.GetFromJsonAsync<SessionStatistics>(path + "/statistics", JsonFormat.Options);
    Console.WriteLine(JsonSerializer.Serialize(new { sessionId = queue.SessionId, acknowledged = queue.AcknowledgedSequence, complete = queue.Complete, sealedStream = queue.Sealed, statistics }, JsonFormat.Options));
}
static Task<T> Post<T>(HttpClient http, string path, object body) => PostJson<T>(http, path, JsonSerializer.Serialize(body, JsonFormat.Options));
static async Task<T> PostJson<T>(HttpClient http, string path, string json)
{
    for (var attempt = 0; ; attempt++)
    {
        try
        {
            using var response = await http.PostAsync(path, new StringContent(json, Encoding.UTF8, "application/json")); response.EnsureSuccessStatusCode();
            return await response.Content.ReadFromJsonAsync<T>(JsonFormat.Options) ?? throw new InvalidDataException("Missing API response.");
        }
        catch (HttpRequestException exception) when (attempt < 2 && (!exception.StatusCode.HasValue || (int)exception.StatusCode.Value >= 500)) { await Task.Delay(100); }
        catch (TaskCanceledException) when (attempt < 2) { await Task.Delay(100); }
    }
}
