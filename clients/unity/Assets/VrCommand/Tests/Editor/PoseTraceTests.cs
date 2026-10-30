using System;
using NUnit.Framework;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class PoseTraceTests
    {
        private static PoseTraceRow Row()=>new PoseTraceRow{point="PoseSend",seconds=1,engineSeconds=3,utcTicks=639290000000000001,frame=10,connection=44,source=1,poseAgeSeconds=-1};
        [Test] public void BoundedTraceRetainsEarliestEvidenceAndDoesNotAliasSnapshots()
        {
            var buffer=new PoseTraceBuffer(2);var first=Row();buffer.Add(first);first.point="Rewritten";var second=Row();second.seconds=2;buffer.Add(second);buffer.Add(Row());
            Assert.IsTrue(buffer.Truncated);var rows=buffer.Snapshot();Assert.AreEqual(2,rows.Length);Assert.AreEqual("PoseSend",rows[0].point);Assert.AreEqual(2,rows[1].seconds);
            rows[0].point="Outside mutation";Assert.AreEqual("PoseSend",buffer.Snapshot()[0].point);
        }
        [Test] public void TraceRejectsInvalidClocksAndCapacityWithoutAddingEvidence()
        {
            Assert.Throws<ArgumentOutOfRangeException>(()=>new PoseTraceBuffer(0));Assert.Throws<ArgumentOutOfRangeException>(()=>new PoseTraceBuffer(32769));
            var b=new PoseTraceBuffer();Assert.Throws<ArgumentException>(()=>b.Add(default));
            var r=Row();r.seconds=double.NaN;Assert.Throws<ArgumentException>(()=>b.Add(r));r=Row();r.engineSeconds=-1;Assert.Throws<ArgumentException>(()=>b.Add(r));
            r=Row();r.durationSeconds=-1;Assert.Throws<ArgumentException>(()=>b.Add(r));r=Row();r.poseAgeSeconds=-2;Assert.Throws<ArgumentException>(()=>b.Add(r));
            r=Row();r.durationSeconds=double.PositiveInfinity;Assert.Throws<ArgumentException>(()=>b.Add(r));Assert.IsEmpty(b.Snapshot());
        }
        [Test] public void JsonUtilityKeepsExactUtcTicksAndSeparatesCompletionFromTruncation()
        {
            var report=new NativePoseTrace.Report{role="Server",complete=false,truncated=true,stopReason="Duration limit",rows=new[]{Row()}};
            var json=JsonUtility.ToJson(report);var read=JsonUtility.FromJson<NativePoseTrace.Report>(json);
            Assert.AreEqual(639290000000000001,read.rows[0].utcTicks);Assert.AreEqual(44,read.rows[0].connection);Assert.AreEqual(-1,read.rows[0].poseAgeSeconds);
            Assert.IsFalse(read.complete);Assert.IsTrue(read.truncated);Assert.AreEqual("NativeWindowsMonotonicTiming",read.source);
            Assert.IsFalse(json.Contains("headRotation"));Assert.IsFalse(json.Contains("gameServerKey"));Assert.IsFalse(json.Contains("joinTicket"));
        }
        [Test] public void OrdinaryEditorRunHasNoActiveTraceOrMeasureSideEffects()
        {
            Assert.IsFalse(NativePoseTrace.Enabled);NativePoseTrace.Event("PoseSend",44,1);NativePoseTrace.OwnerUnavailable("TrackingUnavailable",44);
            NativePoseTrace.Sending(44,1);NativePoseTrace.Accepted(44,1);NativePoseTrace.Body(44,false);
            using(NativePoseTrace.Measure("WorldJournal")){}Assert.IsFalse(NativePoseTrace.Enabled);
        }
        [Test] public void InvalidPeerSourceByteCanBeObservedWithoutChangingAuthorityRejection()
        {
            var invalid=new AvatarPose{source=255};Assert.IsFalse(invalid.Valid());
            var row=Row();row.point="PoseInvalid";row.source=invalid.source;var buffer=new PoseTraceBuffer();buffer.Add(row);
            var report=JsonUtility.FromJson<NativePoseTrace.Report>(JsonUtility.ToJson(new NativePoseTrace.Report{rows=buffer.Snapshot()}));
            Assert.AreEqual(255,report.rows[0].source);
            row.source=256;Assert.Throws<ArgumentException>(()=>buffer.Add(row));
            row.source=-1;Assert.Throws<ArgumentException>(()=>buffer.Add(row));
        }
    }
}
