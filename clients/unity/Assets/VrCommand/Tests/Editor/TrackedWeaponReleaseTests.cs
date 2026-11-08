using System;
using System.Collections;
using NUnit.Framework;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.TestTools;
using UnityEngine.XR.OpenXR.Features.Interactions;

namespace VrCommand.Unity.Tests
{
    public sealed class TrackedWeaponReleaseTests
    {
        [Test] public void FreshReleaseDoesNotSubmitInputOnTheReleaseFrame()
        {
            var gate = new TrackedWeaponReleaseGate();
            Assert.IsFalse(gate.Allows(true, true, true));
            Assert.IsFalse(gate.Allows(true, false, true));
            Assert.IsFalse(gate.Armed);
            Assert.IsFalse(gate.Allows(true, false, false));
            Assert.IsTrue(gate.Armed);
            Assert.IsTrue(gate.Allows(true, true, true));
            Assert.IsTrue(gate.Allows(true, true, false), "A deliberate held trigger retains the normal repeat cadence");
        }

        [Test] public void IneligibleReleaseAndLifecycleResetCannotArmAWeapon()
        {
            var gate = new TrackedWeaponReleaseGate();
            gate.Allows(true, false, false);
            Assert.IsFalse(gate.Allows(false, false, false));
            Assert.IsFalse(gate.Allows(true, true, true));
            gate.Allows(true, false, false);
            Assert.IsTrue(gate.Allows(true, true, true));
            gate.Reset();
            Assert.IsFalse(gate.Allows(true, true, false));
        }

        [UnityTearDown] public IEnumerator LeavePlayMode()
        { if (Application.isPlaying) yield return new ExitPlayMode(); }

        [UnityTest] public IEnumerator OfficialTouchBindingsRequireReleaseAfterTrackingOrReadinessLoss()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            yield return new EnterPlayMode();

            const string layout = "VrCommandTrackedWeaponTestTouch";
            var background = InputSystem.settings.backgroundBehavior;
            InputSystem.settings.backgroundBehavior = InputSettings.BackgroundBehavior.IgnoreFocus;
            InputSystem.RegisterLayout<OculusTouchControllerProfile.OculusTouchController>(layout);
            var device = InputSystem.AddDevice(layout) as OculusTouchControllerProfile.OculusTouchController;
            try
            {
                Assert.IsNotNull(device);
                InputSystem.SetDeviceUsage(device, CommonUsages.RightHand);
                using var tracking = Bind("<XRController>{RightHand}/trackingState");
                using var isTracked = Bind("<XRController>{RightHand}/isTracked");
                using var fire = Bind(NetworkAvatar.TrackedFireBinding);
                using var reload = Bind(NetworkAvatar.TrackedReloadBinding);
                var gate = new TrackedWeaponReleaseGate();
                // Pose/mission readiness is supplied by the fixture. The controller values use actual Dynamic input events.
                var steps = new (int trackingState, bool ready, bool fire, bool reload, bool allowed)[]
                {
                    (3, true, true, false, false), (3, true, false, false, false), (3, true, true, false, true),
                    (1, true, false, false, false), (3, true, true, false, false),
                    (3, true, false, true, false), (3, true, false, false, false), (3, true, false, true, true),
                    (3, false, false, false, false), (3, true, false, true, false),
                    (3, true, false, false, false), (3, true, true, false, true)
                };
                foreach (var step in steps)
                {
                    var sampled = false;
                    var heldFire = false;
                    var heldReload = false;
                    var tracked = false;
                    var allowed = false;
                    Action sample = () =>
                    {
                        if (sampled || InputState.currentUpdateType != InputUpdateType.Dynamic) return;
                        heldFire = fire.ReadValue<float>() > .5f;
                        heldReload = reload.ReadValue<float>() > .5f;
                        tracked = NetworkAvatar.HasTracking(tracking, isTracked);
                        allowed = gate.Allows(step.ready && tracked, heldFire || heldReload,
                            fire.WasPressedThisFrame() || reload.WasPressedThisFrame());
                        sampled = true;
                    };
                    InputSystem.onAfterUpdate += sample;
                    try
                    {
                        using (StateEvent.From(device, out var state))
                        {
                            device.trackingState.WriteValueIntoEvent(step.trackingState, state);
                            device.isTracked.WriteValueIntoEvent(1f, state);
                            device.triggerPressed.WriteValueIntoEvent(step.fire ? 1f : 0f, state);
                            device.primaryButton.WriteValueIntoEvent(step.reload ? 1f : 0f, state);
                            InputSystem.QueueEvent(state);
                        }
                        for (var frame = 0; !sampled && frame < 120; frame++) yield return null;
                    }
                    finally { InputSystem.onAfterUpdate -= sample; }
                    Assert.IsTrue(sampled, "The official controller must deliver a Dynamic input sample");
                    Assert.AreEqual(step.fire, heldFire);
                    Assert.AreEqual(step.reload, heldReload);
                    Assert.AreEqual(step.trackingState == 3, tracked);
                    Assert.AreEqual(step.allowed, allowed);
                }
            }
            finally
            {
                if (device != null) InputSystem.RemoveDevice(device);
                InputSystem.RemoveLayout(layout);
                InputSystem.settings.backgroundBehavior = background;
            }
        }

        private static InputAction Bind(string path)
        {
            var action = new InputAction(type: InputActionType.Value, binding: path);
            action.Enable();
            return action;
        }
    }
}
