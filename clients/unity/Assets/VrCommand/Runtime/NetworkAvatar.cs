using System;
using Unity.Netcode;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.XR;
using UnityEngine.XR;

namespace VrCommand.Unity
{
    public struct AvatarPose : INetworkSerializable, IEquatable<AvatarPose>
    {
        public Vector3 head, left, right;
        public Quaternion headRotation, leftRotation, rightRotation;
        public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T : IReaderWriter
        {
            serializer.SerializeValue(ref head); serializer.SerializeValue(ref left); serializer.SerializeValue(ref right);
            serializer.SerializeValue(ref headRotation); serializer.SerializeValue(ref leftRotation); serializer.SerializeValue(ref rightRotation);
        }
        public bool Equals(AvatarPose other) => head == other.head && left == other.left && right == other.right
            && headRotation == other.headRotation && leftRotation == other.leftRotation && rightRotation == other.rightRotation;
        public bool Valid()
        {
            return Point(head) && Point(left) && Point(right) && Rotation(headRotation) && Rotation(leftRotation) && Rotation(rightRotation);
        }
        private static bool Point(Vector3 value) => float.IsFinite(value.x) && float.IsFinite(value.y) && float.IsFinite(value.z)
            && Mathf.Abs(value.x) <= 10 && Mathf.Abs(value.z) <= 10 && value.y >= -1 && value.y <= 4;
        private static bool Rotation(Quaternion value)
        {
            var norm = value.x * value.x + value.y * value.y + value.z * value.z + value.w * value.w;
            return float.IsFinite(norm) && norm > 0.9f && norm < 1.1f;
        }
    }

    public sealed class NetworkAvatar : NetworkBehaviour
    {
        public Transform head, leftHand, rightHand;
        public NetworkVariable<AvatarPose> Pose = new NetworkVariable<AvatarPose>();
        private InputAction leftPosition, rightPosition, leftRotation, rightRotation;
        private Camera localCamera;
        private float nextSend;
        private double nextServerAccept;
        private bool tracked;

        public override void OnNetworkSpawn()
        {
            if (!IsOwner) return;
            var spectator = GameObject.Find("Desktop Spectator");
            if (spectator != null) spectator.SetActive(false);
            head.GetComponentInChildren<Renderer>().enabled = false;
            localCamera = head.gameObject.AddComponent<Camera>();
            localCamera.nearClipPlane = 0.05f;
            localCamera.farClipPlane = 150;
            localCamera.tag = "MainCamera";
            head.gameObject.AddComponent<AudioListener>();
            tracked = XRSettings.isDeviceActive || Application.platform == RuntimePlatform.Android;
            if (tracked)
            {
                var driver = head.gameObject.AddComponent<TrackedPoseDriver>();
                driver.positionInput = new InputActionProperty(new InputAction("Head Position", InputActionType.Value, "<XRHMD>/centerEyePosition"));
                driver.rotationInput = new InputActionProperty(new InputAction("Head Rotation", InputActionType.Value, "<XRHMD>/centerEyeRotation"));
                driver.ignoreTrackingState = true;
                leftPosition = Action("Left Position", "<XRController>{LeftHand}/devicePosition");
                rightPosition = Action("Right Position", "<XRController>{RightHand}/devicePosition");
                leftRotation = Action("Left Rotation", "<XRController>{LeftHand}/deviceRotation");
                rightRotation = Action("Right Rotation", "<XRController>{RightHand}/deviceRotation");
            }
            else head.localPosition = new Vector3(0, 1.65f, 0);
            CreateStatusPanel();
        }

        private static InputAction Action(string name, string binding)
        {
            var action = new InputAction(name, InputActionType.Value, binding);
            action.Enable();
            return action;
        }

