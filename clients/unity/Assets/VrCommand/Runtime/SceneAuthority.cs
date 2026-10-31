using System;
using System.Collections.Generic;
using Unity.Collections;
using Unity.Netcode;
using UnityEngine;
using SessionSnapshot = VrCommand.Simulation.ManagementSnapshot;

namespace VrCommand.Unity
{
    public struct MissionClockState : INetworkSerializable, IEquatable<MissionClockState>
    {
        public int version, durationSeconds;
        public bool autoEnd;
        public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T:IReaderWriter
        { serializer.SerializeValue(ref version); serializer.SerializeValue(ref durationSeconds); serializer.SerializeValue(ref autoEnd); }
        public bool Equals(MissionClockState other) => version == other.version && durationSeconds == other.durationSeconds && autoEnd == other.autoEnd;
        public bool Valid => version == VrCommand.Simulation.MissionClock.Version && VrCommand.Simulation.MissionClock.ValidDuration(durationSeconds);
        public string Label(long tick) => !Valid || tick < 0 ? "" : autoEnd
            ? "REMAIN " + VrCommand.Simulation.MissionClock.FormatSeconds(VrCommand.Simulation.MissionClock.RemainingSeconds(tick, durationSeconds))
            : "ELAPSED " + VrCommand.Simulation.MissionClock.FormatSeconds(tick / VrCommand.Simulation.MissionClock.TicksPerSecond)
                + " / PLAN " + VrCommand.Simulation.MissionClock.FormatSeconds(durationSeconds);
    }
    public struct WeatherState : INetworkSerializable, IEquatable<WeatherState>
    {
        public long tick;
        public byte weather, phase;
        public bool night, lightning;
        public int rooms;
        public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T : IReaderWriter
        {
            serializer.SerializeValue(ref tick); serializer.SerializeValue(ref weather); serializer.SerializeValue(ref phase);
            serializer.SerializeValue(ref night); serializer.SerializeValue(ref lightning); serializer.SerializeValue(ref rooms);
        }
        public bool Equals(WeatherState other) => tick == other.tick && weather == other.weather && phase == other.phase && night == other.night && lightning == other.lightning && rooms == other.rooms;
    }
    public sealed class SceneAuthority : NetworkBehaviour
    {
        public NetworkVariable<FixedString32Bytes> Phase = new NetworkVariable<FixedString32Bytes>("Preparing");
        public NetworkVariable<WeatherState> Presentation = new NetworkVariable<WeatherState>();
        public NetworkVariable<MissionClockState> Clock = new NetworkVariable<MissionClockState>();
        public NetworkVariable<BriefingHeader> Briefing = new NetworkVariable<BriefingHeader>();
        public NetworkList<FixedString512Bytes> BriefingParts;
        private bool briefingDirty = true;
        private FixedString512Bytes[] briefingCache = Array.Empty<FixedString512Bytes>();
        private string appliedBriefingName, appliedBriefingText;
        public IReadOnlyList<FixedString512Bytes> ReadBriefingParts()
        {
            if (briefingDirty)
            {
                if (BriefingParts.Count > MissionBriefingText.MaximumChunks) { briefingCache = Array.Empty<FixedString512Bytes>(); briefingDirty = false; return briefingCache; }
                briefingCache = new FixedString512Bytes[BriefingParts.Count];
                for (var i = 0; i < briefingCache.Length; i++) briefingCache[i] = BriefingParts[i];
                briefingDirty = false;
            }
            return briefingCache;
        }
        private void Awake() { BriefingParts = new NetworkList<FixedString512Bytes>(); }
        private void BriefingChanged(BriefingHeader before, BriefingHeader after) { briefingDirty = true; }
        private void PartsChanged(NetworkListEvent<FixedString512Bytes> change) { briefingDirty = true; }
        public bool ClockDue => IsSpawned && Clock.Value.Valid && Clock.Value.autoEnd
            && VrCommand.Simulation.MissionClock.Due(Presentation.Value.tick, Clock.Value.durationSeconds);
        public UnityWeatherView environmentView;
        private double observed;
        public bool AudioRunning=>IsSpawned && Presentation.Value.phase==1 && Time.realtimeSinceStartupAsDouble-observed<=1.5;
        private static readonly string[] WeatherNames = { "Clear", "Rain", "Fog", "Storm" }, PhaseNames = { "Preparing", "Running", "Paused", "Ended" };
        public override void OnNetworkSpawn()
        {
            if (environmentView == null) environmentView = GetComponent<UnityWeatherView>();
            observed = Time.realtimeSinceStartupAsDouble; Presentation.OnValueChanged += Changed;
            Briefing.OnValueChanged += BriefingChanged; BriefingParts.OnListChanged += PartsChanged; briefingDirty = true;
        }
        private void Changed(WeatherState before, WeatherState after) { observed = Time.realtimeSinceStartupAsDouble; }
        public void ApplyServerSnapshot(SessionSnapshot snapshot)
        {
            if (!IsServer || !IsSpawned || snapshot == null) return;
            var weather = Array.IndexOf(WeatherNames, snapshot.environment.weather); var phase = Array.IndexOf(PhaseNames, snapshot.state);
            if (weather < 0 || phase < 0) throw new ArgumentException("Unsupported environment state.");
            var value = Presentation.Value; value.weather = (byte)weather; value.phase = (byte)phase;
            value.night = snapshot.environment.timeOfDay == "Night"; value.lightning = snapshot.environment.lightning; value.rooms = 0;
            foreach (var room in snapshot.roomIds) value.rooms |= 1 << (room - 1);
            Phase.Value = snapshot.state; Presentation.Value = value;
            Clock.Value = new MissionClockState { version = 1, durationSeconds = snapshot.mission.definition.durationSeconds,
                autoEnd = snapshot.missionClock?.autoEnd == true };
            var definition = snapshot.mission.definition;
            if (MissionBriefingText.Valid(definition.name, definition.briefing)
                && (appliedBriefingName != definition.name || appliedBriefingText != definition.briefing))
            {
                var header = MissionBriefingText.Pack(definition.name, definition.briefing, out var parts);
                if (!Briefing.Value.Equals(header))
                { BriefingParts.Clear(); foreach (var part in parts) BriefingParts.Add(part); Briefing.Value = header; }
                appliedBriefingName = definition.name; appliedBriefingText = definition.briefing;
            }
        }
        public void PublishTick(long tick, string phase)
        {
            if (!IsServer || !IsSpawned) return;
            var value = Presentation.Value; value.tick = tick; value.phase = (byte)Array.IndexOf(PhaseNames, phase); Presentation.Value = value;
        }
        public void SuspendForManagementLoss()
        {
            if (!IsServer || !IsSpawned) return;
            Phase.Value = "Paused"; var value = Presentation.Value; value.phase = 2; Presentation.Value = value;
        }
        private void Update()
        {
            if (!IsSpawned || environmentView == null) return;
            var value = Presentation.Value;
            if (value.weather > 3 || value.phase > 3 || value.tick < 0 || value.tick > VrCommand.Simulation.EnvironmentPresentation.MaximumTick) { environmentView.Clear(); return; }
            var phase = value.phase == 1 && Time.realtimeSinceStartupAsDouble - observed > 1.5 ? "Paused" : PhaseNames[value.phase];
            environmentView.Apply(value.tick, WeatherNames[value.weather], value.night, value.lightning, phase, value.rooms);
        }
        public override void OnNetworkDespawn()
        {
            Presentation.OnValueChanged -= Changed; Briefing.OnValueChanged -= BriefingChanged;
            BriefingParts.OnListChanged -= PartsChanged; briefingDirty = true;
            if (environmentView != null) environmentView.Clear();
        }
    }
}
