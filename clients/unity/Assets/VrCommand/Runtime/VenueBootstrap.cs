using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using Unity.Netcode;
using Unity.Netcode.Transports.UTP;
using Unity.Networking.Transport;
using UnityEngine;
using UnityEngine.Networking;
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
        private VenueLinkDiagnostics linkDiagnostics;
        private const int MaximumPeerObservations = 256;
        private bool peerDiagnostics;
        private int peerObservations;
        public bool CanReconnect => networkManager != null && ClientReconnectInput.CanOffer(configuration?.role,
            networkManager.IsListening, networkManager.ShutdownInProgress, Time.unscaledTime, nextReconnect);
        public string ReconnectHint => reconnectInput != null && CanReconnect ? "\nRELEASE THEN PRESS RIGHT B TO RELOAD PLAYER TICKET" : "";
        private TelemetryOutbox outbox;
        private WorldRecordingDelivery worldDelivery;
        private sealed class EndingClient
        {
            internal TicketApproval Admission;
            internal MissionDebrief Context;
            internal double Deadline;
            internal bool Sent, Acknowledged;
        }
        private readonly Dictionary<ulong, EndingClient> ending = new Dictionary<ulong, EndingClient>();
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
            var spectator = GameObject.Find("Desktop Spectator");
            if (Application.platform == RuntimePlatform.Android && spectator != null)
            {
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
            Application.targetFrameRate = Application.platform == RuntimePlatform.Android ? 72 : 90;
            if (Application.platform != RuntimePlatform.Android) Application.runInBackground = true;
            try { configuration = LaunchConfiguration.Load(); }
            catch (Exception) { status = "PLEASE CONTACT THE CONTROL DESK"; }
            if (configuration == null) yield break;
            peerDiagnostics = configuration.role == "Server" && Application.platform == RuntimePlatform.WindowsPlayer
                && Application.isBatchMode && Array.Exists(Environment.GetCommandLineArgs(), argument => argument == "--vr-peer-diagnostics");
            if (!DesktopClientExercise.Install(gameObject, configuration.role)) { status = "DESKTOP EXERCISE REJECTED"; if (Application.isBatchMode && !Application.isEditor) Application.Quit(2); yield break; }
            if (configuration.role == "Client" && (Application.platform == RuntimePlatform.Android || UnityEngine.XR.XRSettings.isDeviceActive))
                reconnectInput = new ClientReconnectInput();
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
                    else { sceneAuthority.SuspendForManagementLoss(); combatAuthority.Suspend(); }
                    yield return new WaitForSecondsRealtime(0.5f);
                    yield return RefreshManagement();
                    if (!managementReady) { sceneAuthority.SuspendForManagementLoss(); combatAuthority.Suspend(); }
                }
            }
        }

        private SessionSnapshot latestSnapshot;
        private bool streamReady;
        [Serializable] private sealed class StreamStatus { public string streamId; public string origin; public long acceptedSequence; public bool @sealed; public int missionClockVersion; }
        [Serializable] private sealed class StreamReceipt { public string streamId; public long acceptedSequence; }
        private UnityWebRequest TelemetryRequest(string suffix, string body)
        {
            var request = new UnityWebRequest(configuration.managementApiUrl.TrimEnd('/') + "/api/sessions/" + configuration.sessionId + "/combat-stream" + suffix, "POST");
            request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body)); request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json"); request.SetRequestHeader("Authorization", "Bearer " + configuration.gameServerKey); request.timeout = 5;
            return request;
        }
        private IEnumerator OpenTelemetry()
        {
            using (var request = TelemetryRequest("", "{\"streamId\":\"" + outbox.StreamId.ToString("D") + "\",\"origin\":\"" + outbox.Origin + "\",\"missionClockVersion\":1}"))
            {
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success) yield break;
                StreamStatus response = null; try { response = JsonUtility.FromJson<StreamStatus>(request.downloadHandler.text); } catch (Exception) { }
                streamReady = response != null && Guid.TryParse(response.streamId, out var id) && id == outbox.StreamId && response.origin == outbox.Origin
                    && response.acceptedSequence == 0 && !response.@sealed && response.missionClockVersion == 1;
            }
        }
        private IEnumerator DeliverTelemetry()
        {
            while (outbox != null && !outbox.Sealed)
            {
                var batch = outbox.PendingBatch();
                if (batch.Length == 0 && !outbox.Complete) { yield return new WaitForSecondsRealtime(.2f); continue; }
                var body = batch.Length != 0 ? TelemetryOutbox.BatchJson(batch) : "{\"streamId\":\"" + outbox.StreamId.ToString("D") + "\",\"finalSequence\":" + outbox.LastSequence.ToString(System.Globalization.CultureInfo.InvariantCulture) + "}";
                using (var request = TelemetryRequest(batch.Length != 0 ? "/batch" : "/seal", body))
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
                request.SetRequestHeader("Authorization", "Bearer " + configuration.gameServerKey);
                request.timeout = 5;
                yield return request.SendWebRequest();
                managementReady = false;
                if (request.result != UnityWebRequest.Result.Success) yield break;
                SessionSnapshot snapshot = null;
                try { snapshot = JsonUtility.FromJson<SessionSnapshot>(request.downloadHandler.text); }
                catch (Exception) { }
                if (snapshot == null || snapshot.id != configuration.sessionId || snapshot.environment == null) yield break;
                if (snapshot.environment.mode == "MR" && (configuration.role != "Server" || configuration.telemetryOrigin != "GameServer"))
                {
                    status = "MR REQUIRES A DEDICATED GAME SERVER";
                    yield break;
                }
                if (snapshot.environment.mode == "MR" && snapshot.roomAlignment?.Covers(snapshot.roomIds) != true)
                {
                    status = "MR REQUIRES PINNED ROOM ALIGNMENT FILES";
                    Debug.LogError(status);
                    yield break;
                }
                var valid = true;
                try { combatAuthority.ApplyManagement(snapshot); }
                catch (Exception exception) when (exception is ArgumentException || exception is InvalidOperationException || exception is System.IO.IOException)
                { status = "MISSION NOT READY - CHECK SERVER CONSOLE"; Debug.LogError("Mission validation: " + exception.Message); valid = false; }
                if (!valid) yield break;
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
                    foreach (var delivery in ending.Values) if (!delivery.Sent) { unsent = true; break; }
                    if (unsent && outbox.Sealed && combatAuthority.Recording.Sealed)
                    {
                        using (var request = UnityWebRequest.Get(configuration.managementApiUrl.TrimEnd('/') + "/api/sessions/" + configuration.sessionId + "/statistics"))
                        {
                            request.SetRequestHeader("Authorization", "Bearer " + configuration.gameServerKey); request.timeout = 5;
                            yield return request.SendWebRequest();
                            DebriefStatistics statistics = null;
                            if (request.result == UnityWebRequest.Result.Success)
                                try { statistics = JsonUtility.FromJson<DebriefStatistics>(request.downloadHandler.text); } catch (ArgumentException) { }
                            if (statistics != null)
                                foreach (var client in new List<ulong>(ending.Keys))
                                    if (ending.TryGetValue(client, out var delivery) && !delivery.Sent && Time.realtimeSinceStartupAsDouble < delivery.Deadline)
                                    {
                                        if (!delivery.Context.MatchesSealedWorld(combatAuthority.Recording)) continue;
                                        var result = statistics.Select(delivery.Admission, delivery.Context);
                                        if (result == null) continue;
                                        delivery.Sent = true; combatAuthority.SendDebrief(client, result, true);
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
            if (ending.TryGetValue(client, out var delivery) && delivery.Sent && delivery.Context.sessionId == sessionId
                && delivery.Admission.playerId == playerId && delivery.Admission.admissionId == admissionId) delivery.Acknowledged = true;
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
                request.SetRequestHeader("Authorization", "Bearer " + configuration.gameServerKey);
                request.timeout = 5;
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
            if (reconnectInput?.Poll(CanReconnect, Application.isFocused) == true) ReconnectClient();
        }
        private void OnApplicationFocus(bool focused) { if (!focused) reconnectInput?.Reset(); }
        private void OnApplicationPause(bool paused) { if (paused) reconnectInput?.Reset(); }
        private void OnDisable() { reconnectInput?.Reset(); }
        private void OnDestroy()
        {
            linkDiagnostics?.Finish("Shutdown");
            reconnectInput?.Dispose(); reconnectInput = null;
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
            if (Application.platform == RuntimePlatform.Android) return;
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