        private void Update()
        {
            if (!IsSpawned) return;
            if (IsOwner)
            {
                if (tracked)
                {
                    leftHand.localPosition = leftPosition.ReadValue<Vector3>();
                    rightHand.localPosition = rightPosition.ReadValue<Vector3>();
                    leftHand.localRotation = leftRotation.ReadValue<Quaternion>();
                    rightHand.localRotation = rightRotation.ReadValue<Quaternion>();
                }
                else DesktopPreview();
                if (Time.unscaledTime >= nextSend)
                {
                    nextSend = Time.unscaledTime + 0.05f;
                    var pose = new AvatarPose { head = head.localPosition, left = leftHand.localPosition, right = rightHand.localPosition,
                        headRotation = head.localRotation, leftRotation = leftHand.localRotation, rightRotation = rightHand.localRotation };
                    if (pose.Valid()) SubmitPoseRpc(pose);
                }
            }
            else
            {
                var pose = Pose.Value;
                if (!pose.Valid()) return;
                var blend = 1 - Mathf.Exp(-18 * Time.unscaledDeltaTime);
                head.localPosition = Vector3.Lerp(head.localPosition, pose.head, blend);
                leftHand.localPosition = Vector3.Lerp(leftHand.localPosition, pose.left, blend);
                rightHand.localPosition = Vector3.Lerp(rightHand.localPosition, pose.right, blend);
                head.localRotation = Quaternion.Slerp(head.localRotation, pose.headRotation, blend);
                leftHand.localRotation = Quaternion.Slerp(leftHand.localRotation, pose.leftRotation, blend);
                rightHand.localRotation = Quaternion.Slerp(rightHand.localRotation, pose.rightRotation, blend);
            }
        }

        [Rpc(SendTo.Server, InvokePermission = RpcInvokePermission.Owner, Delivery = RpcDelivery.Unreliable)]
        private void SubmitPoseRpc(AvatarPose pose)
        {
            if (!pose.Valid() || Time.realtimeSinceStartupAsDouble < nextServerAccept) return;
            nextServerAccept = Time.realtimeSinceStartupAsDouble + 0.025;
            Pose.Value = pose;
        }

        private void DesktopPreview()
        {
            var keyboard = Keyboard.current;
            if (keyboard == null) return;
            var motion = new Vector3((keyboard.dKey.isPressed ? 1 : 0) - (keyboard.aKey.isPressed ? 1 : 0), 0,
                (keyboard.wKey.isPressed ? 1 : 0) - (keyboard.sKey.isPressed ? 1 : 0));
            head.localPosition += motion * (2 * Time.deltaTime);
            head.localPosition = new Vector3(Mathf.Clamp(head.localPosition.x, -5, 5), 1.65f, Mathf.Clamp(head.localPosition.z, -5, 5));
            if (Mouse.current != null && Mouse.current.rightButton.isPressed)
            {
                var delta = Mouse.current.delta.ReadValue();
                head.localRotation = Quaternion.Euler(0, delta.x * 0.15f, 0) * head.localRotation;
            }
            leftHand.localPosition = head.localPosition + head.localRotation * new Vector3(-0.3f, -0.35f, 0.4f);
            rightHand.localPosition = head.localPosition + head.localRotation * new Vector3(0.3f, -0.35f, 0.4f);
            leftHand.localRotation = rightHand.localRotation = head.localRotation;
        }

        private void CreateStatusPanel()
        {
            var panel = new GameObject("Mission Status", typeof(Canvas));
            panel.transform.SetParent(head, false);
            panel.transform.localPosition = new Vector3(0, -0.3f, 1);
            panel.transform.localScale = Vector3.one * 0.0015f;
            var canvas = panel.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace;
            panel.GetComponent<RectTransform>().sizeDelta = new Vector2(600, 90);
            var label = new GameObject("Phase", typeof(UnityEngine.UI.Text));
            label.transform.SetParent(panel.transform, false);
            var text = label.GetComponent<UnityEngine.UI.Text>();
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            text.fontSize = 32;
            text.alignment = TextAnchor.MiddleCenter;
            text.color = new Color(0.6f, 1, 0.6f);
            label.GetComponent<RectTransform>().sizeDelta = new Vector2(600, 90);
            label.AddComponent<PhaseLabel>();
        }

        public override void OnNetworkDespawn()
        {
            leftPosition?.Dispose(); rightPosition?.Dispose(); leftRotation?.Dispose(); rightRotation?.Dispose();
        }
    }

}
