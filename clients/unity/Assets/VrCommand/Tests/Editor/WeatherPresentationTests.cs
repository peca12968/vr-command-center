using NUnit.Framework;
using Unity.Collections;
using Unity.Netcode;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class WeatherPresentationTests
    {
        [Test] public void AtomicWeatherStatePreservesTickAndRoomMaskThroughNgo()
        {
            var expected = new WeatherState { tick = 180, weather = 3, phase = 1, night = true, lightning = true, rooms = 31 };
            using (var writer = new FastBufferWriter(128, Allocator.Temp))
            {
                writer.WriteValueSafe(expected);
                using (var reader = new FastBufferReader(writer.ToArray(), Allocator.Temp))
                { reader.ReadValueSafe(out WeatherState actual); Assert.IsTrue(expected.Equals(actual)); }
            }
        }
        [Test] public void ServerClockWindowProducesOneDelayedThunder()
        {
            var cues = new EnvironmentCueTracker(); var count = 0;
            for (var tick = 0; tick <= 190; tick++) if (cues.Advance(tick, "Storm", true, true, "Running")) count++;
            Assert.AreEqual(1, count); Assert.IsFalse(cues.Advance(190, "Storm", true, true, "Running"));
        }
        [Test] public void WorldCodecRetainsThePresentationVersion()
        {
            var codec = new UnityWorldCodec(); var header = WorldRecordingHeader.Create(System.Guid.NewGuid(), System.Guid.NewGuid(), "Simulation", new[] { 3 }, new WorldProp[0]);
            Assert.AreEqual(1, codec.ReadHeader(codec.Header(header)).environmentVersion);
        }
    }
}
