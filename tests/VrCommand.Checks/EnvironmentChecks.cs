using System.Text.Json;
using VrCommand.Simulation;

internal static class EnvironmentChecks
{
    internal static string Vectors()
    {
        var profiles = new List<object>();
        foreach (var weather in new[] { "Clear", "Rain", "Fog", "Storm" })
        foreach (var night in new[] { false, true })
        foreach (var lightning in new[] { false, true })
        foreach (var tick in new long[] { 0, 139, 140, 142, 143, 179, 180, 280, 1728000 })
        {
            var style = EnvironmentPresentation.Sample(tick, weather, night, lightning, "Running");
            profiles.Add(new { tick, weather, night, lightning, phase = "Running", rain = style.Rain, fog = style.Fog, sun = style.Sun,
                ambient = style.Ambient, sky = new[] { style.SkyR, style.SkyG, style.SkyB }, flash = style.Flash, running = style.Running });
        }
        var rainPoints = new List<object>();
        foreach (var room in Enumerable.Range(1, 5)) foreach (var index in new[] { 0, 63, 127 }) foreach (var tick in new long[] { 0, 149, 150, 1728000 })
        { var point = EnvironmentPresentation.RainPoint(room, index, tick); rainPoints.Add(new { room, index, tick, x = point.X, y = point.Y, z = point.Z }); }
        var tracker = new EnvironmentCueTracker();
        var cues = Enumerable.Range(0, 85).Select(index => new { tick = index * 5L, sound = tracker.Advance(index * 5, "Storm", true, true, "Running") }).ToArray();
        return JsonSerializer.Serialize(new { profiles, rainPoints, cues });
    }
    internal static void Run(Action<bool, string> check)
    {
        void Reject(Action action, string label) { try { action(); } catch (ArgumentException) { check(true, label); return; } throw new Exception(label); }
        var day = EnvironmentPresentation.Sample(0, "Clear", false, false, "Running");
        var night = EnvironmentPresentation.Sample(0, "Clear", true, false, "Running");
        check(day.Rain == 0 && day.Fog == 0 && day.Sun > night.Sun && day.Ambient > night.Ambient, "Day and night presentation have distinct deterministic lighting without invented rain");
        check(EnvironmentPresentation.Sample(0, "Rain", false, false, "Running").Rain == .5f && EnvironmentPresentation.Sample(0, "Storm", false, false, "Running").Rain == 1,
            "Rain and storm use bounded different drop densities");
        check(EnvironmentPresentation.Sample(0, "Fog", false, true, "Running").Rain == 0 && EnvironmentPresentation.Sample(0, "Fog", false, true, "Running").Fog > day.Fog,
            "Fog changes visibility presentation without inventing precipitation");
        check(!EnvironmentPresentation.Sample(139, "Storm", true, true, "Running").Flash && EnvironmentPresentation.Sample(140, "Storm", true, true, "Running").Flash
            && EnvironmentPresentation.Sample(142, "Storm", true, true, "Running").Flash && !EnvironmentPresentation.Sample(143, "Storm", true, true, "Running").Flash,
            "Lightning has an exact 140-tick period and three-tick visible window");
        check(!EnvironmentPresentation.Sample(140, "Storm", true, false, "Running").Flash && !EnvironmentPresentation.Sample(140, "Storm", true, true, "Paused").Flash,
            "Operator lightning disable and pause suppress flashes");
        var tracker = new EnvironmentCueTracker(); var sounds = new List<int>();
        for (var tick = 0; tick <= 400; tick++) if (tracker.Advance(tick, "Storm", true, true, "Running")) sounds.Add(tick);
        check(sounds.SequenceEqual([180, 320]), "Observed flashes produce one delayed thunder each at exact simulation ticks");
        check(!tracker.Advance(400, "Storm", true, true, "Running"), "Repeating a received tick never repeats thunder");
        tracker.Reset(); check(!tracker.Advance(180, "Storm", true, true, "Running"), "Late join does not play thunder for an unseen historical flash");
        tracker.Reset(); tracker.Advance(140, "Storm", true, true, "Running"); check(!tracker.Advance(180, "Storm", true, true, "Running"), "A long source gap drops catch-up thunder instead of bursting old audio");
        tracker.Reset(); tracker.Advance(140, "Storm", true, true, "Running"); tracker.Advance(145, "Storm", true, false, "Running");
        var phantom = false; for (var tick = 150; tick <= 190; tick += 5) phantom |= tracker.Advance(tick, "Storm", true, true, "Running");
        check(!phantom, "Re-enabling lightning after a missed flash cannot invent its thunder");
        tracker.Reset(); tracker.Advance(140, "Storm", true, true, "Running"); tracker.Advance(145, "Storm", true, true, "Paused"); tracker.Advance(145, "Storm", true, true, "Paused");
        tracker.Advance(145, "Storm", true, true, "Running"); var resumed = new List<int>();
        for (var tick = 150; tick <= 190; tick += 5) if (tracker.Advance(tick, "Storm", true, true, "Running")) resumed.Add(tick);
        check(resumed.SequenceEqual([180]), "Pause freezes an observed strike until continuous simulated time resumes");
        tracker.Reset(); check(!tracker.Advance(140, "Storm", true, true, "Running") && !tracker.Advance(100, "Storm", true, true, "Running"), "Replay seek rebases cue history without immediate sound");
        var inside = true;
        for (var room = 1; room <= 5; room++) for (var index = 0; index < 128; index++)
        {
            var point = EnvironmentPresentation.RainPoint(room, index, 1728000);
            inside &= Math.Abs(point.X - (room - 3) * 14) <= 6 && Math.Abs(point.Z) <= 6 && point.Y >= 0 && point.Y <= 6;
        }
        check(inside, "All five room rain batches remain inside their exact world volumes");
        var first = EnvironmentPresentation.RainPoint(3, 0, 0); var loop = EnvironmentPresentation.RainPoint(3, 0, 150);
        check(first.Equals(loop) && !first.Equals(EnvironmentPresentation.RainPoint(3, 0, 1)), "Rain positions are reproducible, bounded and driven by simulation ticks");
        Reject(() => EnvironmentPresentation.Sample(-1, "Clear", false, false, "Running"), "Negative presentation time is rejected");
        Reject(() => EnvironmentPresentation.Sample(0, "Unknown", false, false, "Running"), "Unknown environment presentation policy fails closed");
        Reject(() => EnvironmentPresentation.RainPoint(0, 0, 0), "Rain cannot be generated for an unknown room");
        Reject(() => EnvironmentPresentation.RainPoint(1, 128, 0), "Rain samples respect the fixed per-room rendering budget");
        var header = WorldRecordingHeader.Create(Guid.NewGuid(), Guid.NewGuid(), "Simulation", [3], []);
        check(header.environmentVersion == 1 && new WorldRecordingHeader().environmentVersion == 0, "New recordings declare environment profile one while legacy missing fields remain zero");
        header.environmentVersion = 2; Reject(() => WorldRecordingValidation.Header(header), "Unknown persisted presentation versions are rejected");
    }
}
