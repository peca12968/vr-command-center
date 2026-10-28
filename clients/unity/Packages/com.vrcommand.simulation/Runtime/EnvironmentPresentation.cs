using System;

namespace VrCommand.Simulation
{
    // Presentation only: never changes visibility, hit tests, damage or the simulation clock.
    public readonly struct EnvironmentStyle
    {
        public readonly long Tick;
        public readonly float Rain, Fog, Sun, Ambient, SkyR, SkyG, SkyB;
        public readonly bool Flash, Running;
        public EnvironmentStyle(long tick, float rain, float fog, float sun, float ambient, float r, float g, float b, bool flash, bool running)
        { Tick = tick; Rain = rain; Fog = fog; Sun = sun; Ambient = ambient; SkyR = r; SkyG = g; SkyB = b; Flash = flash; Running = running; }
    }

    public static class EnvironmentPresentation
    {
        public const int Version = 1, StrikePeriod = 140, FlashTicks = 3, ThunderDelay = 40, MaximumGap = 10;
        public const long MaximumTick = 1728000;
        public static EnvironmentStyle Sample(long tick, string weather, bool night, bool lightning, string phase)
        {
            if (tick < 0 || tick > MaximumTick || (weather != "Clear" && weather != "Rain" && weather != "Fog" && weather != "Storm")
                || (phase != "Preparing" && phase != "Running" && phase != "Paused" && phase != "Ended"))
                throw new ArgumentException("Invalid environment presentation input.");
            var running = phase == "Running";
            var flash = running && lightning && tick >= StrikePeriod && tick % StrikePeriod < FlashTicks;
            var rain = weather == "Storm" ? 1f : weather == "Rain" ? .5f : 0f;
            var fog = weather == "Fog" ? .035f : weather == "Clear" ? 0f : weather == "Storm" ? .02f : .012f;
            return new EnvironmentStyle(tick, rain, fog, flash ? 2.5f : night ? .08f : 1.15f, night ? .18f : .65f,
                night ? .035f : weather == "Clear" ? .30f : .20f,
                night ? .05f : weather == "Clear" ? .42f : .25f,
                night ? .085f : weather == "Clear" ? .52f : .30f, flash, running);
        }
        public static Vec3 RainPoint(int room, int index, long tick)
        {
            if (room < 1 || room > 5 || index < 0 || index >= 128 || tick < 0 || tick > MaximumTick)
                throw new ArgumentException("Invalid rain sample.");
            var x = (room - 3) * 14 + ((index * 73 + room * 17) % 997) / 997f * 12 - 6;
            var z = ((index * 137 + room * 29) % 991) / 991f * 12 - 6;
            var y = 6 - (((index * 37) % 1000) / 1000f * 6 + (tick % 150) * .28f) % 6;
            return new Vec3(x, y, z);
        }
    }

    // Suppress catch-up thunder after first observation, seeks, policy changes and long gaps.
    public sealed class EnvironmentCueTracker
    {
        private bool initialized;
        private long previous, observedStrike = -1, soundedStrike = -1;
        private string weather = "", phase = "";
        private bool night, lightning;
        public void Reset() { initialized = false; observedStrike = soundedStrike = -1; }
        public bool Advance(long tick, string nextWeather, bool nextNight, bool nextLightning, string nextPhase)
        {
            var sample = EnvironmentPresentation.Sample(tick, nextWeather, nextNight, nextLightning, nextPhase);
            var discontinuity = !initialized || tick < previous || tick - previous > EnvironmentPresentation.MaximumGap
                || weather != nextWeather || night != nextNight || lightning != nextLightning;
            if (discontinuity || nextPhase == "Preparing" || nextPhase == "Ended") observedStrike = soundedStrike = -1;
            var cycle = tick / EnvironmentPresentation.StrikePeriod;
            if (sample.Flash) observedStrike = cycle;
            var cueTick = cycle * EnvironmentPresentation.StrikePeriod + EnvironmentPresentation.ThunderDelay;
            var sound = !discontinuity && sample.Running && phase == "Running" && nextLightning && cycle > 0
                && observedStrike == cycle && soundedStrike != cycle && previous < cueTick && tick >= cueTick;
            if (sound) soundedStrike = cycle;
            initialized = true; previous = tick; weather = nextWeather; night = nextNight; lightning = nextLightning; phase = nextPhase;
            return sound;
        }
    }
}
