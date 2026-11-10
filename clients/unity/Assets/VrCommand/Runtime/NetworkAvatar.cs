using VrCommand.Simulation;
using System;
using System.Collections.Generic;
using Unity.Netcode;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.Controls;
using UnityEngine.InputSystem.XR;
using UnityEngine.XR;
using Unity.Collections;

namespace VrCommand.Unity
{
    internal readonly struct TrackedWeaponInput
    {
        internal readonly bool FireHeld, ReloadHeld, FirePressed, ReloadPressed;
        internal bool Held => FireHeld || ReloadHeld;
        internal bool Pressed => FirePressed || ReloadPressed;
        internal bool WantsFire => FireHeld || FirePressed;

        internal TrackedWeaponInput(InputAction trigger, InputAction reload)
        {
            FireHeld = trigger.ReadValue<float>() > .5f;
            ReloadHeld = reload.ReadValue<float>() > .5f;
            FirePressed = trigger.WasPressedThisFrame();
            ReloadPressed = reload.WasPressedThisFrame();
        }
    }

    internal struct TrackedWeaponReleaseGate
    {
        internal bool Armed { get; private set; }
        internal void Reset() => Armed = false;

        internal bool Allows(bool ready, bool held, bool pressed)
        {
            if (!ready) { Reset(); return false; }
            if (Armed) return true;
            if (!held && !pressed) Armed = true;
            return false;
        }
    }

