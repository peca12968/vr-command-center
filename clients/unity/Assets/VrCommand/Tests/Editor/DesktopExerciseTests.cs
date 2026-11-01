using NUnit.Framework;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class DesktopExerciseTests
    {
        [Test] public void ContextIsOnlyWindowsDevelopmentBatchClientWithoutTrackedDevice()
        {
            Assert.IsTrue(DesktopExercisePlan.Allowed("Client", true, true, true, false, false));
            Assert.IsFalse(DesktopExercisePlan.Allowed("Server", true, true, true, false, false));
            Assert.IsFalse(DesktopExercisePlan.Allowed("Host", true, true, true, false, false));
            Assert.IsFalse(DesktopExercisePlan.Allowed("Client", false, true, true, false, false));
            Assert.IsFalse(DesktopExercisePlan.Allowed("Client", true, false, true, false, false));
            Assert.IsFalse(DesktopExercisePlan.Allowed("Client", true, true, false, false, false));
            Assert.IsFalse(DesktopExercisePlan.Allowed("Client", true, true, true, true, false));
            Assert.IsFalse(DesktopExercisePlan.Allowed("Client", true, true, true, false, true));
        }
        [Test] public void InactiveInputDoesNotStartOrAdvanceThePlan()
        {
            var plan = new DesktopExercisePlan(); Assert.AreEqual(Vector2.zero, plan.Next(400, false).Movement); Assert.AreEqual(-1, plan.FirstTick);
            Assert.AreEqual(.2f, plan.Next(500, true).Movement.y); Assert.AreEqual(500, plan.FirstTick);
            Assert.IsFalse(plan.Next(900, false).Fire); Assert.AreEqual(500, plan.LastTick);
        }
        [Test] public void FireOffersPersistUntilTheNormalWeaponPathSubmitsThem()
        {
            var plan = new DesktopExercisePlan(); plan.Next(100, true);
            Assert.IsFalse(plan.Next(119, true).Fire); Assert.IsTrue(plan.Next(120, true).Fire); Assert.IsTrue(plan.Next(121, true).Fire);
            plan.SubmittedFire(); Assert.IsFalse(plan.Next(121, true).Fire); Assert.IsFalse(plan.Next(219, true).Fire);
            Assert.IsTrue(plan.Next(220, true).Fire); plan.SubmittedFire(); Assert.IsFalse(plan.Next(230, true).Fire);
            Assert.Throws<System.InvalidOperationException>(() => plan.SubmittedFire());
        }
        [Test] public void ReloadIsOneIntentAndDoesNotRepeatWhileItsTickIsUnchanged()
        {
            var plan = new DesktopExercisePlan(); plan.Next(1, true); Assert.IsFalse(plan.Next(60, true).Reload);
            Assert.IsTrue(plan.Next(61, true).Reload); plan.SubmittedReload(); Assert.IsFalse(plan.Next(61, true).Reload);
            Assert.Throws<System.InvalidOperationException>(() => plan.SubmittedReload());
        }
        [Test] public void MovementUsesBoundedOrdinaryDesktopInputAndReversesAtFortyTicks()
        {
            var plan = new DesktopExercisePlan(); var frame = plan.Next(20, true);
            Assert.AreEqual(new Vector2(0, .2f), frame.Movement); Assert.AreEqual(-.2f, plan.Next(60, true).Movement.y);
            Assert.AreEqual(.2f, plan.Next(100, true).Movement.y);
            var moved = DesktopPreviewControls.Move(Vector3.zero, Quaternion.identity, frame.Movement, .1f, Vector3.zero);
            Assert.AreEqual(.04f, moved.z, .000001f);
        }
        [Test] public void BackwardActiveTicksFailRatherThanRestartingWeaponIntents()
        {
            var plan = new DesktopExercisePlan(); plan.Next(100, true);
            Assert.Throws<System.InvalidOperationException>(() => plan.Next(99, true));
        }
        [Test] public void ActiveInputStopsAtTheBoundAndCannotBeReactivated()
        {
            var plan = new DesktopExercisePlan(); plan.Next(10, true);
            Assert.AreEqual(Vector2.zero, plan.Next(1210, true).Movement); Assert.IsTrue(plan.Exhausted);
            Assert.IsFalse(plan.Next(11, true).Fire);
        }
        [Test] public void EnduranceUsesFortyFiveNormalTwoShotReloadCyclesWithinOriginalAmmunition()
        {
            var plan = new DesktopExercisePlan(true); var fires = 0; var reloads = 0;
            for (var tick = 0; tick < DesktopExercisePlan.EnduranceWeaponTicks; tick++)
            {
                var frame = plan.Next(tick, true);
                if (frame.Reload) { plan.SubmittedReload(); reloads++; }
                if (frame.Fire) { plan.SubmittedFire(); fires++; }
            }
            Assert.AreEqual(90, fires); Assert.AreEqual(45, reloads); Assert.Less(fires, 120);
            Assert.IsFalse(plan.Exhausted);
            var tail = plan.Next(18000, true); Assert.IsFalse(tail.Fire); Assert.IsFalse(tail.Reload); Assert.AreNotEqual(Vector2.zero, tail.Movement);
        }
        [Test] public void EnduranceDoesNotRepeatAnIntentAtAnUnchangedTickOrAtCycleStart()
        {
            var plan = new DesktopExercisePlan(true); plan.Next(0, true);
            Assert.IsTrue(plan.Next(20, true).Fire); plan.SubmittedFire(); Assert.IsFalse(plan.Next(20, true).Fire);
            plan.Next(60, true); plan.SubmittedReload(); plan.Next(120, true); plan.SubmittedFire();
            Assert.IsFalse(plan.Next(399, true).Fire); Assert.IsFalse(plan.Next(400, true).Fire);
            Assert.IsTrue(plan.Next(420, true).Fire); plan.SubmittedFire(); Assert.IsFalse(plan.Next(420, true).Fire);
        }
        [Test] public void EnduranceCannotCatchUpAnIncompletePriorCycle()
        {
            var plan = new DesktopExercisePlan(true); plan.Next(0, true); plan.Next(20, true); plan.SubmittedFire();
            Assert.Throws<System.InvalidOperationException>(() => plan.Next(400, true));
        }
        [Test] public void EnduranceCannotSkipACompleteCycleAndReplayMissingShots()
        {
            var plan = new DesktopExercisePlan(true); plan.Next(0, true);
            plan.Next(20, true); plan.SubmittedFire(); plan.Next(60, true); plan.SubmittedReload(); plan.Next(120, true); plan.SubmittedFire();
            Assert.Throws<System.InvalidOperationException>(() => plan.Next(800, true));
        }
        [Test] public void EnduranceInactiveObservationsCannotRestartOrAdvanceIntentCounters()
        {
            var plan = new DesktopExercisePlan(true); plan.Next(0, true); plan.Next(20, true); plan.SubmittedFire();
            Assert.AreEqual(Vector2.zero, plan.Next(800, false).Movement); Assert.AreEqual(20, plan.LastTick);
            Assert.IsFalse(plan.Next(20, true).Fire);
        }
        [Test] public void EnduranceRetainsBackwardClockRejection()
        {
            var plan = new DesktopExercisePlan(true); plan.Next(100, true);
            Assert.Throws<System.InvalidOperationException>(() => plan.Next(99, true));
        }
        [Test] public void EnduranceHasItsOwnFiniteBoundWithoutChangingTheShortPlan()
        {
            var plan = new DesktopExercisePlan(true); plan.Next(0, true);
            Assert.AreEqual(Vector2.zero, plan.Next(19000, true).Movement); Assert.IsTrue(plan.Exhausted); Assert.IsFalse(plan.Next(1, true).Fire);
            Assert.AreEqual(1200, DesktopExercisePlan.MaximumActiveTicks);
        }
        [Test] public void EnduranceReversesAtItsOwnLocalPositionLimits()
        {
            var plan = new DesktopExercisePlan(true);
            Assert.AreEqual(.2f, plan.Next(0, true, 10).Movement.y);
            Assert.AreEqual(-.2f, plan.Next(1, true, 10.81f).Movement.y);
            Assert.AreEqual(.2f, plan.Next(2, true, 9.99f).Movement.y);
        }
        [Test] public void EnduranceFeedbackWorksWhileTheReceivedTickIsUnchanged()
        {
            var plan = new DesktopExercisePlan(true);
            Assert.AreEqual(.2f, plan.Next(0, true, 0).Movement.y);
            Assert.AreEqual(-.2f, plan.Next(0, true, .81f).Movement.y);
            Assert.AreEqual(-.2f, plan.Next(0, true, .4f).Movement.y);
            Assert.AreEqual(.2f, plan.Next(0, true, -.01f).Movement.y);
        }
        [Test] public void UnevenUpdateDurationsCannotAccumulateOutsideTheOriginalTestLane()
        {
            var plan = new DesktopExercisePlan(true); var current = Vector3.zero; var original = Vector3.zero; var oldEscaped = false;
            for (var tick = 0; tick < 18000; tick++)
            {
                var seconds = tick % 80 < 40 ? .049f : .051f;
                var frame = plan.Next(tick, true, current.z);
                if (frame.Reload) plan.SubmittedReload();
                if (frame.Fire) plan.SubmittedFire();
                current = DesktopPreviewControls.Move(current, Quaternion.identity, frame.Movement, seconds, Vector3.zero);
                // Frozen 0.41 tick-direction formula, with the same Move/deltaTime.
                original = DesktopPreviewControls.Move(original, Quaternion.identity, new Vector2(0, (tick / 40) % 2 == 0 ? .2f : -.2f), seconds, Vector3.zero);
                oldEscaped |= original.z < -.4f || original.z > 1.4f;
                Assert.That(current.z, Is.InRange(-.05f, .85f));
            }
            Assert.IsTrue(oldEscaped, "The former open-loop input must reproduce drift under unequal integration steps.");
        }
        [Test] public void EnduranceRejectsNonFiniteLocalFeedback()
        {
            foreach (var value in new[] { float.NaN, float.PositiveInfinity, float.NegativeInfinity })
                Assert.Throws<System.InvalidOperationException>(() => new DesktopExercisePlan(true).Next(0, true, value));
        }
    }
}
