using VrCommand.Core;

if (args.SequenceEqual(["--weather-vectors"])) { Console.WriteLine(EnvironmentChecks.Vectors()); return; }
if (args.SequenceEqual(["--enemy-vectors"])) { Console.WriteLine(EnemyPresentationChecks.Vectors()); return; }
if (args.SequenceEqual(["--weapon-vectors"])) { Console.WriteLine(WeaponPresentationChecks.Vectors()); return; }
if (args.SequenceEqual(["--armed-enemy-vectors"])) { Console.WriteLine(ArmedEnemyChecks.Vectors()); return; }
if (args.SequenceEqual(["--enemy-fire-vectors"])) { Console.WriteLine(EnemyFireChecks.Vectors()); return; }
if (args.SequenceEqual(["--player-fire-vectors"])) { Console.WriteLine(PlayerFireChecks.Vectors()); return; }
if (args.SequenceEqual(["--combat-audio-vectors"])) { Console.WriteLine(CombatAudioChecks.Vectors()); return; }
if(args.SequenceEqual(["--player-body-vectors"])) {Console.WriteLine(PlayerBodyChecks.Vectors());return;}
var checks = 0;
void Check(bool condition, string message)
{
    if (!condition) throw new Exception(message);
    Console.WriteLine($"PASS {++checks}: {message}");
}
void Reject<T>(Action action, string message) where T : Exception
{
    try { action(); }
    catch (T) { Check(true, message); return; }
    throw new Exception($"Expected {typeof(T).Name}: {message}");
}

