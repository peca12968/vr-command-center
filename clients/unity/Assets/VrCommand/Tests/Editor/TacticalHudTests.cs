using NUnit.Framework;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class TacticalHudTests
    {
        private const string Self = "00000000-0000-0000-0000-000000000001", Enemy = "00000000-0000-0000-0000-000000000002";
        private static CombatActorState Subject(float x = 0, float z = 3) => new CombatActorState
        { id = Enemy, position = new Vector3(x, 0, z), room = 3, health = 100, enemy = true, connected = true };
        private static bool Visible(CombatActorState subject, CombatPropState[] props = null, CombatActorState[] others = null)
            => TacticalHudRules.Visible(new Vector3(0, 1.65f, -3), 3, Self, subject, others ?? new CombatActorState[0], props ?? new CombatPropState[0]);

        [Test] public void EliminationCannotBeHiddenByLostTrackingAndPhasesRemainDistinct()
        {
            Assert.AreEqual("ELIMINATED", TacticalHudRules.Status("Running", 0, true, false, false, false, true));
            Assert.AreEqual("CONTROL LINK UNAVAILABLE", TacticalHudRules.Status("Running", 100, false, true, true, true, false));
            Assert.AreEqual("TRACKING INVALID", TacticalHudRules.Status("Running", 100, true, false, true, true, true));
            Assert.AreEqual("POSE REJECTED", TacticalHudRules.Status("Running", 100, true, false, true, true, false));
            foreach (var pair in new[] { new[] { "Preparing", "AWAITING START" }, new[] { "Paused", "MISSION PAUSED" }, new[] { "Ended", "MISSION ENDED" }, new[] { "Running", "ACTIVE" } })
                Assert.AreEqual(pair[1], TacticalHudRules.Status(pair[0], 100, true, true, true, true, false));
        }
        [Test] public void VenueBearingUsesPositiveZAndWrapsWithoutInventingGeographicNorth()
        {
            Assert.AreEqual(0, TacticalHudRules.Bearing(Vector3.forward), .001);
            Assert.AreEqual(90, TacticalHudRules.Bearing(Vector3.right), .001);
            Assert.AreEqual(180, TacticalHudRules.Bearing(Vector3.back), .001);
            Assert.AreEqual(270, TacticalHudRules.Bearing(Vector3.left), .001);
            Assert.AreEqual(0, TacticalHudRules.Bearing(new Vector3(float.NaN, 0, 1)));
        }
        [Test] public void RotatedCoverHidesTorsoLabelsUsingTheAuthoritativeFootprint()
        {
            var barrel = new CombatPropState { center = new Vector3(.4f, .6f, 1.5f), half = new Vector3(.35f, .6f, .35f), yaw = 0 };
            Assert.IsTrue(Visible(Subject(), new[] { barrel }));
            barrel.yaw = 45; Assert.IsFalse(Visible(Subject(), new[] { barrel }));
            var low = new CombatPropState { center = new Vector3(0, .45f, 0), half = new Vector3(1, .45f, .35f) };
            Assert.IsTrue(Visible(Subject(), new[] { low }), "A low sandbag does not hide an otherwise visible torso");
        }
        [Test] public void PeerOcclusionAndRoomHealthAdmissionFiltersPreventHiddenLabels()
        {
            var peer = new CombatActorState { id = "00000000-0000-0000-0000-000000000003", room = 3, position = new Vector3(0, 1.65f, 0), connected = true, health = 100 };
            Assert.IsFalse(Visible(Subject(), others: new[] { peer }));
            peer.health = 0; Assert.IsTrue(Visible(Subject(), others: new[] { peer }));
            var subject = Subject(); subject.room = 4; Assert.IsFalse(Visible(subject));
            subject = Subject(); subject.health = 0; Assert.IsFalse(Visible(subject));
            subject = Subject(); subject.connected = false; Assert.IsFalse(Visible(subject));
            subject = Subject(); subject.id = Self; Assert.IsFalse(Visible(subject));
        }
        [Test] public void NewlyOccludedPositionsAndInvalidOrDistantObserversDoNotKeepLabels()
        {
            var cover = new[] { new CombatPropState { center = new Vector3(0, .6f, 1.5f), half = new Vector3(.35f, .6f, .35f) } };
            Assert.IsTrue(Visible(Subject(2), cover)); Assert.IsFalse(Visible(Subject(), cover));
            Assert.IsFalse(Visible(Subject(0, 30)));
            Assert.IsFalse(TacticalHudRules.Visible(new Vector3(float.NaN, 0, 0), 3, Self, Subject(), new CombatActorState[0], new CombatPropState[0]));
        }
    }
}
