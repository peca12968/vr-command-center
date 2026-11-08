using System;
using System.Linq;
using NUnit.Framework;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class ArenaLayoutTests
    {
        private static ManagedProp Prop(string kind, float x, float z, float yaw = 0) => new ManagedProp
        { assetId = kind, position = new ManagedPosition { x = x, z = z }, yawDegrees = yaw };
        private static ManagementSnapshot Snapshot(ManagedProp[] props, int enemies) => new ManagementSnapshot
        {
            id = "11111111-1111-1111-1111-111111111111", state = "Preparing", sequence = 1, roomIds = new[] { 3 }, players = new ManagedPlayer[0],
            mission = new ManagedMission { id = "22222222-2222-2222-2222-222222222222", definition = new ManagedDefinition { name = "Layout", props = props } },
            environment = new ManagedEnvironment { mode = "VR", weather = "Clear", timeOfDay = "Day" },
            enemies = new ManagedEnemies { count = enemies, behavior = "Hold" }
        };
        [Test] public void RotationUsesActualBoxCornersAndSeparatingAxes()
        {
            Assert.IsTrue(ArenaLayout.Inspect(new[] { Prop("sandbag", 5.2f, 1, 45) }, 0, 1).Issues.Any(i => i.Code == "OutsideRoom"));
            Assert.IsTrue(ArenaLayout.Inspect(new[] { Prop("sandbag", 0, 2, 45), Prop("sandbag", .5656854f, 2.5656854f, 45) }, 0, 1).Valid);
            Assert.IsTrue(ArenaLayout.Inspect(new[] { Prop("sandbag", 0, 2), Prop("sandbag", 2, 2) }, 0, 1).Valid);
        }
        [Test] public void SpawnInspectionMatchesTheRealAdmissionSeatAndMovementClearance()
        {
            var prop = Prop("barrel", -3, -2.4f); var report = ArenaLayout.Inspect(new[] { prop }, 0, 1);
            Assert.IsTrue(report.Issues.Any(i => i.Code == "SpawnBlocked" && i.Seat == 0));
            var surface = new ArenaWalkSurface(new Vec3(), new[] { new WorldProp(Guid.NewGuid(), 3, PropKind.Barrel, prop.position.Vector, 0) });
            Assert.IsFalse(surface.Walkable(ArenaSession.Spawn(3, 0)));
        }
        [Test] public void EnemyCapacityMatchesActualInitialPlanningWithoutChangingItsOrder()
        {
            var props = (from z in new[] { 2f, 4f } from x in new[] { -3f, -1f, 1f, 3f } select Prop("sandbag", x, z)).ToArray();
            Assert.AreEqual(84, ArenaLayout.Inspect(props, 84, 1).EnemyCapacityPerRoom);
            var source = new ArenaSession(); source.Apply(Snapshot(props, 84));
            Assert.AreEqual(84, source.World.Snapshot().Enemies.Length);
            Assert.AreEqual(-4.5f, source.World.Snapshot().Enemies[0].Feet.X); Assert.AreEqual(-1, source.World.Snapshot().Enemies[0].Feet.Z);
            Assert.Throws<ArgumentException>(() => new ArenaSession().Apply(Snapshot(props, 85)));
            Assert.IsFalse(ArenaLayout.Inspect(props, 85, 1).Valid);
            Assert.IsTrue(ArenaLayout.Inspect(props, 100, 5).Valid);
        }
        [Test] public void DiagnosticsAreBoundedAndInvalidMetadataCannotPass()
        {
            var report = ArenaLayout.Inspect(Enumerable.Repeat(Prop("barrel", 0, 2), 500).ToArray(), 0, 1);
            Assert.AreEqual(128, report.Issues.Length); Assert.AreEqual(124750, report.IssueCount); Assert.AreEqual(500, report.InvalidProps.Length); Assert.IsTrue(report.Truncated);
            Assert.IsFalse(ArenaLayout.Inspect(new[] { Prop("unsupported", 0, 0) }, 0, 1).Valid);
            Assert.IsFalse(ArenaLayout.Inspect(new[] { Prop("barrel", 0, 0, 720) }, 0, 1).Valid);
        }
        [Test] public void LiveReinforcementsWaitForClearSpawnWithoutStallingOtherCommands()
        {
            var props = (from z in Enumerable.Range(0, 9)
                         from x in Enumerable.Range(0, 13)
                         where z != 0 || x < 6 || x > 8
                         select Prop("barrel", -4.5f + x * .75f, -1 + z * .75f)).ToArray();
            Assert.AreEqual(3, ArenaLayout.Inspect(props, 3, 1).EnemyCapacityPerRoom);
            var source = new ArenaSession();
            var snapshot = Snapshot(props, 2);
            snapshot.enemies.behavior = "Patrol";
            source.Apply(snapshot);
            snapshot.state = "Running"; snapshot.sequence++;
            source.Apply(snapshot);
            source.Tick(.05);
            var before = source.World.Snapshot().Enemies;
            Assert.That(before.All(enemy => enemy.Walking), "Both original enemies must cover the remaining spawn point.");
            snapshot.enemies.count = 3; snapshot.enemies.behavior = "Hold"; snapshot.sequence++;
            source.Apply(snapshot);
            Assert.AreEqual(2, source.World.Snapshot().Enemies.Length);
            snapshot.state = "Paused"; snapshot.environment.weather = "Storm"; snapshot.sequence++;
            source.Apply(snapshot);
            source.Tick(.10);
            Assert.AreEqual(WorldPhase.Paused, source.World.Phase);
            Assert.AreEqual(Visibility.Storm, source.World.Visibility);
            Assert.AreEqual(1, source.World.TickNumber);
            snapshot.state = "Running"; snapshot.enemies.behavior = "Patrol"; snapshot.sequence++;
            source.Apply(snapshot);
            for (var tick = 2; tick <= 121 && source.World.Snapshot().Enemies.Length < 3; tick++)
                source.Tick(tick * .05);
            var reinforced = source.World.Snapshot().Enemies;
            Assert.AreEqual(3, reinforced.Length);
            Assert.That(before.Select(enemy => enemy.Id), Is.SubsetOf(reinforced.Select(enemy => enemy.Id)));
            Assert.That(reinforced.Take(2).All(enemy => Vec3.Distance(enemy.Feet, reinforced[2].Feet) > .7f));
            snapshot.state = "Ended"; snapshot.enemies.count = 1; snapshot.sequence += 2;
            source.Apply(snapshot);
            Assert.AreEqual(WorldPhase.Ended, source.World.Phase);
            Assert.AreEqual(before[0].Id, source.World.Snapshot().Enemies.Single().Id);
        }
        [Test] public void PreflightDoesNotRewriteTheInterpretationOfHistoricalOverlappingWorlds()
        {
            var props = new[] { Prop("sandbag", 0, 2), Prop("barrel", 0, 2) };
            Assert.IsFalse(ArenaLayout.Inspect(props, 0, 1).Valid);
            var old = new ArenaSession(); old.Apply(Snapshot(props, 0)); Assert.AreEqual(2, old.Props.Length);
        }
    }
}