var directory = Path.Combine(Path.GetTempPath(), "vr-command-checks-" + Guid.NewGuid().ToString("N"));
try
{
    if (args.SequenceEqual(["--venue-setting-scope"]))
    {
        VenueClimateScopeChecks.Run(Check, directory);
        Console.WriteLine($"{checks} venue setting scope checks passed.");
        return;
    }
    var draft = new MissionDraft("夜間防衛", "守住目標", 900,
        new(ExperienceMode.VR, Weather.Storm, TimeOfDay.Night, true),
        new(8, EnemyBehavior.Hold, true), [new("sandbag", new(1, 0, 2), 90)]);
    var store = new MissionStore(directory);
    var mission = store.Create(draft);
    var restored = new MissionStore(directory).Get(mission.Id);
    Check(restored.Definition.Name == draft.Name && restored.Definition.Props.Length == 1,
        "Mission survives store restart with environment and props");
    Reject<ArgumentException>(() => store.Create(draft with { DurationSeconds = 0 }), "Invalid mission rejected");
    Reject<ArgumentException>(() => store.Create(draft with { Props = [new("barrel", new(float.NaN, 0, 0), 0)] }),
        "Non-finite prop coordinates rejected");
    var manager = new SessionManager();
    Reject<ArgumentException>(() => manager.Create(SessionMode.Linked, [1, 2, 3, 4, 4], mission), "Repeated room rejected");
    Reject<ArgumentException>(() => manager.Create(SessionMode.Independent, [0], mission), "Invalid room rejected");
    var independent = Enumerable.Range(1, 5).Select(room => manager.Create(SessionMode.Independent, [room], mission)).ToArray();
    Check(manager.Rooms().All(r => r.SessionId.HasValue), "Five independent rooms coexist");
    Reject<InvalidOperationException>(() => manager.Create(SessionMode.Linked, [1, 2, 3, 4, 5], mission),
        "Occupied rooms cannot join another session");
    var playerId = Guid.NewGuid();
    manager.Join(independent[0].Id, playerId, "Alpha", 1, HeadsetKind.Quest3);
    Reject<InvalidOperationException>(() => manager.Join(independent[1].Id, playerId, "Alpha", 2, HeadsetKind.ViveXr),
        "One player cannot occupy two rooms");
    foreach (var session in independent) manager.End(session.Id);
    var linked = manager.Create(SessionMode.Linked, [1, 2, 3, 4, 5], mission);
    foreach (var room in Enumerable.Range(1, 5))
        foreach (var index in Enumerable.Range(1, 5))
            manager.Join(linked.Id, Guid.NewGuid(), $"P{room}-{index}", room,
                index % 2 == 0 ? HeadsetKind.ViveXr : HeadsetKind.Quest3);
    Check(manager.Get(linked.Id).Players.Length == 25, "Linked session admits 25 mixed-device player records");
    Reject<InvalidOperationException>(() => manager.Join(linked.Id, Guid.NewGuid(), "Overflow", 1, HeadsetKind.Quest3),
        "26th player rejected");
    var snapshot = manager.Get(linked.Id);
    snapshot.RoomIds[0] = 99;
    snapshot.Mission.Definition.Props[0] = new("changed", new(0, 0, 0), 0);
    Check(manager.Get(linked.Id).RoomIds[0] == 1
        && manager.Get(linked.Id).Mission.Definition.Props[0].AssetId == "sandbag", "Returned snapshots cannot mutate session state");
    manager.Leave(linked.Id, manager.Get(linked.Id).Players[0].Id);
    manager.Join(linked.Id, Guid.NewGuid(), "Replacement", 1, HeadsetKind.ViveXr);
    Check(manager.Get(linked.Id).Players.Length == 25, "Leaving releases a player slot");
    manager.End(linked.Id);
    Check(manager.Rooms().All(r => r.SessionId is null && r.PlayerCount == 0), "Ending releases every room and player");
    Check(manager.Get(linked.Id).State == SessionState.Ended, "Ended session remains available as history");
    var concurrent = manager.Create(SessionMode.Independent, [1], mission);
    var accepted = 0;
    Parallel.For(0, 30, i =>
    {
        try { manager.Join(concurrent.Id, Guid.NewGuid(), $"Concurrent-{i}", 1, HeadsetKind.Quest3); Interlocked.Increment(ref accepted); }
        catch (InvalidOperationException) { }
    });
    Check(accepted == 5 && manager.Get(concurrent.Id).Players.Length == 5, "Concurrent joins cannot exceed room capacity");
    LifecycleChecks.Run(Check, directory, mission);
    OperatorChecks.Run(Check, mission);
    PersistenceChecks.Run(Check, directory, mission);
    CombatChecks.Run(Check, mission);
    HardwareFeedbackChecks.Run(Check, mission);
    HardwareFeedbackChecks.Live(Check, mission);
    FinalReportChecks.Run(Check, directory, mission);
    PlayerTicketChecks.Run(Check, mission);
    AdmissionChecks.Run(Check, directory, mission);
    RequestRetryChecks.Run(Check, directory, mission);
    IndependentSetChecks.Run(Check, directory, mission);
    VenueRosterChecks.Run(Check, directory, mission);
    VenuePhaseChecks.Run(Check, directory, mission);
    VenueClimateScopeChecks.Run(Check, directory);
    SimulationChecks.Run(Check);
    NavigationChecks.Run(Check);
    for (var targetingCase = 0; targetingCase < VrCommand.Unity.Tests.AiTargetingCases.Names.Length; targetingCase++)
        Check(VrCommand.Unity.Tests.AiTargetingCases.Run(targetingCase), VrCommand.Unity.Tests.AiTargetingCases.Names[targetingCase]);
    WalkSurfaceChecks.Run(Check);
    ArenaSessionChecks.Run(Check, directory);
    TelemetryChecks.Run(Check, directory, mission);
    MissionLayoutChecks.Run(Check, directory);
    RoomAlignmentChecks.Run(Check);
    WorldChecks.Run(Check, directory);
    ReadinessChecks.Run(Check, directory);
    ConnectionEndpointChecks.Run(Check, directory);
    MissionClockChecks.Run(Check, directory);
    CameraBookmarkChecks.Run(Check, directory);
    MissionLibraryChecks.Run(Check, directory);
    EnvironmentChecks.Run(Check);
    EnemyPresentationChecks.Run(Check);
    ArmedEnemyChecks.Run(Check);
    EnemyFireChecks.Run(Check);
    PlayerFireChecks.Run(Check);
    CombatAudioChecks.Run(Check);
    PlayerBodyChecks.Run(Check);
    WeaponPresentationChecks.Run(Check);
    WorldSourceChecks.Run(Check, directory);
    OperatorNetworkChecks.Run(Check);
    Console.WriteLine($"All {checks} checks passed. These are domain checks, not headset or gameplay load tests.");
}
finally
{
    // Only the unique temporary directory created by this check run is removed.
    var resolved = Path.GetFullPath(directory);
    var tempRoot = Path.GetFullPath(Path.GetTempPath()).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
    if (!resolved.StartsWith(tempRoot, StringComparison.OrdinalIgnoreCase)
        || !Path.GetFileName(resolved).StartsWith("vr-command-checks-", StringComparison.Ordinal))
        throw new InvalidOperationException("Refusing to clean a directory outside this check run.");
    if (Directory.Exists(resolved)) Directory.Delete(resolved, recursive: true);
}
