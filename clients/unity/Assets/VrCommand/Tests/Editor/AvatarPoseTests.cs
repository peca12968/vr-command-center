using NUnit.Framework;
using UnityEngine;
using Unity.Collections;
using Unity.Netcode;

namespace VrCommand.Unity.Tests
{
    public sealed class AvatarPoseTests
    {
        private static AvatarPose TrackedPose() => new AvatarPose
        {
            head = new Vector3(0, 1.65f, 0), left = new Vector3(-0.3f, 1.2f, 0.4f), right = new Vector3(0.3f, 1.2f, 0.4f),
            headRotation = Quaternion.identity, leftRotation = Quaternion.identity, rightRotation = Quaternion.identity, source = 2
        };
        [Test] public void NormalTrackedPoseIsAdmissible() => Assert.IsTrue(TrackedPose().Valid());
        [Test] public void NonFiniteHeadCannotEnterSharedState()
        {
            var pose = TrackedPose(); pose.head.x = float.NaN; Assert.IsFalse(pose.Valid());
        }
        [Test] public void OutOfRangePoseCannotEnterSharedState()
        {
            var pose = TrackedPose(); pose.right.z = 100; Assert.IsFalse(pose.Valid());
        }
        [Test] public void InvalidRotationCannotEnterSharedState()
        {
            var pose = TrackedPose(); pose.leftRotation = new Quaternion(0, 0, 0, 0); Assert.IsFalse(pose.Valid());
        }
        [Test] public void UnknownPoseSourceCannotMasqueradeAsTracking()
        { var pose = TrackedPose(); pose.source = 0; Assert.IsFalse(pose.Valid()); }
        [Test] public void DisconnectedHandsCannotEnterRecordedRig()
        { var pose = TrackedPose(); pose.left.x = 3; Assert.IsFalse(pose.Valid()); }
        [Test] public void NetcodePosePreservesSourceAndAllJointRotations()
        {
            var expected = TrackedPose(); expected.leftRotation = Quaternion.Euler(10, 20, 30);
            using (var writer = new FastBufferWriter(512, Allocator.Temp))
            {
                writer.WriteValueSafe(expected);
                using (var reader = new FastBufferReader(writer.ToArray(), Allocator.Temp))
                { reader.ReadValueSafe(out AvatarPose actual); Assert.IsTrue(actual.Equals(expected)); Assert.AreEqual(2, actual.source); }
            }
        }
    }
}
