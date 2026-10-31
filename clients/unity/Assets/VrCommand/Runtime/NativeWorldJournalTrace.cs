using System;
using System.Diagnostics;
using System.IO;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    public sealed class NativeWorldJournalTrace : MonoBehaviour
    {
        [Serializable] public sealed class Report
        {
            public int version = 1, maximumSeconds = 90, capacity = WorldJournalTrace.MaximumCapacity, inFlight, mainManagedThreadId;
            public string source = "NativeWindowsWorldJournalStages", role = "Server", stopReason, error = "";
            public long frequency = Stopwatch.Frequency;
            public long startedTimestamp, startedUtcTicks, stoppedTimestamp, stoppedUtcTicks;
            public bool complete, truncated;
            public double endedSeconds;
            public WorldJournalTimingRow[] rows;
        }
        private static NativeWorldJournalTrace active;
        public static WorldJournalTrace Current => active == null ? null : active.trace;
        private readonly WorldJournalTrace trace = new WorldJournalTrace();
        private readonly Stopwatch clock = new Stopwatch();
        private string directory, reason;
        private bool stopping, finished, requested;
        private double stopStarted, nextCheck;
        private long startedTimestamp, startedUtcTicks, stoppedTimestamp, stoppedUtcTicks;
        private int mainManagedThreadId;
        public static void Install(GameObject owner, string role)
        {
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            if (Application.isEditor) return;
            var args = Environment.GetCommandLineArgs(); var index = Array.IndexOf(args, "--vr-journal-trace");
            if (index < 0) return;
            if (role != "Server" || active != null) throw new ArgumentException("Journal trace requires one dedicated server.");
            if (index + 1 >= args.Length || !Path.IsPathRooted(args[index + 1])) throw new ArgumentException("Journal trace requires a fresh absolute directory.");
            var path = Path.GetFullPath(args[index + 1]);
            if (Directory.Exists(path) || File.Exists(path)) throw new IOException("Journal trace directory exists.");
            Directory.CreateDirectory(path); active = owner.AddComponent<NativeWorldJournalTrace>(); active.directory = path;
            active.mainManagedThreadId = Environment.CurrentManagedThreadId; active.startedTimestamp = Stopwatch.GetTimestamp(); active.startedUtcTicks = DateTime.UtcNow.Ticks; active.clock.Start();
#endif
        }
        private void Update()
        {
            if (finished) return;
            var now = clock.Elapsed.TotalSeconds;
            if (!stopping && now < 90 && now < nextCheck) return;
            nextCheck = now + .25;
            if (!stopping && (now >= 90 || File.Exists(Path.Combine(directory, "finish.request"))))
            {
                requested = clock.Elapsed.TotalSeconds < 90; stopping = true; stopStarted = clock.Elapsed.TotalSeconds;
                reason = requested ? "Explicit local diagnostic stop" : "Duration limit"; StopObservation();
            }
            if (stopping && (trace.InFlight == 0 || clock.Elapsed.TotalSeconds - stopStarted >= 5)) Write(requested);
        }
        private void Write(bool complete)
        {
            if (finished) return; StopObservation(); finished = true;
            // Observation ends before report serialization / disk IO. Never accesses the outbox gate.
            var report = new Report { endedSeconds = clock.Elapsed.TotalSeconds, stopReason = reason,
                inFlight = trace.InFlight, truncated = trace.Truncated, rows = trace.Snapshot(), mainManagedThreadId = mainManagedThreadId,
                startedTimestamp = startedTimestamp, startedUtcTicks = startedUtcTicks, stoppedTimestamp = stoppedTimestamp, stoppedUtcTicks = stoppedUtcTicks };
            report.complete = complete && report.inFlight == 0 && !report.truncated;
            File.WriteAllText(Path.Combine(directory, "report.json"), JsonUtility.ToJson(report));
        }
        private void StopObservation()
        {
            if (stoppedTimestamp != 0) return;
            trace.Stop(); stoppedTimestamp = Stopwatch.GetTimestamp(); stoppedUtcTicks = DateTime.UtcNow.Ticks;
        }
        private void OnDestroy()
        {
            if (directory != null && !finished) { reason = "Owner destroyed"; Write(false); }
            if (active == this) active = null;
        }
    }
}
