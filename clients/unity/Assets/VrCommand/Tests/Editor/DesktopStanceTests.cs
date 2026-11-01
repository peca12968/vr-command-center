using System;
using System.Collections;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.TestTools;
using UnityEditor.SceneManagement;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class DesktopStanceTests
    {
        [Test] public void WindowControlIsHeldRatherThanToggled()
        {
            var s = new DesktopStanceInput(); s.WindowKey(KeyCode.LeftControl, true, null); Assert.IsTrue(s.Poll(null, true)); Assert.AreEqual(1f, s.EyeHeight);
            s.WindowKey(KeyCode.LeftControl, false, null); Assert.IsFalse(s.Poll(null, true)); Assert.AreEqual(1.65f, s.EyeHeight);
        }
        [Test] public void TwoControlKeysReleaseIndependently()
        {
            var s = new DesktopStanceInput(); s.WindowKey(KeyCode.LeftControl, true, null); s.WindowKey(KeyCode.RightControl, true, null); s.Poll(null, true);
            s.WindowKey(KeyCode.LeftControl, false, null); Assert.IsTrue(s.Poll(null, true)); s.WindowKey(KeyCode.RightControl, false, null); Assert.IsFalse(s.Poll(null, true));
        }
        [Test] public void WindowToggleIgnoresKeyRepeatUntilRelease()
        {
            var s = new DesktopStanceInput(); s.WindowKey(KeyCode.C, true, null); Assert.IsTrue(s.Poll(null, true));
            s.WindowKey(KeyCode.C, true, null); Assert.IsTrue(s.Poll(null, true)); s.WindowKey(KeyCode.C, false, null); Assert.IsTrue(s.Poll(null, true));
            s.WindowKey(KeyCode.C, true, null); Assert.IsFalse(s.Poll(null, true));
        }
        [Test] public void UnfocusedInputDropsToggleAndWindowHolds()
        {
            var s = new DesktopStanceInput(); s.WindowKey(KeyCode.C, true, null); s.WindowKey(KeyCode.RightControl, true, null); Assert.IsTrue(s.Poll(null, true));
            Assert.IsFalse(s.Poll(null, false)); Assert.IsFalse(s.Poll(null, true));
        }
        [Test] public void ResetClearsPendingInputWithoutAnUpdate()
        {
            var s = new DesktopStanceInput(); s.WindowKey(KeyCode.C, true, null); s.Reset(); Assert.IsFalse(s.Crouched); Assert.IsFalse(s.Poll(null, true));
            s.WindowKey(KeyCode.C, true, null); Assert.IsTrue(s.Poll(null, true)); s.Reset(); Assert.AreEqual(1.65f, s.EyeHeight);
        }
        [Test] public void AControlHoldTakesPrecedenceOverAnOffToggle()
        {
            var s = new DesktopStanceInput(); s.WindowKey(KeyCode.C, true, null); s.Poll(null, true); s.WindowKey(KeyCode.C, false, null);
            s.WindowKey(KeyCode.LeftControl, true, null); s.WindowKey(KeyCode.C, true, null); Assert.IsTrue(s.Poll(null, true));
            s.WindowKey(KeyCode.LeftControl, false, null); Assert.IsFalse(s.Poll(null, true));
        }
        [Test] public void StanceDoesNotConsumeMovementOrWeaponKeys()
        {
            var s = new DesktopStanceInput(); foreach (var key in new[] { KeyCode.W, KeyCode.R, KeyCode.Space, KeyCode.B }) Assert.IsFalse(s.WindowKey(key, true, null));
            Assert.IsFalse(s.Poll(null, true));
        }
        [TestCase("OnApplicationFocus"), TestCase("OnApplicationPause"), TestCase("OnDisable")]
        public void LifecycleHooksResetInputEvenWithoutAnotherUpdate(string method)
        {
            var go = new GameObject("Stance lifecycle test");
            try
            {
                var avatar = go.AddComponent<NetworkAvatar>(); var input = (DesktopStanceInput)typeof(NetworkAvatar).GetField("desktopStance", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(avatar);
                input.WindowKey(KeyCode.C, true, null); Assert.IsTrue(input.Poll(null, true));
                // Exercise callback logic directly in EditMode; SendMessage's
                // engine dispatcher rejects a non-running behaviour here.
                typeof(NetworkAvatar).GetMethod(method, BindingFlags.Instance | BindingFlags.NonPublic).Invoke(avatar, method == "OnDisable" ? null : new object[] { method == "OnApplicationPause" });
                Assert.IsFalse(input.Crouched); Assert.IsFalse(input.Poll(null, true));
            }
            finally { UnityEngine.Object.DestroyImmediate(go); }
        }
        [Test] public void CrouchedWalkingKeepsHeightAndOriginalHorizontalSpeed()
        {
            var crouched = new Vector3(0, 1f, 0); var standing = new Vector3(0, 1.65f, 0); var view = Quaternion.Euler(65, 90, 0);
            var a = DesktopPreviewControls.Move(crouched, view, Vector2.one, .1f, Vector3.zero); var b = DesktopPreviewControls.Move(standing, view, Vector2.one, .1f, Vector3.zero);
            Assert.AreEqual(1f, a.y); Assert.AreEqual(1.65f, b.y); Assert.That(a.x, Is.EqualTo(b.x).Within(.000001f)); Assert.That(a.z, Is.EqualTo(b.z).Within(.000001f));
            Assert.That(Vector2.Distance(new Vector2(a.x, a.z), Vector2.zero), Is.LessThanOrEqualTo(.200001f));
        }
        [Test] public void CrouchedBoundaryClampsRemainRelativeToEveryOriginalSeat()
        {
            for (var seat = 0; seat < 5; seat++)
            {
                var root = new Vector3((seat - 2) * 1.5f, 0, -3);
                var result = DesktopPreviewControls.Move(new Vector3(100, 1, -100), Quaternion.identity, Vector2.one, 3, root) + root;
                Assert.AreEqual(5, result.x); Assert.AreEqual(-5, result.z); Assert.AreEqual(1, result.y);
            }
        }
        [Test] public void ExtremeCrouchedAimKeepsTheMuzzleInsideOriginalAuthorityLimits()
        {
            var w = new ArenaWorld(new[] { 3 }, Array.Empty<WorldProp>()); var id = Guid.NewGuid(); w.AddPlayer(id, 3, new Vec3(0, 1.65f, -3));
            foreach (var pitch in new[] { -70f, 0, 70f }) foreach (var yaw in new[] { -180f, -90f, 0, 90f, 180f })
            {
                var q = Quaternion.Euler(pitch, yaw, 0); var head = new Vector3(0, 1, -3); var muzzle = head + q * (DesktopPreviewControls.RightOffset + Vector3.forward * AvatarPose.MuzzleOffset); var forward = q * Vector3.forward;
                Assert.DoesNotThrow(() => w.SetPlayerPose(id, new Vec3(head.x, head.y, head.z), new Vec3(muzzle.x, muzzle.y, muzzle.z), new Vec3(forward.x, forward.y, forward.z)));
            }
        }
    }
    public sealed class DesktopStanceBindingTests
    {
        [UnityTearDown] public IEnumerator LeavePlayMode() { if (Application.isPlaying) yield return new ExitPlayMode(); }
        private readonly struct Step
        {
            internal readonly Key[] Keys; internal readonly bool Expected;
            internal Step(bool expected, params Key[] keys) { Expected = expected; Keys = keys; }
        }
        private static IEnumerator Device(bool duplicateWindowEvent, params Step[] steps)
        {
            var background = InputSystem.settings.backgroundBehavior; InputSystem.settings.backgroundBehavior = InputSettings.BackgroundBehavior.IgnoreFocus;
            var editorRouting = InputSystem.settings.editorInputBehaviorInPlayMode;
            InputSystem.settings.editorInputBehaviorInPlayMode = InputSettings.EditorInputBehaviorInPlayMode.AllDeviceInputAlwaysGoesToGameView;
            Keyboard keyboard = null; var input = new DesktopStanceInput();
            try
            {
                keyboard = InputSystem.AddDevice<Keyboard>();
                var index = 0;
                foreach (var step in steps)
                {
                    var observed = false; var actual = false; var raw = "not sampled"; Exception error = null;
                    Action sample = () =>
                    {
                        if (observed || InputState.currentUpdateType != InputUpdateType.Dynamic) return;
                        try { raw = "enabled=" + keyboard.enabled + " left=" + keyboard.leftCtrlKey.ReadValue() + " right=" + keyboard.rightCtrlKey.ReadValue() + " c=" + keyboard.cKey.ReadValue() + " pressed=" + keyboard.cKey.wasPressedThisFrame; actual = input.Poll(keyboard, true); if (duplicateWindowEvent) input.WindowKey(KeyCode.C, keyboard.cKey.isPressed, keyboard); }
                        catch (Exception value) { error = value; }
                        observed = true;
                    };
                    InputSystem.onAfterUpdate += sample;
                    try { InputSystem.QueueStateEvent(keyboard, new KeyboardState(step.Keys)); for (var frame = 0; !observed && frame < 120; frame++) yield return null; }
                    finally { InputSystem.onAfterUpdate -= sample; }
                    TestContext.WriteLine("Keyboard step " + index + " playing=" + Application.isPlaying + " observed=" + observed + " " + raw + " expected=" + step.Expected + " actual=" + actual);
                    Assert.IsTrue(Application.isPlaying, "Keyboard test must remain in PlayMode"); Assert.IsTrue(observed, "A real Dynamic player input update must consume the official keyboard event"); Assert.IsNull(error); Assert.AreEqual(step.Expected, actual, "Keyboard step " + index + " " + raw); index++;
                }
            }
            finally { if (keyboard != null) InputSystem.RemoveDevice(keyboard); InputSystem.settings.editorInputBehaviorInPlayMode = editorRouting; InputSystem.settings.backgroundBehavior = background; }
        }
        [UnityTest] public IEnumerator OfficialKeyboardControlHoldAndRelease()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single); yield return new EnterPlayMode();
            yield return Device(false, new Step(false), new Step(true, Key.LeftCtrl), new Step(true, Key.LeftCtrl), new Step(false), new Step(true, Key.RightCtrl), new Step(false));
        }
        [UnityTest] public IEnumerator OfficialKeyboardCTogglesOnlyOnNewPresses()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single); yield return new EnterPlayMode();
            yield return Device(false, new Step(false), new Step(true, Key.C), new Step(true, Key.C), new Step(true), new Step(false, Key.C), new Step(false));
        }
        [UnityTest] public IEnumerator OfficialKeyboardAndWindowEventNeverDoubleToggle()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single); yield return new EnterPlayMode();
            yield return Device(true, new Step(false), new Step(true, Key.C), new Step(true, Key.C), new Step(true), new Step(false, Key.C), new Step(false));
        }
    }
}
