using System;
using System.Collections;
using NUnit.Framework;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.XR.OpenXR.Features.Interactions;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEditor.SceneManagement;

namespace VrCommand.Unity.Tests
{
    public sealed class ClientReconnectInputTests
    {
        [Test] public void OnlyStoppedPlayerClientsCanOfferReconnectAfterCooldown()
        {
            Assert.IsTrue(ClientReconnectInput.CanOffer("Client", false, false, 2, 2));
            foreach (var role in new[] { "Server", "Host", "", null }) Assert.IsFalse(ClientReconnectInput.CanOffer(role, false, false, 2, 2));
            Assert.IsFalse(ClientReconnectInput.CanOffer("Client", true, false, 2, 2));
            Assert.IsFalse(ClientReconnectInput.CanOffer("Client", false, true, 2, 2));
            Assert.IsFalse(ClientReconnectInput.CanOffer("Client", false, false, 1.99f, 2));
            Assert.IsFalse(ClientReconnectInput.CanOffer("Client", false, false, float.NaN, 2));
        }
        [Test] public void HeldButtonOnFirstEligibleFrameDoesNotReconnect()
        { var gate = new ReconnectPressGate(); Assert.IsFalse(gate.Poll(true, true, true, true)); Assert.IsFalse(gate.Poll(true, true, true, true)); }
        [Test] public void EachAttemptRequiresAReleaseThenOneNewPress()
        {
            var gate = new ReconnectPressGate(); Assert.IsFalse(gate.Poll(true, true, true, false)); Assert.IsTrue(gate.Poll(true, true, true, true));
            Assert.IsFalse(gate.Poll(true, true, true, true)); Assert.IsFalse(gate.Poll(true, true, true, false)); Assert.IsTrue(gate.Poll(true, true, true, true));
        }
        [Test] public void DisconnectOrCooldownCannotCarryAnArmedPressAcrossEligibility()
        {
            var gate = new ReconnectPressGate(); gate.Poll(true, true, true, false); Assert.IsFalse(gate.Poll(false, true, true, true));
            Assert.IsFalse(gate.Poll(true, true, true, true)); gate.Poll(true, true, true, false); Assert.IsTrue(gate.Poll(true, true, true, true));
        }
        [Test] public void FocusLossRequiresAnotherReleaseInTheForeground()
        {
            var gate = new ReconnectPressGate(); gate.Poll(true, true, true, false); Assert.IsFalse(gate.Poll(true, false, true, false));
            Assert.IsFalse(gate.Poll(true, true, true, true)); gate.Poll(true, true, true, false); Assert.IsTrue(gate.Poll(true, true, true, true));
        }
        [Test] public void TrackingLossDoesNotArmAButtonFromMissingInput()
        {
            var gate = new ReconnectPressGate(); gate.Poll(true, true, true, false); Assert.IsFalse(gate.Poll(true, true, false, false));
            Assert.IsFalse(gate.Poll(true, true, true, true)); gate.Poll(true, true, true, false); Assert.IsTrue(gate.Poll(true, true, true, true));
        }
        [Test] public void NoDeviceCannotRequestReconnectOrThrow()
        { using (var input = new ClientReconnectInput()) Assert.IsFalse(input.Poll(true, true)); }
        [Test] public void LifecycleResetDisarmsEvenIfNoUpdateRunsDuringSuspension()
        {
            var gate = new ReconnectPressGate(); gate.Poll(true, true, true, false);
            gate.Reset(); Assert.IsFalse(gate.Poll(true, true, true, true));
            gate.Poll(true, true, true, false); Assert.IsTrue(gate.Poll(true, true, true, true));
        }
    }

    public sealed class ClientReconnectBindingTests
    {
        [UnityTearDown] public IEnumerator LeavePlayMode()
        { if (Application.isPlaying) yield return new ExitPlayMode(); }

