using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.ExceptionServices;
using NUnit.Framework;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.Controls;
using UnityEngine.InputSystem.Layouts;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.InputSystem.XR;
using UnityEngine.TestTools;
using UnityEngine.XR.OpenXR.Features.Interactions;
using HapticControl = UnityEngine.XR.OpenXR.Input.HapticControl;
using OpenXRPoseControl = UnityEngine.XR.OpenXR.Input.PoseControl;
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
        public void QuestTouchAndViveWandExposeAimTrackingThroughTheirPoseControls()
        {
            var addedHapticLayout = InputSystem.LoadLayout("Haptic") == null;
            if (addedHapticLayout) InputSystem.RegisterLayout<HapticControl>("Haptic");
            try
            {
                AssertStockAimBinding<OculusTouchControllerProfile.OculusTouchController>("VrCommandQuestAimTest");
                AssertStockAimBinding<HTCViveControllerProfile.ViveController>("VrCommandViveAimTest");
            }
            finally
            {
                if (addedHapticLayout) InputSystem.RemoveLayout("Haptic");
            }
        }

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
                AssertAlias(right.isTracked, right.devicePose["isTracked"]);
                AssertAlias(right.trackingState, right.devicePose["trackingState"]);
                AssertAlias(left.devicePosition, left.devicePose["position"]);
                AssertAlias(left.deviceRotation, left.devicePose["rotation"]);
                AssertAlias(right.pointerPosition, right.pointer["position"]);
                AssertAlias(right.pointerRotation, right.pointer["rotation"]);
                Assert.AreNotEqual(right.devicePosition.stateBlock.byteOffset, right.pointerPosition.stateBlock.byteOffset);

                AssertBinding(NetworkAvatar.TrackedFireBinding, right.triggerPressed);
                AssertBinding(NetworkAvatar.TrackedReloadBinding, right.primaryButton);
                AssertBinding(ClientReconnectInput.Binding, right.secondaryButton);
                AssertBinding(NetworkAvatar.RightAimTrackingBinding, right.pointer["trackingState"]);
                AssertBinding(NetworkAvatar.RightAimTrackedBinding, right.pointer["isTracked"]);
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

        [UnityTearDown]
        public IEnumerator LeavePlayMode()
        {
            if (Application.isPlaying) yield return new ExitPlayMode();
        }

        [UnityTest]
        public IEnumerator NativeDescriptorsWithInputSystemPose() => VerifyNativeDescriptors(typeof(PoseControl));

        [UnityTest]
        public IEnumerator NativeDescriptorsWithOpenXRPose() => VerifyNativeDescriptors(typeof(OpenXRPoseControl));

        private static IEnumerator VerifyNativeDescriptors(Type poseType)
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            yield return new EnterPlayMode();

            const string layout = nameof(ViveFocus3ControllerProfile.ViveFocus3Controller);
            var originalPose = InputSystem.LoadLayout("Pose")?.type;
            var background = InputSystem.settings.backgroundBehavior;
            var routing = InputSystem.settings.editorInputBehaviorInPlayMode;
            var leftId = 0;
            var rightId = 0;
            try
            {
                InputSystem.settings.backgroundBehavior = InputSettings.BackgroundBehavior.IgnoreFocus;
                InputSystem.settings.editorInputBehaviorInPlayMode = InputSettings.EditorInputBehaviorInPlayMode.AllDeviceInputAlwaysGoesToGameView;
                if (poseType != originalPose) InputSystem.RegisterLayout(poseType, "Pose");
                InputSystem.RegisterLayout<ViveController>(layout, matches: new InputDeviceMatcher()
                    .WithInterface(XRUtilities.InterfaceMatchAnyVersion).WithProduct(ViveFocus3ControllerProfile.Product));
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
                using var gripTracking = new InputAction(binding: "<XRController>{RightHand}/trackingState");
                using var gripTracked = new InputAction(binding: "<XRController>{RightHand}/isTracked");
                using var aimTracking = new InputAction(binding: NetworkAvatar.RightAimTrackingBinding);
                using var aimTracked = new InputAction(binding: NetworkAvatar.RightAimTrackedBinding);
                gripTracking.Enable();
                gripTracked.Enable();
                aimTracking.Enable();
                aimTracked.Enable();
                yield return CheckDynamicState(left, state =>
                {
                    WriteGrip(left, grip, state);
                    left.primaryButton.WriteValueIntoEvent(1f, state);
                }, () => Assert.IsTrue(left.isTracked.isPressed));
                yield return CheckDynamicState(right, state =>
                {
                    WriteGrip(right, grip, state);
                    WritePose(right.pointer, aim, rotation, false, 0, state);
                    right.triggerPressed.WriteValueIntoEvent(1f, state);
                    right.secondaryButton.WriteValueIntoEvent(1f, state);
                }, () =>
                {
                    Assert.IsTrue(left.isTracked.isPressed && right.isTracked.isPressed);
                    Assert.AreEqual(3, left.trackingState.ReadValue());
                    Assert.AreEqual(3, right.trackingState.ReadValue());
                    Assert.AreEqual(grip, left.devicePosition.ReadValue());
                    Assert.AreEqual(Quaternion.identity, left.deviceRotation.ReadValue());
                    Assert.AreEqual(grip, right.devicePosition.ReadValue());
                    Assert.AreEqual(aim, right.pointerPosition.ReadValue(), "Initial invalid aim retains the supplied coordinates.");
                    Assert.AreEqual(rotation, right.pointerRotation.ReadValue());
                    Assert.IsTrue(left.primaryButton.isPressed && !right.primaryButton.isPressed);
                    Assert.IsTrue(right.triggerPressed.isPressed && !left.triggerPressed.isPressed);
                    Assert.IsTrue(right.secondaryButton.isPressed && !left.secondaryButton.isPressed);
                    Assert.IsTrue(NetworkAvatar.HasTracking(gripTracking, gripTracked));
                    Assert.IsFalse(NetworkAvatar.HasTracking(aimTracking, aimTracked));
                });
                yield return CheckDynamicState(right, state =>
                {
                    WriteGrip(right, grip, state);
                    WritePose(right.pointer, aim, rotation, true, 3, state);
                }, () => Assert.IsTrue(NetworkAvatar.HasTracking(aimTracking, aimTracked)));
                yield return CheckDynamicState(right, state =>
                {
                    WriteGrip(right, grip, state);
                    WritePose(right.pointer, aim, rotation, true, 1, state);
                }, () =>
                {
                    Assert.IsFalse(NetworkAvatar.HasTracking(aimTracking, aimTracked));
                    Assert.AreEqual(aim, right.pointerPosition.ReadValue(), "Partial aim tracking retains the supplied coordinates.");
                    Assert.IsTrue(right.isTracked.isPressed && left.isTracked.isPressed);
                });
                yield return CheckDynamicState(right, state =>
                {
                    WritePose(right.devicePose, grip, Quaternion.identity, false, 0, state);
                    WritePose(right.pointer, aim, rotation, false, 0, state);
                }, () =>
                {
                    Assert.IsFalse(right.isTracked.isPressed);
                    Assert.AreEqual(0, right.trackingState.ReadValue());
                    Assert.IsTrue(left.isTracked.isPressed);
                });
            }
            finally
            {
                if (InputSystem.GetDeviceById(leftId) is InputDevice left) InputSystem.RemoveDevice(left);
                if (InputSystem.GetDeviceById(rightId) is InputDevice right) InputSystem.RemoveDevice(right);
                InputSystem.RemoveLayout(layout);
                RestorePoseLayout(poseType, originalPose);
                InputSystem.settings.backgroundBehavior = background;
                InputSystem.settings.editorInputBehaviorInPlayMode = routing;
            }
        }

        private static IEnumerator CheckDynamicState(ViveController device, Action<InputEventPtr> write, Action check)
        {
            Assert.IsTrue(device.enabled);
            var sampled = false;
            Exception failure = null;
            void Sample()
            {
                if (sampled || InputState.currentUpdateType != InputUpdateType.Dynamic) return;
                sampled = true;
                try { check(); }
                catch (Exception error) { failure = error; }
            }
            InputSystem.onAfterUpdate += Sample;
            try
            {
                using (StateEvent.From(device, out var state))
                {
                    write(state);
                    InputSystem.QueueEvent(state);
                }
                for (var frame = 0; !sampled && frame < 120; frame++) yield return null;
            }
            finally { InputSystem.onAfterUpdate -= Sample; }
            Assert.IsTrue(sampled, "A Dynamic player update must consume the controller state.");
            if (failure != null) ExceptionDispatchInfo.Capture(failure).Throw();
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
            WritePose(controller.devicePose, position, Quaternion.identity, true, 3, state);
        }

        private static void WritePose(InputControl pose, Vector3 position, Quaternion rotation, bool tracked, int flags, InputEventPtr state)
        {
            pose.GetChildControl<ButtonControl>("isTracked").WriteValueIntoEvent(tracked ? 1f : 0f, state);
            pose.GetChildControl<IntegerControl>("trackingState").WriteValueIntoEvent(flags, state);
            pose.GetChildControl<Vector3Control>("position").WriteValueIntoEvent(position, state);
            pose.GetChildControl<QuaternionControl>("rotation").WriteValueIntoEvent(rotation, state);
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

        private static void AssertStockAimBinding<T>(string layout) where T : XRController
        {
            // The pinned OpenXR plugin selects the Pose type when compiling its controller layouts.
            var poseType = typeof(T).GetProperty("pointer").PropertyType;
            WithPoseLayout(poseType, () => VerifyStockAimBinding<T>(layout));
        }

        private static void VerifyStockAimBinding<T>(string layout) where T : XRController
        {
            InputSystem.RegisterLayout<T>(layout);
            InputDevice device = null;
            try
            {
                device = InputSystem.AddDevice(layout);
                InputSystem.SetDeviceUsage(device, CommonUsages.RightHand);
                var aim = device["pointer"];
                AssertBinding(NetworkAvatar.RightAimTrackingBinding, aim["trackingState"]);
                AssertBinding(NetworkAvatar.RightAimTrackedBinding, aim["isTracked"]);
            }
            finally
            {
                if (device != null) InputSystem.RemoveDevice(device);
                InputSystem.RemoveLayout(layout);
            }
        }

        private static void WithPoseLayout(Type type, Action run)
        {
            var original = InputSystem.LoadLayout("Pose")?.type;
            if (type != original) InputSystem.RegisterLayout(type, "Pose");
            try { run(); }
            finally { RestorePoseLayout(type, original); }
        }

        private static void RestorePoseLayout(Type current, Type original)
        {
            if (current == original) return;
            if (original == null) InputSystem.RemoveLayout("Pose");
            else InputSystem.RegisterLayout(original, "Pose");
        }
    }
}
