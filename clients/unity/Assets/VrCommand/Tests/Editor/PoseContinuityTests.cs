using System;
using NUnit.Framework;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class PoseContinuityTests
    {
        private static void Add(PoseContinuityBuffer b,double seconds,ulong id=44,string point="PoseReceive",double duration=0)
            =>b.Add(point,id,1,seconds,639290000000000001+(long)(seconds*10000000),1,seconds+3,duration);
        [Test] public void FrequentEventsAggregateAndSparseGapsKeepBothEndpoints()
        {
            var b=new PoseContinuityBuffer();Add(b,1);Add(b,1.05);Add(b,1.7);Add(b,1.75,duration:.25);
            var stream=b.Streams()[0];Assert.AreEqual(4,stream.count);Assert.AreEqual(.65,stream.maximumGapSeconds,1e-9);Assert.AreEqual(.25,stream.maximumDurationSeconds);
            Assert.AreEqual(2,b.Gaps().Length);Assert.AreEqual(1.05,b.Gaps()[0].fromSeconds);Assert.AreEqual(1.7,b.Gaps()[0].toSeconds);
            Assert.AreEqual(44,b.Gaps()[0].connection);Assert.AreEqual(639290000000000001+17000000,b.Gaps()[0].toUtcTicks);
        }
        [Test] public void OverflowKeepsEarliestGapsAndBoundsStreamsWithoutDroppingExistingCounters()
        {
            var b=new PoseContinuityBuffer(1);Add(b,1);Add(b,2);Add(b,3);
            Assert.IsTrue(b.Truncated);Assert.AreEqual(1,b.Gaps().Length);Assert.AreEqual(2,b.Gaps()[0].toSeconds);Assert.AreEqual(3,b.Streams()[0].count);
            b=new PoseContinuityBuffer();for(ulong i=0;i<257;i++)Add(b,1,i);Assert.IsTrue(b.Truncated);Assert.AreEqual(256,b.Streams().Length);
        }
        [Test] public void InvalidClocksAndCapacityCannotBecomeEvidence()
        {
            Assert.Throws<ArgumentOutOfRangeException>(()=>new PoseContinuityBuffer(0));Assert.Throws<ArgumentOutOfRangeException>(()=>new PoseContinuityBuffer(4097));
            var b=new PoseContinuityBuffer();Assert.Throws<ArgumentException>(()=>Add(b,double.NaN));Assert.Throws<ArgumentException>(()=>Add(b,1,duration:-1));Assert.IsEmpty(b.Streams());
            Add(b,2);Assert.Throws<ArgumentException>(()=>Add(b,1));Assert.AreEqual(1,b.Streams()[0].count);
        }
        [Test] public void SnapshotsCannotRewriteTheBuffersAggregatedEvidence()
        {
            var b=new PoseContinuityBuffer();Add(b,1);var snapshot=b.Streams();snapshot[0].count=999;Add(b,1.05);
            Assert.AreEqual(2,b.Streams()[0].count);Assert.AreEqual(999,snapshot[0].count);
        }
        [Test] public void BodyChangesSeparateUnacceptedAndExpiredAcceptedAges()
        {
            var b=new PoseContinuityBuffer();b.Connection(44,false,1,100,1);Add(b,2,point:"PoseAccepted");b.Connection(44,true,2.1,200,2);
            b.Connection(44,true,2.2,300,3);b.Connection(44,false,2.6,400,4);var changes=b.Bodies();
            Assert.AreEqual(3,changes.Length);Assert.AreEqual(-1,changes[0].poseAgeSeconds);Assert.AreEqual(.6,changes[2].poseAgeSeconds,1e-9);
            Assert.IsFalse(changes[2].connected);Assert.IsFalse(b.Truncated);
        }
        [Test] public void ModesKeepLegacyBoundsAndCannotInstallConflictingCollectors()
        {
            NativePoseContinuity.ValidateOptions(Array.Empty<string>());
            NativePoseContinuity.ValidateOptions(new[]{"--vr-pose-continuity","unused","--vr-pose-continuity-loop"});
            Assert.Throws<ArgumentException>(()=>NativePoseContinuity.ValidateOptions(new[]{"--vr-pose-continuity-loop"}));
            Assert.Throws<ArgumentException>(()=>NativePoseContinuity.ValidateOptions(new[]{"--vr-pose-continuity","unused","--vr-pose-trace","other"}));
            Assert.AreEqual(240,new NativePoseTrace.Report().maximumSeconds);Assert.AreEqual(1200,new NativePoseContinuity.Report().maximumSeconds);
            Assert.IsFalse(NativePoseTrace.AnyEnabled);Assert.IsFalse(NativePoseContinuity.Enabled);using(NativePoseTrace.Measure("WorldCapture")){}
        }
        [Test] public void CounterIdentityMonotonicityAnd64BitJsonStayExplicit()
        {
            var before=new OwnThreadCounters.Stamp{threadId=42,creationTime=100,cycles=9007199254740993,kernel100ns=10,user100ns=20,fromSeconds=1,toSeconds=1.001};
            var after=before;after.cycles++;after.fromSeconds=2;after.toSeconds=2.001;Assert.IsTrue(OwnThreadCounters.Follows(before,after));
            after.threadId++;Assert.IsFalse(OwnThreadCounters.Follows(before,after));after=before;after.cycles--;Assert.IsFalse(OwnThreadCounters.Follows(before,after));
            var report=new NativePoseContinuity.Report{threadWindows=new[]{new NativePoseContinuity.ThreadWindow{before=before,after=before}}};
            var json=JsonUtility.ToJson(report);var read=JsonUtility.FromJson<NativePoseContinuity.Report>(json);
            Assert.AreEqual(before.cycles,read.threadWindows[0].before.cycles);Assert.IsFalse(json.Contains("joinTicket"));Assert.IsFalse(json.Contains("headPosition"));
        }
        [Test] public void ActualWindowsCountersReferToTheCallingEditorThread()
        {
#if UNITY_EDITOR_WIN
            var clock=System.Diagnostics.Stopwatch.StartNew();var before=OwnThreadCounters.Read(()=>clock.Elapsed.TotalSeconds);
            var after=OwnThreadCounters.Read(()=>clock.Elapsed.TotalSeconds);
            Assert.Greater(before.threadId,0);Assert.Greater(before.creationTime,0);Assert.IsTrue(OwnThreadCounters.Follows(before,after));
#else
            Assert.Ignore("Windows calling-thread API only.");
#endif
        }
    }
}