    public struct AvatarPose : INetworkSerializable, IEquatable<AvatarPose>
    {
        public const float MuzzleOffset = .15f;
        public Vector3 head, left, right;
        public Quaternion headRotation, leftRotation, rightRotation;
        public byte source; // 1: desktop simulation; 2: client reports valid XR tracking on all three joints.
        public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T : IReaderWriter
        {
            serializer.SerializeValue(ref head); serializer.SerializeValue(ref left); serializer.SerializeValue(ref right);
            serializer.SerializeValue(ref headRotation); serializer.SerializeValue(ref leftRotation); serializer.SerializeValue(ref rightRotation);
            serializer.SerializeValue(ref source);
        }
        public bool Equals(AvatarPose other) => head == other.head && left == other.left && right == other.right
            && headRotation == other.headRotation && leftRotation == other.leftRotation && rightRotation == other.rightRotation && source == other.source;
        public bool Valid()
        {
            return (source == 1 || source == 2) && Point(head) && Point(left) && Point(right) && Rotation(headRotation) && Rotation(leftRotation) && Rotation(rightRotation)
                && Vector3.Distance(head, left) <= 2.5f && Vector3.Distance(head, right) <= 2.5f;
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
        public NetworkVariable<FixedString64Bytes> PlayerId = new NetworkVariable<FixedString64Bytes>();
        public NetworkVariable<bool> PoseAccepted = new NetworkVariable<bool>(false);
        private InputAction leftPosition, rightPosition, leftRotation, rightRotation, trigger, reload;
        private InputAction briefNext, briefClose, briefLicense;
        private readonly MissionBriefingPanel briefingPanel = new MissionBriefingPanel();
        private bool desktopBriefNext, desktopBriefClose, desktopBriefLicense;
        public bool BriefingOpen => briefingPanel.Open;
        public int BriefingPage => briefingPanel.Page;
        public int BriefingPageCount => briefingPanel.PageCount;
        public int BriefingSuppressedInputs => briefingPanel.Weapons.SuppressedPresses;
        private InputAction headTracking, leftTracking, rightTracking;
        private InputAction headTracked, leftTracked, rightTracked;
        private bool JointTrackingReady => !tracked || HasTracking(headTracking, headTracked) && HasTracking(leftTracking, leftTracked) && HasTracking(rightTracking, rightTracked);
        internal bool TrackedInputAvailable => !tracked || TrackedInputFocus.Available(applicationPaused);
        public bool TrackingReady => TrackedInputAvailable && JointTrackingReady && (floorCalibration == null || floorCalibration.Ready)
            && (questPassthrough == null || questPassthrough.Visible);
        internal string AlignmentHint
        {
            get
            {
                if (questPassthrough != null && !questPassthrough.Visible) return "WAITING FOR QUEST PASSTHROUGH";
                if (floorCalibration == null || !floorCalibration.Ready) return floorCalibration?.Hint;
                if (!JointTrackingReady || PoseAccepted.Value) return null;
                var previous = transform.TransformPoint(Pose.Value.head);
                var origin = ArenaWorld.RoomOrigin(floorCalibration.RoomId);
                return FormattableString.Invariant($"RETURN TO LAST VALID POSITION\nROOM X {previous.x - origin.X:F2} / Z {previous.z - origin.Z:F2} M");
            }
        }
        private RoomFloorCalibration floorCalibration;
        private QuestPassthroughView questPassthrough;
        private XRInputSubsystem floorInput;
        private InputAction captureFloorMarker;
        private readonly ReleasePressGate floorMarkerPress = new ReleasePressGate();
        private bool applicationPaused;
        private float nextFloorSearch;
        internal const string TrackedFireBinding = "<XRController>{RightHand}/triggerPressed";
        internal const string TrackedReloadBinding = "<XRController>{RightHand}/primaryButton";
        internal const string ViveReloadBinding = "<ViveController>{RightHand}/gripPressed";
        private TrackedWeaponReleaseGate trackedWeaponRelease;
        internal bool TrackedWeaponReleasePending => tracked && !trackedWeaponRelease.Armed;
        internal static bool HasTracking(InputAction state, InputAction tracked) => state != null && tracked != null && tracked.ReadValue<float>() > .5f && (state.ReadValue<int>() & 3) == 3;
        private Camera localCamera;
        private float nextSend;
        private double nextServerAccept;
        private bool tracked;
        private bool desktopInitialized;
        private float nextFire;
        private double nextWeaponAccept;
        private ulong inputSequence;
        private Renderer[] visuals;
        private bool desktopFire, desktopReload, windowKeyFallbackLogged;
        private Vector2 windowLook, windowMovement;
        private readonly DesktopStanceInput desktopStance = new DesktopStanceInput();
        private readonly TacticalHud tacticalHud = new TacticalHud();
        private FiringRifleModels rifleModels;
        private FiringRifleView firingRifle;
        private GameObject rifle;
        private PlayerBodyModels bodyModels;
        private PlayerBodyView bodyView;
        internal PlayerBodyObservation ObservePlayerBody()=>IsSpawned&&!IsOwner?bodyView?.Observation:null;
        internal PlayerBodyObservation ObserveFirstPersonBody()=>IsSpawned&&IsOwner&&!tracked?bodyView?.Observation:null;

        public override void OnNetworkSpawn()
        {
            PoseAccepted.OnValueChanged += AcceptanceChanged;
            // Keep saved prefab file IDs and tracked joint scales intact. The
            // old tiny cube is inactive; the new mesh is a full-scale sibling.
            var oldWeapon = rightHand.Find("Weapon");
            if (oldWeapon != null) oldWeapon.gameObject.SetActive(false);
            var pointerMarker = rightHand.GetComponent<Renderer>();
            if (pointerMarker != null) pointerMarker.enabled = false;
            rifleModels = new FiringRifleModels(); firingRifle = rifleModels.Create(); rifle = firingRifle.Root;
            rifle.transform.SetParent(transform, false); ServiceRifleModels.Align(rifle.transform, rightHand);
            var activeVisuals = new List<Renderer>(GetComponentsInChildren<Renderer>());
            foreach(var oldHead in head.GetComponentsInChildren<Renderer>(true)){oldHead.enabled=false;activeVisuals.Remove(oldHead);}
            bodyModels=new PlayerBodyModels();bodyView=bodyModels.Create();bodyView.Root.SetActive(false);
            activeVisuals.Remove(pointerMarker);activeVisuals.Remove(firingRifle.HiddenBody); visuals = activeVisuals.ToArray();
            if (IsServer)
            {
                var admission = VenueBootstrap.Instance?.Admission(OwnerClientId);
                if (admission != null) PlayerId.Value = admission.playerId;
                Pose.Value = VenueBootstrap.Instance.combatAuthority.DesktopSpawnPose(OwnerClientId);
            }
            if (!IsOwner) return;
            trackedWeaponRelease.Reset();
            var spectator = GameObject.Find("Desktop Spectator");
            if (spectator != null) spectator.SetActive(false);
            head.GetComponentInChildren<Renderer>().enabled = false;
            localCamera = head.gameObject.AddComponent<Camera>();
            localCamera.nearClipPlane = 0.05f;
            localCamera.farClipPlane = 150;
            localCamera.tag = "MainCamera";
            head.gameObject.AddComponent<AudioListener>();
            CombatAudioView.Install(head.gameObject,this);
            var desktopOpenXR = VenueBootstrap.Instance?.DesktopOpenXRActive == true;
            tracked = desktopOpenXR || XRSettings.isDeviceActive || Application.platform == RuntimePlatform.Android;
            if (tracked)
            {
                var trackingSpace = CreateTrackingSpace(transform, head, leftHand, rightHand);
                var plan = VenueBootstrap.Instance?.AlignmentPlan;
                if (plan != null)
                {
                    trackingSpace.localPosition = Vector3.zero;
                    floorCalibration = new RoomFloorCalibration(plan, transform.position, trackingSpace);
                    captureFloorMarker = Action("Capture Floor Marker", "<XRController>{LeftHand}/triggerPressed");
                    if (plan.MatchesSpawn(transform.position) && VenueBootstrap.Instance.QuestPassthrough)
                        questPassthrough = QuestPassthroughView.Attach(localCamera);
                }
                var driver = head.gameObject.AddComponent<TrackedPoseDriver>();
                driver.positionInput = new InputActionProperty(new InputAction("Head Position", InputActionType.Value, "<XRHMD>/centerEyePosition"));
                driver.rotationInput = new InputActionProperty(new InputAction("Head Rotation", InputActionType.Value, "<XRHMD>/centerEyeRotation"));
                headTracking = Action("Head Tracking", "<XRHMD>/trackingState");
                leftTracking = Action("Left Tracking", "<XRController>{LeftHand}/trackingState");
                rightTracking = Action("Right Tracking", "<XRController>{RightHand}/trackingState");
                headTracked = Action("Head Is Tracked", "<XRHMD>/isTracked");
                leftTracked = Action("Left Is Tracked", "<XRController>{LeftHand}/isTracked");
                rightTracked = Action("Right Is Tracked", "<XRController>{RightHand}/isTracked");
                driver.trackingStateInput = new InputActionProperty(headTracking); driver.ignoreTrackingState = false;
                leftPosition = Action("Left Position", "<XRController>{LeftHand}/devicePosition");
                rightPosition = Action("Right Aim Position", "<XRController>{RightHand}/pointerPosition");
                leftRotation = Action("Left Rotation", "<XRController>{LeftHand}/deviceRotation");
                rightRotation = Action("Right Aim Rotation", "<XRController>{RightHand}/pointerRotation");
                trigger = Action("Fire", TrackedFireBinding);
                reload = Action("Reload", TrackedReloadBinding, desktopOpenXR ? ViveReloadBinding : null);
                briefNext = Action("Briefing Next", "<XRController>{LeftHand}/primaryButton", desktopOpenXR ? "<ViveController>{LeftHand}/trackpadClicked" : null);
                briefClose = Action("Briefing Close", "<XRController>{LeftHand}/secondaryButton", desktopOpenXR ? "<ViveController>{LeftHand}/menu" : null);
                briefLicense = Action("Briefing Font License", "<XRController>{LeftHand}/gripPressed");
                briefingPanel.CreateTracked(head);
            }
            else
            {
                head.localPosition = new Vector3(0, 1.65f, 0);
                InitializeDesktopPose();
                NativePlayerBodyProbe.Install(head.gameObject);
                NativeCombatAudioProbe.Install(head.gameObject);
                NativePlayerFireProbe.Install(head.gameObject);
                NativeEnemyFireProbe.Install(head.gameObject);
                NativeWeatherProbe.Install(head.gameObject);
                Debug.Log("Desktop preview input devices: keyboard=" + (Keyboard.current != null) + ", mouse=" + (Mouse.current != null));
            }
            if (tracked) CreateStatusPanel();
        }

        private bool InitializeDesktopPose()
        {
            if (desktopInitialized) return true;
            var saved = Pose.Value;
            if (saved.source != 1 || !saved.Valid()) return false;
            ApplyDesktopPose(saved); return true;
        }
        private void ApplyDesktopPose(AvatarPose saved)
        {
            head.localPosition = saved.head; head.localRotation = saved.headRotation;
            leftHand.localPosition = saved.left; leftHand.localRotation = saved.leftRotation;
            rightHand.localPosition = saved.right; rightHand.localRotation = saved.rightRotation;
            desktopInitialized = true;
        }
        private void AcceptanceChanged(bool before, bool after)
        {
            if (IsOwner && tracked && !after) trackedWeaponRelease.Reset();
            if (IsOwner && !tracked && desktopInitialized && !after && Pose.Value.source == 1 && Pose.Value.Valid()) ApplyDesktopPose(Pose.Value);
        }

        private static InputAction Action(string name, string binding, string additionalBinding = null)
        {
            var action = new InputAction(name, InputActionType.Value, binding);
            if (additionalBinding != null) action.AddBinding(additionalBinding);
            action.Enable();
            return action;
        }

        private void Update()
        {
            if (!IsSpawned) return;
            var authority = CombatAuthority.Instance;
            var body = default(CombatActorState);
            var hasBody = authority != null && authority.Player(PlayerId.Value.ToString(), out body);
            if (hasBody)
                foreach (var visual in visuals) visual.enabled = body.connected && body.health > 0 && !(IsOwner && visual.transform.IsChildOf(head));
            if (IsOwner)
            {
                var mission = VenueBootstrap.Instance?.sceneAuthority;
                if (mission != null && mission.IsSpawned) briefingPanel.Set(mission.Briefing.Value, mission.ReadBriefingParts());
                var ending = VenueBootstrap.Instance?.Debrief.Active == true;
                var inputAvailable = tracked ? TrackedInputAvailable : Application.isFocused || Application.isBatchMode;
                if (ending) briefingPanel.Close();
                else if (inputAvailable)
                {
                    if (tracked ? briefClose?.WasPressedThisFrame() == true : desktopBriefClose || Keyboard.current?.escapeKey.wasPressedThisFrame == true) briefingPanel.Close();
                    else if (tracked ? briefNext?.WasPressedThisFrame() == true : desktopBriefNext || Keyboard.current?.bKey.wasPressedThisFrame == true) briefingPanel.Next();
                    if (tracked ? briefLicense?.WasPressedThisFrame() == true : desktopBriefLicense || Keyboard.current?.lKey.wasPressedThisFrame == true) briefingPanel.License();
                }
                desktopBriefNext = desktopBriefClose = desktopBriefLicense = false;
                if (tracked && !inputAvailable)
                {
                    SuspendTrackedInput();
                    NativePoseTrace.OwnerUnavailable("TrackedInputUnfocused", OwnerClientId);
                    return;
                }
                var jointsTracked = JointTrackingReady;
                if (questPassthrough != null && !questPassthrough.UpdateAvailability())
                {
                    floorCalibration.Invalidate();
                    floorMarkerPress.Reset();
                    trackedWeaponRelease.Reset();
                    NativePoseTrace.OwnerUnavailable("QuestPassthroughUnavailable", OwnerClientId);
                    return;
                }
                if (floorCalibration != null && !UpdateFloorCalibration(mission, jointsTracked))
                { trackedWeaponRelease.Reset(); NativePoseTrace.OwnerUnavailable("FloorAlignmentUnavailable", OwnerClientId); return; }
                if (!jointsTracked)
                { trackedWeaponRelease.Reset(); NativePoseTrace.OwnerUnavailable("TrackingUnavailable", OwnerClientId); return; }
                if (DesktopClientExercise.Enabled && tracked) { DesktopClientExercise.RejectTracked(); return; }
                if (!tracked && !InitializeDesktopPose()) {NativePoseTrace.OwnerUnavailable("DesktopInitializing",OwnerClientId);return;}
                var exercising = DesktopClientExercise.Enabled;
                var exercise = default(DesktopExerciseFrame);
                if (exercising && CombatAuthority.Instance != null && CombatAuthority.Instance.Player(PlayerId.Value.ToString(), out var exerciseBody))
                    exercise = DesktopClientExercise.Sample(PlayerId.Value.ToString(), OwnerClientId, exerciseBody.room, exerciseBody.presentationTick,
                        !ending && exerciseBody.connected && exerciseBody.health > 0 && CombatAuthority.Instance.Ready.Value && VenueBootstrap.Instance.State == "Running", head.localPosition.z);
                if (tracked)
                {
                    leftHand.localPosition = leftPosition.ReadValue<Vector3>();
                    rightHand.localPosition = rightPosition.ReadValue<Vector3>();
                    leftHand.localRotation = leftRotation.ReadValue<Quaternion>();
                    rightHand.localRotation = rightRotation.ReadValue<Quaternion>();
                }
                else DesktopPreview(!ending, exercise);
                var trackedPose = tracked ? CurrentPose() : default;
                var validTrackedPose = tracked && trackedPose.Valid();
                if (VenueBootstrap.Instance.State != "Ended" && Time.unscaledTime >= nextSend)
                {
                    nextSend = Time.unscaledTime + 0.05f;
                    var pose = tracked ? trackedPose : CurrentPose();
                    if (tracked ? validTrackedPose : pose.Valid()) {NativePoseTrace.Sending(OwnerClientId,pose.source);SubmitPoseRpc(pose);}
                    else NativePoseTrace.OwnerUnavailable("LocalPoseInvalid",OwnerClientId);
                }
                var trackedInput = tracked ? new TrackedWeaponInput(trigger, reload) : default;
                var held = exercising ? exercise.Fire || exercise.Reload : tracked ? trackedInput.Held
                    : desktopFire || desktopReload || Mouse.current?.leftButton.isPressed == true || Keyboard.current?.spaceKey.isPressed == true || Keyboard.current?.rKey.isPressed == true;
                var pressed = exercising ? exercise.Fire || exercise.Reload : tracked ? trackedInput.Pressed
                    : desktopFire || desktopReload || Mouse.current?.leftButton.wasPressedThisFrame == true || Keyboard.current?.spaceKey.wasPressedThisFrame == true || Keyboard.current?.rKey.wasPressedThisFrame == true;
                var allowWeapon = briefingPanel.Weapons.Allows(briefingPanel.Open, held, pressed);
                var ready = authority != null && authority.Ready.Value && VenueBootstrap.Instance.State == "Running" && !ending;
                var trackedArmed = !tracked || trackedWeaponRelease.Allows(ready && allowWeapon && validTrackedPose
                    && PoseAccepted.Value && hasBody && body.connected && body.health > 0, held, pressed);
                if (ready && allowWeapon && trackedArmed && inputAvailable)
                {
                    var wantsReload = exercising ? exercise.Reload : tracked ? trackedInput.ReloadPressed : desktopReload || Keyboard.current != null && Keyboard.current.rKey.wasPressedThisFrame;
                    var wantsFire = exercising ? exercise.Fire : tracked ? trackedInput.WantsFire
                        : desktopFire || Mouse.current != null && Pressed(Mouse.current.leftButton) || Keyboard.current != null && Pressed(Keyboard.current.spaceKey);
                    if (wantsReload) { SubmitWeaponRpc(++inputSequence, true, tracked ? trackedPose : CurrentPose()); if (exercising) DesktopClientExercise.Submitted(true); }
                    else if (wantsFire && Time.unscaledTime >= nextFire)
                    { nextFire = Time.unscaledTime + .2f; SubmitWeaponRpc(++inputSequence, false, tracked ? trackedPose : CurrentPose()); if (exercising) DesktopClientExercise.Submitted(false); }
                }
                desktopFire = desktopReload = false;
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

        private void LateUpdate()
        {
            if (!IsSpawned || rifle == null) return;
            ServiceRifleModels.Align(rifle.transform,rightHand);
            if (CombatAuthority.Instance!=null && CombatAuthority.Instance.Player(PlayerId.Value.ToString(),out var body))
            {
                firingRifle.Apply(body.presentationTick,body.health,body.connected,IsOwner?!tracked:Pose.Value.source==1,body.reloading,body.reloadUntilTick,
                    new PlayerFireState(body.fireSequence,body.fireTickPlusOne,new Vec3(body.fireOrigin.x,body.fireOrigin.y,body.fireOrigin.z),new Vec3(body.fireDirection.x,body.fireDirection.y,body.fireDirection.z)));
                if(IsOwner)bodyView.ApplyFirstPerson(PlayerId.Value.ToString(),head.position,head.rotation,rifle.transform.position,rifle.transform.forward,body,!tracked);
                else bodyView.Apply(PlayerId.Value.ToString(),head.position,head.rotation,rifle.transform.position,rifle.transform.forward,body,Pose.Value.source==1,true);
            }
            // Desktop gloves are cosmetic siblings; never move the tracked joints.
            if(IsOwner?!tracked:Pose.Value.source==1){HideJoint(leftHand);HideJoint(rightHand);}
        }
        private static void HideJoint(Transform joint){foreach(var renderer in joint.GetComponentsInChildren<Renderer>(true))renderer.enabled=false;}

        internal PlayerFireObservation ObservePlayerFire()
        {
            if(!IsSpawned || !IsOwner || firingRifle==null)return null;
            var fire=firingRifle.AppliedFire;
            return new PlayerFireObservation{id=PlayerId.Value.ToString(),tick=firingRifle.AppliedTick,fireSequence=fire.Sequence,fireTickPlusOne=fire.TickPlusOne,
                acceptedOrigin=new Vector3(fire.Origin.X,fire.Origin.Y,fire.Origin.Z),acceptedDirection=new Vector3(fire.Direction.X,fire.Direction.Y,fire.Direction.Z),
                visible=firingRifle.Flash.gameObject.activeInHierarchy,recoil=-firingRifle.RecoilVisual.localPosition.z,gun=rifle.transform.position,
                pointer=rightHand.position,pointerDirection=rightHand.forward,flashOrigin=firingRifle.Flash.position,flashDirection=firingRifle.Flash.forward};
        }
        [Rpc(SendTo.Server, InvokePermission = RpcInvokePermission.Owner, Delivery = RpcDelivery.Unreliable)]
        private void SubmitPoseRpc(AvatarPose pose)
        {
            NativePoseTrace.Event("PoseReceive",OwnerClientId,pose.source);
            if (!pose.Valid()) {NativePoseTrace.Event("PoseInvalid",OwnerClientId,pose.source);return;}
            if (Time.realtimeSinceStartupAsDouble < nextServerAccept) {NativePoseTrace.Event("PoseThrottled",OwnerClientId,pose.source);return;}
            nextServerAccept = Time.realtimeSinceStartupAsDouble + 0.025;
            PoseAccepted.Value = CombatAuthority.Instance != null && CombatAuthority.Instance.AcceptPose(OwnerClientId, pose, transform.position, transform.rotation);
            if (PoseAccepted.Value) {Pose.Value = pose;NativePoseTrace.Accepted(OwnerClientId,pose.source);}
            else NativePoseTrace.Event("PoseRejected",OwnerClientId,pose.source);
        }

        private AvatarPose CurrentPose() => new AvatarPose { source = (byte)(tracked ? 2 : 1), head = transform.InverseTransformPoint(head.position), left = transform.InverseTransformPoint(leftHand.position), right = transform.InverseTransformPoint(rightHand.position),
            headRotation = Quaternion.Inverse(transform.rotation) * head.rotation, leftRotation = Quaternion.Inverse(transform.rotation) * leftHand.rotation, rightRotation = Quaternion.Inverse(transform.rotation) * rightHand.rotation };

        public static Transform CreateTrackingSpace(Transform root, params Transform[] joints)
        {
            var space = new GameObject("XR Tracking Origin").transform; space.SetParent(root, false);
            var inputs = new List<XRInputSubsystem>(); SubsystemManager.GetSubsystems(inputs);
            var floor = false;
            foreach (var input in inputs)
                if (input.running && input.TrySetTrackingOriginMode(TrackingOriginModeFlags.Floor)) floor = true;
            space.localPosition = floor ? Vector3.zero : new Vector3(0, 1.65f, 0);
            foreach (var joint in joints) joint.SetParent(space, false);
            return space;
        }

        private bool UpdateFloorCalibration(SceneAuthority mission, bool jointsTracked)
        {
            if ((floorInput == null || !floorInput.running || floorInput.GetTrackingOriginMode() != TrackingOriginModeFlags.Floor)
                && Time.unscaledTime >= nextFloorSearch)
            {
                nextFloorSearch = Time.unscaledTime + 1;
                var inputs = new List<XRInputSubsystem>();
                SubsystemManager.GetSubsystems(inputs);
                var candidate = inputs.Find(input => input.running && (input.GetSupportedTrackingOriginModes() & TrackingOriginModeFlags.Floor) != 0);
                if (candidate != floorInput)
                {
                    if (floorInput != null) floorInput.trackingOriginUpdated -= FloorOriginChanged;
                    floorInput = candidate;
                    floorMarkerPress.Reset();
                    floorCalibration.Invalidate();
                    if (floorInput != null) floorInput.trackingOriginUpdated += FloorOriginChanged;
                }
                if (floorInput != null && floorInput.GetTrackingOriginMode() != TrackingOriginModeFlags.Floor)
                    floorInput.TrySetTrackingOriginMode(TrackingOriginModeFlags.Floor);
            }
            var floorReady = floorInput != null && floorInput.running && floorInput.GetTrackingOriginMode() == TrackingOriginModeFlags.Floor;
            var phase = mission != null && mission.IsSpawned ? mission.Phase.Value.ToString() : "";
            var allowed = phase == "Preparing" || phase == "Paused";
            var capture = floorMarkerPress.Poll(allowed && floorReady && !floorCalibration.Ready, true, jointsTracked,
                captureFloorMarker.ReadValue<float>() > .5f);
            return floorCalibration.Update(allowed, floorReady, jointsTracked, capture, leftPosition.ReadValue<Vector3>());
        }

        private void FloorOriginChanged(XRInputSubsystem input)
        {
            trackedWeaponRelease.Reset();
            floorMarkerPress.Reset();
            floorCalibration?.Invalidate();
        }

        [Rpc(SendTo.Server, InvokePermission = RpcInvokePermission.Owner)]
        private void SubmitWeaponRpc(ulong input, bool reloadWeapon, AvatarPose pose)
        {
            if (!pose.Valid() || Time.realtimeSinceStartupAsDouble < nextWeaponAccept) return;
            nextWeaponAccept = Time.realtimeSinceStartupAsDouble + .025;
            CombatAuthority.Instance?.Weapon(OwnerClientId, input, reloadWeapon, pose, transform.position, transform.rotation);
        }

        private void DesktopPreview(bool playing, DesktopExerciseFrame exercise = default)
        {
            if (DesktopClientExercise.Enabled)
            {
                desktopStance.Reset(); head.localPosition = new Vector3(head.localPosition.x, DesktopStanceInput.StandingHeight, head.localPosition.z);
                if (playing) MoveDesktop(exercise.Movement, Time.unscaledDeltaTime);
                windowLook = windowMovement = Vector2.zero; UpdateDesktopHands(); return;
            }
            var keyboard = Keyboard.current;
            var active = playing && (Application.isFocused || Application.isBatchMode);
            desktopStance.Poll(keyboard, active);
            head.localPosition = new Vector3(head.localPosition.x, desktopStance.EyeHeight, head.localPosition.z);
            if (active)
            {
                var look = keyboard == null ? Vector2.zero : new Vector2(Turn(keyboard.rightArrowKey) - Turn(keyboard.leftArrowKey), Turn(keyboard.downArrowKey) - Turn(keyboard.upArrowKey));
                if (look.x == 0) look.x = windowLook.x;
                if (look.y == 0) look.y = windowLook.y;
                if (Mouse.current != null && Mouse.current.rightButton.isPressed)
                { var delta = Mouse.current.delta.ReadValue(); look += new Vector2(delta.x, -delta.y) * .15f; }
                head.localRotation = DesktopPreviewControls.Look(head.localRotation, look);
                var movement = keyboard == null ? Vector2.zero : new Vector2((Pressed(keyboard.dKey) ? 1 : 0) - (Pressed(keyboard.aKey) ? 1 : 0),
                    (Pressed(keyboard.wKey) ? 1 : 0) - (Pressed(keyboard.sKey) ? 1 : 0));
                if (movement == Vector2.zero && windowMovement != Vector2.zero) MoveDesktop(windowMovement, .025f);
                else MoveDesktop(movement, Time.unscaledDeltaTime);
            }
            windowLook = windowMovement = Vector2.zero;
            UpdateDesktopHands();
        }
        private void UpdateDesktopHands()
        {
            leftHand.localPosition = head.localPosition + head.localRotation * new Vector3(-0.3f, -0.35f, 0.4f);
            rightHand.localPosition = head.localPosition + head.localRotation * DesktopPreviewControls.RightOffset;
            leftHand.localRotation = rightHand.localRotation = head.localRotation;
        }
        private void ResetDesktopStance()
        {
            desktopStance.Reset();
            if (!IsOwner || tracked || head == null) return;
            head.localPosition = new Vector3(head.localPosition.x, DesktopStanceInput.StandingHeight, head.localPosition.z);
            if (leftHand != null && rightHand != null) UpdateDesktopHands();
        }
        private void SuspendTrackedInput(bool invalidateAlignment = false)
        {
            trackedWeaponRelease.Reset();
            floorMarkerPress.Reset();
            if (floorCalibration != null && (invalidateAlignment || !floorCalibration.Ready)) floorCalibration.Invalidate();
        }
        private void OnApplicationFocus(bool focused)
        {
            if (focused) return;
            ResetDesktopStance();
            SuspendTrackedInput();
        }
        private void OnApplicationPause(bool paused)
        {
            applicationPaused = paused;
            ResetDesktopStance();
            if (paused) SuspendTrackedInput(invalidateAlignment: true);
        }
        private void OnDisable() { ResetDesktopStance(); SuspendTrackedInput(invalidateAlignment: true); questPassthrough?.Stop(); }
        private static bool Pressed(ButtonControl button) => button.isPressed || button.wasPressedThisFrame;
        private static float Turn(ButtonControl button) => button.wasPressedThisFrame ? 3 : button.isPressed ? 60 * Time.unscaledDeltaTime : 0;
        private void MoveDesktop(Vector2 movement, float seconds)
        {
            var authority = CombatAuthority.Instance;
            if (authority == null || !authority.Player(PlayerId.Value.ToString(), out var player)) return;
            var origin = VenueBootstrap.RoomOrigin(player.room);
            var desired = DesktopPreviewControls.Move(head.localPosition, head.localRotation, movement, seconds, transform.position - origin);
            if (authority.ConstrainDesktop(player.room, head.position, transform.TransformPoint(desired), out var constrained))
                head.localPosition = transform.InverseTransformPoint(constrained);
        }
        private void DesktopWindowKey()
        {
            if (!Application.isFocused || (Event.current.type != EventType.KeyDown && Event.current.type != EventType.KeyUp)) return;
            var keyboard = Keyboard.current; ButtonControl raw = null;
            if (desktopStance.WindowKey(Event.current.keyCode, Event.current.type == EventType.KeyDown, keyboard)) { Event.current.Use(); return; }
            if (Event.current.type != EventType.KeyDown) return;
            var look = Vector2.zero; var movement = Vector2.zero; var fire = false; var reloadWeapon = false;
            switch (Event.current.keyCode)
            {
                case KeyCode.LeftArrow: raw = keyboard?.leftArrowKey; look.x = -3; break;
                case KeyCode.RightArrow: raw = keyboard?.rightArrowKey; look.x = 3; break;
                case KeyCode.UpArrow: raw = keyboard?.upArrowKey; look.y = -3; break;
                case KeyCode.DownArrow: raw = keyboard?.downArrowKey; look.y = 3; break;
                case KeyCode.W: raw = keyboard?.wKey; movement.y = 1; break;
                case KeyCode.S: raw = keyboard?.sKey; movement.y = -1; break;
                case KeyCode.A: raw = keyboard?.aKey; movement.x = -1; break;
                case KeyCode.D: raw = keyboard?.dKey; movement.x = 1; break;
                case KeyCode.Space: raw = keyboard?.spaceKey; fire = true; break;
                case KeyCode.R: raw = keyboard?.rKey; reloadWeapon = true; break;
                case KeyCode.B: if (keyboard?.bKey.wasPressedThisFrame != true) desktopBriefNext = true; Event.current.Use(); return;
                case KeyCode.Escape: if (keyboard?.escapeKey.wasPressedThisFrame != true) desktopBriefClose = true; Event.current.Use(); return;
                case KeyCode.L: if (keyboard?.lKey.wasPressedThisFrame != true) desktopBriefLicense = true; Event.current.Use(); return;
                default: return;
            }
            // Window-message input (e.g. accessibility keyboards) may not appear on the raw device.
            // A physical press already observed by InputSystem must never be applied twice.
            if (raw != null && Pressed(raw)) return;
            if (!windowKeyFallbackLogged) { windowKeyFallbackLogged = true; Debug.Log("Desktop window key fallback active."); }
            windowLook += look; windowMovement += movement; desktopFire |= fire; desktopReload |= reloadWeapon;
            Event.current.Use();
        }

        private void OnGUI()
        {
            if (!IsSpawned || !IsOwner || tracked || localCamera == null || VenueBootstrap.Instance?.Debrief.Active == true) return;
            DesktopWindowKey();
            var combat = CombatAuthority.Instance;
            if (combat == null || !combat.Player(PlayerId.Value.ToString(), out var player)) return;
            var phaseName = VenueBootstrap.Instance == null ? "Preparing" : VenueBootstrap.Instance.State;
            if (Event.current.type == EventType.Repaint) tacticalHud.Draw(this, combat, player, localCamera, rightHand, phaseName);
            briefingPanel.Draw();
        }

        private void CreateStatusPanel()
        {
            var panel = new GameObject("Mission Status", typeof(Canvas));
            panel.transform.SetParent(head, false);
            panel.transform.localPosition = new Vector3(0, -0.3f, 1);
            panel.transform.localScale = Vector3.one * 0.0015f;
            var canvas = panel.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace;
            panel.GetComponent<RectTransform>().sizeDelta = new Vector2(600, 150);
            var label = new GameObject("Phase", typeof(UnityEngine.UI.Text));
            label.transform.SetParent(panel.transform, false);
            var text = label.GetComponent<UnityEngine.UI.Text>();
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            text.fontSize = 24;
            text.alignment = TextAnchor.MiddleCenter;
            text.color = new Color(0.6f, 1, 0.6f);
            label.GetComponent<RectTransform>().sizeDelta = new Vector2(600, 150);
            label.AddComponent<PhaseLabel>().avatar = this;
        }

        public override void OnNetworkDespawn()
        {
            SuspendTrackedInput();
            if (questPassthrough != null)
            {
                questPassthrough.enabled = false;
                Destroy(questPassthrough);
                questPassthrough = null;
            }
            if (floorInput != null) floorInput.trackingOriginUpdated -= FloorOriginChanged;
            floorInput = null; floorCalibration = null;
            captureFloorMarker?.Dispose(); captureFloorMarker = null;
            head.GetComponent<CombatAudioView>()?.Dispose();
            if (IsOwner) tacticalHud.Reset();
            PoseAccepted.OnValueChanged -= AcceptanceChanged;
            leftPosition?.Dispose(); rightPosition?.Dispose(); leftRotation?.Dispose(); rightRotation?.Dispose(); trigger?.Dispose(); reload?.Dispose();
            headTracking?.Dispose(); leftTracking?.Dispose(); rightTracking?.Dispose();
            headTracked?.Dispose(); leftTracked?.Dispose(); rightTracked?.Dispose();
            briefNext?.Dispose(); briefClose?.Dispose(); briefLicense?.Dispose(); briefingPanel.Dispose();
            firingRifle?.Dispose();firingRifle=null;
            bodyView?.Dispose();bodyView=null;bodyModels?.Dispose();bodyModels=null;
            if (rifle != null) Destroy(rifle); rifle = null;
            rifleModels?.Dispose(); rifleModels = null;
        }
    }

    public static class DesktopPreviewControls
    {
        // Synthetic desktop pose only. Real XR pointer input is never moved.
        public static Vector3 RightOffset => new Vector3(.18f, -.12f, .75f);
        public static Quaternion Look(Quaternion rotation, Vector2 degrees)
        {
            var pitch = Mathf.DeltaAngle(0, rotation.eulerAngles.x);
            return Quaternion.Euler(Mathf.Clamp(pitch + degrees.y, -70, 70), rotation.eulerAngles.y + degrees.x, 0);
        }
        public static Vector3 Move(Vector3 position, Quaternion rotation, Vector2 axes, float seconds, Vector3 rootInRoom)
        {
            var yaw = Quaternion.Euler(0, rotation.eulerAngles.y, 0);
            var motion = yaw * new Vector3(axes.x, 0, axes.y).normalized * (Mathf.Min(Mathf.Max(seconds, 0), .1f) * 2 * Mathf.Min(axes.magnitude, 1));
            return new Vector3(Mathf.Clamp(position.x + motion.x, -5 - rootInRoom.x, 5 - rootInRoom.x), position.y,
                Mathf.Clamp(position.z + motion.z, -5 - rootInRoom.z, 5 - rootInRoom.z));
        }
    }

}
