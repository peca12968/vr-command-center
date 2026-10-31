using System;
using NUnit.Framework;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class MissionDebriefTests
    {
        private static MissionDebrief Sample() => new MissionDebrief { sessionId = Guid.NewGuid().ToString("D"), playerId = Guid.NewGuid().ToString("D"),
            admissionId = Guid.NewGuid().ToString("D"), roomId = 3, origin = "Simulation", streamId = Guid.NewGuid().ToString("D"),
            throughSequence = 10, finalStreamSequence = 3, worldSequence = 20, ammoUsed = 3, shotsHit = 1, kills = 1,
            hitsReceived = 2, damageTaken = 20, health = 80, accuracyPercent = 33.33 };
        private static MissionDebrief Copy(MissionDebrief source) => JsonUtility.FromJson<MissionDebrief>(JsonUtility.ToJson(source));
        private static DebriefStatistics Statistics(MissionDebrief c) => new DebriefStatistics { sessionId = c.sessionId, origin = c.origin, throughSequence = 12,
            players = new[] { new DebriefPlayerStatistics { playerId = c.playerId, roomId = c.roomId, health = 80, ammoUsed = 3, shotsHit = 1,
                kills = 1, hitsReceived = 2, damageTaken = 20, accuracyPercent = 33.33 } } };
        private static TicketApproval Admission(MissionDebrief c) => new TicketApproval { sessionId = c.sessionId, playerId = c.playerId, admissionId = c.admissionId, roomId = c.roomId };
        [Test] public void ResultRequiresVersionIdentityAndFiniteConsistentMetrics()
        {
            var value = Sample(); Assert.IsTrue(value.Valid());
            value.accuracyPercent = double.NaN; Assert.IsFalse(value.Valid());
            value.accuracyPercent = 33.333; Assert.IsFalse(value.Valid());
            value.accuracyPercent = 33.33; value.version = 2; Assert.IsFalse(value.Valid());
            value.version = 1; value.admissionId = Guid.Empty.ToString(); Assert.IsFalse(value.Valid());
        }
        [Test] public void ImpossibleCountsAreRejectedAndZeroShotAccuracyIsDefined()
        {
            var value = Sample(); value.shotsHit = 4; Assert.IsFalse(value.Valid());
            value.shotsHit = 1; value.kills = 2; Assert.IsFalse(value.Valid());
            value.kills = 0; value.shotsHit = 0; value.ammoUsed = 0; value.accuracyPercent = 0; Assert.IsTrue(value.Valid());
            value.hitsReceived = -1; Assert.IsFalse(value.Valid());
            Assert.AreEqual(66.67, MissionDebrief.ExpectedAccuracy(3, 2));
        }
        [Test] public void UnannouncedAndOtherPlayersResultsCannotBeAccepted()
        {
            var state = new MissionDebriefState(); var value = Sample();
            Assert.IsFalse(state.Accept(value)); Assert.IsFalse(state.Begin(value, Guid.NewGuid().ToString()));
            Assert.IsFalse(state.Active); Assert.IsTrue(state.Begin(value, value.playerId)); Assert.IsTrue(state.Pending);
        }
        [Test] public void SessionAdmissionAndRoomRemainFenced()
        {
            var state = new MissionDebriefState(); var value = Sample(); state.Begin(value, value.playerId);
            var foreign = Copy(value); foreign.admissionId = Guid.NewGuid().ToString(); Assert.IsFalse(state.Accept(foreign));
            foreign = Copy(value); foreign.sessionId = Guid.NewGuid().ToString(); Assert.IsFalse(state.Accept(foreign));
            foreign = Copy(value); foreign.roomId = 4; Assert.IsFalse(state.Accept(foreign)); Assert.IsTrue(state.Pending);
        }
        [Test] public void FinalSequencesAndSourceCannotRegressOrChange()
        {
            var state = new MissionDebriefState(); var value = Sample(); state.Begin(value, value.playerId);
            var bad = Copy(value); bad.throughSequence--; Assert.IsFalse(state.Accept(bad));
            bad = Copy(value); bad.worldSequence++; Assert.IsFalse(state.Accept(bad));
            bad = Copy(value); bad.finalStreamSequence++; Assert.IsFalse(state.Accept(bad));
            bad = Copy(value); bad.streamId = Guid.NewGuid().ToString(); Assert.IsFalse(state.Accept(bad));
            bad = Copy(value); bad.origin = "GameServer"; Assert.IsFalse(state.Accept(bad));
        }
        [Test] public void FinalResultRemainsImmutableUntilExplicitReconnectClear()
        {
            var state = new MissionDebriefState(); var value = Sample(); state.Begin(value, value.playerId);
            var final = Copy(value); final.throughSequence++; Assert.IsTrue(state.Accept(final)); Assert.IsFalse(state.Pending);
            var changed = Copy(final); changed.health = 20; Assert.IsFalse(state.Accept(changed)); Assert.AreEqual(80, state.Result.health);
            state.Clear(); Assert.IsFalse(state.Active); Assert.IsNull(state.Result); Assert.IsFalse(state.Accept(final));
        }
        [Test] public void StatisticsNeedMatchingSealedSessionAndUniquePlayer()
        {
            var c = Sample(); var stats = Statistics(c); var admission = Admission(c);
            Assert.NotNull(stats.Select(admission, c));
            stats.pendingTelemetry = true; Assert.IsNull(stats.Select(admission, c)); stats.pendingTelemetry = false;
            stats.sessionId = Guid.NewGuid().ToString(); Assert.IsNull(stats.Select(admission, c)); stats.sessionId = c.sessionId;
            stats.throughSequence = 9; Assert.IsNull(stats.Select(admission, c)); stats.throughSequence = 12;
            stats.players = new[] { stats.players[0], stats.players[0] }; Assert.IsNull(stats.Select(admission, c));
        }
        [Test] public void SelectionDoesNotDiscloseOtherPlayersAndKeepsAdmission()
        {
            var c = Sample(); var stats = Statistics(c); var other = new DebriefPlayerStatistics { playerId = Guid.NewGuid().ToString(), roomId = 5 };
            stats.players = new[] { other, stats.players[0] }; var selected = stats.Select(Admission(c), c);
            Assert.AreEqual(c.playerId, selected.playerId); Assert.AreEqual(c.admissionId, selected.admissionId);
            StringAssert.DoesNotContain(other.playerId, JsonUtility.ToJson(selected));
            stats.players[1].roomId = 4; Assert.IsNull(stats.Select(Admission(c), c));
        }
        [Test] public void NoCombatCanHaveNullLedgerOriginButNonzeroCombatCannot()
        {
            var c = Sample(); var stats = Statistics(c); stats.origin = null;
            Assert.IsNull(stats.Select(Admission(c), c));
            stats.players[0] = new DebriefPlayerStatistics { playerId = c.playerId, roomId = c.roomId, health = 100 };
            Assert.IsNull(stats.Select(Admission(c), c)); c.finalStreamSequence = 0;
            Assert.NotNull(stats.Select(Admission(c), c));
            stats.players = new[] { stats.players[0], new DebriefPlayerStatistics { playerId = Guid.NewGuid().ToString(), roomId = 3, health = 100, ammoUsed = 1 } };
            Assert.IsNull(stats.Select(Admission(c), c));
        }
        [Test] public void ServerSelectionCannotMixAnotherAdmissionContext()
        {
            var c = Sample(); var stats = Statistics(c); var admission = Admission(c);
            admission.admissionId = Guid.NewGuid().ToString(); Assert.IsNull(stats.Select(admission, c));
            Assert.IsNull(stats.Select(null, c)); Assert.IsNull(stats.Select(Admission(c), null));
        }
        [Test] public void ActualApiNullOriginJsonProducesASealedZeroEventResult()
        {
            var c = Sample(); c.finalStreamSequence = 0;
            var json = "{\"sessionId\":\"" + c.sessionId + "\",\"throughSequence\":12,\"origin\":null,\"pendingTelemetry\":false,"
                + "\"players\":[{\"playerId\":\"" + c.playerId + "\",\"roomId\":3,\"ammoUsed\":0,\"shotsHit\":0,\"kills\":0,"
                + "\"hitsReceived\":0,\"damageTaken\":0,\"health\":100,\"accuracyPercent\":0}]}";
            var stats = JsonUtility.FromJson<DebriefStatistics>(json);
            var selected = stats.Select(Admission(c), c);
            Assert.NotNull(selected, "JsonUtility null origin was [" + stats.origin + "]");
            Assert.AreEqual("Simulation", selected.origin); Assert.AreEqual(0, selected.finalStreamSequence); Assert.AreEqual(100, selected.health);
        }
    }
}
