using System;
using System.Collections.Generic;
using System.Linq;

namespace VrCommand.Simulation
{
    // Single-owner simulation. Only the server calls these methods; this class is not a network/auth boundary.
    public sealed class ArenaWorld
    {
        public const float TickSeconds = .05f;
        public const int MagazineSize = 30;
        private sealed class Player
        {
            internal Guid Id; internal int Room; internal Vec3 Head, Muzzle, Forward;
            internal int Health = 100, Magazine = MagazineSize, Reserve = 90;
            internal long NextShot, ReloadUntil;
        }
        private sealed class Enemy
        {
            internal Guid Id; internal int Room; internal Vec3 Feet, Start, Patrol, RouteTarget;
            internal int Health = 100; internal long NextShot, NextPlan; internal bool Returning;
            internal List<Vec3> Route = new List<Vec3>();
        }
        private sealed class Hit
        {
            internal HitKind Kind; internal Guid? Id; internal float Distance;
        }
        private readonly Dictionary<int, GridNavigation> rooms = new Dictionary<int, GridNavigation>();
        private readonly List<Player> players = new List<Player>();
        private readonly List<Enemy> enemies = new List<Enemy>();
        private readonly WorldProp[] props;
        private readonly HashSet<Guid> entities = new HashSet<Guid>();
        private readonly Dictionary<Guid, ShotResult> shots = new Dictionary<Guid, ShotResult>();
        private readonly Dictionary<Guid, Guid> reloads = new Dictionary<Guid, Guid>();
        private readonly List<WorldEvent> events = new List<WorldEvent>();
        public long TickNumber { get; private set; }
        public WorldPhase Phase { get; private set; } = WorldPhase.Preparing;
        public AiBehavior Behavior { get; private set; } = AiBehavior.Hold;
        public bool AutoAttack { get; private set; } = true;
        public Visibility Visibility { get; private set; }
        public bool Night { get; private set; }

