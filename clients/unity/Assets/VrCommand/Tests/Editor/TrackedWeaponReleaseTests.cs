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
        [TestCase(false, true, false)]
        [TestCase(true, false, false)]
        [TestCase(true, true, true)]
        public void TrackedInputNeedsApplicationAndSessionFocusWithoutPause(bool application, bool session, bool paused)
        {
            Assert.IsFalse(TrackedInputFocus.Available(application, session, paused));
            Assert.IsTrue(TrackedInputFocus.Available(true, true, false));
        }

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

        [UnityTest] public IEnumerator OfficialTouchBindingsRequireReleaseAfterTrackingReadinessOrFocusLoss()
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
                // Pose, readiness and focus are fixtures. The controller uses actual Dynamic input events.
                var steps = new (int trackingState, bool ready, bool xrFocused, bool fire, bool reload, bool tap, bool allowed)[]
                {
                    (3, true, true, true, false, false, false), (3, true, true, false, false, false, false), (3, true, true, true, false, false, true),
                    (1, true, true, false, false, false, false), (3, true, true, true, false, false, false),
                    (3, true, true, false, true, false, false), (3, true, true, false, false, false, false), (3, true, true, false, true, false, true),
                    (3, false, true, false, false, false, false), (3, true, true, false, true, false, false),
                    (3, true, true, false, false, false, false), (3, true, true, true, false, false, true),
                    (3, true, false, true, false, false, false), (3, true, false, false, false, false, false),
                    (3, true, true, true, false, false, false), (3, true, true, false, true, false, false),
                    (3, true, true, false, false, false, false), (3, true, true, false, true, false, true),
                    // A tap on the first restored frame cannot arm the weapon.
                    (3, true, false, false, false, false, false), (3, true, true, false, false, true, false),
                    (3, true, true, false, false, false, false), (3, true, true, false, false, true, true),
                    (3, true, true, false, false, false, true)
                };
                foreach (var step in steps)
                {
                    var sampled = false;
                    TrackedWeaponInput input = default;
                    var tracked = false;
                    var allowed = false;
                    Action sample = () =>
                    {
                        if (sampled || InputState.currentUpdateType != InputUpdateType.Dynamic) return;
                        input = new TrackedWeaponInput(fire, reload);
                        tracked = NetworkAvatar.HasTracking(tracking, isTracked);
                        allowed = gate.Allows(step.ready && tracked && TrackedInputFocus.Available(true, step.xrFocused, false),
                            input.Held, input.Pressed);
                        sampled = true;
                    };
                    InputSystem.onAfterUpdate += sample;
                    try
                    {
                        using (StateEvent.From(device, out var state))
                        {
                            device.trackingState.WriteValueIntoEvent(step.trackingState, state);
                            device.isTracked.WriteValueIntoEvent(1f, state);
                            device.triggerPressed.WriteValueIntoEvent(step.fire || step.tap ? 1f : 0f, state);
                            device.primaryButton.WriteValueIntoEvent(step.reload ? 1f : 0f, state);
                            InputSystem.QueueEvent(state);
                            if (step.tap)
                            {
                                device.triggerPressed.WriteValueIntoEvent(0f, state);
                                InputSystem.QueueEvent(state);
                            }
                        }
                        for (var frame = 0; !sampled && frame < 120; frame++) yield return null;
                    }
                    finally { InputSystem.onAfterUpdate -= sample; }
                    Assert.IsTrue(sampled, "The official controller must deliver a Dynamic input sample");
                    Assert.AreEqual(step.fire, input.FireHeld);
                    Assert.AreEqual(step.reload, input.ReloadHeld);
                    if (step.tap) Assert.IsTrue(input.FirePressed, "The press and release must arrive in one Dynamic update");
                    Assert.AreEqual(step.trackingState == 3, tracked);
                    Assert.AreEqual(step.allowed, allowed);
                    Assert.AreEqual(step.allowed && (step.fire || step.tap), allowed && input.WantsFire,
                        "An eligible short trigger tap submits once even when the sampled button is already released");
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
