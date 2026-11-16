using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.Layouts;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.InputSystem.XR;
using InputDeviceCharacteristics = UnityEngine.XR.InputDeviceCharacteristics;
using ViveController = VrCommand.Unity.ViveFocus3ControllerProfile.ViveFocus3Controller;

namespace VrCommand.Unity.Tests
{
    public sealed class ViveFocus3ControllerTests
    {
        [TestCase(false, "1.0.34", false)]
        [TestCase(false, "", false)]
        [TestCase(true, "1.0.34", true)]
        [TestCase(false, "1.1.0", true)]
        public void UsesTheExtensionOrOpenXr11(bool extension, string version, bool supported)
            => Assert.AreEqual(supported, ViveFocus3ControllerProfile.SupportsProfile(extension, version));

        [Test]
        public void ExposesGameplayButtonsAndTheTwoDistinctPosesThroughExistingPaths()
        {
            const string layout = nameof(ViveFocus3ControllerProfile.ViveFocus3Controller);
            InputSystem.RegisterLayout<ViveFocus3ControllerProfile.ViveFocus3Controller>(layout);
            ViveFocus3ControllerProfile.ViveFocus3Controller right = null;
            ViveFocus3ControllerProfile.ViveFocus3Controller left = null;
            try
            {
                right = (ViveFocus3ControllerProfile.ViveFocus3Controller)InputSystem.AddDevice(layout);
                left = (ViveFocus3ControllerProfile.ViveFocus3Controller)InputSystem.AddDevice(layout);
                InputSystem.SetDeviceUsage(right, CommonUsages.RightHand);
                InputSystem.SetDeviceUsage(left, CommonUsages.LeftHand);

                Assert.IsNotNull(right.devicePose);
                Assert.IsNotNull(right.pointer);
                AssertAlias(right.isTracked, right.devicePose.isTracked);
                AssertAlias(right.trackingState, right.devicePose.trackingState);
                AssertAlias(left.devicePosition, left.devicePose.position);
                AssertAlias(left.deviceRotation, left.devicePose.rotation);
                AssertAlias(right.pointerPosition, right.pointer.position);
                AssertAlias(right.pointerRotation, right.pointer.rotation);
                Assert.AreNotEqual(right.devicePosition.stateBlock.byteOffset, right.pointerPosition.stateBlock.byteOffset);

                AssertBinding(NetworkAvatar.TrackedFireBinding, right.triggerPressed);
                AssertBinding(NetworkAvatar.TrackedReloadBinding, right.primaryButton);
                AssertBinding(ClientReconnectInput.Binding, right.secondaryButton);
                AssertBinding("<XRController>{LeftHand}/primaryButton", left.primaryButton);
                AssertBinding("<XRController>{LeftHand}/secondaryButton", left.secondaryButton);
                AssertBinding("<XRController>{LeftHand}/gripPressed", left.gripPressed);
            }
            finally
            {
                if (right != null) InputSystem.RemoveDevice(right);
                if (left != null) InputSystem.RemoveDevice(left);
                InputSystem.RemoveLayout(layout);
            }
        }

