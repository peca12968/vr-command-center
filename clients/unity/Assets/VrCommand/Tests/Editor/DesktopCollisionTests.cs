using System;
using NUnit.Framework;
using Unity.Collections;
using Unity.Netcode;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class DesktopCollisionTests
    {
        [Test] public void RepeatedWallInputStaysAdmissibleAndCanRetreat()
        {
            var prop = new WorldProp(Guid.NewGuid(), 3, PropKind.Sandbag, new Vec3(-3.9f, 0, -2), 0);
            var surface = new ArenaWalkSurface(new Vec3(), new[] { prop });
            var world = new ArenaWorld(new[] { 3 }, new[] { prop }); var player = Guid.NewGuid();
            var position = new Vec3(-3, 1.65f, -3); world.AddPlayer(player, 3, position);
            for (var i = 0; i < 40; i++)
            {
                position = surface.Constrain(position, position + new Vec3(0, 0, .05f));
                Assert.DoesNotThrow(() => world.SetPlayerPose(player, position, position, new Vec3(0, 0, 1)));
            }
            Assert.That(position.Z, Is.InRange(-2.651f, -2.649f));
            var retreat = surface.Constrain(position, position + new Vec3(0, 0, -.25f));
            Assert.That(retreat.Z, Is.LessThan(-2.89f)); Assert.IsTrue(surface.ClearSegment(position, retreat));
        }
        [Test] public void RotatedBarrelBlocksTheSharedFootprintInsteadOfOnlyItsMesh()
        {
            var prop = new WorldProp(Guid.NewGuid(), 3, PropKind.Barrel, new Vec3(-2.5f, 0, -1.3f), 45);
            var surface = new ArenaWalkSurface(new Vec3(), new[] { prop }); var from = new Vec3(-2.5f, 1.65f, -2.85f);
            var stopped = surface.Constrain(from, new Vec3(-2.5f, 1.65f, 0));
            Assert.That(stopped.Z, Is.InRange(-2.225f, -2.219f)); Assert.IsTrue(surface.ClearSegment(from, stopped));
            Assert.IsFalse(surface.ClearSegment(from, new Vec3(-2.5f, 1.65f, 0)));
        }
        [Test] public void AxisSlideCannotCutTheAuthorityCornerOrIncreaseInputDisplacement()
        {
            var prop = new WorldProp(Guid.NewGuid(), 3, PropKind.Barrel, new Vec3(), 0);
            var surface = new ArenaWalkSurface(new Vec3(), new[] { prop });
            var from = new Vec3(-.7f, 1.65f, -.7f); var desired = new Vec3(-.5f, 1.65f, -.5f);
            var result = surface.Constrain(from, desired);
            Assert.IsFalse(surface.ClearSegment(from, desired)); Assert.IsTrue(surface.ClearSegment(from, result));
            Assert.That(Vec3.Distance(from, result), Is.LessThanOrEqualTo(Vec3.Distance(from, desired)));
            Assert.That(Vec3.Distance(result, desired), Is.LessThan(Vec3.Distance(from, desired)));
        }
        [Test] public void RoomOriginAndNonFiniteWishesDoNotFabricateMovement()
        {
            var origin = new Vec3(-28, 0, 0); var surface = new ArenaWalkSurface(origin, new WorldProp[0]);
            var from = origin + new Vec3(5.6f, 1.65f, 0);
            var result = surface.Constrain(from, from + new Vec3(.2f, 0, 0));
            Assert.That(result.X - origin.X, Is.InRange(5.699f, 5.701f));
            var invalid = surface.Constrain(from, new Vec3(float.NaN, 1.65f, 0));
            Assert.That(Vec3.Distance(from, invalid), Is.Zero); Assert.IsFalse(surface.ClearSegment(from, new Vec3(float.PositiveInfinity, 0, 0)));
        }
        [Test] public void NetcodePropPreservesRoomAlongsideCollisionGeometry()
        {
            var expected = new CombatPropState { id = Guid.NewGuid().ToString("D"), room = 5, center = new Vector3(28, .6f, 2), half = new Vector3(.35f, .6f, .35f), yaw = 45, barrel = true };
            using (var writer = new FastBufferWriter(512, Allocator.Temp))
            {
                writer.WriteValueSafe(expected);
                using (var reader = new FastBufferReader(writer.ToArray(), Allocator.Temp))
                { reader.ReadValueSafe(out CombatPropState actual); Assert.IsTrue(actual.Equals(expected)); Assert.AreEqual(5, actual.room); }
            }
        }
    }
}
