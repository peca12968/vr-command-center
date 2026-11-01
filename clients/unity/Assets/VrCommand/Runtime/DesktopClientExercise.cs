using System;
using System.IO;
using System.Text;
using UnityEngine;
using Stopwatch = System.Diagnostics.Stopwatch;

namespace VrCommand.Unity
{
    public readonly struct DesktopExerciseFrame
    {
        public readonly Vector2 Movement;
        public readonly bool Fire, Reload;
        public DesktopExerciseFrame(Vector2 movement, bool fire, bool reload) { Movement = movement; Fire = fire; Reload = reload; }
    }

    // Explicit synthetic input for short native network exercises. This never
    // writes a pose or calls a server/test RPC; NetworkAvatar retains that path.
    public sealed class DesktopExercisePlan
    {
        public const long MaximumActiveTicks = 1200;
        public const long EnduranceActiveTicks = 19000, EnduranceWeaponTicks = 18000;
        public const int EnduranceCycleTicks = 400, EnduranceCycles = 45;
        private readonly bool endurance;
        private int cycle = -1;
        private long start = -1, last = -1;
        private int fires;
        private bool reloaded;
        public bool Exhausted { get; private set; }
        public long FirstTick => start;
        public long LastTick => last;
        public DesktopExercisePlan(bool endurance = false) { this.endurance = endurance; }
        public static bool Allowed(string role, bool windows, bool development, bool batch, bool editor, bool tracked)
            => role == "Client" && windows && development && batch && !editor && !tracked;
        public DesktopExerciseFrame Next(long tick, bool active)
        {
            if (!active || Exhausted) return default;
            if (tick < 0 || (last >= 0 && tick < last)) throw new InvalidOperationException("Exercise tick moved backwards.");
            if (start < 0) start = tick;
            last = tick; var elapsed = tick - start;
            if (elapsed >= (endurance ? EnduranceActiveTicks : MaximumActiveTicks)) { Exhausted = true; return default; }
            // 0.4m/s through DesktopPreviewControls.Move; 0.8m forward/back.
            var forward = (elapsed / 40) % 2 == 0 ? .2f : -.2f;
            if (endurance)
            {
                if (elapsed >= EnduranceWeaponTicks)
                {
                    if (cycle != EnduranceCycles - 1 || fires != 2 || !reloaded) throw new InvalidOperationException("Endurance cycle incomplete.");
                    return new DesktopExerciseFrame(new Vector2(0, forward), false, false);
                }
                var next = (int)(elapsed / EnduranceCycleTicks);
                if (next != cycle)
                {
                    if (next != cycle + 1 || (cycle >= 0 && (fires != 2 || !reloaded))) throw new InvalidOperationException("Endurance cycle missed.");
                    cycle = next; fires = 0; reloaded = false;
                }
                elapsed %= EnduranceCycleTicks;
            }
            return new DesktopExerciseFrame(new Vector2(0, forward), fires < 2 && elapsed >= (fires == 0 ? 20 : 120), !reloaded && elapsed >= 60);
        }
        public void SubmittedFire() { if (fires >= 2) throw new InvalidOperationException("Exercise fire bound."); fires++; }
        public void SubmittedReload() { if (reloaded) throw new InvalidOperationException("Exercise reload bound."); reloaded = true; }
    }

