using System;
using NUnit.Framework;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class DesktopResumeTests
    {
        private static AvatarPose Pose(byte source = 1) => new AvatarPose { source = source, head = new Vector3(0, 1.65f, .8f),
            left = new Vector3(-.3f, 1.3f, 1.2f), right = new Vector3(.3f, 1.3f, 1.2f), headRotation = Quaternion.identity,
            leftRotation = Quaternion.identity, rightRotation = Quaternion.identity };

        [Test] public void ReentryEvenAtSameSeatCannotRestorePreviousAdmissionPose()
        {
            var cache = new DesktopResumeCache(); var player = Guid.NewGuid(); var old = Guid.NewGuid(); var current = Guid.NewGuid();
            cache.Remember(player, old, Pose());
            Assert.IsTrue(cache.TryRestore(player, old, out var saved)); Assert.That(saved.head.z, Is.EqualTo(.8f));
            cache.Retain(new[] { new ManagedPlayer { id = player.ToString("D"), admissionId = current.ToString("D"), roomId = 5, seat = 0 } });
            Assert.IsFalse(cache.TryRestore(player, old, out _)); Assert.IsFalse(cache.TryRestore(player, current, out _));
        }
        [Test] public void TrackedPoseClearsDesktopResumeInsteadOfFabricatingTracking()
        {
            var cache = new DesktopResumeCache(); var player = Guid.NewGuid(); var admission = Guid.NewGuid();
            cache.Remember(player, admission, Pose()); cache.Remember(player, admission, Pose(2));
            Assert.IsFalse(cache.TryRestore(player, admission, out _));
        }
        [Test] public void InvalidPoseAndEmptyAdmissionCannotBecomeResumeState()
        {
            var cache = new DesktopResumeCache(); var player = Guid.NewGuid(); var admission = Guid.NewGuid(); var bad = Pose();
            bad.head.x = float.NaN;
            Assert.Throws<ArgumentException>(() => cache.Remember(player, admission, bad));
            Assert.Throws<ArgumentException>(() => cache.Remember(player, Guid.Empty, Pose()));
            Assert.IsFalse(cache.TryRestore(player, admission, out _));
        }
    }
}
