using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.Controls;

namespace VrCommand.Unity
{
    // Local desktop input only. No tracked joint or network state is written here.
    public sealed class DesktopStanceInput
    {
        public const float StandingHeight = 1.65f, CrouchedHeight = 1f;
        private int windowControls;
        private bool windowToggleHeld, windowTogglePressed, toggled;
        public bool Crouched { get; private set; }
        public float EyeHeight => Crouched ? CrouchedHeight : StandingHeight;
        private static bool Pressed(ButtonControl key) => key != null && (key.isPressed || key.wasPressedThisFrame);
        public bool Poll(Keyboard keyboard, bool active)
        {
            if (!active) { Reset(); return false; }
            if (keyboard?.cKey.wasPressedThisFrame == true || windowTogglePressed) toggled = !toggled;
            windowTogglePressed = false;
            return Crouched = toggled || windowControls != 0 || Pressed(keyboard?.leftCtrlKey) || Pressed(keyboard?.rightCtrlKey);
        }
        public bool WindowKey(KeyCode key, bool down, Keyboard keyboard)
        {
            if (key == KeyCode.LeftControl || key == KeyCode.RightControl)
            {
                var bit = key == KeyCode.LeftControl ? 1 : 2;
                var raw = key == KeyCode.LeftControl ? keyboard?.leftCtrlKey : keyboard?.rightCtrlKey;
                if (!down) windowControls &= ~bit;
                else if (!Pressed(raw)) windowControls |= bit;
                return true;
            }
            if (key != KeyCode.C) return false;
            if (!down) windowToggleHeld = false;
            else if (!Pressed(keyboard?.cKey))
            {
                if (!windowToggleHeld) windowTogglePressed = true;
                windowToggleHeld = true;
            }
            return true;
        }
        public void Reset()
        {
            windowControls = 0; windowToggleHeld = windowTogglePressed = toggled = Crouched = false;
        }
    }
}