        private static void EmptyScene() => EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        private readonly struct Step
        {
            internal readonly int tracking; internal readonly bool tracked, held, expected;
            internal Step(int tracking, bool tracked, bool held, bool expected)
            { this.tracking = tracking; this.tracked = tracked; this.held = held; this.expected = expected; }
        }
        private static IEnumerator Device(bool right, params Step[] steps)
        {
            const string layout = "VrCommandReconnectTestTouch";
            var background = InputSystem.settings.backgroundBehavior;
            InputSystem.settings.backgroundBehavior = InputSettings.BackgroundBehavior.IgnoreFocus;
            InputSystem.RegisterLayout<OculusTouchControllerProfile.OculusTouchController>(layout);
            var device = InputSystem.AddDevice(layout) as OculusTouchControllerProfile.OculusTouchController;
            try
            {
                InputSystem.SetDeviceUsage(device, right ? CommonUsages.RightHand : CommonUsages.LeftHand);
                using (var input = new ClientReconnectInput())
                foreach (var step in steps)
                {
                    var observed = false; var actualTracking = -1; var actualTracked = -1f; var actualHeld = -1f; var actualAllowed = false;
                    Exception error = null;
                    Action sample = () =>
                    {
                        if (observed || InputState.currentUpdateType != InputUpdateType.Dynamic) return;
                        try
                        {
                            actualTracking = device.trackingState.ReadValue(); actualTracked = device.isTracked.ReadValue(); actualHeld = device.secondaryButton.ReadValue();
                            actualAllowed = input.Poll(true, true);
                        }
                        catch (Exception value) { error = value; }
                        observed = true;
                    };
                    InputSystem.onAfterUpdate += sample;
                    try
                    {
                        State(device, step.tracking, step.tracked, step.held);
                        for (var frame = 0; !observed && frame < 120; frame++) yield return null;
                    }
                    finally { InputSystem.onAfterUpdate -= sample; }
                    Assert.IsNull(error); Assert.IsTrue(observed, "A real Dynamic player input update must consume the event");
                    Assert.AreEqual(step.tracking, actualTracking, "Queued tracking state must reach the official device");
                    Assert.AreEqual(step.tracked ? 1f : 0f, actualTracked, "Queued tracked bit must reach the official device");
                    Assert.AreEqual(step.held ? 1f : 0f, actualHeld, "Queued B/Y bit must reach the official device");
                    Assert.AreEqual(step.expected, actualAllowed);
                }
            }
            finally { if (device != null) InputSystem.RemoveDevice(device); InputSystem.RemoveLayout(layout); InputSystem.settings.backgroundBehavior = background; }
        }
        private static void State(OculusTouchControllerProfile.OculusTouchController device, int tracking, bool tracked, bool held)
        {
            Assert.IsTrue(Application.isPlaying, "Controller binding events run in a real Editor player loop");
            Assert.IsTrue(device.enabled, "The isolated test controller must accept state events");
            using (StateEvent.From(device, out var state))
            {
                device.trackingState.WriteValueIntoEvent(tracking, state);
                device.isTracked.WriteValueIntoEvent(tracked ? 1f : 0f, state);
                device.secondaryButton.WriteValueIntoEvent(held ? 1f : 0f, state);
                InputSystem.QueueEvent(state);
            }
        }

        [UnityTest] public IEnumerator OfficialTouchLayoutRightBResolvesThroughRealInputActions()
        {
            EmptyScene(); yield return new EnterPlayMode();
            yield return Device(true, new Step(3, true, true, false), new Step(3, true, false, false), new Step(3, true, true, true), new Step(3, true, true, false));
        }
        [UnityTest] public IEnumerator OfficialTouchLayoutLeftYIsNotTheRightBReconnectBinding()
        { EmptyScene(); yield return new EnterPlayMode(); yield return Device(false, new Step(3, true, false, false), new Step(3, true, true, false)); }
        [UnityTest] public IEnumerator OfficialTouchLayoutRequiresBothTrackedFlagAndCompleteTrackingState()
        {
            EmptyScene(); yield return new EnterPlayMode();
            yield return Device(true, new Step(3, false, false, false), new Step(3, true, true, false), new Step(1, true, false, false),
                new Step(3, true, true, false), new Step(3, true, false, false), new Step(3, true, true, true));
        }
    }
}
