using NUnit.Framework;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class AvatarPoseTests
    {
        private static AvatarPose TrackedPose() => new AvatarPose
        {
            head = new Vector3(0, 1.65f, 0), left = new Vector3(-0.3f, 1.2f, 0.4f), right = new Vector3(0.3f, 1.2f, 0.4f),
            headRotation = Quaternion.identity, leftRotation = Quaternion.identity, rightRotation = Quaternion.identity
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
    }
}
