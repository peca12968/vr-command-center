using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using Unity.Netcode;
using Unity.Netcode.Transports.UTP;
using UnityEngine;
using UnityEngine.Networking;

namespace VrCommand.Unity
{
    public sealed class VenueBootstrap : MonoBehaviour
    {
        public NetworkManager networkManager;
        public SceneAuthority sceneAuthority;
        private readonly Dictionary<ulong, TicketApproval> admitted = new Dictionary<ulong, TicketApproval>();
        private LaunchConfiguration configuration;
        private string status = "WAITING FOR CONTROL DESK";
        private bool managementReady;
        public static VenueBootstrap Instance { get; private set; }
        public string State => sceneAuthority != null && sceneAuthority.IsSpawned ? sceneAuthority.Phase.Value.ToString() : "Preparing";
        public string Status => status;

        private IEnumerator Start()
        {
            Instance = this;
            var spectator = GameObject.Find("Desktop Spectator");
            if (Application.platform == RuntimePlatform.Android && spectator != null)
            {
                spectator.transform.position = new Vector3(0, 1.65f, 0);
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
            networkManager.NetworkConfig.ClientConnectionBufferTimeout = 15;
            if (configuration.IsServer)
            {
                networkManager.ConnectionApprovalCallback = ApproveConnection;
                yield return RefreshManagement();
                if (!managementReady) { status = "CONTROL DESK CONNECTION FAILED"; yield break; }
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
                    else sceneAuthority.SuspendForManagementLoss();
                    yield return new WaitForSecondsRealtime(0.5f);
                    yield return RefreshManagement();
                    if (!managementReady) sceneAuthority.SuspendForManagementLoss();
                }
            }
        }

        private SessionSnapshot latestSnapshot;
        private IEnumerator RefreshManagement()
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
                latestSnapshot = snapshot;
                managementReady = true;
            }
        }

        private void ApproveConnection(NetworkManager.ConnectionApprovalRequest request, NetworkManager.ConnectionApprovalResponse response)
        {
            response.Pending = true;
            StartCoroutine(ValidateAdmission(request.ClientNetworkId, request.Payload, response));
        }

        private IEnumerator ValidateAdmission(ulong clientId, byte[] payload, NetworkManager.ConnectionApprovalResponse response)
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
                if (request.result != UnityWebRequest.Result.Success || !networkManager.IsListening)
                { Reject(response); yield break; }
                TicketApproval approval = null;
                try { approval = JsonUtility.FromJson<TicketApproval>(request.downloadHandler.text); }
                catch (Exception) { }
                if (approval == null || approval.sessionId != configuration.sessionId || !Guid.TryParse(approval.playerId, out _)
                    || approval.roomId < 1 || approval.roomId > 5 || approval.seat < 0 || approval.seat > 4 || admitted.Count >= 25)
                { Reject(response); yield break; }
                foreach (var existing in admitted.Values)
                    if (existing.playerId == approval.playerId) { Reject(response); yield break; }
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
            GUI.Box(new Rect(12, 12, 430, 58), "VR COMMAND - QUEST 3 VERTICAL SLICE");
            GUI.Label(new Rect(24, 40, 410, 24), status + " / " + State);
        }
    }

}
