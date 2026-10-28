using Unity.Collections;
using Unity.Netcode;
using UnityEngine;
using SessionSnapshot = VrCommand.Simulation.ManagementSnapshot;

namespace VrCommand.Unity
{
    public sealed class SceneAuthority : NetworkBehaviour
    {
        public NetworkVariable<FixedString32Bytes> Phase = new NetworkVariable<FixedString32Bytes>("Preparing");
        public NetworkVariable<FixedString32Bytes> Weather = new NetworkVariable<FixedString32Bytes>("Clear");
        public NetworkVariable<bool> Night = new NetworkVariable<bool>(false);
        public NetworkVariable<bool> Lightning = new NetworkVariable<bool>(false);
        public Light sun;

        public void ApplyServerSnapshot(SessionSnapshot snapshot)
        {
            if (!IsServer || !IsSpawned || snapshot == null) return;
            Phase.Value = snapshot.state;
            Weather.Value = snapshot.environment.weather;
            Night.Value = snapshot.environment.timeOfDay == "Night";
            Lightning.Value = snapshot.environment.lightning;
        }
        public void SuspendForManagementLoss()
        {
            if (IsServer && IsSpawned) Phase.Value = "Paused";
        }
        private void Update()
        {
            if (!IsSpawned) return;
            RenderSettings.fog = Weather.Value.ToString() != "Clear";
            RenderSettings.fogColor = Night.Value ? new Color(0.06f, 0.08f, 0.1f) : new Color(0.34f, 0.39f, 0.42f);
            RenderSettings.fogDensity = Weather.Value.ToString() == "Fog" ? 0.035f : 0.012f;
            RenderSettings.ambientLight = Night.Value ? new Color(0.12f, 0.15f, 0.2f) : new Color(0.55f, 0.57f, 0.53f);
            var flash = Lightning.Value && NetworkManager.ServerTime.Time % 7 < 0.12;
            if (sun != null) sun.intensity = flash ? 2.5f : Night.Value ? 0.08f : 1.15f;
        }
    }
}
