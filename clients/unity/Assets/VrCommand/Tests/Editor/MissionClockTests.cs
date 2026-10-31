using System;
using NUnit.Framework;
using Unity.Collections;
using Unity.Netcode;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class MissionClockTests
    {
        [Test] public void ClockRoundsUpRemainingSecondsAndStopsAtTheExactTick()
        {
            Assert.AreEqual(60, MissionClock.RemainingSeconds(1, 60));
            Assert.AreEqual(1, MissionClock.RemainingSeconds(1199, 60));
            Assert.IsFalse(MissionClock.Due(1199, 60)); Assert.IsTrue(MissionClock.Due(1200, 60));
            Assert.AreEqual(0, MissionClock.RemainingSeconds(1201, 60));
            Assert.Throws<ArgumentOutOfRangeException>(() => MissionClock.LimitTicks(59));
        }
        [Test] public void NetcodeClockSerializationPreservesExplicitPolicyAndDuration()
        {
            var expected = new MissionClockState { version = 1, durationSeconds = 600, autoEnd = true };
            using (var writer = new FastBufferWriter(128, Allocator.Temp))
            {
                writer.WriteValueSafe(expected);
                using (var reader = new FastBufferReader(writer.ToArray(), Allocator.Temp))
                { reader.ReadValueSafe(out MissionClockState actual); Assert.IsTrue(expected.Equals(actual)); }
            }
        }
        [Test] public void HudLabelsDistinguishManualElapsedFromAutomaticRemaining()
        {
            var value = new MissionClockState { version = 1, durationSeconds = 60, autoEnd = true };
            Assert.AreEqual("REMAIN 00:01", value.Label(1199));
            Assert.AreEqual("REMAIN 00:00", value.Label(1200));
            value.autoEnd = false; Assert.AreEqual("ELAPSED 01:01 / PLAN 01:00", value.Label(1220));
            value.version = 2; Assert.AreEqual("", value.Label(0));
        }
        private static ManagementSnapshot Snapshot(bool autoEnd)
        {
            return new ManagementSnapshot { id = Guid.NewGuid().ToString(), sequence = 2, state = "Preparing", roomIds = new[] { 1 },
                mission = new ManagedMission { id = Guid.NewGuid().ToString(), definition = new ManagedDefinition { name = "Clock", durationSeconds = 60, props = new ManagedProp[0] } },
                environment = new ManagedEnvironment { mode = "VR", weather = "Clear", timeOfDay = "Day" },
                enemies = new ManagedEnemies { count = 0, behavior = "Hold", autoAttack = false }, players = new ManagedPlayer[0],
                missionClock = autoEnd ? new ManagedMissionClock { version = 1, autoEnd = true, configuredAtSequence = 2 } : null };
        }
        [Test] public void ArenaClockPausesAndFreezesBeforeAnyFurtherCombatTick()
        {
            var snapshot = Snapshot(true); var session = new ArenaSession(); session.Apply(snapshot);
            snapshot.sequence++; snapshot.state = "Running"; session.Apply(snapshot);
            for (var i = 0; i < 400; i++) session.Tick(i * .05);
            snapshot.sequence++; snapshot.state = "Paused"; session.Apply(snapshot);
            for (var i = 400; i < 500; i++) session.Tick(i * .05);
            Assert.AreEqual(400, session.World.TickNumber);
            snapshot.sequence++; snapshot.state = "Running"; session.Apply(snapshot);
            for (var i = 500; i < 1500; i++) session.Tick(i * .05);
            Assert.AreEqual(1200, session.World.TickNumber); Assert.IsTrue(session.ClockDue);
            Assert.IsFalse(session.Weapon(1, 1, false, 80));
        }
        [Test] public void UnityNullClockRemainsManualAndCanExceedPlannedTime()
        {
            var original = Snapshot(false);
            var snapshot = JsonUtility.FromJson<ManagementSnapshot>(JsonUtility.ToJson(original));
            var session = new ArenaSession(); session.Apply(snapshot);
            snapshot.sequence++; snapshot.state = "Running"; session.Apply(snapshot);
            for (var i = 0; i < 1220; i++) session.Tick(i * .05);
            Assert.AreEqual(1220, session.World.TickNumber); Assert.IsFalse(session.ClockDue);
        }
        [Test] public void RecordingClockCapabilityRoundTripsWithoutInventingLegacyMetadata()
        {
            var codec = new UnityWorldCodec();
            var header = WorldRecordingHeader.Create(Guid.NewGuid(), Guid.NewGuid(), "Simulation", new[] { 1 }, new WorldProp[0], missionClockVersion: 1, missionDurationSeconds: 60);
            var result = codec.ReadHeader(codec.Header(header)); WorldRecordingValidation.Header(result);
            Assert.AreEqual(1, result.missionClockVersion); Assert.AreEqual(60, result.missionDurationSeconds);
            var old = WorldRecordingHeader.Create(Guid.NewGuid(), Guid.NewGuid(), "Simulation", new[] { 1 }, new WorldProp[0]);
            Assert.AreEqual(0, codec.ReadHeader(codec.Header(old)).missionClockVersion);
        }
    }
}
