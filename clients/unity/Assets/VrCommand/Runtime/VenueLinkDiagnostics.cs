using System;
using System.Collections.Generic;
using System.IO;
using Unity.Collections;
using Unity.Netcode;
using UnityEngine;

namespace VrCommand.Unity
{
    // Shared by the opt-in client and the bounded, admission-scoped responder.
    internal sealed class VenueLinkDiagnostics
    {
        private const string Request = "vr.link-probe.request.v1", Reply = "vr.link-probe.reply.v1";
        private const int SampleLimit = 30;
        private const double SampleInterval = 1, ReplySeconds = .9, LifetimeSeconds = 240;

        [Serializable] private sealed class Sample
        {
            public uint sequence;
            public long tick;
            public int playerLoopFrames;
            public double windowSeconds, roundTripMilliseconds;
            public string result;
        }

        [Serializable] private sealed class Report
        {
            public int version = 1, processId;
            public ulong connection;
            public bool complete, batchMode, graphicsDeviceActive;
            public string reason;
            public Sample[] samples;
        }

        private readonly VenueBootstrap owner;
        private readonly bool server;
        private readonly string output;
        private readonly LinkProbeConnection client;
        private readonly LinkEchoRateGate replies = new LinkEchoRateGate();
        private readonly List<Sample> samples = new List<Sample>(SampleLimit);
        private double deadline;
        private CustomMessagingManager messaging;
        private Sample pending;
        private double sentAt, windowStarted = double.NaN;
        private int firstFrame;

        private VenueLinkDiagnostics(VenueBootstrap owner, bool server, string output)
        {
            this.owner = owner; this.server = server; this.output = output;
            if (!server) client = new LinkProbeConnection(output == null);
            deadline = !server && output == null ? double.PositiveInfinity : Time.realtimeSinceStartupAsDouble + LifetimeSeconds;
        }

        internal static VenueLinkDiagnostics Create(VenueBootstrap owner, LaunchConfiguration configuration)
        {
            if (configuration.IsServer) return new VenueLinkDiagnostics(owner, true, null);
#if UNITY_ANDROID && !UNITY_EDITOR && DEVELOPMENT_BUILD
            if (configuration.recordQuestLinkMetrics) return new VenueLinkDiagnostics(owner, false, null);
#elif UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            var args = Environment.GetCommandLineArgs();
            var index = Array.IndexOf(args, "--vr-link-metrics");
            if (index < 0) return null;
            try
            {
                if (index + 1 >= args.Length || Array.LastIndexOf(args, "--vr-link-metrics") != index
                    || !Path.IsPathFullyQualified(args[index + 1]))
                    throw new ArgumentException();
                var path = Path.GetFullPath(args[index + 1]);
                if (!string.Equals(Path.GetExtension(path), ".json", StringComparison.OrdinalIgnoreCase)
                    || !Directory.Exists(Path.GetDirectoryName(path)) || File.Exists(path) || Directory.Exists(path))
                    throw new IOException();
                return new VenueLinkDiagnostics(owner, false, path);
            }
            catch (Exception error) when (error is IOException || error is ArgumentException || error is UnauthorizedAccessException || error is NotSupportedException)
            { Debug.LogWarning("VR_LINK_METRICS_OUTPUT_REJECTED"); }
#endif
            return null;
        }

        internal void Attach()
        {
            if (client?.Closed == true) return;
            var current = owner.networkManager.CustomMessagingManager;
            if (current == null || current == messaging) return;
            messaging = current;
            if (server) messaging.RegisterNamedMessageHandler(Request, HandleRequest);
            else messaging.RegisterNamedMessageHandler(Reply, HandleReply);
        }

        private void HandleRequest(ulong sender, FastBufferReader reader)
        {
            if (sender == NetworkManager.ServerClientId || owner.Admission(sender) == null
                || !owner.networkManager.ConnectedClients.ContainsKey(sender)
                || !TrySequence(reader, out var sequence) || !replies.TryReply(sender, Time.realtimeSinceStartupAsDouble))
                return;
            Send(Reply, sender, sequence);
        }

        private void HandleReply(ulong sender, FastBufferReader reader)
        {
            if (sender != NetworkManager.ServerClientId || pending == null || !TrySequence(reader, out var sequence)
                || !client.IsPendingReply(sequence)) return;
            var elapsed = Time.realtimeSinceStartupAsDouble - sentAt;
            if (elapsed >= ReplySeconds) return;
            pending.roundTripMilliseconds = elapsed * 1000;
            Record("Reply");
        }

        private static bool TrySequence(FastBufferReader reader, out uint sequence)
        {
            sequence = 0;
            if (reader.Length - reader.Position != sizeof(uint)) return false;
            reader.ReadValueSafe(out sequence);
            return sequence != 0;
        }

        private void Send(string name, ulong target, uint sequence)
        {
            using var writer = new FastBufferWriter(sizeof(uint), Allocator.Temp);
            writer.WriteValueSafe(sequence);
            messaging.SendNamedMessage(name, target, writer, NetworkDelivery.Unreliable);
        }

        internal void Connected(ulong clientId)
        {
            if (client?.TryBegin(clientId) != true) return;
            samples.Clear();
            windowStarted = double.NaN;
            if (output == null) deadline = double.PositiveInfinity;
        }

        internal void Disconnected(ulong clientId)
        {
            if (server) { replies.Forget(clientId); return; }
            if (client.Id != clientId) return;
            Finish("Disconnected");
            client.Disconnect();
        }

