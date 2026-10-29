using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using Unity.Netcode;
using Unity.Netcode.Transports.UTP;
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
        private string status = "WAITING FOR CONTROL DESK";
        private bool managementReady;
        private TelemetryOutbox outbox;
        private WorldRecordingDelivery worldDelivery;
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
            try { configuration = LaunchConfiguration.Load(); }
            catch (Exception) { status = "PLEASE CONTACT THE CONTROL DESK"; }
            if (configuration == null) yield break;
            var transport = (UnityTransport)networkManager.NetworkConfig.NetworkTransport;
            transport.SetConnectionData(configuration.address, configuration.port, configuration.IsServer ? "0.0.0.0" : null);
            networkManager.OnClientDisconnectCallback += Disconnected;
            networkManager.OnClientConnectedCallback += Connected;
            networkManager.NetworkConfig.ConnectionApproval = true;
            networkManager.NetworkConfig.ClientConnectionBufferTimeout = 20;
            if (configuration.IsServer)
            {
                networkManager.ConnectionApprovalCallback = ApproveConnection;
                yield return RefreshManagement();
                if (!managementReady) { status = "CONTROL DESK CONNECTION FAILED"; yield break; }
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
                worldDelivery.Initialize(combatAuthority.Recording, outbox, configuration, message => { status = message; combatAuthority.TelemetryFault(); });
                if (configuration.role == "Host")
                {
                    // NGO 2.7 ignores asynchronous host approval; validate before StartHost and answer it synchronously.
                    var hostApproval = new NetworkManager.ConnectionApprovalResponse();
                    yield return ValidateAdmission(NetworkManager.ServerClientId, Encoding.UTF8.GetBytes(configuration.joinTicket), hostApproval, true);
                    if (!hostApproval.Approved) { status = "HOST ADMISSION FAILED"; yield break; }
                }
            }
            if (configuration.role != "Server")
                networkManager.NetworkConfig.ConnectionData = Encoding.UTF8.GetBytes(configuration.joinTicket);
            status = "CONNECTING";
            var started = configuration.role == "Server" ? networkManager.StartServer()
                : configuration.role == "Host" ? networkManager.StartHost() : networkManager.StartClient();
            if (!started) { status = "CONNECTION FAILED"; yield break; }
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
        [Serializable] private sealed class StreamStatus { public string streamId; public string origin; public long acceptedSequence; public bool @sealed; }
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
            using (var request = TelemetryRequest("", "{\"streamId\":\"" + outbox.StreamId.ToString("D") + "\",\"origin\":\"" + outbox.Origin + "\"}"))
            {
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success) yield break;
                StreamStatus response = null; try { response = JsonUtility.FromJson<StreamStatus>(request.downloadHandler.text); } catch (Exception) { }
                streamReady = response != null && Guid.TryParse(response.streamId, out var id) && id == outbox.StreamId && response.origin == outbox.Origin
                    && response.acceptedSequence == 0 && !response.@sealed;
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
                    var present = snapshot.state != "Ended" && Array.Exists(snapshot.players, player => player.id == admission.playerId
                        && player.roomId == admission.roomId && player.seat == admission.seat && player.admissionId == admission.admissionId);
                    if (!present)
                    {
                        if (clientId == NetworkManager.ServerClientId && networkManager.IsHost)
                        { status = "HOST ADMISSION REVOKED"; networkManager.Shutdown(); yield break; }
                        admitted.Remove(clientId); combatAuthority.Unbind(clientId); networkManager.DisconnectClient(clientId);
                    }
                }
            }
        }

        private void ApproveConnection(NetworkManager.ConnectionApprovalRequest request, NetworkManager.ConnectionApprovalResponse response)
        {
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
            if (!managementReady || payload == null || payload.Length == 0 || payload.Length > 256)
            {
                Reject(response);
                yield break;
            }
            var body = JsonUtility.ToJson(new TicketValidationRequest { sessionId = configuration.sessionId, ticket = Encoding.UTF8.GetString(payload) });
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
                        && player.roomId == approval.roomId && player.seat == approval.seat) || admitted.Count >= 25)
                { Reject(response); yield break; }
                foreach (var existing in admitted.Values)
                    if (existing.playerId == approval.playerId) { Reject(response); yield break; }
                if (!combatAuthority.Bind(clientId, approval)) { Reject(response); yield break; }
                admitted[clientId] = approval;
                response.Approved = true;
                response.CreatePlayerObject = true;
                response.Position = RoomOrigin(approval.roomId) + new Vector3((approval.seat - 2) * 1.5f, 0, -3);
                response.Rotation = Quaternion.identity;
                response.Pending = false;
            }
        }

        private static void Reject(NetworkManager.ConnectionApprovalResponse response)
        {
            response.Approved = false;
            response.Reason = "Admission rejected. Please contact the control desk.";
            response.Pending = false;
        }

        public TicketApproval Admission(ulong clientId) => admitted.TryGetValue(clientId, out var identity) ? identity : null;
        public static Vector3 RoomOrigin(int roomId) => new Vector3((roomId - 3) * 14, 0, 0);
        private void Connected(ulong clientId) { if (clientId == networkManager.LocalClientId) status = "CONNECTED"; }
        private void Disconnected(ulong clientId)
        {
            combatAuthority?.Unbind(clientId);
            admitted.Remove(clientId);
            if (clientId == networkManager.LocalClientId)
            {
                status = "DISCONNECTED - CONTACT CONTROL DESK";
                var cameras = Resources.FindObjectsOfTypeAll<Camera>();
                foreach (var camera in cameras)
                    if (camera.gameObject.scene.IsValid() && camera.name == "Desktop Spectator") camera.gameObject.SetActive(true);
            }
        }
        private void OnDestroy()
        {
            if (worldDelivery != null) worldDelivery.StopAndDispose();
            else combatAuthority?.Recording?.Dispose();
            outbox?.Dispose();
            if (networkManager != null)
            {
                networkManager.OnClientDisconnectCallback -= Disconnected;
                networkManager.OnClientConnectedCallback -= Connected;
            }
            if (Instance == this) Instance = null;
        }
        private void OnGUI()
        {
            if (Application.platform == RuntimePlatform.Android) return;
            if (networkManager != null && networkManager.IsConnectedClient && networkManager.LocalClient.PlayerObject != null) return;
            GUI.Box(new Rect(12, 12, 430, 58), "VR COMMAND - QUEST 3 VERTICAL SLICE");
            GUI.Label(new Rect(24, 40, 410, 24), Status + " / " + State);
        }
    }

}
