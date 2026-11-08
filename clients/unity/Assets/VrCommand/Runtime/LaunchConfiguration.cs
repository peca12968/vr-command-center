using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    [Serializable]
    public sealed class LaunchConfiguration
    {
        public string role = "Client";
        public string address = "127.0.0.1";
        public string listenAddress = "";
        public ushort port = 7777;
        public string joinTicket = "";
        public string sessionId = "";
        public string managementApiUrl = "http://127.0.0.1:5080";
        public string gameServerKey = "";
        public string telemetryOrigin = "Simulation";
        public string telemetryDirectory = "";
        public string roomAlignmentSha256 = "";
        public bool questPassthrough;
        public bool requestMixedReality;
        [NonSerialized] internal RoomFloorPlan AlignmentPlan;

        public bool IsServer => role == "Server" || role == "Host";
        internal byte[] AdmissionPayload() => requestMixedReality
            ? ArenaConnectionProfile.Encode(joinTicket, AlignmentPlan.RoomId, roomAlignmentSha256)
            : ArenaConnectionProfile.Encode(joinTicket, 0);
        public string ServerListenAddress
        {
            get
            {
                var value = string.IsNullOrEmpty(listenAddress) ? "0.0.0.0" : listenAddress;
                if (!IPAddress.TryParse(value, out var ip) || ip.AddressFamily != AddressFamily.InterNetwork
                    || ip.ToString() != value || ip.GetAddressBytes()[0] >= 224)
                    throw new InvalidOperationException("Server listen address must be a canonical IPv4 bind address.");
                return value;
            }
        }

        public static LaunchConfiguration Load()
        {
            var path = Path.Combine(Application.persistentDataPath, "vr-connection.json");
            var args = Environment.GetCommandLineArgs();
            for (var i = 0; i < args.Length - 1; i++)
                if (args[i] == "--vr-config") path = Path.GetFullPath(args[i + 1]);
            if (!File.Exists(path)) throw new InvalidOperationException("Connection configuration is missing.");
            var config = JsonUtility.FromJson<LaunchConfiguration>(File.ReadAllText(path));
            if (config == null || (config.role != "Server" && config.role != "Client" && config.role != "Host") || config.port == 0)
                throw new InvalidOperationException("Connection configuration is invalid.");
            if (Application.platform == RuntimePlatform.Android && config.role != "Client")
                throw new InvalidOperationException("Headsets must use client mode.");
            if (config.IsServer && (!Guid.TryParse(config.sessionId, out _) || string.IsNullOrWhiteSpace(config.gameServerKey)))
                throw new InvalidOperationException("Server management configuration is missing.");
            if (config.IsServer)
            {
                _ = config.ServerListenAddress;
                config.sessionId = Guid.Parse(config.sessionId).ToString("D");
                if (string.IsNullOrEmpty(config.telemetryOrigin)) config.telemetryOrigin = "Simulation";
            }
            if (config.IsServer && config.telemetryOrigin != "Simulation" && config.telemetryOrigin != "GameServer")
                throw new InvalidOperationException("Telemetry origin must be explicit.");
            if (config.role != "Server" && string.IsNullOrWhiteSpace(config.joinTicket))
                throw new InvalidOperationException("Player admission ticket is missing.");
            if (!string.IsNullOrEmpty(config.roomAlignmentSha256))
            {
                if (config.role != "Client" || (Application.platform != RuntimePlatform.Android && !UnityEngine.XR.XRSettings.isDeviceActive))
                    throw new InvalidOperationException("Room alignment requires a tracked XR client.");
                config.AlignmentPlan = RoomFloorPlan.Load(Path.GetDirectoryName(path), config.roomAlignmentSha256);
            }
            if (config.questPassthrough && (Application.platform != RuntimePlatform.Android || config.AlignmentPlan == null))
                throw new InvalidOperationException("Quest passthrough requires a checked room alignment file on an Android client.");
            if (config.requestMixedReality && !config.questPassthrough)
                throw new InvalidOperationException("MR admission requires the Quest passthrough profile.");
            return config;
        }
    }

    [Serializable] public sealed class TicketValidationRequest { public string sessionId; public string ticket; public int protocolVersion = 2; }
    [Serializable] public sealed class TicketApproval
    {
        public string sessionId;
        public string playerId;
        public string admissionId;
        public long throughSequence;
        public string expiresAtUtc;
        public int roomId;
        public int seat;
    }
}
