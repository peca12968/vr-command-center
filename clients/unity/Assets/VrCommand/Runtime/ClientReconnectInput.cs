using System;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.XR.OpenXR;

namespace VrCommand.Unity
{
    internal static class TrackedInputFocus
    {
        internal static bool Available(bool paused) => Available(Application.isFocused, OpenXRUtility.IsSessionFocused, paused);
        internal static bool Available(bool applicationFocused, bool sessionFocused, bool paused)
            => applicationFocused && sessionFocused && !paused;
    }

    // A fresh release while eligible is required before each explicit press.
    internal sealed class ReleasePressGate
    {
        private bool armed;
        public void Reset() { armed = false; }
        public bool Poll(bool eligible, bool focused, bool controllerTracked, bool held)
        {
            if (!eligible || !focused || !controllerTracked) { armed = false; return false; }
            if (!held) { armed = true; return false; }
            if (!armed) return false;
            armed = false; return true;
        }
    }

    public sealed class ClientReconnectInput : IDisposable
    {
        public const string Binding = "<XRController>{RightHand}/secondaryButton";
        private readonly InputAction button, tracking, isTracked;
        private readonly ReleasePressGate gate = new ReleasePressGate();
        public ClientReconnectInput()
        {
            button = new InputAction("Reconnect player", InputActionType.Value, Binding);
            tracking = new InputAction("Reconnect controller tracking", InputActionType.Value, "<XRController>{RightHand}/trackingState");
            isTracked = new InputAction("Reconnect controller valid", InputActionType.Value, "<XRController>{RightHand}/isTracked");
            button.Enable(); tracking.Enable(); isTracked.Enable();
        }
        public static bool CanOffer(string role, bool listening, bool shuttingDown, float now, float next)
            => role == "Client" && !listening && !shuttingDown && float.IsFinite(now) && float.IsFinite(next) && now >= next;
        public bool Poll(bool eligible, bool focused)
            => gate.Poll(eligible, focused, isTracked.ReadValue<float>() > .5f && (tracking.ReadValue<int>() & 3) == 3, button.ReadValue<float>() > .5f);
        public void Reset() => gate.Reset();
        public void Dispose() { button.Dispose(); tracking.Dispose(); isTracked.Dispose(); }
    }
}
