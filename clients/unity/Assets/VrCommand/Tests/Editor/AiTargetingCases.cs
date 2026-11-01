using System;
using System.Linq;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    // Identical behavioral cases run in the real Unity Editor and .NET checks.
    public static class AiTargetingCases
    {
        public static readonly string[] Names = { "Generated three-player scene selects a visible farther player", "Crouched player behind cover does not hide a visible target", "Blocked attempts do not consume the firing cooldown", "Equal-distance visible players retain the GUID tie break", "Cooldown reacquires visibility instead of trusting the last aim ID", "Operator disable and Pause still suppress every shot", "Visibility range and same-room targeting remain enforced", "Advance movement keeps the original nearest-player policy", "Aim tracks the selected player without rewriting its saved shot ray" };
        private sealed class Scene
        {
            internal ArenaWorld World = new ArenaWorld(new[] { 3 }, Array.Empty<WorldProp>());
            internal Guid Close = Guid.NewGuid(), Middle = Guid.NewGuid(), Far = Guid.NewGuid(), Front = Guid.NewGuid(), Rear = Guid.NewGuid();
            internal Scene(bool attack = true)
            {
                World.AddPlayer(Close, 3, new Vec3(0, 1.65f, -2)); World.AddPlayer(Middle, 3, new Vec3(1, 1.65f, -2)); World.AddPlayer(Far, 3, new Vec3(3, 1.65f, -2));
                World.AddEnemy(Front, 3, new Vec3(0, 0, 1), new Vec3(0, 0, 1)); World.AddEnemy(Rear, 3, new Vec3(0, 0, 2), new Vec3(0, 0, 2));
                World.SetPolicy(AiBehavior.Hold, attack, Visibility.Clear, false); World.SetPhase(WorldPhase.Running);
            }
        }
        public static bool Run(int index)
        {
            if (index == 0) return Generated();
            if (index == 1)
            {
                var w = new ArenaWorld(new[] { 3 }, new[] { new WorldProp(Guid.NewGuid(), 3, PropKind.Barrel, new Vec3(0, 0, -1), 0) });
                var close = Guid.NewGuid(); var far = Guid.NewGuid(); w.AddPlayer(close, 3, new Vec3(0, .6f, -2)); w.AddPlayer(far, 3, new Vec3(3, 1.65f, -3)); w.AddEnemy(Guid.NewGuid(), 3, new Vec3(0, 0, 2), new Vec3(0, 0, 2));
                w.SetPolicy(AiBehavior.Hold, true, Visibility.Clear, false); w.SetPhase(WorldPhase.Running); w.Tick();
                return w.PlayerSnapshot(close).Health == 100 && w.PlayerSnapshot(far).Health == 80;
            }
            if (index == 2)
            {
                var s = new Scene(); s.World.SetPlayerConnected(s.Far, false); s.World.Tick();
                var blocked = !s.World.Events().Any(e => e.EnemyId == s.Rear); s.World.RemoveEnemy(s.Front); s.World.Tick();
                return blocked && s.World.Events().Any(e => e.Kind == WorldEventKind.EnemyShot && e.EnemyId == s.Rear && e.Tick == 2 && e.PlayerId == s.Close);
            }
            if (index == 3)
            {
                var w = new ArenaWorld(new[] { 3 }, Array.Empty<WorldProp>()); var low = Guid.Parse("10000000-0000-0000-0000-000000000001"); var high = Guid.Parse("10000000-0000-0000-0000-000000000002");
                w.AddPlayer(high, 3, new Vec3(-2, 1.65f, -3)); w.AddPlayer(low, 3, new Vec3(2, 1.65f, -3)); w.AddEnemy(Guid.NewGuid(), 3, new Vec3(), new Vec3());
                w.SetPolicy(AiBehavior.Hold, true, Visibility.Clear, false); w.SetPhase(WorldPhase.Running); w.Tick(); return w.Events().Single(e => e.Kind == WorldEventKind.EnemyShot).PlayerId == low;
            }
            if (index == 4)
            {
                var s = new Scene(); s.World.Tick(); s.World.SetPlayerConnected(s.Far, false); s.World.RemoveEnemy(s.Front);
                for (var i = 0; i < 19; i++) s.World.Tick();
                var before = s.World.Events().Count(e => e.Kind == WorldEventKind.EnemyShot && e.EnemyId == s.Rear); s.World.Tick();
                var shots = s.World.Events().Where(e => e.Kind == WorldEventKind.EnemyShot && e.EnemyId == s.Rear).ToArray();
                return before == 1 && shots.Length == 2 && shots[0].Tick == 1 && shots[0].PlayerId == s.Far && shots[1].Tick == 21 && shots[1].PlayerId == s.Close;
            }
            if (index == 5)
            {
                var s = new Scene(false); s.World.Tick(); s.World.SetPhase(WorldPhase.Paused); s.World.SetPolicy(AiBehavior.Hold, true, Visibility.Clear, false);
                for (var i = 0; i < 20; i++) s.World.Tick();
                var suppressed = s.World.TickNumber == 1 && s.World.Events().Length == 0; s.World.SetPhase(WorldPhase.Running); s.World.Tick();
                return suppressed && s.World.Events().Count(e => e.Kind == WorldEventKind.EnemyShot) == 2;
            }
            if (index == 6)
            {
                var w = new ArenaWorld(new[] { 1, 2, 3, 4, 5 }, Array.Empty<WorldProp>()); var own = Guid.NewGuid(); var other = Guid.NewGuid();
                w.AddPlayer(own, 3, new Vec3(-4, 1.65f, 0)); w.AddPlayer(other, 4, new Vec3(8.5f, 1.65f, 0)); w.AddEnemy(Guid.NewGuid(), 3, new Vec3(5, 0, 0), new Vec3(5, 0, 0));
                w.SetPolicy(AiBehavior.Hold, true, Visibility.Fog, false); w.SetPhase(WorldPhase.Running); w.Tick(); var fog = w.Events().Length == 0;
                w.SetPolicy(AiBehavior.Hold, true, Visibility.Clear, false); w.Tick();
                return fog && w.PlayerSnapshot(own).Health == 80 && w.PlayerSnapshot(other).Health == 100;
            }
            if (index == 7)
            {
                var a = new Scene(); var b = new Scene(false); a.World.SetPolicy(AiBehavior.Advance, true, Visibility.Clear, false); b.World.SetPolicy(AiBehavior.Advance, false, Visibility.Clear, false);
                for (var i = 0; i < 10; i++) { a.World.Tick(); b.World.Tick(); }
                var left = a.World.Snapshot().Enemies; var right = b.World.Snapshot().Enemies;
                return left.Zip(right, (x, y) => Vec3.Distance(x.Feet, y.Feet) < .000001f).All(value => value);
            }
            if (index == 8)
            {
                var s = new Scene(); s.World.Tick(); var before = s.World.Snapshot().Enemies.Single(e => e.Id == s.Rear); var shot = s.World.Events().Single(e => e.Kind == WorldEventKind.EnemyShot && e.EnemyId == s.Rear);
                var moved = new Vec3(3.1f, 1.65f, -2); s.World.SetPlayerPose(s.Far, moved, moved, new Vec3(0, 0, 1)); s.World.Tick(); var after = s.World.Snapshot().Enemies.Single(e => e.Id == s.Rear);
                return shot.Origin is Vec3 origin && shot.Direction is Vec3 direction && before.Fire.Sequence == shot.Sequence && before.Fire.TickPlusOne == 2 && before.Fire.Origin.Equals(origin) && before.Fire.Direction.Equals(direction)
                    && after.Fire.Sequence == before.Fire.Sequence && after.Fire.Direction.Equals(before.Fire.Direction) && Vec3.Distance(after.Forward, (moved - (after.Feet + new Vec3(0, 1.4f, 0))).Normalized()) < .000001f;
            }
            throw new ArgumentOutOfRangeException(nameof(index));
        }
        private static bool Generated()
        {
            var ids = new[] { Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid() }; var admissions = new[] { Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid() };
            var props = new[] { new ManagedProp { assetId = "sandbag", position = new ManagedPosition { x = -4.6f, z = -.6f }, yawDegrees = 90 }, new ManagedProp { assetId = "barrel", position = new ManagedPosition { x = -3.8f, z = -.6f } } }
                .Concat(new[] { -1.5f, .8f, 3.1f }.Select(x => new ManagedProp { assetId = "sandbag", position = new ManagedPosition { x = x, z = -.625f } }))
                .Concat(new[] { new ManagedProp { assetId = "barrel", position = new ManagedPosition { x = 4.9f, z = -.625f } } }).ToArray();
            var s = new ArenaSession(); s.Apply(new ManagementSnapshot { id = Guid.NewGuid().ToString(), state = "Preparing", sequence = 1, roomIds = new[] { 3 },
                mission = new ManagedMission { id = Guid.NewGuid().ToString(), definition = new ManagedDefinition { name = "Visible target", briefing = "Original producer", durationSeconds = 180, props = props } },
                environment = new ManagedEnvironment { mode = "VR", weather = "Clear", timeOfDay = "Day" }, enemies = new ManagedEnemies { count = 2, behavior = "Hold", autoAttack = true },
                players = ids.Select((id, seat) => new ManagedPlayer { id = id.ToString(), admissionId = admissions[seat].ToString(), roomId = 3, seat = seat }).ToArray() });
            for (var i = 0; i < ids.Length; i++) if (!s.Connect((ulong)i + 1, ids[i], 3, i, admissions[i]) || !s.Pose((ulong)i + 1, ArenaSession.Spawn(3, i), ArenaSession.Spawn(3, i), new Vec3(0, 0, 1), 0)) return false;
            var rear = s.World.Snapshot().Enemies.Single(e => Math.Abs(e.Feet.Z + .25f) < .0001f); s.World.SetPhase(WorldPhase.Running); s.World.Tick();
            return ArenaLayout.Inspect(props, 2, 1).Valid && s.World.Events().Any(e => e.Kind == WorldEventKind.EnemyShot && e.EnemyId == rear.Id && e.PlayerId == ids[2] && e.Tick == 1)
                && s.World.PlayerSnapshot(ids[0]).Health == 80 && s.World.PlayerSnapshot(ids[1]).Health == 100 && s.World.PlayerSnapshot(ids[2]).Health == 80;
        }
    }
}
