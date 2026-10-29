using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using UnityEngine;

namespace VrCommand.Unity
{
    // Explicit development-only desktop evidence, attached to THIS player's
    // AudioListener. No microphone, OS loopback, gameplay input or remote switch.
    public sealed class NativeWeatherProbe : MonoBehaviour
    {
        [Serializable] public sealed class Frame
        {
            public double seconds;
            public long tick;
            public string phase;
            public int weather, vertices;
            public bool night, lightning, flash, rainPlaying, thunderPlaying;
            public float sun, rainVolume;
            public TacticalHudSnapshot hud;
        }
        [Serializable] public sealed class AudioWindow
        { public double seconds, rms; public float peak; public int samples, channels; }
        [Serializable] public sealed class Report
        {
            public int schemaVersion = 1, sampleRate, channels, audioSamples, callbackCount;
            public string source = "Simulation", startedAtUtc, error = "", mode = "weather";
            public bool complete, truncated, formatChanged;
            public Frame frame;
            public Frame[] frames;
            public AudioWindow[] audio;
            public string[] captures;
        }
        private readonly object gate = new object();
        private readonly Stopwatch clock = new Stopwatch();
        private readonly List<Frame> frames = new List<Frame>();
        private readonly List<AudioWindow> audio = new List<AudioWindow>();
        private readonly List<string> captures = new List<string>();
        private readonly HashSet<string> requested = new HashSet<string>();
        private readonly Report report = new Report();
        private string directory;
        private SceneAuthority scene;
        private UnityWeatherView view;
        private AudioSource rain, thunder;
        private MeshFilter rainMesh;
        private float[] pcm;
        private int count, channels, callbacks;
        private bool recording, finished, truncated, formatChanged;
        private double next, ended = -1;
        public static bool Recording { get; private set; }

