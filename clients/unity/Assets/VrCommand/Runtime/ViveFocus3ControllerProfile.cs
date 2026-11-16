using System;
using System.Collections.Generic;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.Controls;
using UnityEngine.InputSystem.Layouts;
using UnityEngine.InputSystem.XR;
using UnityEngine.Scripting;
using UnityEngine.XR;
using UnityEngine.XR.OpenXR;
using UnityEngine.XR.OpenXR.Features;

namespace VrCommand.Unity
{
#if UNITY_EDITOR
    [UnityEditor.XR.OpenXR.Features.OpenXRFeature(
        UiName = "HTC Vive Focus 3 Controller Profile",
        Desc = "Tracked controllers for VIVE Focus 3, XR Elite and Focus Vision through VIVE Streaming.",
        Company = "VR Command",
        Version = "1.0.0",
        FeatureId = "vrcommand.openxr.interaction.vive-focus3",
        OpenxrExtensionStrings = ViveFocus3ControllerProfile.Extension,
        BuildTargetGroups = new[] { UnityEditor.BuildTargetGroup.Standalone })]
#endif
    [Preserve]
    public sealed class ViveFocus3ControllerProfile : OpenXRInteractionFeature
    {
        internal const string Extension = "XR_HTC_vive_focus3_controller_interaction";
        internal const string Profile = "/interaction_profiles/htc/vive_focus3_controller";
        internal const string Product = "HTC Vive Focus 3 Controller OpenXR";

        [Preserve]
        [InputControlLayout(displayName = Product, commonUsages = new[] { "LeftHand", "RightHand" })]
        public sealed class ViveFocus3Controller : XRController
        {
            [InputControl(layout = "Pose")] public PoseControl devicePose => GetChildControl<PoseControl>(nameof(devicePose));
            [InputControl(layout = "Pose")] public PoseControl pointer => GetChildControl<PoseControl>(nameof(pointer));
            [InputControl(useStateFrom = "devicePose/isTracked")] public new ButtonControl isTracked => base.isTracked;
            [InputControl(useStateFrom = "devicePose/trackingState")] public new IntegerControl trackingState => base.trackingState;
            [InputControl(useStateFrom = "devicePose/position")] public new Vector3Control devicePosition => base.devicePosition;
            [InputControl(useStateFrom = "devicePose/rotation")] public new QuaternionControl deviceRotation => base.deviceRotation;
            [InputControl(useStateFrom = "pointer/position")] public Vector3Control pointerPosition => GetChildControl<Vector3Control>(nameof(pointerPosition));
            [InputControl(useStateFrom = "pointer/rotation")] public QuaternionControl pointerRotation => GetChildControl<QuaternionControl>(nameof(pointerRotation));
            [InputControl] public ButtonControl triggerPressed => GetChildControl<ButtonControl>(nameof(triggerPressed));
            [InputControl] public ButtonControl primaryButton => GetChildControl<ButtonControl>(nameof(primaryButton));
            [InputControl] public ButtonControl secondaryButton => GetChildControl<ButtonControl>(nameof(secondaryButton));
            [InputControl] public ButtonControl gripPressed => GetChildControl<ButtonControl>(nameof(gripPressed));
        }

        protected override string GetDeviceLayoutName() => nameof(ViveFocus3Controller);

        protected override void RegisterDeviceLayout() => InputSystem.RegisterLayout<ViveFocus3Controller>(
            matches: new InputDeviceMatcher().WithInterface(XRUtilities.InterfaceMatchAnyVersion).WithProduct(Product));

        protected override void UnregisterDeviceLayout() => InputSystem.RemoveLayout(nameof(ViveFocus3Controller));

        protected override void RegisterActionMapsWithRuntime()
        {
            if (SupportsProfile(OpenXRRuntime.IsExtensionEnabled(Extension), OpenXRRuntime.apiVersion))
                AddActionMap(CreateControllerMap());
        }

        internal static bool SupportsProfile(bool extensionEnabled, string version) => extensionEnabled ||
            Version.TryParse(version, out var api) && api >= new Version(1, 1);

        private static ActionMapConfig CreateControllerMap() => new ActionMapConfig
        {
            name = "vrcommandvivefocus3",
            localizedName = Product,
            manufacturer = "HTC",
            serialNumber = string.Empty,
            desiredInteractionProfile = Profile,
            deviceInfos = new List<DeviceConfig>
            {
                Hand(UserPaths.leftHand, InputDeviceCharacteristics.Left),
                Hand(UserPaths.rightHand, InputDeviceCharacteristics.Right)
            },
            actions = new List<ActionConfig>
            {
                Action("devicePose", "Grip Pose", ActionType.Pose, Bind("/input/grip/pose")),
                Action("pointer", "Aim Pose", ActionType.Pose, Bind("/input/aim/pose")),
                Action("triggerPressed", "Trigger", ActionType.Binary, Bind("/input/trigger/click")),
                Action("gripPressed", "Grip Button", ActionType.Binary, Bind("/input/squeeze/click")),
                Action("primaryButton", "Primary Button", ActionType.Binary,
                    Bind("/input/x/click", UserPaths.leftHand), Bind("/input/a/click", UserPaths.rightHand)),
                Action("secondaryButton", "Secondary Button", ActionType.Binary,
                    Bind("/input/y/click", UserPaths.leftHand), Bind("/input/b/click", UserPaths.rightHand))
            }
        };

        private static DeviceConfig Hand(string userPath, InputDeviceCharacteristics side) => new DeviceConfig
        {
            userPath = userPath,
            characteristics = side | InputDeviceCharacteristics.HeldInHand |
                InputDeviceCharacteristics.TrackedDevice | InputDeviceCharacteristics.Controller
        };

        private static ActionConfig Action(string name, string label, ActionType type, params ActionBinding[] bindings) => new ActionConfig
        {
            name = name,
            localizedName = label,
            type = type,
            usages = new List<string>(),
            bindings = new List<ActionBinding>(bindings)
        };

        private static ActionBinding Bind(string path, string hand = null) => new ActionBinding
        {
            interactionPath = path,
            interactionProfileName = Profile,
            userPaths = hand == null ? new List<string>() : new List<string> { hand }
        };
    }
}
