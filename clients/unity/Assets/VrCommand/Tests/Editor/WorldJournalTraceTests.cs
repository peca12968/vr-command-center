using System;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using NUnit.Framework;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class WorldJournalTraceTests
    {
        [Test] public void BoundsDrainAndCopiedStampsCannotDoubleFinish()
        {
            Assert.Throws<ArgumentOutOfRangeException>(() => new WorldJournalTrace(0));
            Assert.Throws<ArgumentOutOfRangeException>(() => new WorldJournalTrace(32769));
            var trace = new WorldJournalTrace(); var stamps = new WorldJournalTrace.Stamp[64];
            for(var i=0;i<64;i++) stamps[i]=trace.Begin(0,1,i);
            trace.Begin(0,1).Finish(true); Assert.IsTrue(trace.Truncated); Assert.AreEqual(64,trace.InFlight);
            trace.Stop(); trace.Begin(0,1).Finish(true); Assert.AreEqual(64,trace.InFlight);
            foreach(var stamp in stamps){stamp.Finish(true);stamp.Finish(false);}
            Assert.AreEqual(0,trace.InFlight);Assert.AreEqual(64,trace.Snapshot().Length);
            Assert.IsTrue(trace.Snapshot().All(row=>row.succeeded));
        }
        [Test] public void CompletedRowCapacityKeepsEarliestAndContainsOnlyTimingMetadata()
        {
            var trace=new WorldJournalTrace(2);
            for(var i=1;i<=3;i++)trace.Begin(2,2,i).Finish(true);
            trace.Stop();Assert.IsTrue(trace.Truncated);Assert.AreEqual(new long[]{1,2},trace.Snapshot().Select(row=>row.sequence).ToArray());
            Assert.IsTrue(typeof(WorldJournalTimingRow).GetFields().All(field=>field.FieldType==typeof(int)||field.FieldType==typeof(long)||field.FieldType==typeof(bool)));
        }
        private static string PathFor()=>Path.Combine(Path.GetTempPath(),"vr-journal-trace-"+Guid.NewGuid().ToString("N")+".worldlog");
        private static WorldRecordingPacket Packet(long sequence)
        {
            var world=new ArenaWorld(new[]{3},new WorldProp[0]);
            return WorldRecordingPacket.Capture(world,sequence,(sequence-1)*100,1,0,0,_=>new RecordedRig());
        }
        [Test] public void TracedAndUntracedDurableFilesAreByteIdentical()
        {
            var a=PathFor();var b=PathFor();var trace=new WorldJournalTrace();var codec=new UnityWorldCodec();
            var header=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",new[]{3},new WorldProp[0],"2026-10-31T00:00:00.0000000+00:00");
            try
            {
                foreach(var path in new[]{a,b})
                {
                    using(var source=WorldOutbox.Create(path,header,codec,path==a?trace:null))
                    {source.Append(Packet(1));source.Acknowledge(1);}
                }
                Assert.AreEqual(File.ReadAllBytes(a),File.ReadAllBytes(b));trace.Stop();
                foreach(var op in new[]{0,1,2})
                {
                    Assert.IsTrue(trace.Snapshot().Any(row=>row.stage==1&&row.operation==op&&row.succeeded));
                    Assert.IsTrue(trace.Snapshot().Any(row=>row.stage==2&&row.operation==op&&row.succeeded));
                }
                Assert.IsTrue(trace.Snapshot().Any(row=>row.stage==2&&row.operation==2&&row.sequence==1));
                Assert.IsTrue(trace.Snapshot().All(row=>row.endedTimestamp>=row.startedTimestamp));
            }
            finally{if(File.Exists(a))File.Delete(a);if(File.Exists(b))File.Delete(b);}
        }
        private sealed class BlockReceipt : IWorldJournal
        {
            private readonly IWorldJournal inner;
            internal readonly ManualResetEventSlim entered=new ManualResetEventSlim(),release=new ManualResetEventSlim();
            internal BlockReceipt(IWorldJournal inner){this.inner=inner;}
            public long Length=>inner.Length;
            public WorldJournalRecord Read(long position)=>inner.Read(position);
            public void Append(byte[] payload)
            {
                if(payload[0]==2){entered.Set();if(!release.Wait(5000))throw new TimeoutException("Owned receipt gate");}
                inner.Append(payload);
            }
            public void Dispose(){inner.Dispose();entered.Dispose();release.Dispose();}
        }
        [Test] public void PendingReceiptBlocksFrameButDurableStateReadsRemainNonblocking()
        {
            var path=PathFor();var trace=new WorldJournalTrace();var codec=new UnityWorldCodec();
            var header=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",new[]{3},new WorldProp[0]);
            var journal=new BlockReceipt(new FileWorldJournal(path,true,trace));var source=new WorldOutbox(journal,codec,header,trace);
            Task ack=null,frame=null,state=null;
            try
            {
                source.Append(Packet(1));ack=Task.Run(()=>source.Acknowledge(1));Assert.IsTrue(journal.entered.Wait(3000));
                frame=Task.Run(()=>source.Append(Packet(2)));state=Task.Run(()=>{var observed=source.LastSequence;Assert.GreaterOrEqual(observed,1);});
                Assert.IsTrue(state.Wait(1000));Assert.AreEqual(0,source.AcknowledgedSequence);
                Assert.IsTrue(SpinWait.SpinUntil(()=>trace.InFlight>=1,3000));Thread.Sleep(80);journal.release.Set();
                Assert.IsTrue(Task.WaitAll(new[]{ack,frame,state},5000));trace.Stop();
                Assert.IsTrue(trace.Snapshot().Any(row=>row.stage==0&&row.operation==1&&(row.endedTimestamp-row.startedTimestamp)/(double)System.Diagnostics.Stopwatch.Frequency>=.05));
                Assert.IsFalse(trace.Snapshot().Any(row=>row.stage==0&&row.operation==6));
                Assert.AreEqual(1,source.AcknowledgedSequence);Assert.AreEqual(2,source.LastSequence);
            }
            finally
            {
                journal.release.Set();foreach(var task in new[]{ack,frame,state})if(task!=null)task.Wait(5000);
                source.Dispose();if(File.Exists(path))File.Delete(path);
            }
        }
        [Test] public void FailedWriteIsRecordedAsFailureAndNeverInventsSuccessfulFlush()
        {
            var path=PathFor();var trace=new WorldJournalTrace();var journal=new FileWorldJournal(path,true,trace);journal.Dispose();
            try
            {
                Assert.Throws<ObjectDisposedException>(()=>journal.Append(new byte[]{1,123}));
                Assert.Throws<IOException>(()=>journal.Append(new byte[]{1,123}));trace.Stop();
                Assert.AreEqual(1,trace.Snapshot().Length);Assert.IsFalse(trace.Snapshot()[0].succeeded);Assert.AreEqual(1,trace.Snapshot()[0].stage);
            }
            finally{if(File.Exists(path))File.Delete(path);}
        }
        [Test] public void ConcurrentStopDrainsAlreadyStartedSpansAndRejectsNewObservations()
        {
            var trace=new WorldJournalTrace();using(var ready=new CountdownEvent(4))using(var release=new ManualResetEventSlim())
            {
                var threads=Enumerable.Range(0,4).Select(i=>new Thread(()=>{var stamp=trace.Begin(2,2,i);ready.Signal();release.Wait();stamp.Finish(true);stamp.Finish(false);})).ToArray();
                foreach(var thread in threads)thread.Start();
                try{Assert.IsTrue(ready.Wait(3000));trace.Stop();Assert.AreEqual(4,trace.InFlight);trace.Begin(0,1).Finish(true);}
                finally{release.Set();foreach(var thread in threads)Assert.IsTrue(thread.Join(3000));}
                Assert.AreEqual(0,trace.InFlight);Assert.AreEqual(4,trace.Snapshot().Length);Assert.IsFalse(trace.Truncated);
            }
        }
    }
}