        internal void Update()
        {
            if (server || client.Closed) return;
            var now = Time.realtimeSinceStartupAsDouble;
            if (!client.Reported && now >= deadline) { Finish("Deadline"); return; }
            var network = owner.networkManager;
            if (!network.IsConnectedClient || messaging == null || !client.Id.HasValue) return;

            var scene = owner.sceneAuthority;
            var state = scene != null && scene.IsSpawned ? scene.Presentation.Value : default;
            if (state.phase == 3) { Finish("Ended"); return; }
            if (client.Reported) return;
            if (state.phase != 1)
            {
                if (pending != null) Record("Interrupted");
                windowStarted = double.NaN;
                return;
            }
            if (double.IsPositiveInfinity(deadline)) deadline = now + LifetimeSeconds;
            if (pending != null && now - sentAt >= ReplySeconds) Record("Timeout");
            if (client.Reported || pending != null) return;
            if (double.IsNaN(windowStarted))
            { windowStarted = now; firstFrame = Time.frameCount; return; }
            if (now - windowStarted < SampleInterval) return;

            pending = new Sample { sequence = (uint)samples.Count + 1, tick = state.tick,
                playerLoopFrames = Time.frameCount - firstFrame, windowSeconds = now - windowStarted };
            sentAt = windowStarted = now;
            firstFrame = Time.frameCount;
            Send(Request, NetworkManager.ServerClientId, client.BeginRequest());
        }

        private void Record(string result)
        {
            pending.result = result;
            samples.Add(pending); pending = null;
            client.ClearRequest();
            if (samples.Count == SampleLimit) Finish("Limit");
        }

        internal void Finish(string reason)
        {
            if (server || !client.TryFinish(reason == "Ended" || reason == "Shutdown")) return;
            if (pending != null) { pending.result = "Interrupted"; samples.Add(pending); pending = null; }
            var connection = client.Id.GetValueOrDefault();
            var report = new Report { processId = CurrentProcessId(), connection = connection,
                complete = reason == "Limit", batchMode = Application.isBatchMode, reason = reason, samples = samples.ToArray(),
                graphicsDeviceActive = SystemInfo.graphicsDeviceType != UnityEngine.Rendering.GraphicsDeviceType.Null };
#if UNITY_ANDROID && !UNITY_EDITOR && DEVELOPMENT_BUILD
            if (output == null)
            {
                const int chunkSize = 480;
                var json = JsonUtility.ToJson(report);
                var count = (json.Length + chunkSize - 1) / chunkSize;
                for (var index = 0; index < count; index++)
                {
                    var offset = index * chunkSize;
                    var chunk = json.Substring(offset, Math.Min(chunkSize, json.Length - offset));
                    Debug.Log($"VR_QUEST_LINK_METRICS id={connection} part={index + 1}/{count} {chunk}");
                }
                return;
            }
#endif
            var temporary = output + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                File.WriteAllText(temporary, JsonUtility.ToJson(report, true));
                File.Move(temporary, output);
            }
            catch (Exception error) when (error is IOException || error is UnauthorizedAccessException)
            { Debug.LogWarning("VR_LINK_METRICS_WRITE_FAILED"); }
        }

        private static int CurrentProcessId()
        {
#if UNITY_ANDROID && !UNITY_EDITOR && DEVELOPMENT_BUILD
            using var process = new AndroidJavaClass("android.os.Process");
            return process.CallStatic<int>("myPid");
#else
            return System.Diagnostics.Process.GetCurrentProcess().Id;
#endif
        }
    }

    internal sealed class LinkProbeConnection
    {
        private readonly bool repeatOnReconnect;
        private uint lastRequest, pendingRequest;
        internal ulong? Id { get; private set; }
        internal bool Reported { get; private set; }
        internal bool Closed { get; private set; }

        internal LinkProbeConnection(bool repeatOnReconnect) => this.repeatOnReconnect = repeatOnReconnect;

        internal bool TryBegin(ulong id)
        {
            if (Closed || Id.HasValue || id == NetworkManager.ServerClientId) return false;
            Id = id;
            Reported = false;
            return true;
        }

        internal bool TryFinish(bool terminal)
        {
            Closed |= terminal || !repeatOnReconnect;
            if (Reported || (repeatOnReconnect && !Id.HasValue)) return false;
            Reported = true;
            ClearRequest();
            return true;
        }

        internal void Disconnect() => Id = null;

        // Report ordinals restart on a new connection. Echo tokens stay unique across reconnects.
        internal uint BeginRequest()
        {
            if (++lastRequest == 0) ++lastRequest;
            return pendingRequest = lastRequest;
        }

        internal bool IsPendingReply(uint request) => request != 0 && request == pendingRequest;

        internal void ClearRequest() => pendingRequest = 0;
    }

    internal sealed class LinkEchoRateGate
    {
        private readonly Dictionary<ulong, double> lastReply = new Dictionary<ulong, double>();

        internal bool TryReply(ulong sender, double now)
        {
            // Allow a little scheduling jitter between nominal one-second requests.
            if (lastReply.TryGetValue(sender, out var prior) ? now - prior < .8 : lastReply.Count >= 25) return false;
            lastReply[sender] = now;
            return true;
        }

        internal void Forget(ulong sender) => lastReply.Remove(sender);
    }
}
