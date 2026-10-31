using System;
using System.Globalization;

namespace VrCommand.Simulation
{
    // Mission policy, separate from combat rules. Tick time excludes pauses and management suspension.
    public static class MissionClock
    {
        public const int Version = 1, TicksPerSecond = 20;
        public static bool ValidDuration(int seconds) => seconds >= 60 && seconds <= 14400;
        public static long LimitTicks(int seconds)
        {
            if (!ValidDuration(seconds)) throw new ArgumentOutOfRangeException(nameof(seconds));
            return (long)seconds * TicksPerSecond;
        }
        public static bool Due(long tick, int seconds) => tick >= 0 && tick >= LimitTicks(seconds);
        public static long RemainingSeconds(long tick, int seconds)
        {
            if (tick < 0) throw new ArgumentOutOfRangeException(nameof(tick));
            var remaining = Math.Max(0, LimitTicks(seconds) - tick);
            return (remaining + TicksPerSecond - 1) / TicksPerSecond;
        }
        public static string FormatSeconds(long seconds)
        {
            if (seconds < 0) throw new ArgumentOutOfRangeException(nameof(seconds));
            return (seconds / 60).ToString("00", CultureInfo.InvariantCulture) + ":" + (seconds % 60).ToString("00", CultureInfo.InvariantCulture);
        }
    }
}
