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
        [Test] public void PreflightDoesNotRewriteTheInterpretationOfHistoricalOverlappingWorlds()
        {
            var props = new[] { Prop("sandbag", 0, 2), Prop("barrel", 0, 2) };
            Assert.IsFalse(ArenaLayout.Inspect(props, 0, 1).Valid);
            var old = new ArenaSession(); old.Apply(Snapshot(props, 0)); Assert.AreEqual(2, old.Props.Length);
        }
    }
}
