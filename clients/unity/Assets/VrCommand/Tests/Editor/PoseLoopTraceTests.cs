using System;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.LowLevel;

namespace VrCommand.Unity.Tests
{
    public sealed class PoseLoopTraceTests
    {
        private sealed class EngineNode{}
        private sealed class LaterNode{}
        private static void NoOp(){}
        private static PlayerLoopSystem Tree()=>new PlayerLoopSystem{type=typeof(PoseLoopTraceTests),subSystemList=new[]{
            new PlayerLoopSystem{type=typeof(EngineNode),updateDelegate=NoOp,updateFunction=new IntPtr(123),loopConditionFunction=new IntPtr(456),
                subSystemList=new[]{new PlayerLoopSystem{type=typeof(LaterNode),updateDelegate=NoOp}}}}};
        private static void Same(PlayerLoopSystem expected,PlayerLoopSystem actual)
        {
            Assert.AreEqual(expected.type,actual.type);Assert.AreEqual(expected.updateDelegate,actual.updateDelegate);
            Assert.AreEqual(expected.updateFunction,actual.updateFunction);Assert.AreEqual(expected.loopConditionFunction,actual.loopConditionFunction);
            if(expected.subSystemList==null){Assert.IsNull(actual.subSystemList);return;}
            Assert.AreEqual(expected.subSystemList.Length,actual.subSystemList.Length);
            for(var i=0;i<expected.subSystemList.Length;i++)Same(expected.subSystemList[i],actual.subSystemList[i]);
        }
        [Test] public void SiblingInsertionPreservesNativeFunctionsConditionsAndOriginalArrays()
        {
            var original=Tree();var trace=new NativePoseLoopTrace(()=>1,()=>100,()=>1);var decorated=trace.Decorate(original);
            Assert.AreEqual(1,original.subSystemList.Length);Assert.AreEqual(3,decorated.subSystemList.Length);
            Assert.AreEqual(original.subSystemList[0].updateDelegate,decorated.subSystemList[1].updateDelegate);
            Same(original,trace.Remove(decorated));
            Assert.Throws<InvalidOperationException>(()=>trace.Decorate(original));
        }
        [Test] public void RemovalKeepsLaterChangesAndAnotherOwnersMarkers()
        {
            var original=Tree();var a=new NativePoseLoopTrace(()=>1,()=>100,()=>1);var b=new NativePoseLoopTrace(()=>1,()=>100,()=>1);
            var decorated=b.Decorate(a.Decorate(original));var later=new PlayerLoopSystem{type=typeof(LaterNode),updateDelegate=NoOp};
            var children=new System.Collections.Generic.List<PlayerLoopSystem>(decorated.subSystemList);children.Add(later);decorated.subSystemList=children.ToArray();
            var removed=a.Remove(decorated);Assert.Greater(removed.subSystemList.Length,2);
            var both=b.Remove(removed);Same(original.subSystemList[0],both.subSystemList[0]);Same(later,both.subSystemList[1]);
        }
        [Test] public void AdjacentBoundaryGapIdentifiesInsideNodeAndAcrossFrameWithoutCpuAttribution()
        {
            double time=1;long utc=639290000000000001;var frame=8;
            var trace=new NativePoseLoopTrace(()=>time,()=>utc,()=>frame);var loop=trace.Decorate(Tree());
            var before=loop.subSystemList[0];var after=loop.subSystemList[2];before.updateDelegate();
            time+=.75;utc+=7500000;after.updateDelegate();time+=.6;utc+=6000000;frame++;before.updateDelegate();
            var report=trace.Stop(true,true);Assert.IsTrue(report.complete);Assert.AreEqual(2,report.gaps.Length);
            var inside=report.gaps[0];Assert.AreEqual("before",report.boundaries[inside.fromBoundary].side);
            Assert.AreEqual("after",report.boundaries[inside.toBoundary].side);Assert.AreEqual(inside.fromFrame,inside.toFrame);
            Assert.AreEqual(8,report.gaps[1].fromFrame);Assert.AreEqual(9,report.gaps[1].toFrame);Assert.AreEqual(0,report.maximumClockStepSeconds,1e-9);
        }
        [Test] public void OverflowKeepsFirstGapAndSnapshotsDoNotAliasCounters()
        {
            double time=1;var trace=new NativePoseLoopTrace(()=>time,()=>100,()=>1,1);var marker=trace.Decorate(Tree()).subSystemList[0].updateDelegate;
            marker();time+=.2;marker();time+=.3;marker();var report=trace.Stop(true,true);
            Assert.IsTrue(report.truncated);Assert.IsFalse(report.complete);Assert.AreEqual(1,report.gaps.Length);
            Assert.AreEqual(1.2,report.gaps[0].toSeconds,1e-9);report.boundaries[0].calls=999;
            Assert.AreEqual(3,trace.Stop(true,true).boundaries[0].calls);
        }
        [Test] public void InvalidClockAndTreeBoundsFailBeforeUnsafeDecoration()
        {
            Assert.Throws<ArgumentOutOfRangeException>(()=>new NativePoseLoopTrace(()=>1,()=>1,()=>1,0));
            var oversized=new PlayerLoopSystem{subSystemList=new PlayerLoopSystem[513]};var trace=new NativePoseLoopTrace(()=>1,()=>1,()=>1);
            Assert.Throws<InvalidOperationException>(()=>trace.Decorate(oversized));Assert.AreEqual(513,oversized.subSystemList.Length);
            var deep=new PlayerLoopSystem();for(var i=0;i<34;i++)deep=new PlayerLoopSystem{subSystemList=new[]{deep}};
            Assert.Throws<InvalidOperationException>(()=>trace.Decorate(deep));
            double time=1;trace=new NativePoseLoopTrace(()=>time,()=>1,()=>1);var marker=trace.Decorate(Tree()).subSystemList[0].updateDelegate;
            marker();time=0;Assert.Throws<InvalidOperationException>(()=>marker());time=double.NaN;Assert.Throws<InvalidOperationException>(()=>marker());
        }
        [Test] public void ClockStepsRemainVisibleJsonKeepsTicksAndStoppedCallbacksAreNoOps()
        {
            double time=1;long utc=639290000000000001;var trace=new NativePoseLoopTrace(()=>time,()=>utc,()=>1);
            var marker=trace.Decorate(Tree()).subSystemList[0].updateDelegate;marker();time+=.2;utc+=4000000;marker();
            var report=trace.Stop(true,false);Assert.IsFalse(report.complete);Assert.AreEqual(.2,report.maximumClockStepSeconds,1e-9);
            var read=JsonUtility.FromJson<NativePoseLoopTrace.Report>(JsonUtility.ToJson(report));Assert.AreEqual(639290000000000001,read.firstUtcTicks);
            marker();Assert.AreEqual(2,trace.Stop(true,true).callbacks);
        }
        [Test] public void ActualEditorCurrentLoopRoundTripsWithoutInstallingOrResettingIt()
        {
            var original=PlayerLoop.GetCurrentPlayerLoop();var trace=new NativePoseLoopTrace(()=>1,()=>1,()=>1);
            Same(original,trace.Remove(trace.Decorate(original)));Same(original,PlayerLoop.GetCurrentPlayerLoop());
            Assert.IsFalse(NativePoseTrace.Enabled);
        }
    }
}
