using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using Unity.Netcode;
using Unity.Netcode.Transports.UTP;
using Unity.Networking.Transport;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.Rendering;
using UnityEngine.XR;
using UnityEngine.XR.Management;
using UnityEngine.XR.OpenXR;
using SessionSnapshot = VrCommand.Simulation.ManagementSnapshot;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    public sealed class VenueBootstrap : MonoBehaviour
    {
        public NetworkManager networkManager;
        public SceneAuthority sceneAuthority;
        public CombatAuthority combatAuthority;
        private readonly Dictionary<ulong, TicketApproval> admitted = new Dictionary<ulong, TicketApproval>();
        private LaunchConfiguration configuration;
        internal RoomFloorPlan AlignmentPlan => configuration?.AlignmentPlan;
        internal bool QuestPassthrough => configuration?.questPassthrough == true;
        private string status = "WAITING FOR CONTROL DESK";
        private bool managementReady;
        private float nextReconnect;
        private ClientReconnectInput reconnectInput;
        private XRManagerSettings desktopXrManager;
        private bool clientConnectionReady;
        internal bool DesktopOpenXRActive { get; private set; }
        private bool applicationPaused;
        private VenueLinkDiagnostics linkDiagnostics;
        private const int MaximumPeerObservations = 256;
        private bool peerDiagnostics;
        private int peerObservations;
        public bool CanReconnect => clientConnectionReady && networkManager != null && ClientReconnectInput.CanOffer(configuration?.role,
            networkManager.IsListening, networkManager.ShutdownInProgress, Time.unscaledTime, nextReconnect);
        public string ReconnectHint => reconnectInput != null && CanReconnect
            ? DesktopOpenXRActive ? "\nRELEASE THEN PRESS RIGHT B / VIVE MENU TO RELOAD PLAYER TICKET"
                : "\nRELEASE THEN PRESS RIGHT B TO RELOAD PLAYER TICKET"
            : "";
        private TelemetryOutbox outbox;
        private WorldRecordingDelivery worldDelivery;
        private sealed class EndingClient
        {
            internal TicketApproval Admission;
            internal MissionDebrief Context, Result;
            internal double Deadline;
            internal bool Acknowledged;
        }
        [Serializable] private sealed class DebriefReceiptAdmission
        {
            public string playerId, admissionId;
            public int roomId;
        }
        [Serializable] private sealed class DebriefReceiptBatch
        {
            public string streamId;
            public long throughSequence, finalStreamSequence, worldSequence;
            public DebriefReceiptAdmission[] players;
        }
        private readonly Dictionary<ulong, EndingClient> ending = new Dictionary<ulong, EndingClient>();
        private readonly List<DebriefReceiptAdmission> pendingDebriefReceipts = new List<DebriefReceiptAdmission>();
        private bool publishingDebriefReceipts;
        public MissionDebriefState Debrief { get; } = new MissionDebriefState();
        private bool deliveringDebriefs;
        public string PlayerStatus => Debrief.Result != null ? Debrief.Result.Display : Debrief.Pending
            ? (networkManager.IsConnectedClient ? "MISSION ENDED - WAITING FOR SEALED RESULTS" : "MISSION ENDED - RESULTS NOT CONFIRMED; CONTACT CONTROL DESK") : Status;
        public static VenueBootstrap Instance { get; private set; }
        public string State => sceneAuthority != null && sceneAuthority.IsSpawned ? sceneAuthority.Phase.Value.ToString() : "Preparing";
        public string Status => status + (outbox == null ? "" : " / REPORTS PENDING " + (outbox.LastSequence - outbox.AcknowledgedSequence));

        private IEnumerator Start()
        {
            Instance = this;
#if UNITY_ANDROID && !UNITY_EDITOR
            if (ReadQuestOpenXRProbe() is Guid nonce) StartCoroutine(ObserveQuestOpenXR(nonce));
#endif
            var spectator = GameObject.Find("Desktop Spectator");
            if (Application.platform == RuntimePlatform.Android) ConfigureWaitingHead(spectator);
            Application.targetFrameRate = Application.platform == RuntimePlatform.Android ? 72 : 90;
            if (Application.platform != RuntimePlatform.Android) Application.runInBackground = true;
            var desktopOpenXR = Array.IndexOf(Environment.GetCommandLineArgs(), "--vr-openxr") >= 0;
            try { configuration = LaunchConfiguration.Load(); }
            catch (Exception) { status = "PLEASE CONTACT THE CONTROL DESK"; }
            if (desktopOpenXR)
            {
                if (!CanStartDesktopOpenXR(configuration?.role, Application.platform, Application.isBatchMode, SystemInfo.graphicsDeviceType))
                {
                    EndDesktopOpenXRStartup("rejected");
                    yield break;
                }
                yield return StartDesktopOpenXR();
                if (!DesktopOpenXRActive) yield break;
                ConfigureWaitingHead(spectator);
            }
            if (configuration == null) yield break;
            peerDiagnostics = configuration.role == "Server" && Application.platform == RuntimePlatform.WindowsPlayer
                && Application.isBatchMode && Array.Exists(Environment.GetCommandLineArgs(), argument => argument == "--vr-peer-diagnostics");
            if (!DesktopClientExercise.Install(gameObject, configuration.role)) { status = "DESKTOP EXERCISE REJECTED"; if (Application.isBatchMode && !Application.isEditor) Application.Quit(2); yield break; }
            if (configuration.role == "Client" && (Application.platform == RuntimePlatform.Android || DesktopOpenXRActive || XRSettings.isDeviceActive))
                reconnectInput = new ClientReconnectInput(DesktopOpenXRActive);
            NativePoseContinuity.Install(gameObject,configuration.role);
            NativePoseTrace.Install(gameObject,configuration.role);
            NativeWorldJournalTrace.Install(gameObject,configuration.role);
            NativeReplicationProbe.Install(this,configuration.role);
            linkDiagnostics = VenueLinkDiagnostics.Create(this, configuration.role);
            var transport = (UnityTransport)networkManager.NetworkConfig.NetworkTransport;
            VenueTransportProfile.Apply(transport,configuration.IsServer);
            transport.SetConnectionData(configuration.address, configuration.port, configuration.IsServer ? configuration.ServerListenAddress : null);
            networkManager.OnClientDisconnectCallback += Disconnected;
            networkManager.OnClientConnectedCallback += Connected;
            networkManager.OnServerStopped += ServerStopped;
            networkManager.OnTransportFailure += TransportFailed;
            networkManager.NetworkConfig.ConnectionApproval = true;
            networkManager.NetworkConfig.ClientConnectionBufferTimeout = 20;
            if (configuration.IsServer)
            {
                networkManager.ConnectionApprovalCallback = ApproveConnection;
                yield return RefreshManagement();
                if (!managementReady)
                {
                    if (status == "WAITING FOR CONTROL DESK") status = "CONTROL DESK CONNECTION FAILED";
                    yield break;
                }
                var telemetryReady = true;
                try
                {
                    var directory = string.IsNullOrWhiteSpace(configuration.telemetryDirectory) ? System.IO.Path.Combine(Application.persistentDataPath, "telemetry") : configuration.telemetryDirectory;
                    combatAuthority.InitializeTelemetry(System.IO.Path.Combine(directory, configuration.sessionId + ".journal"), Guid.Parse(configuration.sessionId), configuration.telemetryOrigin);
                    outbox = combatAuthority.Outbox;
                    combatAuthority.InitializeRecording(System.IO.Path.Combine(directory, configuration.sessionId + ".worldlog"));
                }
                catch (Exception) { status = "TELEMETRY JOURNAL NEEDS RECOVERY"; telemetryReady = false; }
                if (!telemetryReady) yield break;
                yield return OpenTelemetry();
                if (!streamReady) { status = "TELEMETRY ATTACHMENT FAILED"; yield break; }
                yield return RefreshManagement();
                if (!managementReady) yield break;
                StartCoroutine(DeliverTelemetry());
                worldDelivery = gameObject.AddComponent<WorldRecordingDelivery>();
                worldDelivery.Initialize(combatAuthority.Recording, combatAuthority.RecordingWriter, outbox, configuration, message => { status = message; combatAuthority.TelemetryFault(); });
                if (configuration.role == "Host")
                {
                    // NGO 2.7 ignores asynchronous host approval; validate before StartHost and answer it synchronously.
                    var hostApproval = new NetworkManager.ConnectionApprovalResponse();
                    yield return ValidateAdmission(NetworkManager.ServerClientId, configuration.AdmissionPayload(), hostApproval, true);
                    if (!hostApproval.Approved) { status = "HOST ADMISSION FAILED"; yield break; }
                }
            }
            if (configuration.role != "Server")
                networkManager.NetworkConfig.ConnectionData = configuration.AdmissionPayload();
            clientConnectionReady = configuration.role == "Client";
            status = "CONNECTING";
            var started = configuration.role == "Server" ? networkManager.StartServer()
                : configuration.role == "Host" ? networkManager.StartHost() : networkManager.StartClient();
            Debug.Log("VR_NETWORK_STARTED role=" + configuration.role + " started=" + started + " background=" + Application.runInBackground + " port=" + transport.ConnectionData.Port);
            if (!started) { status = "CONNECTION FAILED"; yield break; }
            linkDiagnostics?.Attach();
            if (configuration.IsServer)
            {
                while (networkManager.IsListening)
                {
                    if (managementReady) sceneAuthority.ApplyServerSnapshot(latestSnapshot);
                    else { sceneAuthority.SuspendForManagementLoss(); combatAuthority.Suspend(AuthoritySuspension.ManagementRefresh); }
                    yield return new WaitForSecondsRealtime(0.5f);
                    yield return RefreshManagement();
                    if (!managementReady) { sceneAuthority.SuspendForManagementLoss(); combatAuthority.Suspend(AuthoritySuspension.ManagementRefresh); }
                }
            }
        }

#if UNITY_ANDROID && !UNITY_EDITOR
        private static Guid? ReadQuestOpenXRProbe()
        {
            try
            {
                using var player = new AndroidJavaClass("com.unity3d.player.UnityPlayer");
                using var activity = player.GetStatic<AndroidJavaObject>("currentActivity");
                using var intent = activity?.Call<AndroidJavaObject>("getIntent");
                var value = intent?.Call<string>("getStringExtra", "com.vrcommand.quest.OPENXR_PROBE");
                return Guid.TryParseExact(value, "N", out var nonce) && nonce != Guid.Empty ? nonce : (Guid?)null;
            }
            catch (AndroidJavaException) { return null; }
        }

        private static IEnumerator ObserveQuestOpenXR(Guid nonce)
        {
            var deadline = Time.realtimeSinceStartupAsDouble + 12;
            bool loaderReady, displayRunning, inputRunning;
            do
            {
                var loader = XRGeneralSettings.Instance?.Manager?.activeLoader as OpenXRLoader;
                loaderReady = loader != null;
                displayRunning = loader?.GetLoadedSubsystem<XRDisplaySubsystem>()?.running == true;
                inputRunning = loader?.GetLoadedSubsystem<XRInputSubsystem>()?.running == true;
                if (displayRunning && inputRunning || Time.realtimeSinceStartupAsDouble >= deadline) break;
                yield return null;
            } while (true);
            Debug.Log($"VR_QUEST_OPENXR nonce={nonce:N} loader={(loaderReady ? 1 : 0)} display={(displayRunning ? 1 : 0)} input={(inputRunning ? 1 : 0)}");
        }
#endif

        internal static bool CanStartDesktopOpenXR(string role, RuntimePlatform platform, bool batchMode, GraphicsDeviceType graphics)
            => role == "Client" && platform == RuntimePlatform.WindowsPlayer && !batchMode && graphics != GraphicsDeviceType.Null;

        private IEnumerator StartDesktopOpenXR()
        {
            status = "STARTING OPENXR";
            Debug.Log("VR_OPENXR_STARTUP status=requested");
            // Manual initialization runs after the first Start callback and graphics setup.
            yield return null;
            var manager = XRGeneralSettings.Instance?.Manager;
            if (manager != null && manager.activeLoader == null)
            {
                yield return manager.InitializeLoader();
                if (manager.activeLoader is OpenXRLoader loader)
                {
                    desktopXrManager = manager;
                    manager.StartSubsystems();
                    var deadline = Time.realtimeSinceStartupAsDouble + 12;
                    var display = loader.GetLoadedSubsystem<XRDisplaySubsystem>();
                    var input = loader.GetLoadedSubsystem<XRInputSubsystem>();
                    while (display != null && input != null && Time.realtimeSinceStartupAsDouble < deadline)
                    {
                        if (display.running && input.running)
                        {
                            DesktopOpenXRActive = true;
                            Debug.Log("VR_OPENXR_STARTUP status=active");
                            yield break;
                        }
                        yield return null;
                    }
                }
            }
            EndDesktopOpenXRStartup("unavailable");
        }

        private void EndDesktopOpenXRStartup(string reason)
        {
            status = "OPENXR STARTUP FAILED - CONTACT CONTROL DESK";
            Debug.Log("VR_OPENXR_STARTUP status=" + reason);
            if (!Application.isEditor) Application.Quit(2);
        }

        private static void ConfigureWaitingHead(GameObject spectator)
        {
            if (spectator == null) return;
            NetworkAvatar.CreateTrackingSpace(null, spectator.transform);
            spectator.transform.localPosition = Vector3.zero;
            spectator.transform.rotation = Quaternion.identity;
            var driver = spectator.AddComponent<UnityEngine.InputSystem.XR.TrackedPoseDriver>();
            driver.positionInput = new UnityEngine.InputSystem.InputActionProperty(new UnityEngine.InputSystem.InputAction(
                "Waiting Head Position", UnityEngine.InputSystem.InputActionType.Value, "<XRHMD>/centerEyePosition"));
            driver.rotationInput = new UnityEngine.InputSystem.InputActionProperty(new UnityEngine.InputSystem.InputAction(
                "Waiting Head Rotation", UnityEngine.InputSystem.InputActionType.Value, "<XRHMD>/centerEyeRotation"));
            driver.ignoreTrackingState = true;
            WaitingStatusPanel.Create(spectator.transform);
        }

        private SessionSnapshot latestSnapshot;
        private bool streamReady;
        [Serializable] private sealed class StreamStatus { public string streamId, origin, venueLaunchId; public long acceptedSequence, expectedSequence; public bool @sealed; public int missionClockVersion, roomEnemyPolicyVersion; }
        [Serializable] private sealed class VenueStreamStatus { public string id, state; public StreamStatus combatStream; }
        [Serializable] private sealed class StreamReceipt { public string streamId; public long acceptedSequence; }
        private sealed class ManagementCertificateHandler : CertificateHandler
        {
            private readonly string expected;
            internal ManagementCertificateHandler(string expected) { this.expected = expected; }
            protected override bool ValidateCertificate(byte[] certificateData) => ManagementCertificatePin.Matches(certificateData, expected);
        }
        private void AuthorizeManagement(UnityWebRequest request)
        {
            request.SetRequestHeader("Authorization", "Bearer " + configuration.gameServerKey);
            request.redirectLimit = 0;
            request.timeout = 5;
            if (!string.IsNullOrEmpty(configuration.managementCertificateSha256))
                request.certificateHandler = new ManagementCertificateHandler(configuration.managementCertificateSha256);
        }
        private UnityWebRequest ManagementPost(string suffix, string body)
        {
            var request = new UnityWebRequest(configuration.managementApiUrl.TrimEnd('/') + "/api/sessions/" + configuration.sessionId + suffix, "POST");
            request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body)); request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json"); AuthorizeManagement(request);
            return request;
        }
        private IEnumerator OpenTelemetry()
        {
            if (!string.IsNullOrEmpty(configuration.venueLaunchId))
            {
                yield return AwaitVenueStream();
                yield break;
            }
            var expected = configuration.expectedSequence;
            var route = expected > 0 ? "/combat-stream/guarded-open" : "/combat-stream";
            var body = "{\"streamId\":\"" + outbox.StreamId.ToString("D") + "\",\"origin\":\"" + outbox.Origin
                + "\",\"missionClockVersion\":1,\"roomEnemyPolicyVersion\":1";
            if (expected > 0) body += ",\"expectedSequence\":" + expected.ToString(System.Globalization.CultureInfo.InvariantCulture);
            using (var request = ManagementPost(route, body + "}"))
            {
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success)
                {
                    if (expected > 0)
                    {
                        Debug.Log(request.responseCode == 409 ? "VR_GUARDED_SOURCE_OPEN status=conflict" : "VR_GUARDED_SOURCE_OPEN status=failed");
                        if (!Application.isEditor) Application.Quit(2);
                    }
                    yield break;
                }
                StreamStatus response = null; try { response = JsonUtility.FromJson<StreamStatus>(request.downloadHandler.text); } catch (Exception) { }
                streamReady = MatchesStream(response);
                if (expected > 0 && !streamReady)
                {
                    Debug.Log("VR_GUARDED_SOURCE_OPEN status=failed");
                    if (!Application.isEditor) Application.Quit(2);
                }
            }
        }

        private IEnumerator AwaitVenueStream()
        {
            Debug.Log("VR_VENUE_STREAM_CANDIDATE stream=" + outbox.StreamId.ToString("D"));
            var deadline = Time.realtimeSinceStartupAsDouble + 90;
            while (Time.realtimeSinceStartupAsDouble < deadline)
            {
                using (var request = UnityWebRequest.Get(configuration.managementApiUrl.TrimEnd('/') + "/api/sessions/" + configuration.sessionId))
                {
                    AuthorizeManagement(request);
                    yield return request.SendWebRequest();
                    if (request.result == UnityWebRequest.Result.Success)
                    {
                        VenueStreamStatus response = null;
                        try { response = JsonUtility.FromJson<VenueStreamStatus>(request.downloadHandler.text); } catch (Exception) { }
                        if (response == null || response.id != configuration.sessionId || response.state != "Preparing") break;
                        if (!string.IsNullOrEmpty(response.combatStream?.streamId))
                        {
                            streamReady = MatchesStream(response.combatStream);
                            if (streamReady) yield break;
                            break;
                        }
                    }
                }
                yield return new WaitForSecondsRealtime(.25f);
            }
            Debug.Log("VR_GUARDED_SOURCE_OPEN status=failed");
            if (!Application.isEditor) Application.Quit(2);
        }

        private bool MatchesStream(StreamStatus response) =>
            response != null && Guid.TryParse(response.streamId, out var id) && id == outbox.StreamId && response.origin == outbox.Origin
            && response.acceptedSequence == 0 && !response.@sealed && response.missionClockVersion == 1 && response.roomEnemyPolicyVersion == 1
            && (configuration.expectedSequence == 0 || response.expectedSequence == configuration.expectedSequence)
            && (string.IsNullOrEmpty(configuration.venueLaunchId) || response.venueLaunchId == configuration.venueLaunchId);
        private IEnumerator DeliverTelemetry()
        {
            while (outbox != null && !outbox.Sealed)
            {
                var batch = outbox.PendingBatch();
                if (batch.Length == 0 && !outbox.Complete) { yield return new WaitForSecondsRealtime(.2f); continue; }
                var body = batch.Length != 0 ? TelemetryOutbox.BatchJson(batch) : "{\"streamId\":\"" + outbox.StreamId.ToString("D") + "\",\"finalSequence\":" + outbox.LastSequence.ToString(System.Globalization.CultureInfo.InvariantCulture) + "}";
                using (var request = ManagementPost(batch.Length != 0 ? "/combat-stream/batch" : "/combat-stream/seal", body))
                {
                    yield return request.SendWebRequest();
                    if (request.responseCode >= 400 && request.responseCode < 500)
                    { status = "TELEMETRY REJECTED - RECOVER JOURNAL"; combatAuthority.TelemetryFault(); yield break; }
                    if (request.result == UnityWebRequest.Result.Success)
                    {
                        var valid = true;
                        try
                        {
                            if (batch.Length != 0)
                            {
                                var receipt = JsonUtility.FromJson<StreamReceipt>(request.downloadHandler.text);
                                if (!Guid.TryParse(receipt.streamId, out var id) || id != outbox.StreamId || receipt.acceptedSequence < batch[batch.Length - 1].StreamSequence) throw new InvalidOperationException("Invalid receipt.");
                                outbox.AcknowledgeThrough(batch[batch.Length - 1].StreamSequence, batch[batch.Length - 1].ReportId);
                            }
                            else
                            {
                                var receipt = JsonUtility.FromJson<StreamStatus>(request.downloadHandler.text);
                                if (!Guid.TryParse(receipt.streamId, out var id) || id != outbox.StreamId || !receipt.@sealed || receipt.acceptedSequence != outbox.LastSequence) throw new InvalidOperationException("Invalid seal.");
                                outbox.MarkSealed();
                            }
                        }
                        catch (Exception) { status = "TELEMETRY RECEIPT OR DISK ERROR"; combatAuthority.TelemetryFault(); valid = false; }
                        if (!valid) yield break;
                    }
                }
                yield return new WaitForSecondsRealtime(.2f);
            }
        }
        private bool refreshingManagement;
        private string lastRefreshFailure;
        private long lastRefreshStatus;

        private void RecordRefreshFailure(string reason, long httpStatus, double started)
        {
            if (reason == lastRefreshFailure && httpStatus == lastRefreshStatus) return;
            lastRefreshFailure = reason;
            lastRefreshStatus = httpStatus;
            var now = Time.realtimeSinceStartupAsDouble;
            Debug.LogWarning(FormattableString.Invariant(
                $"VR_MANAGEMENT_REFRESH_FAILED reason={reason} httpStatus={httpStatus} elapsedSeconds={now - started:F3} monotonicSeconds={now:F3}"));
        }

        private IEnumerator RefreshManagement()
        {
            if (refreshingManagement) { while (refreshingManagement) yield return null; yield break; }
            refreshingManagement = true;
            try { yield return RefreshManagementCore(); }
            finally { refreshingManagement = false; }
        }
        private IEnumerator RefreshManagementCore()
        {
            using (var request = UnityWebRequest.Get(configuration.managementApiUrl.TrimEnd('/') + "/api/sessions/" + configuration.sessionId))
            {
                AuthorizeManagement(request);
                var started = Time.realtimeSinceStartupAsDouble;
                yield return request.SendWebRequest();
                managementReady = false;
                if (request.result != UnityWebRequest.Result.Success)
                {
                    RecordRefreshFailure(request.result.ToString(), request.responseCode, started);
                    yield break;
                }
                SessionSnapshot snapshot = null;
                try { snapshot = JsonUtility.FromJson<SessionSnapshot>(request.downloadHandler.text); }
                catch (Exception) { }
                if (snapshot == null || snapshot.id != configuration.sessionId || snapshot.environment == null)
                {
                    RecordRefreshFailure("InvalidSnapshot", request.responseCode, started);
                    yield break;
                }
                if (snapshot.environment.mode == "MR" && (configuration.role != "Server" || configuration.telemetryOrigin != "GameServer"))
                {
                    status = "MR REQUIRES A DEDICATED GAME SERVER";
                    RecordRefreshFailure("UnsupportedMrRole", request.responseCode, started);
                    yield break;
                }
                if (snapshot.environment.mode == "MR" && snapshot.roomAlignment?.Covers(snapshot.roomIds) != true)
                {
                    status = "MR REQUIRES PINNED ROOM ALIGNMENT FILES";
                    RecordRefreshFailure("MissingMrAlignment", request.responseCode, started);
                    Debug.LogError(status);
                    yield break;
                }
                var valid = true;
                try { combatAuthority.ApplyManagement(snapshot); }
                catch (Exception exception) when (exception is ArgumentException || exception is InvalidOperationException || exception is System.IO.IOException)
                { status = "MISSION NOT READY - CHECK SERVER CONSOLE"; Debug.LogError("Mission validation: " + exception.Message); valid = false; }
                if (!valid)
                {
                    RecordRefreshFailure("ApplyRejected", request.responseCode, started);
                    yield break;
                }
                lastRefreshFailure = null;
                latestSnapshot = snapshot;
                managementReady = true;
                if (sceneAuthority.IsSpawned) sceneAuthority.ApplyServerSnapshot(snapshot);
                // Revoke current connections whose admitted roster entry was removed or reassigned.
                foreach (var clientId in new List<ulong>(admitted.Keys))
                {
                    var admission = admitted[clientId];
                    var present = Array.Exists(snapshot.players, player => player.id == admission.playerId
                        && player.roomId == admission.roomId && player.seat == admission.seat && player.admissionId == admission.admissionId);
                    if (present && snapshot.state == "Ended" && outbox != null && combatAuthority.Recording != null)
                    {
                        // Gameplay binding ends now. Only this pre-existing connection may receive its result.
                        admitted.Remove(clientId); combatAuthority.Unbind(clientId);
                        var context = new MissionDebrief { sessionId = snapshot.id, playerId = admission.playerId, admissionId = admission.admissionId,
                            roomId = admission.roomId, origin = outbox.Origin, streamId = outbox.StreamId.ToString("D"), throughSequence = snapshot.sequence,
                            finalStreamSequence = outbox.LastSequence, worldSequence = MissionDebrief.PendingWorldSequence(combatAuthority.RecordingWriter) };
                        ending[clientId] = new EndingClient { Admission = admission, Context = context, Deadline = Time.realtimeSinceStartupAsDouble + 30 };
                        combatAuthority.SendDebrief(clientId, context, false);
                        continue;
                    }
                    if (!present || snapshot.state == "Ended")
                    {
                        if (clientId == NetworkManager.ServerClientId && networkManager.IsHost)
                        { status = "HOST ADMISSION REVOKED"; networkManager.Shutdown(); yield break; }
                        admitted.Remove(clientId); combatAuthority.Unbind(clientId); networkManager.DisconnectClient(clientId);
                    }
                }
                if (ending.Count != 0 && !deliveringDebriefs) StartCoroutine(DeliverDebriefs());
            }
        }

        private IEnumerator DeliverDebriefs()
        {
            deliveringDebriefs = true;
            try
            {
                while (ending.Count != 0 && networkManager.IsListening)
                {
                    foreach (var client in new List<ulong>(ending.Keys))
                        if (ending.TryGetValue(client, out var delivery) && (delivery.Acknowledged || Time.realtimeSinceStartupAsDouble >= delivery.Deadline))
                        {
                            // A host's own ack must not shut down NGO before the other recipients finish.
                            if (client == NetworkManager.ServerClientId && networkManager.IsHost && ending.Count > 1) continue;
                            ending.Remove(client);
                            Debug.Log(delivery.Acknowledged ? "VR_SERVER_DEBRIEF_ACK id=" + client : "VR_SERVER_DEBRIEF_TIMEOUT id=" + client);
                            if (client == NetworkManager.ServerClientId && networkManager.IsHost) { networkManager.Shutdown(); yield break; }
                            networkManager.DisconnectClient(client);
                        }
                    if (ending.Count == 0) yield break;
                    var unsent = false;
                    foreach (var delivery in ending.Values) if (delivery.Result == null) { unsent = true; break; }
                    if (unsent && outbox.Sealed && combatAuthority.Recording.Sealed)
                    {
                        using (var request = UnityWebRequest.Get(configuration.managementApiUrl.TrimEnd('/') + "/api/sessions/" + configuration.sessionId + "/statistics"))
                        {
                            AuthorizeManagement(request);
                            yield return request.SendWebRequest();
                            DebriefStatistics statistics = null;
                            if (request.result == UnityWebRequest.Result.Success)
                                try { statistics = JsonUtility.FromJson<DebriefStatistics>(request.downloadHandler.text); } catch (ArgumentException) { }
                            if (statistics != null)
                                foreach (var client in new List<ulong>(ending.Keys))
                                    if (ending.TryGetValue(client, out var delivery) && delivery.Result == null && Time.realtimeSinceStartupAsDouble < delivery.Deadline)
                                    {
                                        if (!delivery.Context.MatchesSealedWorld(combatAuthority.Recording)) continue;
                                        var result = statistics.Select(delivery.Admission, delivery.Context);
                                        if (result == null) continue;
                                        delivery.Result = result; combatAuthority.SendDebrief(client, result, true);
                                    }
                        }
                    }
                    yield return new WaitForSecondsRealtime(.25f);
                }
            }
            finally { deliveringDebriefs = false; }
        }
        public void AcknowledgeDebrief(ulong client, string sessionId, string playerId, string admissionId)
        {
            if (!ending.TryGetValue(client, out var delivery) || delivery.Acknowledged || delivery.Result == null
                || delivery.Result.sessionId != sessionId || delivery.Result.playerId != playerId || delivery.Result.admissionId != admissionId) return;
            delivery.Acknowledged = true;
            pendingDebriefReceipts.Add(new DebriefReceiptAdmission { playerId = playerId, admissionId = admissionId, roomId = delivery.Result.roomId });
            if (!publishingDebriefReceipts) StartCoroutine(PublishDebriefReceipts(delivery.Result));
        }

        private IEnumerator PublishDebriefReceipts(MissionDebrief boundary)
        {
            publishingDebriefReceipts = true;
            var deadline = Time.realtimeSinceStartupAsDouble + 15;
            try
            {
                while (pendingDebriefReceipts.Count != 0 && Time.realtimeSinceStartupAsDouble < deadline)
                {
                    yield return new WaitForSecondsRealtime(.25f);
                    var batch = new DebriefReceiptBatch { streamId = boundary.streamId, throughSequence = boundary.throughSequence,
                        finalStreamSequence = boundary.finalStreamSequence, worldSequence = boundary.worldSequence,
                        players = pendingDebriefReceipts.ToArray() };
                    using (var request = ManagementPost("/debrief-receipts", JsonUtility.ToJson(batch)))
                    {
                        request.timeout = 3;
                        yield return request.SendWebRequest();
                        if (request.responseCode == 204)
                            pendingDebriefReceipts.RemoveRange(0, batch.players.Length);
                        else if (request.responseCode >= 400 && request.responseCode < 500 && request.responseCode != 429)
                            break;
                    }
                }
            }
            finally
            {
                if (pendingDebriefReceipts.Count != 0) Debug.LogWarning("VR_SERVER_DEBRIEF_RECEIPTS_UNCONFIRMED count=" + pendingDebriefReceipts.Count);
                pendingDebriefReceipts.Clear();
                publishingDebriefReceipts = false;
            }
        }
        public bool ReceiveDebrief(MissionDebrief value, bool final)
        {
            if (networkManager == null || !networkManager.IsClient) return false;
            if (final)
            {
                if (!Debrief.Accept(value)) return false;
                Debug.Log("VR_CLIENT_DEBRIEF_FINAL " + JsonUtility.ToJson(value)); return true;
            }
            var avatar = networkManager.LocalClient?.PlayerObject?.GetComponent<NetworkAvatar>();
            if (avatar == null || !Debrief.Begin(value, avatar.PlayerId.Value.ToString())) return false;
            Debug.Log("VR_CLIENT_DEBRIEF_PENDING " + value.sessionId); return true;
        }

        private void ApproveConnection(NetworkManager.ConnectionApprovalRequest request, NetworkManager.ConnectionApprovalResponse response)
        {
            Debug.Log("VR_SERVER_CLIENT_PENDING id=" + request.ClientNetworkId);
            if (request.ClientNetworkId == NetworkManager.ServerClientId && configuration.role == "Host")
            {
                if (admitted.TryGetValue(request.ClientNetworkId, out var host))
                {
                    response.Approved = true; response.CreatePlayerObject = true;
                    response.Position = RoomOrigin(host.roomId) + new Vector3((host.seat - 2) * 1.5f, 0, -3);
                    response.Rotation = Quaternion.identity;
                }
                else Reject(response);
                return;
            }
            response.Pending = true;
            StartCoroutine(ValidateAdmission(request.ClientNetworkId, request.Payload, response));
        }

        private IEnumerator ValidateAdmission(ulong clientId, byte[] payload, NetworkManager.ConnectionApprovalResponse response, bool preflight = false)
        {
            if (!managementReady || !ArenaConnectionProfile.TryDecode(payload, out var ticket, out var requestedRoom, out var requestedHash))
            {
                Reject(response);
                yield break;
            }
            var body = JsonUtility.ToJson(new TicketValidationRequest { sessionId = configuration.sessionId, ticket = ticket });
            using (var request = new UnityWebRequest(configuration.managementApiUrl.TrimEnd('/') + "/api/player-tickets/validate", "POST"))
            {
                request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body));
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");
                AuthorizeManagement(request);
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success || (!preflight && (!networkManager.IsListening || !networkManager.PendingClients.ContainsKey(clientId))))
                { Reject(response); yield break; }
                TicketApproval approval = null;
                try { approval = JsonUtility.FromJson<TicketApproval>(request.downloadHandler.text); }
                catch (Exception) { }
                if (approval == null || approval.sessionId != configuration.sessionId || !Guid.TryParse(approval.playerId, out _)
                    || !Guid.TryParse(approval.admissionId, out var epoch) || epoch == Guid.Empty || approval.throughSequence < 1
                    || approval.roomId < 1 || approval.roomId > 5 || approval.seat < 0 || approval.seat > 4)
                { Reject(response); yield break; }
                // Observe at least the roster revision validated by the API before binding the transport.
                yield return RefreshManagement();
                if (managementReady && latestSnapshot.sequence < approval.throughSequence) yield return RefreshManagement();
                if (!managementReady || latestSnapshot.sequence < approval.throughSequence || latestSnapshot.state == "Ended"
                    || !DateTimeOffset.TryParse(approval.expiresAtUtc, System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, out var expires)
                    || expires <= DateTimeOffset.UtcNow
                    || (!preflight && (!networkManager.IsListening || !networkManager.PendingClients.ContainsKey(clientId)))
                    || !Array.Exists(latestSnapshot.players, player => player.id == approval.playerId && player.admissionId == approval.admissionId
                        && player.roomId == approval.roomId && player.seat == approval.seat
                        && ArenaConnectionProfile.Matches(latestSnapshot.environment.mode == "MR", requestedRoom, approval.roomId,
                            player.headset, requestedHash, latestSnapshot.roomAlignment?.ForRoom(approval.roomId)))
                    || admitted.Count >= 25)
                { Reject(response); yield break; }
                foreach (var existing in admitted.Values)
                    if (existing.playerId == approval.playerId) { Reject(response); yield break; }
                if (!combatAuthority.Bind(clientId, approval)) { Reject(response); yield break; }
                admitted[clientId] = approval;
                Debug.Log("VR_SERVER_ADMISSION_APPROVED id=" + clientId);
                response.Approved = true;
                response.CreatePlayerObject = true;
                response.Position = RoomOrigin(approval.roomId) + new Vector3((approval.seat - 2) * 1.5f, 0, -3);
                response.Rotation = Quaternion.identity;
                response.Pending = false;
            }
        }

        private static void Reject(NetworkManager.ConnectionApprovalResponse response)
        {
            Debug.Log("VR_SERVER_ADMISSION_REJECTED");
            response.Approved = false;
            response.Reason = "Admission rejected. Please contact the control desk.";
            response.Pending = false;
        }

        public TicketApproval Admission(ulong clientId) => admitted.TryGetValue(clientId, out var identity) ? identity : null;
        public static Vector3 RoomOrigin(int roomId) => new Vector3((roomId - 3) * 14, 0, 0);
        private void ServerStopped(bool wasHost) { Debug.Log("VR_SERVER_STOPPED host=" + wasHost); }
        private void TransportFailed() { Debug.LogError("VR_TRANSPORT_FAILED"); }
        private void Connected(ulong clientId)
        {
            if (clientId == networkManager.LocalClientId) { status = "CONNECTED"; Debug.Log("VR_CLIENT_CONNECTED id=" + clientId); }
            if (peerDiagnostics && clientId != NetworkManager.ServerClientId && admitted.ContainsKey(clientId))
                ObservePeer(clientId);
        }
        private void ObservePeer(ulong clientId)
        {
            if (peerObservations > MaximumPeerObservations) return;
            if (peerObservations++ == MaximumPeerObservations)
            {
                Debug.Log("VR_SERVER_PEER_LIMIT");
                return;
            }
            var transport = (UnityTransport)networkManager.NetworkConfig.NetworkTransport;
            var endpoint = transport.GetEndpoint(clientId);
            var available = (endpoint.Family == NetworkFamily.Ipv4 || endpoint.Family == NetworkFamily.Ipv6) && endpoint.Port != 0;
            Debug.Log("VR_SERVER_PEER id=" + clientId + " endpoint=" + (available ? endpoint.ToString() : "unavailable"));
        }
        private void Disconnected(ulong clientId)
        {
            linkDiagnostics?.Disconnected(clientId);
            if (configuration != null && configuration.IsServer) Debug.Log("VR_SERVER_CLIENT_LEFT id=" + clientId);
            combatAuthority?.Unbind(clientId);
            admitted.Remove(clientId);
            ending.Remove(clientId);
            if (clientId == networkManager.LocalClientId)
            {
                Debug.Log(networkManager.DisconnectReason == "Admission rejected. Please contact the control desk."
                    ? "VR_CLIENT_ADMISSION_REJECTED" : "VR_CLIENT_DISCONNECTED");
                status = "DISCONNECTED - CONTACT CONTROL DESK";
                var cameras = Resources.FindObjectsOfTypeAll<Camera>();
                foreach (var camera in cameras)
                    if (camera.gameObject.scene.IsValid() && camera.name == "Desktop Spectator") camera.gameObject.SetActive(true);
            }
        }
        private void ReconnectClient()
        {
            if (!CanReconnect) return;
            nextReconnect = Time.unscaledTime + 2;
            try
            {
                var fresh = LaunchConfiguration.Load();
                if (fresh.role != "Client") throw new InvalidOperationException("A client reconnect cannot change server roles.");
                var transport = (UnityTransport)networkManager.NetworkConfig.NetworkTransport;
                transport.SetConnectionData(fresh.address, fresh.port);
                networkManager.NetworkConfig.ConnectionData = fresh.AdmissionPayload();
                configuration = fresh; status = "CONNECTING"; Debrief.Clear();
                if (!networkManager.StartClient()) status = "RECONNECT FAILED - CONTACT CONTROL DESK";
                else linkDiagnostics?.Attach();
            }
            catch (Exception) { status = "CONNECTION FILE INVALID - CONTACT CONTROL DESK"; }
        }
        private void Update()
        {
            linkDiagnostics?.Update();
            if (reconnectInput?.Poll(CanReconnect, TrackedInputFocus.Available(applicationPaused)) == true) ReconnectClient();
        }
        private void OnApplicationFocus(bool focused) { if (!focused) reconnectInput?.Reset(); }
        private void OnApplicationPause(bool paused)
        {
            applicationPaused = paused;
            if (paused) reconnectInput?.Reset();
        }
        private void OnDisable() { reconnectInput?.Reset(); }
        private void OnDestroy()
        {
            linkDiagnostics?.Finish("Shutdown");
            reconnectInput?.Dispose(); reconnectInput = null;
            if (desktopXrManager != null && desktopXrManager.isInitializationComplete) desktopXrManager.DeinitializeLoader();
            if (worldDelivery != null) worldDelivery.StopAndDispose();
            else if (combatAuthority?.RecordingWriter != null)
            {
                var writer = combatAuthority.RecordingWriter; var source = combatAuthority.Recording;
                writer.Stop(); writer.Completion.ContinueWith(_ => { try { source?.Dispose(); } finally { writer.Dispose(); } }, System.Threading.Tasks.TaskScheduler.Default);
            }
            else combatAuthority?.Recording?.Dispose();
            outbox?.Dispose();
            if (networkManager != null)
            {
                networkManager.OnClientDisconnectCallback -= Disconnected;
                networkManager.OnClientConnectedCallback -= Connected;
                networkManager.OnServerStopped -= ServerStopped;
                networkManager.OnTransportFailure -= TransportFailed;
            }
            if (Instance == this) Instance = null;
        }
        private void OnGUI()
        {
            if (Application.platform == RuntimePlatform.Android || DesktopOpenXRActive) return;
            if (Debrief.Active)
            {
                var width = Mathf.Min(820, Screen.width - 32); var height = 280;
                var area = new Rect((Screen.width - width) / 2, (Screen.height - height) / 2, width, height);
                GUI.Box(area, "AFTER ACTION REPORT");
                GUI.Label(new Rect(area.x + 24, area.y + 34, area.width - 48, height - 52), PlayerStatus,
                    new GUIStyle(GUI.skin.label) { fontSize = 22, wordWrap = true, richText = false });
                if (CanReconnect && GUI.Button(new Rect(area.x, area.yMax + 12, 300, 42), "Reconnect / reload player ticket")) ReconnectClient();
                return;
            }
            if (networkManager != null && networkManager.IsConnectedClient && networkManager.LocalClient.PlayerObject != null) return;
            GUI.Box(new Rect(12, 12, 430, 58), "VR COMMAND - QUEST 3 VERTICAL SLICE");
            GUI.Label(new Rect(24, 40, 410, 24), Status + " / " + State);
            if (CanReconnect && GUI.Button(new Rect(12, 82, 300, 42), "Reconnect / reload player ticket")) ReconnectClient();
        }
    }

}
