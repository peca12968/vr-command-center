using System.IO;
using NUnit.Framework;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class RoomFloorCalibrationTests
    {
        private const string Export = @"{
            ""version"":1, ""profile"":""room-floor-alignment-v1"", ""withinTolerance"":true,
            ""roomId"":5, ""roomOrigin"":{""x"":28,""z"":0},
            ""markers"":[
                {""name"":""A"",""room"":{""x"":-2,""z"":-2},""tracking"":{""x"":-1,""z"":-3}},
                {""name"":""B"",""room"":{""x"":2,""z"":-2},""tracking"":{""x"":-1,""z"":1}},
                {""name"":""C"",""room"":{""x"":-2,""z"":2},""tracking"":{""x"":-5,""z"":-3}}
            ]}";
        private static readonly Vector3 Spawn = new Vector3(28, 0, -3);
        private static readonly Vector3 A = new Vector3(-5, 0, 4);
        private static readonly Vector3 B = new Vector3(-5, 0, 0);
        private static readonly Vector3 C = new Vector3(-1, 0, 4);
        private GameObject root;
        private Transform trackingSpace;
        private RoomFloorCalibration calibration;

        [SetUp]
        public void Setup()
        {
            root = new GameObject("Test avatar");
            root.transform.SetPositionAndRotation(Spawn, Quaternion.Euler(0, 35, 0));
            trackingSpace = Joint(root.transform, Vector3.zero);
            calibration = new RoomFloorCalibration(RoomFloorPlan.Parse(Export), Spawn, trackingSpace);
        }

        [TearDown]
        public void Cleanup() => Object.DestroyImmediate(root);

        [Test]
        public void FreshCaptureMapsHeadAndBothHandsInOneTrackingSpace()
        {
            var head = Joint(trackingSpace, new Vector3(-4, 1.65f, 2));
            var left = Joint(trackingSpace, new Vector3(-3, 1.3f, 3));
            var right = Joint(trackingSpace, new Vector3(-4, 1.4f, 1));
            Capture(A); Capture(B);
            Assert.That(calibration.Ready, Is.False);
            Capture(C);
            Assert.That(calibration.Ready, Is.True);
            Assert.That(calibration.Update(false, true, true, false, Vector3.zero), Is.True);
            AssertPosition(head.position, new Vector3(28, 1.65f, -1));
            AssertPosition(left.position, new Vector3(27, 1.3f, 0));
            AssertPosition(right.position, new Vector3(29, 1.4f, -1));
            AssertPosition(right.forward, Vector3.left);
            AssertPosition(root.transform.TransformPoint(root.transform.InverseTransformPoint(right.position)), right.position);
        }

        [Test]
        public void AReportFromAnotherRoomCannotCaptureOrReleaseInput()
        {
            calibration = new RoomFloorCalibration(RoomFloorPlan.Parse(Export), Spawn - new Vector3(14, 0, 0), trackingSpace);
            Capture(A); Capture(B); Capture(C);
            Assert.That(calibration.Ready, Is.False);
            Assert.That(calibration.Hint, Does.Contain("ANOTHER ROOM"));
        }

        [Test]
        public void CaptureRequiresFloorTrackingAndPreparingOrPaused()
        {
            Capture(A);
            Assert.That(calibration.Update(true, true, false, true, B), Is.False);
            Assert.That(calibration.Hint, Does.Contain("BOTH CONTROLLERS"));
            Capture(A);
            Assert.That(calibration.Update(false, true, true, true, B), Is.False);
            Assert.That(calibration.Hint, Does.Contain("PAUSE MISSION"));
            Assert.That(calibration.Update(true, false, true, true, A), Is.False);
            Assert.That(calibration.Hint, Does.Contain("FLOOR TRACKING"));
            Capture(A);
            Assert.That(calibration.Hint, Does.Contain("OVER A"));
            Capture(B); Capture(C);
            Assert.That(calibration.Ready, Is.True);
        }

        [TestCase(0.049f, true)]
        [TestCase(0.051f, false)]
        [TestCase(-8f, false)]
        public void IndependentThirdMarkerEnforcesToleranceAndRejectsReflection(float offset, bool valid)
        {
            Capture(A); Capture(B); Capture(C + new Vector3(offset, 0, 0));
            Assert.That(calibration.Ready, Is.EqualTo(valid));
            if (valid) return;
            Assert.That(calibration.Update(true, true, true, false, Vector3.zero), Is.False);
            Assert.That(calibration.Hint, Does.Contain("MARKERS DID NOT MATCH"));
            Capture(A); Capture(B); Capture(C);
            Assert.That(calibration.Ready, Is.True);
        }

        [Test]
        public void ChangedOriginAndLostFloorRequireFreshMeasurements()
        {
            Capture(A); Capture(B); Capture(C);
            calibration.Invalidate();
            Assert.That(calibration.Update(false, true, true, false, Vector3.zero), Is.False);
            Capture(A); Capture(B); Capture(C);
            Assert.That(calibration.Update(false, true, false, false, Vector3.zero), Is.False);
            Assert.That(calibration.Update(false, false, true, false, Vector3.zero), Is.False);
            Assert.That(calibration.Update(false, true, true, false, Vector3.zero), Is.False);
            Assert.That(calibration.Ready, Is.False);
        }

        [TestCase(@"""x"":28", @"""x"":14")]
        [TestCase(@"""withinTolerance"":true", @"""withinTolerance"":false")]
        [TestCase(@"""name"":""C""", @"""name"":""B""")]
        [TestCase(@"""x"":-5,""z"":-3", @"""z"":-3")]
        [TestCase(@"""x"":-5,""z"":-3", @"""x"":3,""z"":-3")]
        public void InvalidExportCannotActivate(string original, string replacement)
        {
            Assert.Throws<InvalidDataException>(() => RoomFloorPlan.Parse(Export.Replace(original, replacement)));
        }

        private void Capture(Vector3 point) =>
            Assert.That(calibration.Update(true, true, true, true, point), Is.False);

        private static Transform Joint(Transform parent, Vector3 localPosition)
        {
            var joint = new GameObject("Joint").transform;
            joint.SetParent(parent, false);
            joint.localPosition = localPosition;
            return joint;
        }

        private static void AssertPosition(Vector3 actual, Vector3 expected) =>
            Assert.That(Vector3.Distance(actual, expected), Is.LessThan(.0001f));
    }
}
