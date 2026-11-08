using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace VrCommand.Simulation
{
    // Field DTOs are shared by Unity JsonUtility and the real API contract fixture. No Unity or backend dependency.
    [Serializable] public sealed class ManagementSnapshot
    {
        public string id = null!, state = null!;
        public long sequence;
        public int[] roomIds = null!;
        public ManagedMission mission = null!;
        public ManagedEnvironment environment = null!;
        public ManagedEnemies enemies = null!;
        public ManagedPlayer[] players = null!;
        public ManagedMissionClock? missionClock;
        public ManagedRoomAlignment? roomAlignment;
    }
    [Serializable] public sealed class ManagedRoomAlignment
    {
        public string? room1, room2, room3, room4, room5;
        public string? ForRoom(int room) => room switch { 1 => room1, 2 => room2, 3 => room3, 4 => room4, 5 => room5, _ => null };
        public bool Covers(int[] rooms)
        {
            if (rooms is null || rooms.Length is not (1 or 5) || rooms.Any(room => room < 1 || room > 5)
                || rooms.Distinct().Count() != rooms.Length) return false;
            for (var room = 1; room <= 5; room++)
            {
                var hash = ForRoom(room);
                if (rooms.Contains(room) ? !ArenaConnectionProfile.IsAlignmentHash(hash) : !string.IsNullOrEmpty(hash)) return false;
            }
            return true;
        }
    }
    [Serializable] public sealed class ManagedMission { public string id = null!; public ManagedDefinition definition = null!; }
    [Serializable] public sealed class ManagedDefinition { public string name = null!, briefing = null!; public ManagedProp[] props = null!; public int durationSeconds; }
    [Serializable] public sealed class ManagedMissionClock { public int version; public bool autoEnd; public long configuredAtSequence; }
    [Serializable] public sealed class ManagedProp { public string assetId = null!; public ManagedPosition position = null!; public float yawDegrees; }
    [Serializable] public sealed class ManagedPosition { public float x, y, z; public Vec3 Vector => new Vec3(x, y, z); }
    [Serializable] public sealed class ManagedEnvironment { public string mode = null!, weather = null!, timeOfDay = null!; public bool lightning; }
    [Serializable] public sealed class ManagedEnemies { public int count; public string behavior = null!; public bool autoAttack; }
    [Serializable] public sealed class ManagedPlayer { public string id = null!, admissionId = null!, headset = null!; public int roomId, seat; }

    // Single-threaded server adapter. Transport authenticates a ticket before binding its connection here.
    public sealed class ArenaSession
    {
        private sealed class Binding
        {
            internal Guid Player;
            internal Guid Admission;
            internal double LastPose = double.NegativeInfinity;
            internal ulong LastInput;
        }
        private readonly Dictionary<ulong, Binding> connections = new Dictionary<ulong, Binding>();
        private Dictionary<Guid, ManagedPlayer> roster = new Dictionary<Guid, ManagedPlayer>();
        private SortedDictionary<int, Guid> enemySlots = new SortedDictionary<int, Guid>();
        private const int ReinforcementIntervalTicks = 20;
        private Guid sessionId, missionId;
        private int enemyGeneration, enemyTarget;
        private long nextReinforcementTick;
        private int missionDuration;
        private bool clockAutoEnd;
        private long sequence;
        private int[] roomIds = null!;
        private WorldProp[] props = null!;
        public ArenaWorld World { get; private set; } = null!;
        public bool IsMixedReality { get; private set; }
        public WorldProp[] Props => props == null ? new WorldProp[0] : (WorldProp[])props.Clone();
        public bool ClockDue => World != null && clockAutoEnd && MissionClock.Due(World.TickNumber, missionDuration);

        public static Guid StableId(Guid session, string purpose)
        {
            using (var hash = SHA256.Create())
            {
                var bytes = hash.ComputeHash(Encoding.UTF8.GetBytes(session.ToString("D") + ":" + purpose));
                var id = new byte[16]; Array.Copy(bytes, id, id.Length); return new Guid(id);
            }
        }
        public static Vec3 Spawn(int room, int seat) => ArenaWorld.RoomOrigin(room) + new Vec3((seat - 2) * 1.5f, 1.65f, -3);

        public void Apply(ManagementSnapshot snapshot)
        {
            if (snapshot == null || !Guid.TryParse(snapshot.id, out var id) || id == Guid.Empty || snapshot.sequence < 1
                || snapshot.mission == null || !Guid.TryParse(snapshot.mission.id, out var mission) || mission == Guid.Empty
                || snapshot.mission.definition == null || snapshot.mission.definition.props == null
                || snapshot.mission.definition.props.Length > 500 || snapshot.environment == null || snapshot.environment.mode is not ("VR" or "MR")
                || snapshot.enemies == null || snapshot.enemies.count < 0 || snapshot.enemies.count > 100
                || !Enum.TryParse<AiBehavior>(snapshot.enemies.behavior, out var behavior) || !Enum.IsDefined(typeof(AiBehavior), behavior)
                || !Enum.TryParse<WorldPhase>(snapshot.state, out var phase) || !Enum.IsDefined(typeof(WorldPhase), phase)
                || snapshot.players == null || snapshot.players.Length > 25 || snapshot.roomIds == null
                || (snapshot.roomIds.Length != 1 && snapshot.roomIds.Length != 5) || snapshot.roomIds.Distinct().Count() != snapshot.roomIds.Length
                || snapshot.roomIds.Any(room => room < 1 || room > 5)
                || !new[] { "Clear", "Rain", "Fog", "Storm" }.Contains(snapshot.environment.weather)
                || !new[] { "Day", "Night" }.Contains(snapshot.environment.timeOfDay))
                throw new ArgumentException("Unsupported or incomplete arena mission snapshot.");
            var mixedReality = snapshot.environment.mode == "MR";
            if (World != null && (id != sessionId || mission != missionId || snapshot.sequence < sequence
                || mixedReality != IsMixedReality || !snapshot.roomIds.OrderBy(room => room).SequenceEqual(roomIds)))
                throw new InvalidOperationException("The running server cannot switch session, mission, experience mode or rewind management state.");
            if ((World == null && phase != WorldPhase.Preparing) || (World != null && World.Phase == WorldPhase.Ended && phase != WorldPhase.Ended))
                throw new InvalidOperationException("Start the game server during Preparing; ended worlds cannot restart.");
            var clock = snapshot.missionClock; var autoEnd = clock?.autoEnd == true;
            var duration = snapshot.mission.definition.durationSeconds;
            if ((duration != 0 && !MissionClock.ValidDuration(duration)) || (clock != null && (clock.version == 0
                ? autoEnd || clock.configuredAtSequence != 0 : clock.version != MissionClock.Version || clock.configuredAtSequence < 1
                    || clock.configuredAtSequence > snapshot.sequence)) || (autoEnd && !MissionClock.ValidDuration(duration)))
                throw new ArgumentException("Unsupported mission clock settings.");
            if (World != null && ((missionDuration != 0 && missionDuration != duration)
                || (World.Phase != WorldPhase.Preparing && clockAutoEnd != autoEnd)))
                throw new InvalidOperationException("Running mission clock policy and duration are immutable.");
            var nextRoster = new Dictionary<Guid, ManagedPlayer>();
            foreach (var player in snapshot.players)
            {
                if (player == null || !Guid.TryParse(player.id, out var playerId) || playerId == Guid.Empty
                    || !Guid.TryParse(player.admissionId, out var admission) || admission == Guid.Empty
                    || nextRoster.Values.Any(other => other.admissionId == admission.ToString("D"))
                    || nextRoster.ContainsKey(playerId) || !snapshot.roomIds.Contains(player.roomId) || player.seat < 0 || player.seat > 4
                    || nextRoster.Values.Any(other => other.roomId == player.roomId && other.seat == player.seat))
                    throw new ArgumentException("Invalid mission roster or duplicate seat.");
                nextRoster.Add(playerId, new ManagedPlayer { id = playerId.ToString("D"), admissionId = admission.ToString("D"), roomId = player.roomId, seat = player.seat });
            }
            var nextProps = new List<WorldProp>();
            foreach (var room in snapshot.roomIds.OrderBy(value => value))
                for (var index = 0; index < snapshot.mission.definition.props.Length; index++)
                {
                    var prop = snapshot.mission.definition.props[index];
                    if (prop == null || prop.position == null || (prop.assetId != "barrel" && prop.assetId != "sandbag")
                        || Math.Abs(prop.position.y) > .001f)
                        throw new ArgumentException("Only floor-level sandbag and barrel props are supported by this VR arena.");
                    nextProps.Add(new WorldProp(StableId(id, "prop:" + room + ":" + index), room,
                        prop.assetId == "barrel" ? PropKind.Barrel : PropKind.Sandbag,
                        ArenaWorld.RoomOrigin(room) + prop.position.Vector, prop.yawDegrees));
                }
            var changedRoster = roster.Count != nextRoster.Count || roster.Any(pair => !nextRoster.TryGetValue(pair.Key, out var value)
                || pair.Value.roomId != value.roomId || pair.Value.seat != value.seat || pair.Value.admissionId != value.admissionId);
            if (World != null && (!SameProps(props, nextProps.ToArray()) || (phase == WorldPhase.Preparing && World.Phase != WorldPhase.Preparing)))
                throw new InvalidOperationException("Mission geometry cannot change after server initialization.");
            if (World != null && World.Phase != WorldPhase.Preparing && nextRoster.Any(pair => !roster.ContainsKey(pair.Key)
                || roster[pair.Key].roomId != pair.Value.roomId || roster[pair.Key].seat != pair.Value.seat || roster[pair.Key].admissionId != pair.Value.admissionId))
                throw new InvalidOperationException("New roster bodies require Preparing.");

            var rebuilt = World == null || (World.Phase == WorldPhase.Preparing && changedRoster);
            if (rebuilt)
            {
                // Build and validate a replacement before publishing any state; Preparing has no combat to preserve.
                var orderedRooms = snapshot.roomIds.OrderBy(room => room).ToArray();
                var geometry = nextProps.ToArray();
                var candidate = new ArenaWorld(orderedRooms, geometry);
                foreach (var pair in nextRoster)
                {
                    candidate.AddPlayer(pair.Key, pair.Value.roomId, Spawn(pair.Value.roomId, pair.Value.seat));
                    candidate.SetPlayerConnected(pair.Key, false);
                }
                var slots = new SortedDictionary<int, Guid>();
                var generation = SpawnAvailable(candidate, orderedRooms, slots, snapshot.enemies.count, id, enemyGeneration);
                if (slots.Count != snapshot.enemies.count) throw new ArgumentException("Mission has no free enemy spawn area.");
                World = candidate; props = geometry; roomIds = orderedRooms; enemySlots = slots;
                enemyGeneration = generation;
                enemyTarget = snapshot.enemies.count; nextReinforcementTick = ReinforcementIntervalTicks;
                foreach (var binding in connections.Values) binding.LastPose = double.NegativeInfinity;
            }
            else if (World!.Phase != WorldPhase.Ended && snapshot.enemies.count != enemyTarget)
            {
                enemyTarget = snapshot.enemies.count;
                foreach (var slot in enemySlots.Keys.Reverse().TakeWhile(slot => slot >= enemyTarget).ToArray())
                { World.RemoveEnemy(enemySlots[slot]); enemySlots.Remove(slot); }
                if (phase != WorldPhase.Ended) TryReinforce();
            }
            foreach (var connection in connections.Where(pair => !nextRoster.TryGetValue(pair.Value.Player, out var entry)
                || entry.admissionId != pair.Value.Admission.ToString("D")).Select(pair => pair.Key).ToArray())
            {
                if (rebuilt) connections.Remove(connection); // The replacement world already omits this body.
                else Disconnect(connection);
            }
            roster = nextRoster; sessionId = id; missionId = mission; sequence = snapshot.sequence; IsMixedReality = mixedReality;
            clockAutoEnd = autoEnd; missionDuration = duration;
            if (World.Phase == WorldPhase.Ended)
            { if (phase != WorldPhase.Ended) throw new InvalidOperationException("World is already ended."); return; }
            World.SetPolicy(behavior, snapshot.enemies.autoAttack,
                snapshot.environment.weather == "Fog" ? Visibility.Fog : snapshot.environment.weather == "Storm" ? Visibility.Storm : Visibility.Clear,
                snapshot.environment.timeOfDay == "Night");
            if (phase == WorldPhase.Paused && World.Phase == WorldPhase.Preparing) World.SetManagedPhase(WorldPhase.Running);
            if (World.Phase != phase) World.SetManagedPhase(phase);
        }

        private void TryReinforce()
        {
            enemyGeneration = SpawnAvailable(World, roomIds, enemySlots, enemyTarget, sessionId, enemyGeneration);
            nextReinforcementTick = World.TickNumber + ReinforcementIntervalTicks;
        }

        private static int SpawnAvailable(ArenaWorld world, int[] rooms, SortedDictionary<int, Guid> slots,
            int target, Guid session, int generation)
        {
            if (slots.Count >= target) return generation;
            var existing = world.Snapshot().Enemies;
            var available = new Dictionary<int, List<Vec3>>();
            for (var slot = 0; slot < target; slot++)
            {
                if (slots.ContainsKey(slot)) continue;
                var room = rooms[slot % rooms.Length];
                if (!available.TryGetValue(room, out var candidates))
                {
                    candidates = world.EnemySpawnCandidates(room);
                    var occupants = existing.Where(enemy => enemy.RoomId == room).ToArray();
                    candidates.RemoveAll(point => occupants.Any(enemy => Vec3.Distance(enemy.Feet, point) <= .7f));
                    available.Add(room, candidates);
                }
                if (candidates.Count == 0) continue;
                // Candidate spacing is .75m, so selecting one leaves every other candidate clear.
                var id = StableId(session, "enemy:" + generation);
                world.AddEnemy(id, room, candidates[0], candidates[candidates.Count - 1]);
                slots.Add(slot, id);
                candidates.RemoveAt(0);
                generation++;
            }
            return generation;
        }
        private static bool SameProps(WorldProp[] left, WorldProp[] right) => left.Length == right.Length && left.Zip(right, (a, b) =>
            a.Id == b.Id && a.RoomId == b.RoomId && a.Kind == b.Kind && a.Feet.Equals(b.Feet) && a.Yaw.Equals(b.Yaw)).All(value => value);

        public bool Connect(ulong connection, Guid player, int room, int seat, Guid admission)
        {
            if (World == null || World.Phase == WorldPhase.Ended || ClockDue || connections.ContainsKey(connection)
                || connections.Values.Any(binding => binding.Player == player) || !roster.TryGetValue(player, out var entry)
                || admission == Guid.Empty || entry.admissionId != admission.ToString("D") || entry.roomId != room || entry.seat != seat) return false;
            connections.Add(connection, new Binding { Player = player, Admission = admission }); return true;
        }
        public void Disconnect(ulong connection)
        {
            if (!connections.TryGetValue(connection, out var binding)) return;
            if (World.Phase != WorldPhase.Ended) World.SetPlayerConnected(binding.Player, false);
            connections.Remove(connection);
        }
        public bool Pose(ulong connection, Vec3 head, Vec3 muzzle, Vec3 forward, double now, bool tracked = false)
        {
            if (IsMixedReality && !tracked) return false;
            if (!connections.TryGetValue(connection, out var binding) || !ValidTime(now) || now < binding.LastPose || World.Phase == WorldPhase.Ended) return false;
            var previous = World.PlayerSnapshot(binding.Player);
            if (Vec3.Distance(Vec3.Flat(previous.Head), Vec3.Flat(head)) > .5 + 4 * Math.Min(.5, double.IsNegativeInfinity(binding.LastPose) ? 0 : now - binding.LastPose)) return false;
            try { World.SetPlayerPose(binding.Player, head, muzzle, forward); }
            catch (ArgumentException) { return false; }
            binding.LastPose = now; World.SetPlayerConnected(binding.Player, true); return true;
        }
        public bool Weapon(ulong connection, ulong input, bool reload, double now)
        {
            if (ClockDue || !connections.TryGetValue(connection, out var binding) || input == 0 || input <= binding.LastInput || !ValidTime(now)
                || now < binding.LastPose || now - binding.LastPose > .5 || World.Phase != WorldPhase.Running) return false;
            binding.LastInput = input;
            var id = StableId(sessionId, "input:" + connection + ":" + input);
            try { if (reload) World.Reload(binding.Player, id); else World.Fire(binding.Player, id); return true; }
            catch (InvalidOperationException) { return false; }
        }
        public void Tick(double now)
        {
            if (!ValidTime(now) || World == null || ClockDue) return;
            if (World.Phase != WorldPhase.Ended)
                foreach (var binding in connections.Values) World.SetPlayerConnected(binding.Player, now >= binding.LastPose && now - binding.LastPose <= .5);
            World.Tick();
            if (World.Phase == WorldPhase.Running && enemySlots.Count < enemyTarget && World.TickNumber >= nextReinforcementTick)
                TryReinforce();
        }
        public void Suspend() { if (World != null && World.Phase == WorldPhase.Running) World.SetPhase(WorldPhase.Paused); }
        private static bool ValidTime(double now) => !double.IsNaN(now) && !double.IsInfinity(now) && now >= 0;
    }
}