        [Test]
        public void NativeDescriptorsKeepBothHandsAndReadIndependentState()
        {
            const string layout = nameof(ViveFocus3ControllerProfile.ViveFocus3Controller);
            InputSystem.RegisterLayout<ViveController>(layout, matches: new InputDeviceMatcher()
                .WithInterface(XRUtilities.InterfaceMatchAnyVersion).WithProduct(ViveFocus3ControllerProfile.Product));
            var leftId = 0;
            var rightId = 0;
            try
            {
                leftId = AddDescribedController(InputDeviceCharacteristics.Left).deviceId;
                rightId = AddDescribedController(InputDeviceCharacteristics.Right).deviceId;
                // A second descriptor can recreate an existing device when Unity updates their shared generated layout.
                var left = InputSystem.GetDeviceById(leftId) as ViveController;
                var right = InputSystem.GetDeviceById(rightId) as ViveController;
                Assert.IsNotNull(left);
                Assert.IsNotNull(right);
                Assert.AreEqual("XRS0", left.stateBlock.format.ToString());
                Assert.AreEqual("XRS0", right.stateBlock.format.ToString());
                Assert.That(left.usages, Does.Contain(CommonUsages.LeftHand));
                Assert.That(right.usages, Does.Contain(CommonUsages.RightHand));

                var grip = new Vector3(.11f, .35f, .42f);
                var aim = new Vector3(.61f, .73f, .84f);
                var rotation = Quaternion.Euler(5, 30, 10);
                using (StateEvent.From(left, out var state))
                {
                    WriteGrip(left, grip, state);
                    left.primaryButton.WriteValueIntoEvent(1f, state);
                    InputState.Change(left, state, InputUpdateType.Editor);
                }
                using (StateEvent.From(right, out var state))
                {
                    WriteGrip(right, grip, state);
                    right.pointer.position.WriteValueIntoEvent(aim, state);
                    right.pointer.rotation.WriteValueIntoEvent(rotation, state);
                    right.triggerPressed.WriteValueIntoEvent(1f, state);
                    right.secondaryButton.WriteValueIntoEvent(1f, state);
                    InputState.Change(right, state, InputUpdateType.Editor);
                }

                Assert.IsTrue(left.isTracked.isPressed && right.isTracked.isPressed);
                Assert.AreEqual(3, left.trackingState.ReadValue());
                Assert.AreEqual(3, right.trackingState.ReadValue());
                Assert.AreEqual(grip, left.devicePosition.ReadValue());
                Assert.AreEqual(Quaternion.identity, left.deviceRotation.ReadValue());
                Assert.AreEqual(grip, right.devicePosition.ReadValue());
                Assert.AreEqual(aim, right.pointerPosition.ReadValue());
                Assert.AreEqual(rotation, right.pointerRotation.ReadValue());
                Assert.IsTrue(left.primaryButton.isPressed && !right.primaryButton.isPressed);
                Assert.IsTrue(right.triggerPressed.isPressed && !left.triggerPressed.isPressed);
                Assert.IsTrue(right.secondaryButton.isPressed && !left.secondaryButton.isPressed);
                using (StateEvent.From(right, out var state))
                {
                    right.devicePose.isTracked.WriteValueIntoEvent(0f, state);
                    right.devicePose.trackingState.WriteValueIntoEvent(0, state);
                    InputState.Change(right, state, InputUpdateType.Editor);
                }
                Assert.IsFalse(right.isTracked.isPressed);
                Assert.AreEqual(0, right.trackingState.ReadValue());
                Assert.IsTrue(left.isTracked.isPressed);
            }
            finally
            {
                if (InputSystem.GetDeviceById(leftId) is InputDevice left) InputSystem.RemoveDevice(left);
                if (InputSystem.GetDeviceById(rightId) is InputDevice right) InputSystem.RemoveDevice(right);
                InputSystem.RemoveLayout(layout);
            }
        }

        private static InputDevice AddDescribedController(InputDeviceCharacteristics hand)
        {
            const string product = ViveFocus3ControllerProfile.Product;
            var descriptor = new XRDeviceDescriptor
            {
                deviceName = product,
                manufacturer = "HTC",
                characteristics = hand | InputDeviceCharacteristics.Controller |
                    InputDeviceCharacteristics.HeldInHand | InputDeviceCharacteristics.TrackedDevice,
                inputFeatures = PoseFeatures("devicePose").Concat(PoseFeatures("pointer"))
                    .Concat(new[] { "triggerPressed", "gripPressed", "primaryButton", "secondaryButton" }
                        .Select(name => new XRFeatureDescriptor { name = name, featureType = FeatureType.Binary })).ToList()
            };
            return InputSystem.AddDevice(new InputDeviceDescription
            {
                interfaceName = XRUtilities.InterfaceCurrent,
                product = product,
                manufacturer = descriptor.manufacturer,
                capabilities = descriptor.ToJson()
            });
        }

        private static IEnumerable<XRFeatureDescriptor> PoseFeatures(string name)
        {
            yield return new XRFeatureDescriptor { name = name + "/isTracked", featureType = FeatureType.Binary };
            yield return new XRFeatureDescriptor { name = name + "/trackingState", featureType = FeatureType.DiscreteStates };
            yield return new XRFeatureDescriptor { name = name + "/position", featureType = FeatureType.Axis3D };
            yield return new XRFeatureDescriptor { name = name + "/rotation", featureType = FeatureType.Rotation };
            yield return new XRFeatureDescriptor { name = name + "/velocity", featureType = FeatureType.Axis3D };
            yield return new XRFeatureDescriptor { name = name + "/angularVelocity", featureType = FeatureType.Axis3D };
        }

        private static void WriteGrip(ViveController controller, Vector3 position, InputEventPtr state)
        {
            controller.devicePose.isTracked.WriteValueIntoEvent(1f, state);
            controller.devicePose.trackingState.WriteValueIntoEvent(3, state);
            controller.devicePose.position.WriteValueIntoEvent(position, state);
            controller.devicePose.rotation.WriteValueIntoEvent(Quaternion.identity, state);
        }

        private static void AssertAlias(InputControl alias, InputControl source)
        {
            Assert.AreEqual(source.stateBlock.byteOffset, alias.stateBlock.byteOffset);
            Assert.AreEqual(source.stateBlock.bitOffset, alias.stateBlock.bitOffset);
            Assert.AreEqual(source.stateBlock.sizeInBits, alias.stateBlock.sizeInBits);
        }

        private static void AssertBinding(string path, InputControl expected)
        {
            using var action = new InputAction(binding: path);
            action.Enable();
            Assert.That(action.controls, Does.Contain(expected));
        }
    }
}
