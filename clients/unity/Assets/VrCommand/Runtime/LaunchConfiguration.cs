using System;
using System.IO;
using UnityEngine;

namespace VrCommand.Unity
{
    [Serializable]
    public sealed class LaunchConfiguration
    {
        public string role = "Client";
        public string address = "127.0.0.1";
        public ushort port = 7777;
        public string joinTicket = "";
        public string sessionId = "";
        public string managementApiUrl = "http://127.0.0.1:5080";
        public string gameServerKey = "";

        public bool IsServer => role == "Server" || role == "Host";

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
            if (config.role != "Server" && string.IsNullOrWhiteSpace(config.joinTicket))
                throw new InvalidOperationException("Player admission ticket is missing.");
            return config;
        }
    }

    [Serializable] public sealed class SessionSnapshot
    {
        public string id;
        public string state;
        public MissionSnapshot mission;
        public EnvironmentSnapshot environment;
    }
    [Serializable] public sealed class MissionSnapshot { public MissionDefinition definition; }
    [Serializable] public sealed class MissionDefinition { public string name; }
    [Serializable] public sealed class EnvironmentSnapshot
    {
        public string mode;
        public string weather;
        public string timeOfDay;
        public bool lightning;
    }
    [Serializable] public sealed class TicketValidationRequest { public string sessionId; public string ticket; }
    [Serializable] public sealed class TicketApproval
    {
        public string sessionId;
        public string playerId;
        public int roomId;
        public int seat;
    }
}