        public static Vec3 RoomOrigin(int roomId)
        {
            if (roomId < 1 || roomId > 5) throw new ArgumentException("Room must be 1–5.");
            return new Vec3((roomId - 3) * 14, 0, 0);
        }
        public ArenaWorld(int[] roomIds, WorldProp[] props)
        {
            if (roomIds == null || (roomIds.Length != 1 && roomIds.Length != 5)
                || roomIds.Distinct().Count() != roomIds.Length || roomIds.Any(r => r < 1 || r > 5)
                || props == null || props.Length > 2500) throw new ArgumentException("Invalid arena configuration.");
            this.props = (WorldProp[])props.Clone();
            foreach (var prop in this.props)
            {
                if (prop == null || prop.Id == Guid.Empty || !entities.Add(prop.Id) || !roomIds.Contains(prop.RoomId)
                    || !Enum.IsDefined(typeof(PropKind), prop.Kind) || !prop.Feet.Finite || !Vec3.Valid(prop.Yaw)
                    || Math.Abs(prop.Feet.Y) > 10 || Math.Abs(prop.Feet.X - RoomOrigin(prop.RoomId).X) > 6 || Math.Abs(prop.Feet.Z) > 6)
                    throw new ArgumentException("Invalid arena prop.");
            }
            foreach (var room in roomIds) rooms.Add(room, new GridNavigation(RoomOrigin(room), this.props.Where(p => p.RoomId == room).ToArray()));
        }
        private void Active() { if (Phase == WorldPhase.Ended) throw new InvalidOperationException("World has ended."); }
        private void Running() { if (Phase != WorldPhase.Running) throw new InvalidOperationException("World is not running."); }
        private void Reserve(Guid id, int room)
        {
            if (id == Guid.Empty || !rooms.ContainsKey(room) || entities.Contains(id)) throw new ArgumentException("Invalid or reused entity identity.");
        }
        public void AddPlayer(Guid id, int room, Vec3 head)
        {
            if (Phase != WorldPhase.Preparing) throw new InvalidOperationException("Roster must be prepared before running.");
            Reserve(id, room); ValidatePose(room, head, head, new Vec3(0, 0, 1));
            if (players.Count(p => p.Room == room) >= 5 || players.Count >= 25) throw new InvalidOperationException("Player capacity reached.");
            entities.Add(id); players.Add(new Player { Id = id, Room = room, Head = head, Muzzle = head, Forward = new Vec3(0, 0, 1) });
        }
        public void RemovePlayer(Guid id) { Active(); players.Remove(FindPlayer(id)); }
        public void AddEnemy(Guid id, int room, Vec3 feet, Vec3 patrol)
        {
            Active(); Reserve(id, room);
            if (enemies.Count >= 100 || !feet.Finite || !patrol.Finite || Math.Abs(feet.Y) > .001f || Math.Abs(patrol.Y) > .001f
                || !rooms[room].Walkable(feet) || !rooms[room].Walkable(patrol)) throw new ArgumentException("Enemy spawn or patrol point is not walkable.");
            entities.Add(id); enemies.Add(new Enemy { Id = id, Room = room, Feet = feet, Start = feet, Patrol = patrol });
        }
        public void RemoveEnemy(Guid id)
        {
            Active(); var enemy = enemies.SingleOrDefault(e => e.Id == id) ?? throw new KeyNotFoundException("Enemy not found.");
            enemies.Remove(enemy);
        }
        public void SetPhase(WorldPhase next)
        {
            if (!Enum.IsDefined(typeof(WorldPhase), next) || Phase == WorldPhase.Ended || next == Phase
                || (next == WorldPhase.Running ? Phase != WorldPhase.Preparing && Phase != WorldPhase.Paused
                    : next == WorldPhase.Paused ? Phase != WorldPhase.Running : next != WorldPhase.Ended))
                throw new InvalidOperationException("Invalid world phase transition.");
            if (next == WorldPhase.Running && players.Count == 0) throw new InvalidOperationException("At least one player is required.");
            Phase = next;
        }
        public void SetPolicy(AiBehavior behavior, bool autoAttack, Visibility visibility, bool night)
        {
            Active();
            if (!Enum.IsDefined(typeof(AiBehavior), behavior) || !Enum.IsDefined(typeof(Visibility), visibility)) throw new ArgumentException("Invalid AI policy.");
            if (Behavior != behavior) foreach (var enemy in enemies) enemy.Route.Clear();
            Behavior = behavior; AutoAttack = autoAttack; Visibility = visibility; Night = night;
        }
        private Player FindPlayer(Guid id) => players.SingleOrDefault(p => p.Id == id) ?? throw new KeyNotFoundException("Player not found.");
        private void ValidatePose(int room, Vec3 head, Vec3 muzzle, Vec3 forward)
        {
            if (!head.Finite || !muzzle.Finite || !forward.Finite || head.Y < .45f || head.Y > 2.4f || muzzle.Y < .1f || muzzle.Y > 2.6f
                || Math.Abs(forward.Length - 1) > .01f || Vec3.Distance(head, muzzle) > 1.2f
                || !rooms[room].Walkable(Vec3.Flat(head)) || Math.Abs(muzzle.X - RoomOrigin(room).X) > 6 || Math.Abs(muzzle.Z) > 6)
                throw new ArgumentException("Player pose is outside the supported tracking volume.");
        }
        public void SetPlayerPose(Guid id, Vec3 head, Vec3 muzzle, Vec3 forward)
        {
            Active(); var player = FindPlayer(id); ValidatePose(player.Room, head, muzzle, forward);
            if (!rooms[player.Room].ClearSegment(Vec3.Flat(player.Head), Vec3.Flat(head))) throw new ArgumentException("Player movement crosses cover.");
            player.Head = head; player.Muzzle = muzzle; player.Forward = forward;
        }
        public ShotResult Fire(Guid playerId, Guid shotId)
        {
            if (shotId == Guid.Empty) throw new ArgumentException("Shot ID is required.");
            if (shots.TryGetValue(shotId, out var prior))
            {
                if (prior.PlayerId != playerId) throw new InvalidOperationException("Shot belongs to another player.");
                return prior;
            }
            Running(); var player = FindPlayer(playerId);
            if (player.Health <= 0 || player.Magazine <= 0 || player.ReloadUntil != 0 || TickNumber < player.NextShot)
                throw new InvalidOperationException("Weapon cannot fire now.");
            var hit = Cast(player.Muzzle, player.Forward, 40, player.Id, null);
            player.Magazine--; player.NextShot = TickNumber + 4;
            Emit(WorldEventKind.ShotFired, playerId, shotId);
            var eliminated = false;
            if (hit.Kind == HitKind.Enemy)
            {
                var enemy = enemies.Single(e => e.Id == hit.Id);
                enemy.Health = Math.Max(0, enemy.Health - 50);
                Emit(WorldEventKind.ShotHit, playerId, shotId, enemy.Id);
                eliminated = enemy.Health == 0;
                if (eliminated) Emit(WorldEventKind.EnemyEliminated, playerId, shotId, enemy.Id);
            }
            var result = new ShotResult(shotId, playerId, hit.Kind, hit.Id, hit.Distance, eliminated);
            shots.Add(shotId, result); return result;
        }
        public void Reload(Guid playerId, Guid commandId)
        {
            if (commandId == Guid.Empty) throw new ArgumentException("Reload command ID is required.");
            if (reloads.TryGetValue(commandId, out var owner))
            { if (owner != playerId) throw new InvalidOperationException("Reload belongs to another player."); return; }
            Running(); var player = FindPlayer(playerId);
            if (player.Health <= 0 || player.Magazine == MagazineSize || player.Reserve == 0 || player.ReloadUntil != 0)
                throw new InvalidOperationException("Weapon cannot reload now.");
            player.ReloadUntil = TickNumber + 30; reloads.Add(commandId, playerId);
            Emit(WorldEventKind.ReloadStarted, playerId);
        }
        public void Tick()
        {
            if (Phase != WorldPhase.Running) return;
            TickNumber++;
            foreach (var player in players)
            {
                if (player.ReloadUntil == 0 || player.ReloadUntil > TickNumber || player.Health <= 0) continue;
                var amount = Math.Min(MagazineSize - player.Magazine, player.Reserve);
                player.Magazine += amount; player.Reserve -= amount; player.ReloadUntil = 0;
                Emit(WorldEventKind.ReloadCompleted, player.Id);
            }
            var range = Math.Min(Visibility == Visibility.Fog ? 6 : Visibility == Visibility.Storm ? 10 : 15, Night ? 8 : 15);
            foreach (var enemy in enemies)
            {
                if (enemy.Health <= 0) continue;
                var target = players.Where(p => p.Health > 0 && p.Room == enemy.Room && Vec3.Distance(p.Head, enemy.Feet + new Vec3(0, 1.4f, 0)) <= range)
                    .OrderBy(p => Vec3.Distance(p.Head, enemy.Feet)).ThenBy(p => p.Id).FirstOrDefault();
                if (Behavior == AiBehavior.Patrol)
                {
                    var destination = enemy.Returning ? enemy.Start : enemy.Patrol;
                    if (Vec3.Distance(enemy.Feet, destination) < .15f) { enemy.Returning = !enemy.Returning; destination = enemy.Returning ? enemy.Start : enemy.Patrol; }
                    Move(enemy, destination);
                }
                else if (Behavior == AiBehavior.Advance && target != null && Vec3.Distance(enemy.Feet, Vec3.Flat(target.Head)) > 2)
                    Move(enemy, Vec3.Flat(target.Head));
                if (!AutoAttack || target == null || TickNumber < enemy.NextShot) continue;
                var muzzle = enemy.Feet + new Vec3(0, 1.4f, 0); var direction = target.Head - muzzle;
                if (direction.Length < .001f) continue;
                var hit = Cast(muzzle, direction.Normalized(), range, null, enemy.Id);
                if (hit.Kind != HitKind.Friendly || hit.Id != target.Id) continue;
                enemy.NextShot = TickNumber + 20;
                Emit(WorldEventKind.EnemyShot, target.Id, null, enemy.Id);
                var damage = Math.Min(20, target.Health); target.Health -= damage;
                Emit(WorldEventKind.PlayerDamaged, target.Id, null, enemy.Id, damage);
            }
        }
        private void Move(Enemy enemy, Vec3 destination)
        {
            if (enemy.Route.Count == 0 && TickNumber < enemy.NextPlan) return;
            if (enemy.Route.Count == 0 || (TickNumber >= enemy.NextPlan && Vec3.Distance(destination, enemy.RouteTarget) > .5f))
            {
                enemy.Route = rooms[enemy.Room].Find(enemy.Feet, destination); enemy.RouteTarget = destination; enemy.NextPlan = TickNumber + 4;
            }
            while (enemy.Route.Count > 0 && Vec3.Distance(enemy.Feet, enemy.Route[0]) < .02f) enemy.Route.RemoveAt(0);
            if (enemy.Route.Count == 0) return;
            var delta = enemy.Route[0] - enemy.Feet; var length = delta.Length;
            var next = enemy.Feet + delta * (Math.Min(.1f, length) / length);
            if (rooms[enemy.Room].ClearSegment(enemy.Feet, next)) enemy.Feet = next; else enemy.Route.Clear();
        }
        private Hit Cast(Vec3 origin, Vec3 direction, float range, Guid? ignorePlayer, Guid? ignoreEnemy)
        {
            var hit = new Hit { Kind = HitKind.Miss, Distance = range };
            foreach (var prop in props) Consider(HitKind.Cover, prop.Id, prop.Center, prop.HalfSize, prop.Yaw);
            foreach (var player in players.Where(p => p.Health > 0 && p.Id != ignorePlayer))
            {
                var height = player.Head.Y + .15f;
                Consider(HitKind.Friendly, player.Id, new Vec3(player.Head.X, height / 2, player.Head.Z), new Vec3(.25f, height / 2, .25f), 0);
            }
            foreach (var enemy in enemies.Where(e => e.Health > 0 && e.Id != ignoreEnemy))
                Consider(HitKind.Enemy, enemy.Id, enemy.Feet + new Vec3(0, .9f, 0), new Vec3(.3f, .9f, .3f), 0);
            return hit;
            void Consider(HitKind kind, Guid id, Vec3 center, Vec3 half, float yaw)
            {
                var distance = ArenaGeometry.RayBox(origin, direction, center, half, yaw, range);
                if (distance.HasValue && (hit.Kind == HitKind.Miss || distance.Value < hit.Distance - .0001f))
                { hit.Kind = kind; hit.Id = id; hit.Distance = distance.Value; }
            }
        }
        private void Emit(WorldEventKind kind, Guid player, Guid? shot = null, Guid? enemy = null, int damage = 0)
            => events.Add(new WorldEvent(events.Count + 1L, TickNumber, kind, player, shot, enemy, damage));
        public WorldEvent[] Events(long after = 0, int limit = 500)
        {
            if (after < 0 || limit < 1 || limit > 500) throw new ArgumentException("Invalid world event page.");
            var start = (int)Math.Min(after, events.Count); return events.GetRange(start, Math.Min(limit, events.Count - start)).ToArray();
        }
        public WorldFrame Snapshot() => new WorldFrame(TickNumber, Phase, events.Count,
            players.Select(p => new PlayerFrame(p.Id, p.Room, p.Head, p.Muzzle, p.Forward, p.Health, p.Magazine, p.Reserve, p.ReloadUntil != 0)).ToArray(),
            enemies.Select(e => new EnemyFrame(e.Id, e.Room, e.Feet, e.Health)).ToArray());
    }
}
