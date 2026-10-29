using NUnit.Framework;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class DesktopPreviewTests
    {
        [Test] public void AimCanTurnAndPitchWithoutRollingOrFlipping()
        {
            var up = DesktopPreviewControls.Look(Quaternion.Euler(0, 350, 0), new Vector2(30, -100));
            Assert.That(Mathf.DeltaAngle(0, up.eulerAngles.x), Is.EqualTo(-70).Within(.001));
            Assert.That(Mathf.DeltaAngle(0, up.eulerAngles.y), Is.EqualTo(20).Within(.001));
            var down = DesktopPreviewControls.Look(up, new Vector2(-60, 200));
            Assert.That(Mathf.DeltaAngle(0, down.eulerAngles.x), Is.EqualTo(70).Within(.001));
            Assert.That(Mathf.DeltaAngle(0, down.eulerAngles.z), Is.EqualTo(0).Within(.001));
        }

        [Test] public void WalkingIsLevelRelativeToAimAndDiagonalSpeedDoesNotIncrease()
        {
            var start = new Vector3(0, 1.65f, 0);
            var view = Quaternion.Euler(-60, 90, 0);
            var forward = DesktopPreviewControls.Move(start, view, Vector2.up, .1f, Vector3.zero);
            var diagonal = DesktopPreviewControls.Move(start, view, Vector2.one, .1f, Vector3.zero);
            Assert.That(forward.x, Is.EqualTo(.2f).Within(.001));
            Assert.That(forward.y, Is.EqualTo(1.65f));
            Assert.That((forward - start).magnitude, Is.EqualTo((diagonal - start).magnitude).Within(.001));
        }

        [Test] public void LongFramesDoNotTeleportDesktopBody()
        {
            var start = new Vector3(0, 1.65f, 0);
            var moved = DesktopPreviewControls.Move(start, Quaternion.identity, Vector2.up, 3, Vector3.zero);
            Assert.That(Vector3.Distance(start, moved), Is.LessThanOrEqualTo(.201f));
        }

        [Test] public void EverySpawnSeatClampsAgainstRoomRatherThanAvatarRoot()
        {
            for (var seat = 0; seat < 5; seat++)
            {
                var root = new Vector3((seat - 2) * 1.5f, 0, -3);
                var right = DesktopPreviewControls.Move(new Vector3(100, 1.65f, 100), Quaternion.identity, Vector2.zero, 0, root) + root;
                var left = DesktopPreviewControls.Move(new Vector3(-100, 1.65f, -100), Quaternion.identity, Vector2.zero, 0, root) + root;
                Assert.That(right.x, Is.EqualTo(5)); Assert.That(right.z, Is.EqualTo(5));
                Assert.That(left.x, Is.EqualTo(-5)); Assert.That(left.z, Is.EqualTo(-5));
            }
        }
    }
}