    public sealed class DesktopClientExercise : MonoBehaviour
    {
        [Serializable] public sealed class Report
        {
            public int version = 1, pid, room, activeFrames, movementFrames, fireSubmissions, reloadSubmissions;
            public string mode = "AutomatedSimulation", role = "Client", playerId, reason, fault;
            public string profile = "Short";
            public int maximumCollectionSeconds = 240;
            public long maximumActiveTicks = DesktopExercisePlan.MaximumActiveTicks;
            public bool complete, truncated, physicalInput;
            public int headsets;
            public ulong connection;
            public long firstTick, lastTick, startedUtcTicks, endedUtcTicks;
            public double seconds;
        }
        private static DesktopClientExercise instance;
        public static bool Enabled => instance != null;
        private DesktopExercisePlan plan = new DesktopExercisePlan();
        private readonly Stopwatch clock = new Stopwatch();
        private readonly Report report = new Report();
        private string directory;
        private double nextCheck;
        private bool finished, bound;
        public static bool Install(GameObject owner, string role)
        {
            var args = Environment.GetCommandLineArgs(); var index = Array.IndexOf(args, "--vr-desktop-exercise");
            var longIndex = Array.IndexOf(args, "--vr-desktop-endurance"); var endurance = longIndex >= 0;
            if (index < 0 && longIndex < 0) return true;
            if (endurance) index = longIndex;
            try
            {
                var count = 0; foreach (var arg in args) if (arg == "--vr-desktop-exercise" || arg == "--vr-desktop-endurance") count++;
                var windowsDevelopment = false;
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
                windowsDevelopment = true;
#endif
                if (!DesktopExercisePlan.Allowed(role, windowsDevelopment, Debug.isDebugBuild, Application.isBatchMode, Application.isEditor, UnityEngine.XR.XRSettings.isDeviceActive)
                    || count != 1 || index + 1 >= args.Length || !Path.IsPathRooted(args[index + 1])) throw new ArgumentException("Exercise context rejected.");
                var path = Path.GetFullPath(args[index + 1]);
                if (Directory.Exists(path) || File.Exists(path) || path.StartsWith(@"\\", StringComparison.Ordinal)) throw new IOException("Exercise directory rejected.");
                Directory.CreateDirectory(path); var exercise = owner.AddComponent<DesktopClientExercise>(); exercise.directory = path;
                exercise.plan = new DesktopExercisePlan(endurance);
                exercise.report.profile = endurance ? "Endurance" : "Short";
                exercise.report.maximumCollectionSeconds = endurance ? 1200 : 240;
                exercise.report.maximumActiveTicks = endurance ? DesktopExercisePlan.EnduranceActiveTicks : DesktopExercisePlan.MaximumActiveTicks;
                exercise.report.pid = System.Diagnostics.Process.GetCurrentProcess().Id; exercise.report.startedUtcTicks = DateTime.UtcNow.Ticks;
                exercise.clock.Start(); exercise.Save("ready.json", "Ready", false); instance = exercise; return true;
            }
            catch (Exception) { Debug.LogError("Desktop exercise requires a fresh local directory and Windows Development batch Client without XR."); return false; }
        }
        internal static DesktopExerciseFrame Sample(string playerId, ulong connection, int room, long tick, bool active)
        {
            var self = instance; if (self == null || self.finished) return default;
            if (!Guid.TryParse(playerId, out var id) || id == Guid.Empty || room < 1 || room > 5) return default;
            if (!self.bound) { self.report.playerId = playerId; self.report.connection = connection; self.report.room = room; self.bound = true; }
            else if (self.report.playerId != playerId || self.report.connection != connection || self.report.room != room)
            { self.report.fault = "OwnerChanged"; self.Finish(false, "OwnerChanged"); return default; }
            try
            {
                var frame = self.plan.Next(tick, active);
                if (self.plan.Exhausted) { self.Finish(false, "ActiveTickLimit"); return default; }
                if (active) { self.report.activeFrames++; if (frame.Movement != Vector2.zero) self.report.movementFrames++; }
                return frame;
            }
            catch (InvalidOperationException)
            {
                self.report.fault = tick < self.plan.LastTick ? "TickWentBackwards" : "ScheduleIncomplete";
                self.Finish(false, self.report.fault); return default;
            }
        }
        internal static void Submitted(bool reload)
        {
            var self = instance; if (self == null || self.finished) return;
            if (reload) { self.plan.SubmittedReload(); self.report.reloadSubmissions++; }
            else { self.plan.SubmittedFire(); self.report.fireSubmissions++; }
        }
        internal static void RejectTracked()
        {
            if (instance == null || instance.finished) return;
            instance.report.fault = "TrackedDevice"; instance.Finish(false, "TrackedDevice");
        }
        private void Update()
        {
            if (finished || directory == null) return;
            if (clock.Elapsed.TotalSeconds >= report.maximumCollectionSeconds) { Finish(false, "Timeout"); return; }
            if (clock.Elapsed.TotalSeconds < nextCheck) return;
            nextCheck = clock.Elapsed.TotalSeconds + .1;
            if (File.Exists(Path.Combine(directory, "finish.request"))) Finish(true, "Requested");
        }
        private void Save(string filename, string reason, bool complete)
        {
            report.reason = reason; report.complete = complete; report.truncated = plan.Exhausted || reason == "Timeout";
            report.firstTick = plan.FirstTick; report.lastTick = plan.LastTick; report.seconds = clock.Elapsed.TotalSeconds;
            report.endedUtcTicks = DateTime.UtcNow.Ticks;
            var bytes = new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(report, true));
            using (var file = new FileStream(Path.Combine(directory, filename), FileMode.CreateNew, FileAccess.Write, FileShare.None)) { file.Write(bytes, 0, bytes.Length); file.Flush(true); }
        }
        private void Finish(bool requested, string reason)
        {
            if (finished) return; finished = true;
            Save("report.json", reason, requested && bound && report.activeFrames > 0 && report.fault == null && !plan.Exhausted);
        }
        private void OnApplicationQuit() { if (directory != null) Finish(false, "ApplicationQuit"); }
        private void OnDestroy() { if (directory != null) Finish(false, "OwnerDestroyed"); if (instance == this) instance = null; }
    }
}
