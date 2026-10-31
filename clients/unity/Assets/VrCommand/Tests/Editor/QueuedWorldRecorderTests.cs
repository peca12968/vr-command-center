using System;
using System.IO;
using System.Threading;
using NUnit.Framework;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class QueuedWorldRecorderTests
    {
        private static WorldRecordingPacket Packet(long sequence, bool ended = false)
        {
            var packet = WorldRecordingPacket.Capture(new ArenaWorld(new[]{3},new WorldProp[0]),sequence,(sequence-1)*100,1,0,0,_=>new RecordedRig());
            if(ended)packet.frame.phase="Ended";return packet;
        }
        private sealed class ControlledJournal : IWorldJournal
        {
            private readonly FileWorldJournal file;
            internal bool Block,Fail;
            internal int FrameThread;
            internal readonly ManualResetEventSlim Entered=new ManualResetEventSlim(),Release=new ManualResetEventSlim();
            internal ControlledJournal(string path){file=new FileWorldJournal(path,true);}
            public long Length=>file.Length;
            public WorldJournalRecord Read(long position)=>file.Read(position);
            public void Append(byte[] payload)
            {
                if(payload[0]==1)
                {
                    FrameThread=Environment.CurrentManagedThreadId;Entered.Set();
                    if(Block&&!Release.Wait(5000))throw new TimeoutException("Owned frame gate");
                    if(Fail)throw new IOException("Owned write failure");
                }
                file.Append(payload);
            }
            public void Dispose(){file.Dispose();Entered.Dispose();Release.Dispose();}
        }
        private sealed class Fixture : IDisposable
        {
            internal readonly string PathName=Path.Combine(Path.GetTempPath(),"vr-queued-world-"+Guid.NewGuid().ToString("N")+".worldlog");
            internal readonly UnityWorldCodec Codec=new UnityWorldCodec();
            internal readonly ControlledJournal Journal;
            internal readonly WorldOutbox Source;
            internal readonly QueuedWorldRecorder Writer;
            internal readonly WorldRecordingHeader Header;
            private bool sourceClosed;
            internal Fixture(bool block=false,int frames=32,int bytes=8*1024*1024)
            {
                Header=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",new[]{3},new WorldProp[0],"2026-11-01T00:00:00.0000000+00:00");
                Journal=new ControlledJournal(PathName){Block=block};Source=new WorldOutbox(Journal,Codec,Header);
                Writer=new QueuedWorldRecorder(Source,Codec,frames,bytes);
            }
            public void Dispose()
            {
                if(!sourceClosed)Journal.Release.Set();Writer.Stop();Assert.IsTrue(Writer.Completion.Wait(5000));Writer.Dispose();CloseSource();
                if(File.Exists(PathName))File.Delete(PathName);
            }
            internal void CloseSource(){if(sourceClosed)return;Source.Dispose();sourceClosed=true;}
        }
        [Test] public void CapturedFrameDoesNotAdvanceDurableStateOrBlockProducerDuringDiskWait()
        {
            using(var f=new Fixture(true))
            {
                var main=Environment.CurrentManagedThreadId;f.Writer.Enqueue(Packet(1));Assert.IsTrue(f.Journal.Entered.Wait(3000));
                Assert.AreEqual(1,f.Writer.CapturedSequence);Assert.AreEqual(1,f.Writer.PendingFrames);
                Assert.AreEqual(0,f.Source.State.LastSequence);Assert.IsFalse(f.Source.Complete);Assert.IsFalse(f.Source.Sealed);
                Assert.AreNotEqual(main,f.Journal.FrameThread);f.Journal.Release.Set();f.Writer.Stop();Assert.IsTrue(f.Writer.Completion.Wait(3000));
                Assert.AreEqual(1,f.Source.LastSequence);Assert.AreEqual(0,f.Source.AcknowledgedSequence);
            }
        }
        [Test] public void CallerMutationsNeverCrossIntoBackgroundPersistence()
        {
            using(var f=new Fixture(true))
            {
                var p=Packet(1);f.Writer.Enqueue(p);Assert.IsTrue(f.Journal.Entered.Wait(3000));p.sequence=99;p.frame.phase="Ended";
                f.Journal.Release.Set();f.Writer.Stop();Assert.IsTrue(f.Writer.Completion.Wait(3000));
                var saved=f.Codec.ReadPacket(f.Source.Pending.Json);Assert.AreEqual(1,saved.sequence);Assert.AreEqual("Preparing",saved.frame.phase);Assert.IsFalse(f.Source.Complete);
            }
        }
        [Test] public void OrderedDrainAndCompletionProduceTheExactSynchronousJournalBytes()
        {
            using(var f=new Fixture(true))
            {
                for(var i=1;i<=4;i++)f.Writer.Enqueue(Packet(i,i==4));
                Assert.IsTrue(f.Writer.EndQueued);Assert.IsFalse(f.Source.Complete);f.Writer.Stop();f.Journal.Release.Set();Assert.IsTrue(f.Writer.Completion.Wait(3000));
                Assert.AreEqual(4,f.Source.LastSequence);Assert.IsTrue(f.Source.Complete);Assert.IsFalse(f.Source.Sealed);Assert.AreEqual(0,f.Source.AcknowledgedSequence);
                var other=f.PathName+".sync";
                try
                {
                    using(var sync=WorldOutbox.Create(other,f.Header,f.Codec)){for(var i=1;i<=4;i++)sync.Append(Packet(i,i==4));sync.Finish();}
                    // The source is exclusively leased; compare after an explicit close.
                    f.CloseSource();Assert.AreEqual(File.ReadAllBytes(other),File.ReadAllBytes(f.PathName));
                }
                finally{if(File.Exists(other))File.Delete(other);}
            }
        }
        [Test] public void FrameCapacityIncludesInflightAndFailsClosedWithoutDroppingAcceptedFrames()
        {
            using(var f=new Fixture(true,2))
            {
                f.Writer.Enqueue(Packet(1));Assert.IsTrue(f.Journal.Entered.Wait(3000));f.Writer.Enqueue(Packet(2));
                Assert.Throws<InvalidOperationException>(()=>f.Writer.Enqueue(Packet(3)));Assert.IsTrue(f.Writer.Faulted);Assert.AreEqual(2,f.Writer.CapturedSequence);
                f.Journal.Release.Set();Assert.IsTrue(f.Writer.Completion.Wait(3000));Assert.AreEqual(2,f.Source.LastSequence);
                Assert.Throws<IOException>(()=>f.Writer.Enqueue(Packet(3)));Assert.IsFalse(f.Source.Complete);
            }
        }
        [Test] public void ByteCapacityRejectsBeforeAssigningTheFirstCaptureSequence()
        {
            using(var f=new Fixture(false,32,10))
            {
                Assert.Throws<InvalidOperationException>(()=>f.Writer.Enqueue(Packet(1)));Assert.AreEqual(0,f.Writer.CapturedSequence);
                Assert.IsTrue(f.Writer.Faulted);Assert.IsTrue(f.Writer.Completion.Wait(3000));Assert.AreEqual(0,f.Source.LastSequence);
            }
        }
        [Test] public void FailedDiskWriteCannotManufactureDurableFrameAckOrCompletion()
        {
            using(var f=new Fixture(true))
            {
                f.Journal.Fail=true;f.Writer.Enqueue(Packet(1));Assert.IsTrue(f.Journal.Entered.Wait(3000));f.Writer.Enqueue(Packet(2,true));
                f.Journal.Release.Set();Assert.IsTrue(f.Writer.Completion.Wait(3000));Assert.IsTrue(f.Writer.Faulted);
                Assert.AreEqual(2,f.Writer.CapturedSequence);Assert.AreEqual(0,f.Source.LastSequence);Assert.AreEqual(0,f.Source.AcknowledgedSequence);Assert.IsFalse(f.Source.Complete);
            }
        }
        [Test] public void StopDrainsAcceptedFramesAndKeepsExclusiveLeaseUntilOwnerClosesSource()
        {
            using(var f=new Fixture(true))
            {
                f.Writer.Enqueue(Packet(1));Assert.IsTrue(f.Journal.Entered.Wait(3000));f.Writer.Enqueue(Packet(2));f.Writer.Stop();
                Assert.IsFalse(f.Writer.Completion.IsCompleted);Assert.Throws<InvalidOperationException>(()=>f.Writer.Enqueue(Packet(3)));
                Assert.Throws<IOException>(()=>WorldOutbox.Recover(f.PathName,f.Codec));f.Journal.Release.Set();Assert.IsTrue(f.Writer.Completion.Wait(3000));
                f.CloseSource();using(var recovered=WorldOutbox.Recover(f.PathName,f.Codec)){Assert.AreEqual(2,recovered.LastSequence);Assert.IsFalse(recovered.Complete);}
            }
        }
        [Test] public void InvalidOrderAndConfigurationDoNotConsumeAcceptedCaptureBoundaries()
        {
            using(var f=new Fixture())
            {
                Assert.Throws<ArgumentOutOfRangeException>(()=>new QueuedWorldRecorder(f.Source,f.Codec,0));
                Assert.Throws<ArgumentException>(()=>f.Writer.Enqueue(Packet(2)));Assert.AreEqual(0,f.Writer.CapturedSequence);Assert.IsFalse(f.Writer.Faulted);
                f.Writer.Enqueue(Packet(1));Assert.Throws<ArgumentException>(()=>f.Writer.Enqueue(Packet(1)));
                f.Writer.Stop();Assert.IsTrue(f.Writer.Completion.Wait(3000));Assert.AreEqual(1,f.Source.LastSequence);
            }
        }
    }
}
