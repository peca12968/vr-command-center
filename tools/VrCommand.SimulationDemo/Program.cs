using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using VrCommand.Core;
using VrCommand.Simulation;

var arguments = args.Chunk(2).ToArray();
if (arguments.Any(pair => pair.Length != 2) || arguments.Any(pair => pair[0] is not ("--base-url" or "--key-file" or "--room" or "--output"))
    || arguments.Select(pair => pair[0]).Distinct().Count() != arguments.Length)
    throw new ArgumentException("Use --base-url, --key-file, --room and --output as named value pairs.");
var options = arguments.ToDictionary(pair => pair[0], pair => pair[1]);
var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../.."));
var keyFile = options.GetValueOrDefault("--key-file", Path.Combine(root, "data/operator-keys.local.json"));
using var keyJson = JsonDocument.Parse(File.ReadAllText(keyFile).TrimStart('\uFEFF'));
var keys = keyJson.RootElement.GetProperty("OperatorKeys");
using var master = new HttpClient { BaseAddress = new Uri(options.GetValueOrDefault("--base-url", "http://127.0.0.1:5080")), Timeout = TimeSpan.FromSeconds(10) };
using var gameServer = new HttpClient { BaseAddress = master.BaseAddress, Timeout = master.Timeout };
master.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", keys.GetProperty("Master").GetString());
gameServer.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", keys.GetProperty("GameServer").GetString());
var room = int.Parse(options.GetValueOrDefault("--room", "1"));
if (room is < 1 or > 5) throw new ArgumentException("Room must be 1–5.");
var rooms = await Get<RoomView[]>(master, "/api/rooms");
if (rooms.Single(r => r.Id == room).SessionId is not null) throw new InvalidOperationException("Room is in use; no existing session was changed.");
var mission = await Post<Mission>(master, "/api/missions", new MissionDraft("射線與掩體模擬", "頭戴裝置未接入。依幾何判定掩體阻擋、AI 傷害與兩次命中擊殺。", 900,
    new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(1, EnemyBehavior.Hold, true), [new("barrel", new(0, 0, 0), 0)]));
