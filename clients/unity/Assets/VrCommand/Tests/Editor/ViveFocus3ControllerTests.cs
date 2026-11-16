using NUnit.Framework;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.Controls;

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