        public static void Install(GameObject listener)
        {
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            if (Application.isBatchMode || Application.isEditor || listener.GetComponent<AudioListener>() == null) return;
            var args = Environment.GetCommandLineArgs(); var index = Array.IndexOf(args, "--vr-weather-probe");
            var hudIndex = Array.IndexOf(args, "--vr-hud-probe");
            if (index >= 0 && hudIndex >= 0) throw new ArgumentException("Select either weather audio or HUD-only capture.");
            var captureAudio = index >= 0; if (index < 0) index = hudIndex;
            if (index < 0) return;
            if (index + 1 >= args.Length || !Path.IsPathRooted(args[index + 1])) throw new ArgumentException("Weather probe requires an absolute fresh directory.");
            var path = Path.GetFullPath(args[index + 1]);
            if (Directory.Exists(path) || File.Exists(path)) throw new IOException("Weather probe directory must not already exist.");
            Directory.CreateDirectory(path);
            var probe = listener.AddComponent<NativeWeatherProbe>(); probe.Begin(path, captureAudio);
#endif
        }
        private void Begin(string path, bool captureAudio)
        {
            directory = path; report.startedAtUtc = DateTimeOffset.UtcNow.ToString("O");
            report.sampleRate = AudioSettings.outputSampleRate;
            var mode = AudioSettings.speakerMode;
            var expectedChannels = mode == AudioSpeakerMode.Mono ? 1 : mode == AudioSpeakerMode.Quad ? 4
                : mode == AudioSpeakerMode.Surround ? 5 : mode == AudioSpeakerMode.Mode5point1 ? 6 : mode == AudioSpeakerMode.Mode7point1 ? 8 : 2;
            report.mode = captureAudio ? "weather" : "hud";
            if (captureAudio) pcm = new float[checked(report.sampleRate * expectedChannels * 90)];
            clock.Start(); recording = captureAudio; Recording = true;
        }
        private void OnAudioFilterRead(float[] data, int channelCount)
        {
            lock (gate)
            {
                if (!recording || data.Length == 0) return;
                if (channels == 0) channels = channelCount;
                if (channels != channelCount) { formatChanged = true; return; }
                double squares = 0; float peak = 0;
                for (var i = 0; i < data.Length; i++)
                {
                    var sample = data[i];
                    if (float.IsNaN(sample) || float.IsInfinity(sample)) { formatChanged = true; sample = 0; }
                    squares += (double)sample * sample; peak = Math.Max(peak, Math.Abs(sample));
                }
                callbacks++;
                if (audio.Count < 12000) audio.Add(new AudioWindow { seconds = clock.Elapsed.TotalSeconds, rms = Math.Sqrt(squares / data.Length), peak = peak, samples = data.Length, channels = channelCount });
                else truncated = true;
                if (count + data.Length <= pcm.Length) { Array.Copy(data, 0, pcm, count, data.Length); count += data.Length; }
                else truncated = true;
            }
        }
        private void LateUpdate()
        {
            if (directory == null || finished) return;
            try
            {
                if (AudioSettings.outputSampleRate != report.sampleRate) formatChanged = true;
                if (scene == null) { scene = FindFirstObjectByType<SceneAuthority>(); if (scene == null) return; view = scene.environmentView; }
                if (view == null || !scene.IsSpawned) return;
                if (rain == null || thunder == null)
                    foreach (var source in view.GetComponents<AudioSource>()) { if (source.clip == view.rainClip) rain = source; if (source.clip == view.thunderClip) thunder = source; }
                if (rain == null || thunder == null) throw new InvalidOperationException("Weather clips / AudioSources are missing.");
                if (rainMesh == null) rainMesh = view.GetComponentInChildren<MeshFilter>();
                var state = scene.Presentation.Value; var style = view.LastApplied;
                report.frame = new Frame { seconds = clock.Elapsed.TotalSeconds, tick = style.Tick, phase = view.AppliedPhase,
                    weather = state.weather, night = state.night, lightning = state.lightning, flash = style.Flash,
                    sun = view.sun == null ? -1 : view.sun.intensity, rainVolume = rain.volume,
                    rainPlaying = rain.isPlaying, thunderPlaying = thunder.isPlaying,
                    vertices = rainMesh != null && rainMesh.GetComponent<Renderer>().enabled ? rainMesh.sharedMesh.vertexCount : 0, hud = TacticalHud.LastDrawn };
                if (style.Running && style.Tick > 20 && !style.Flash) Capture(state.night ? "night" : "day");
                if (style.Flash) Capture("flash");
                if (view.AppliedPhase == "Paused") Capture("paused");
                if (style.Running && style.Rain > 0) Capture(style.Rain > .75f ? "storm" : "rain");
                if (report.mode == "hud" && report.frame.hud != null && requested.Count < 16)
                {
                    var hud = report.frame.hud;
                    Capture("hud-" + hud.status.Replace(' ', '_') + "-h" + hud.health + "-a" + hud.magazine
                        + (hud.reloading ? "-reload" : "") + "-d" + (Mathf.RoundToInt(hud.bearing / 30) * 30));
                }
                if (clock.Elapsed.TotalSeconds >= next)
                {
                    if (frames.Count < 1200) frames.Add(report.frame); else truncated = true;
                    Write(false); next = clock.Elapsed.TotalSeconds + (report.mode == "hud" ? .25 : .1);
                }
                if (view.AppliedPhase == "Ended") { if (ended < 0) ended = clock.Elapsed.TotalSeconds; if (clock.Elapsed.TotalSeconds - ended > .6) Finish(); }
                if (clock.Elapsed.TotalSeconds > (report.mode == "hud" ? 285 : 85)) { report.error = "Probe time limit reached before End."; Finish(); }
            }
            catch (Exception error) { report.error = error.GetType().Name + ": " + error.Message; Finish(); }
        }
        private void Capture(string name)
        {
            if (requested.Add(name)) StartCoroutine(CaptureFrame(name));
        }
        private IEnumerator CaptureFrame(string name)
        {
            yield return new WaitForEndOfFrame();
            Texture2D texture = null;
            try
            {
                texture = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
                texture.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0); texture.Apply();
                File.WriteAllBytes(Path.Combine(directory, name + ".png"), texture.EncodeToPNG()); captures.Add(name);
            }
            catch (Exception error) { report.error = "Capture: " + error.Message; }
            finally { if (texture != null) Destroy(texture); }
        }
        private void Write(bool complete)
        {
            lock (gate)
            {
                report.channels = channels; report.audioSamples = count; report.callbackCount = callbacks;
                report.truncated = truncated; report.formatChanged = formatChanged;
                report.audio = complete ? audio.ToArray() : null;
            }
            report.complete = complete; report.frames = complete ? frames.ToArray() : null; report.captures = captures.ToArray();
            File.WriteAllText(Path.Combine(directory, complete ? "report.json" : "status.json"), JsonUtility.ToJson(report, true));
        }
        private void Finish()
        {
            if (directory == null || finished) return;
            finished = true; lock (gate) recording = false; Recording = false;
            try
            {
                if (channels > 0)
                {
                    using (var writer = new BinaryWriter(File.Create(Path.Combine(directory, "audio.wav"))))
                    {
                        var bytes = count * 2;
                        writer.Write(System.Text.Encoding.ASCII.GetBytes("RIFF")); writer.Write(36 + bytes); writer.Write(System.Text.Encoding.ASCII.GetBytes("WAVEfmt "));
                        writer.Write(16); writer.Write((short)1); writer.Write((short)channels); writer.Write(report.sampleRate);
                        writer.Write(report.sampleRate * channels * 2); writer.Write((short)(channels * 2)); writer.Write((short)16);
                        writer.Write(System.Text.Encoding.ASCII.GetBytes("data")); writer.Write(bytes);
                        for (var i = 0; i < count; i++) writer.Write((short)Math.Round(Math.Max(-1, Math.Min(1, pcm[i])) * 32767));
                    }
                }
                Write(true);
            }
            catch (Exception error) { UnityEngine.Debug.LogError("Weather probe finalization failed: " + error.Message); }
        }
        private void OnDestroy() => Finish();
        private void OnApplicationQuit() => Finish();
    }
}
