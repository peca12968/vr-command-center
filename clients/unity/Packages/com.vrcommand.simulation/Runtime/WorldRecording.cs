using System;
using System.Collections.Generic;
using System.Linq;

namespace VrCommand.Simulation
{
    public static class WorldAssetSets
    {
        public const string Legacy = "primitives-v1", FieldProps = "field-props-v1";
        public static bool Supported(string value) => value == Legacy || value == FieldProps;
    }
    [Serializable] public sealed class RecordedVector
    {
        public float x, y, z;
        public RecordedVector() { }
        public RecordedVector(Vec3 value) { x = value.X; y = value.Y; z = value.Z; }
        public Vec3 ToVector() => new Vec3(x, y, z);
    }
    [Serializable] public sealed class RecordedRotation { public float x, y, z, w = 1; }
    [Serializable] public sealed class RecordedRig
    {
        public string kind = "None";
        public RecordedRotation headRotation = new RecordedRotation(), leftRotation = new RecordedRotation(), rightRotation = new RecordedRotation();
        public RecordedVector left = new RecordedVector(), right = new RecordedVector();
    }
    [Serializable] public sealed class RecordedProp
    {
        public string id = "", kind = "";
        public int roomId;
        public RecordedVector feet = new RecordedVector();
        public float yaw;
    }
    [Serializable] public sealed class WorldRecordingHeader
    {
        public int schemaVersion = 1;
        public int environmentVersion;
        public string sessionId = "", streamId = "", origin = "Simulation", rulesVersion = "0.8.0", assetSet = "primitives-v1", calibration = "uncalibrated-vr";
        public string captureStartedAtUtc = "";
        public int[] roomIds = new int[0];
        public RecordedProp[] props = new RecordedProp[0];
        public static WorldRecordingHeader Create(Guid session, Guid stream, string origin, int[] rooms, WorldProp[] geometry, string captureStartedAtUtc = "", int environmentVersion = EnvironmentPresentation.Version, string assetSet = WorldAssetSets.Legacy) => new WorldRecordingHeader
        {
            sessionId = session.ToString("D"), streamId = stream.ToString("D"), origin = origin, captureStartedAtUtc = captureStartedAtUtc, environmentVersion = environmentVersion, assetSet = assetSet, roomIds = (int[])rooms.Clone(),
            props = geometry.Select(prop => new RecordedProp { id = prop.Id.ToString("D"), roomId = prop.RoomId, kind = prop.Kind.ToString(), feet = new RecordedVector(prop.Feet), yaw = prop.Yaw }).ToArray()
        };
    }
    [Serializable] public sealed class RecordedPlayer
    {
        public string id = ""; public int roomId, health, magazine, reserve; public bool connected, reloading;
        public RecordedVector head = new RecordedVector(), muzzle = new RecordedVector(), forward = new RecordedVector();
        public RecordedRig rig = new RecordedRig();
    }
    [Serializable] public sealed class RecordedEnemy { public string id = ""; public int roomId, health; public RecordedVector feet = new RecordedVector(); }
    [Serializable] public sealed class RecordedFrame
    {
        public long tick, throughSequence;
        public string phase = "Preparing", behavior = "Hold", visibility = "Clear";
        public bool autoAttack, night;
        public RecordedPlayer[] players = new RecordedPlayer[0]; public RecordedEnemy[] enemies = new RecordedEnemy[0];
    }
    [Serializable] public sealed class RecordedEvent
    {
        public long sequence, tick; public string eventId = "", kind = "", playerId = "", shotId = "", enemyId = "", hit = "", targetId = "";
        public int damage; public bool hasRay; public float distance;
        public RecordedVector origin = new RecordedVector(), direction = new RecordedVector();
    }
    [Serializable] public sealed class WorldRecordingPacket
    {
        public long sequence, elapsedMilliseconds, observedSequence, throughCombatSequence;
        public bool suspended, lightning; public string weather = "Clear";
        public RecordedFrame frame = new RecordedFrame(); public RecordedEvent[] events = new RecordedEvent[0];
        public static WorldRecordingPacket Capture(ArenaWorld world, long sequence, long elapsed, long observed, long combat,
            long afterWorld, Func<Guid, RecordedRig> rig, string weather = "Clear", bool lightning = false, bool suspended = false)
        {
            var snapshot = world.Snapshot(); var events = new List<WorldEvent>(); var cursor = afterWorld;
            while (cursor < snapshot.ThroughSequence) { var page = world.Events(cursor); events.AddRange(page); cursor = page[page.Length - 1].Sequence; }
            return new WorldRecordingPacket { sequence = sequence, elapsedMilliseconds = elapsed, observedSequence = observed, throughCombatSequence = combat,
                weather = weather, lightning = lightning, suspended = suspended,
                frame = new RecordedFrame { tick = snapshot.Tick, throughSequence = snapshot.ThroughSequence, phase = snapshot.Phase.ToString(), behavior = snapshot.Behavior.ToString(),
                    visibility = snapshot.Visibility.ToString(), autoAttack = snapshot.AutoAttack, night = snapshot.Night,
                    players = snapshot.Players.Select(player => new RecordedPlayer { id = player.Id.ToString("D"), roomId = player.RoomId, head = new RecordedVector(player.Head),
                        muzzle = new RecordedVector(player.Muzzle), forward = new RecordedVector(player.Forward), health = player.Health, magazine = player.Magazine, reserve = player.Reserve,
                        connected = player.Connected, reloading = player.Reloading, rig = rig(player.Id) }).ToArray(),
                    enemies = snapshot.Enemies.Select(enemy => new RecordedEnemy { id = enemy.Id.ToString("D"), roomId = enemy.RoomId, health = enemy.Health, feet = new RecordedVector(enemy.Feet) }).ToArray() },
                events = events.Select(entry => new RecordedEvent { sequence = entry.Sequence, eventId = entry.EventId.ToString("D"), tick = entry.Tick, kind = entry.Kind.ToString(),
                    playerId = entry.PlayerId.ToString("D"), shotId = entry.ShotId?.ToString("D") ?? "", enemyId = entry.EnemyId?.ToString("D") ?? "", damage = entry.Damage,
                    hasRay = entry.Origin.HasValue, origin = new RecordedVector(entry.Origin ?? default), direction = new RecordedVector(entry.Direction ?? default),
                    distance = entry.Distance ?? 0, hit = entry.Hit?.ToString() ?? "", targetId = entry.TargetId?.ToString("D") ?? "" }).ToArray() };
        }
    }
    public static class WorldRecordingValidation
    {
        public static void Header(WorldRecordingHeader header)
        {
            if (header == null || header.schemaVersion != 1 || header.environmentVersion < 0 || header.environmentVersion > EnvironmentPresentation.Version || !Id(header.sessionId) || !Id(header.streamId)
                || !new[] { "Simulation", "GameServer" }.Contains(header.origin) || header.rulesVersion != "0.8.0" || !WorldAssetSets.Supported(header.assetSet)
                || header.calibration != "uncalibrated-vr" || header.roomIds == null || (header.roomIds.Length != 1 && header.roomIds.Length != 5)
                || header.roomIds.Distinct().Count() != header.roomIds.Length || header.roomIds.Any(room => room < 1 || room > 5)
                || header.props == null || header.props.Length > 2500) throw new ArgumentException("Unsupported recording identity, profile or geometry.");
            if (header.captureStartedAtUtc != "" && (!DateTimeOffset.TryParseExact(header.captureStartedAtUtc, "O", System.Globalization.CultureInfo.InvariantCulture,
                System.Globalization.DateTimeStyles.None, out var started) || started.Offset != TimeSpan.Zero || started.Year < 2020 || started.Year > 2100))
                throw new ArgumentException("Recording capture clock must be an explicit UTC timestamp, or empty for legacy sources.");
            var ids = new HashSet<string>();
            foreach (var prop in header.props)
                if (prop == null || !Id(prop.id) || !ids.Add(prop.id) || !header.roomIds.Contains(prop.roomId)
                    || !new[] { "Sandbag", "Barrel" }.Contains(prop.kind) || !Point(prop.feet) || Math.Abs(prop.feet.y) > .001f
                    || Math.Abs(prop.feet.x - ArenaWorld.RoomOrigin(prop.roomId).X) > 6 || Math.Abs(prop.feet.z) > 6 || !Vec3.Valid(prop.yaw))
                    throw new ArgumentException("Invalid recorded prop.");
        }
        public static void Packet(WorldRecordingHeader header, WorldRecordingPacket packet, WorldRecordingPacket? previous)
        {
            if (packet == null || packet.sequence != (previous?.sequence ?? 0) + 1 || packet.elapsedMilliseconds < (previous?.elapsedMilliseconds ?? 0)
                || packet.elapsedMilliseconds > 86400000 || packet.observedSequence < 1 || packet.frame == null || packet.frame.tick < (previous?.frame.tick ?? 0)
                || packet.events == null || packet.events.Length > 500 || packet.frame.players == null || packet.frame.players.Length > 25
                || packet.frame.enemies == null || packet.frame.enemies.Length > 100 || packet.frame.throughSequence != (previous?.frame.throughSequence ?? 0) + packet.events.Length
                || !new[] { "Preparing", "Running", "Paused", "Ended" }.Contains(packet.frame.phase)
                || !new[] { "Hold", "Patrol", "Advance" }.Contains(packet.frame.behavior) || !new[] { "Clear", "Fog", "Storm" }.Contains(packet.frame.visibility)
                || !new[] { "Clear", "Rain", "Fog", "Storm" }.Contains(packet.weather)) throw new ArgumentException("Invalid recording packet sequence or frame.");
            if (previous == null && (packet.frame.phase != "Preparing" || packet.frame.tick != 0 || packet.events.Length != 0 || packet.throughCombatSequence != 0 || packet.elapsedMilliseconds != 0))
                throw new ArgumentException("Recording must start from the unstarted world.");
            if (packet.frame.phase == "Preparing" && (packet.frame.tick != 0 || packet.events.Length != 0)) throw new ArgumentException("Preparing worlds cannot advance combat time.");
            var ids = new HashSet<string>();
            foreach (var player in packet.frame.players)
            {
                if (player == null || !Id(player.id) || !ids.Add(player.id) || !header.roomIds.Contains(player.roomId) || !Point(player.head) || !Point(player.muzzle) || !Point(player.forward)
                    || player.health < 0 || player.health > 100 || player.magazine < 0 || player.magazine > 30 || player.reserve < 0 || player.reserve > 90
                    || Math.Abs(player.forward.ToVector().Length - 1) > .01f || Math.Abs(player.head.x - ArenaWorld.RoomOrigin(player.roomId).X) > 6
                    || Math.Abs(player.head.z) > 6 || player.head.y < .45f || player.head.y > 2.4f || Vec3.Distance(player.head.ToVector(), player.muzzle.ToVector()) > 1.2f
                    || player.rig == null || !new[] { "None", "Simulated", "Tracked" }.Contains(player.rig.kind)
                    || !Rotation(player.rig.headRotation) || !Rotation(player.rig.leftRotation) || !Rotation(player.rig.rightRotation)
                    || !Point(player.rig.left) || !Point(player.rig.right) || (player.connected && player.rig.kind == "None")
                    || (player.rig.kind != "None" && (Vec3.Distance(player.head.ToVector(), player.rig.left.ToVector()) > 2.5f || Vec3.Distance(player.head.ToVector(), player.rig.right.ToVector()) > 2.5f)))
                    throw new ArgumentException("Invalid recorded player or tracked rig.");
            }
            if (packet.frame.players.GroupBy(player => player.roomId).Any(group => group.Count() > 5)) throw new ArgumentException("Recorded player capacity exceeded.");
            foreach (var enemy in packet.frame.enemies)
                if (enemy == null || !Id(enemy.id) || !ids.Add(enemy.id) || !header.roomIds.Contains(enemy.roomId) || !Point(enemy.feet) || Math.Abs(enemy.feet.y) > .001f
                    || Math.Abs(enemy.feet.x - ArenaWorld.RoomOrigin(enemy.roomId).X) > 6 || Math.Abs(enemy.feet.z) > 6 || enemy.health < 0 || enemy.health > 100)
                    throw new ArgumentException("Invalid recorded enemy.");
            var eventIds = new HashSet<string>(); var sequence = previous?.frame.throughSequence ?? 0; var combat = previous?.throughCombatSequence ?? 0;
            foreach (var entry in packet.events)
            {
                if (entry == null || entry.sequence != ++sequence || !Id(entry.eventId) || !eventIds.Add(entry.eventId) || !Id(entry.playerId)
                    || entry.tick < (previous?.frame.tick ?? 0) || entry.tick > packet.frame.tick || !Enum.TryParse<WorldEventKind>(entry.kind, out var kind)
                    || !Enum.IsDefined(typeof(WorldEventKind), kind)) throw new ArgumentException("Invalid recorded event.");
                if (TelemetryRecord.Combat(kind)) combat++;
                if (kind == WorldEventKind.ShotFired || kind == WorldEventKind.EnemyShot)
                {
                    if (!entry.hasRay || !Point(entry.origin) || !Point(entry.direction) || Math.Abs(entry.direction.ToVector().Length - 1) > .01f
                        || !Vec3.Valid(entry.distance) || entry.distance < 0 || entry.distance > 40 || !Enum.TryParse<HitKind>(entry.hit, out var hit)
                        || !Enum.IsDefined(typeof(HitKind), hit) || entry.hit != hit.ToString()) throw new ArgumentException("Invalid recorded ray.");
                }
                else if (entry.hasRay) throw new ArgumentException("Only shot events contain a ray.");
                if (entry.kind != kind.ToString() || entry.damage < 0 || entry.damage > 100 || (kind != WorldEventKind.PlayerDamaged && entry.damage != 0)
                    || ((kind == WorldEventKind.ShotFired || kind == WorldEventKind.ShotHit || kind == WorldEventKind.EnemyEliminated) ? !Id(entry.shotId) : entry.shotId != "")
                    || ((kind == WorldEventKind.ShotHit || kind == WorldEventKind.EnemyEliminated || kind == WorldEventKind.EnemyShot || kind == WorldEventKind.PlayerDamaged) ? !Id(entry.enemyId) : entry.enemyId != "")
                    || (entry.targetId != "" && !Id(entry.targetId)) || (kind == WorldEventKind.PlayerDamaged && entry.damage == 0)) throw new ArgumentException("Invalid recorded event content.");
            }
            if (combat != packet.throughCombatSequence) throw new ArgumentException("Recorded combat boundary disagrees with its world events.");
        }
        private static bool Id(string value) => Guid.TryParseExact(value, "D", out var id) && id != Guid.Empty && value == id.ToString("D");
        private static bool Point(RecordedVector value) => value != null && value.ToVector().Finite && Math.Abs(value.x) < 10000 && Math.Abs(value.y) < 10000 && Math.Abs(value.z) < 10000;
        private static bool Rotation(RecordedRotation value) => value != null && Vec3.Valid(value.x) && Vec3.Valid(value.y) && Vec3.Valid(value.z) && Vec3.Valid(value.w)
            && Math.Abs(value.x * value.x + value.y * value.y + value.z * value.z + value.w * value.w - 1) < .1f;
    }
}
