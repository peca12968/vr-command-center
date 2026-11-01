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
    }
}