var session = await Post<SessionView>(master, "/api/sessions", new { missionId = mission.Id, mode = "Independent", roomIds = new[] { room } });
var ended = false;
try
{
    var playerId = Guid.NewGuid();
    await Post<SessionView>(master, $"/api/sessions/{session.Id}/players", new { playerId, name = "Quest3-Simulation", roomId = room, headset = "Quest3" });
    var origin = ArenaWorld.RoomOrigin(room);
    var enemyId = Guid.NewGuid();
    var props = new[] { new WorldProp(Guid.NewGuid(), room, PropKind.Barrel, origin, 0) };
    var world = new ArenaWorld([room], props);
    world.AddPlayer(playerId, room, origin + new Vec3(0, 1.4f, -3));
    world.AddEnemy(enemyId, room, origin + new Vec3(0, 0, 3), origin + new Vec3(2, 0, 3));
    var frames = new List<WorldFrame> { world.Snapshot() };
    await Control("Begin"); world.SetPhase(WorldPhase.Running);
    var muzzle = origin + new Vec3(0, .6f, -3);
    world.SetPlayerPose(playerId, origin + new Vec3(0, 1.4f, -3), muzzle, (origin + new Vec3(0, .9f, 3) - muzzle).Normalized());
    frames.Add(world.Snapshot());
    var blocked = world.Fire(playerId, Guid.NewGuid());
    frames.Add(world.Snapshot());
    world.Tick(); frames.Add(world.Snapshot()); // Enemy has line of sight above the barrel; player muzzle does not.
    await Control("SetEnemies", new(1, EnemyBehavior.Hold, false));
    world.SetPolicy(AiBehavior.Hold, false, Visibility.Clear, false);
    for (var i = 0; i < 3; i++) { world.Tick(); frames.Add(world.Snapshot()); }
    muzzle = origin + new Vec3(2, 1.4f, -3);
    world.SetPlayerPose(playerId, muzzle, muzzle, (origin + new Vec3(0, .9f, 3) - muzzle).Normalized());
    frames.Add(world.Snapshot());
    var firstHit = world.Fire(playerId, Guid.NewGuid());
    frames.Add(world.Snapshot());
    for (var i = 0; i < 4; i++) { world.Tick(); frames.Add(world.Snapshot()); }
    var kill = world.Fire(playerId, Guid.NewGuid()); frames.Add(world.Snapshot());
    await Control("SetEnemies", new(2, EnemyBehavior.Patrol, false));
    world.AddEnemy(Guid.NewGuid(), room, origin + new Vec3(-3, 0, 0), origin + new Vec3(3, 0, 0));
    world.SetPolicy(AiBehavior.Patrol, false, Visibility.Clear, false); frames.Add(world.Snapshot());
    for (var i = 0; i < 200; i++) { world.Tick(); frames.Add(world.Snapshot()); }
    var reports = world.Events().Select(ToReport).Where(r => r is not null).ToArray();
    foreach (var report in reports)
    {
        // Same immutable report ID/body on network retry. A lost response cannot count a shot twice.
        for (var attempt = 0; ; attempt++)
        {
            try { await Post<CombatReceipt>(gameServer, $"/api/sessions/{session.Id}/combat", report!); break; }
            catch (HttpRequestException) when (attempt < 2) { await Task.Delay(100); }
        }
    }
    await Control("End"); ended = true; world.SetPhase(WorldPhase.Ended); frames.Add(world.Snapshot());
    var statistics = await Get<SessionStatistics>(master, $"/api/sessions/{session.Id}/statistics");
    var player = statistics.Players.Single(p => p.PlayerId == playerId);
    if (blocked.Hit != HitKind.Cover || firstHit.Hit != HitKind.Enemy || !kill.Eliminated || statistics.Origin != CombatOrigin.Simulation
        || player.AmmoUsed != 3 || player.ShotsHit != 2 || player.Kills != 1 || player.HitsReceived != 1 || player.Health != 80)
        throw new InvalidOperationException("Geometry simulation and persisted statistics did not match.");
    var output = Path.GetFullPath(options.GetValueOrDefault("--output", Path.Combine(root, "artifacts/simulation-demo", session.Id + ".json")));
    Directory.CreateDirectory(Path.GetDirectoryName(output)!);
    await File.WriteAllTextAsync(output, JsonSerializer.Serialize(new { schemaVersion = 2, rulesVersion = "0.8.0", origin = "Simulation", sessionId = session.Id,
        roomIds = new[] { room }, mission, props, tickSeconds = ArenaWorld.TickSeconds, frames, events = world.Events(), statistics }, JsonFormat.Options));
    Console.WriteLine(JsonSerializer.Serialize(new { sessionId = session.Id, origin = "Simulation", blockedByCover = true, player, output }, JsonFormat.Options));
}
finally
{
    if (!ended)
    {
        try { await Control("End"); }
        catch (Exception) { Console.Error.WriteLine("Could not end the demo session; inspect its ID: " + session.Id); }
    }
}
async Task Control(string action, EnemySettings? enemies = null) =>
    await Post<CommandReceipt>(master, $"/api/sessions/{session.Id}/commands", new { commandId = Guid.NewGuid(), action, enemies });
static async Task<T> Get<T>(HttpClient client, string path) => await client.GetFromJsonAsync<T>(path, JsonFormat.Options) ?? throw new InvalidDataException("Empty API response.");
static async Task<T> Post<T>(HttpClient client, string path, object body)
{
    using var response = await client.PostAsJsonAsync(path, body, JsonFormat.Options);
    response.EnsureSuccessStatusCode();
    return await response.Content.ReadFromJsonAsync<T>(JsonFormat.Options) ?? throw new InvalidDataException("Empty API response.");
}
static CombatReport? ToReport(WorldEvent entry) => entry.Kind switch
{
    WorldEventKind.ShotFired => new(entry.EventId, CombatKind.ShotFired, CombatOrigin.Simulation, entry.PlayerId, entry.ShotId),
    WorldEventKind.ShotHit => new(entry.EventId, CombatKind.ShotHit, CombatOrigin.Simulation, entry.PlayerId, entry.ShotId, entry.EnemyId),
    WorldEventKind.EnemyEliminated => new(entry.EventId, CombatKind.EnemyEliminated, CombatOrigin.Simulation, entry.PlayerId, entry.ShotId, entry.EnemyId),
    WorldEventKind.PlayerDamaged => new(entry.EventId, CombatKind.PlayerDamaged, CombatOrigin.Simulation, entry.PlayerId, Damage: entry.Damage),
    _ => null
};
