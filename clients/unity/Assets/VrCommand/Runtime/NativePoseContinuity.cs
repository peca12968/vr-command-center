using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.LowLevel;

namespace VrCommand.Unity
{
    // A separate sparse long-run diagnostic. Legacy 240s traces remain unchanged.
    public sealed class PoseContinuityBuffer
    {
        [Serializable] public sealed class Stream
        {
            public string point; public ulong connection; public int source;
            public long count,firstUtcTicks,lastUtcTicks; public int firstFrame,lastFrame;
            public double firstSeconds,lastSeconds,lastEngineSeconds,maximumGapSeconds,maximumDurationSeconds;
        }
        [Serializable] public struct Gap
        {
            public string point; public ulong connection; public int source,fromFrame,toFrame;
            public double fromSeconds,toSeconds,fromEngineSeconds,toEngineSeconds,durationSeconds;
            public long fromUtcTicks,toUtcTicks;
        }
        [Serializable] public struct Body
        { public ulong connection; public bool connected; public int frame; public double seconds,poseAgeSeconds; public long utcTicks; }
        private readonly struct Key : IEquatable<Key>
        {
            private readonly string point; private readonly ulong connection; private readonly int source;
            public Key(string point,ulong connection,int source){this.point=point;this.connection=connection;this.source=source;}
            public bool Equals(Key other)=>point==other.point&&connection==other.connection&&source==other.source;
            public override bool Equals(object other)=>other is Key key&&Equals(key);
            public override int GetHashCode()=>((point.GetHashCode()*397)^connection.GetHashCode())*397^source;
        }
        private readonly Dictionary<Key,Stream> streams=new Dictionary<Key,Stream>();
        private readonly Dictionary<ulong,double> accepted=new Dictionary<ulong,double>();
        private readonly Dictionary<ulong,bool> bodies=new Dictionary<ulong,bool>();
        private readonly List<Gap> gaps=new List<Gap>(); private readonly List<Body> changes=new List<Body>();
        private readonly int capacity;
        public bool Truncated {get;private set;}
        public PoseContinuityBuffer(int capacity=4096)
        {if(capacity<1||capacity>4096)throw new ArgumentOutOfRangeException(nameof(capacity));this.capacity=capacity;}
        public void Add(string point,ulong connection,int source,double seconds,long utcTicks,int frame,double engine,double duration=0)
        {
            if(string.IsNullOrEmpty(point)||point.Length>40||source<0||source>255||!Finite(seconds)||seconds<0||utcTicks<0||frame<0||!Finite(engine)||engine<0||!Finite(duration)||duration<0)
                throw new ArgumentException("Invalid continuity observation.");
            var key=new Key(point,connection,source);
            if(!streams.TryGetValue(key,out var stream))
            {
                if(streams.Count==256){Truncated=true;return;}
                stream=new Stream{point=point,connection=connection,source=source,firstSeconds=seconds,firstUtcTicks=utcTicks,firstFrame=frame};streams.Add(key,stream);
            }
            if(stream.count>0)
            {
                if(seconds<stream.lastSeconds)throw new ArgumentException("Continuity clock rewound.");
                var delta=seconds-stream.lastSeconds;stream.maximumGapSeconds=Math.Max(stream.maximumGapSeconds,delta);
                // Sparse inter-arrival / measured-work evidence, not every pose.
                if(delta>.2||duration>.2)
                {
                    if(gaps.Count==capacity)Truncated=true;
                    else gaps.Add(new Gap{point=point,connection=connection,source=source,fromSeconds=stream.lastSeconds,toSeconds=seconds,
                        fromEngineSeconds=stream.lastEngineSeconds,toEngineSeconds=engine,fromUtcTicks=stream.lastUtcTicks,toUtcTicks=utcTicks,
                        fromFrame=stream.lastFrame,toFrame=frame,durationSeconds=duration});
                }
            }
            stream.count++;stream.lastSeconds=seconds;stream.lastUtcTicks=utcTicks;stream.lastFrame=frame;stream.lastEngineSeconds=engine;
            stream.maximumDurationSeconds=Math.Max(stream.maximumDurationSeconds,duration);
            if(point=="PoseAccepted")
            {if(accepted.Count<256||accepted.ContainsKey(connection))accepted[connection]=seconds;else Truncated=true;}
        }
        public void Connection(ulong connection,bool connected,double seconds,long utcTicks,int frame)
        {
            if(!Finite(seconds)||seconds<0||utcTicks<0||frame<0)throw new ArgumentException("Invalid body observation.");
            if(bodies.TryGetValue(connection,out var prior)&&prior==connected)return;
            if(!bodies.ContainsKey(connection)&&bodies.Count==256){Truncated=true;return;}bodies[connection]=connected;
            if(accepted.TryGetValue(connection,out var latest)&&seconds<latest)throw new ArgumentException("Body clock rewound before accepted pose.");
            if(changes.Count==capacity){Truncated=true;return;}
            changes.Add(new Body{connection=connection,connected=connected,seconds=seconds,utcTicks=utcTicks,frame=frame,
                poseAgeSeconds=accepted.TryGetValue(connection,out var last)?Math.Max(0,seconds-last):-1});
        }
        public Stream[] Streams()
        {
            var result=new List<Stream>();foreach(var s in streams.Values)result.Add(new Stream{point=s.point,connection=s.connection,source=s.source,count=s.count,
                firstSeconds=s.firstSeconds,lastSeconds=s.lastSeconds,firstUtcTicks=s.firstUtcTicks,lastUtcTicks=s.lastUtcTicks,firstFrame=s.firstFrame,lastFrame=s.lastFrame,
                lastEngineSeconds=s.lastEngineSeconds,maximumGapSeconds=s.maximumGapSeconds,maximumDurationSeconds=s.maximumDurationSeconds});return result.ToArray();
        }
        public Gap[] Gaps()=>gaps.ToArray(); public Body[] Bodies()=>changes.ToArray();
        private static bool Finite(double x)=>!double.IsNaN(x)&&!double.IsInfinity(x);
    }

    public static class OwnThreadCounters
    {
        [Serializable] public struct Stamp
        {
            public uint threadId; public ulong creationTime,kernel100ns,user100ns,cycles;
            public double fromSeconds,toSeconds; public long fromUtcTicks,toUtcTicks;
        }
#if UNITY_STANDALONE_WIN || UNITY_EDITOR_WIN
        [StructLayout(LayoutKind.Sequential)] private struct FileTime {public uint low,high;public ulong Value=>((ulong)high<<32)|low;}
        [DllImport("kernel32.dll")] private static extern IntPtr GetCurrentThread();
        [DllImport("kernel32.dll")] private static extern uint GetCurrentThreadId();
        [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
        private static extern bool GetThreadTimes(IntPtr thread,out FileTime created,out FileTime exit,out FileTime kernel,out FileTime user);
        [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
        private static extern bool QueryThreadCycleTime(IntPtr thread,out ulong cycles);
#endif
        public static Stamp Read(Func<double> seconds)
        {
#if UNITY_STANDALONE_WIN || UNITY_EDITOR_WIN
            var result=new Stamp{threadId=GetCurrentThreadId(),fromSeconds=seconds(),fromUtcTicks=DateTime.UtcNow.Ticks};
            var pseudo=GetCurrentThread();
            if(!GetThreadTimes(pseudo,out var created,out _,out var kernel,out var user)||!QueryThreadCycleTime(pseudo,out var cycles))
                throw new InvalidOperationException("Own main-thread counters unavailable.");
            result.creationTime=created.Value;result.kernel100ns=kernel.Value;result.user100ns=user.Value;result.cycles=cycles;
            result.toUtcTicks=DateTime.UtcNow.Ticks;result.toSeconds=seconds();return result;
#else
            throw new PlatformNotSupportedException("Windows own-thread counters only.");
#endif
        }
        public static bool Follows(Stamp before,Stamp after)=>before.threadId>0&&before.threadId==after.threadId&&before.creationTime==after.creationTime
            &&after.kernel100ns>=before.kernel100ns&&after.user100ns>=before.user100ns&&after.cycles>=before.cycles
            &&before.toSeconds>=before.fromSeconds&&after.toSeconds>=after.fromSeconds&&after.fromSeconds>=before.toSeconds;
    }

    public sealed class NativePoseContinuity : MonoBehaviour
    {
        [Serializable] public struct ThreadWindow {public OwnThreadCounters.Stamp before,after;}
        [Serializable] public sealed class Report
        {
            public int version=1,maximumSeconds=1200,streamCapacity=256,gapCapacity=4096;
            public string source="NativeWindowsSparsePoseContinuity",role,startedAtUtc,stopReason,error="";
            public bool complete,truncated;public double endedSeconds,maximumClockStepSeconds;public long stopwatchFrequency,mainThreadSamples;
            public uint mainThreadId;public PoseContinuityBuffer.Stream[] streams;public PoseContinuityBuffer.Gap[] gaps;
            public PoseContinuityBuffer.Body[] bodies;public ThreadWindow[] threadWindows;public NativePoseLoopTrace.Report playerLoop;
        }
        private static NativePoseContinuity active;
        private readonly PoseContinuityBuffer buffer=new PoseContinuityBuffer();
        private readonly List<ThreadWindow> windows=new List<ThreadWindow>();private readonly Stopwatch clock=new Stopwatch();
        private string directory,role,startedAtUtc;private double nextCheck,clockStep;private bool finished,truncated;
        private OwnThreadCounters.Stamp previous;private bool sampled;private long samples;
        private NativePoseLoopTrace loop;
        public static bool Enabled=>active!=null&&!active.finished;
        internal static NativePoseContinuity Current=>Enabled?active:null;
        public static void ValidateOptions(string[] args)
        {
            var requested=Array.IndexOf(args,"--vr-pose-continuity")>=0;
            if(!requested&&Array.IndexOf(args,"--vr-pose-continuity-loop")>=0)throw new ArgumentException("Continuity loop requires its collector.");
            if(requested&&(Array.IndexOf(args,"--vr-pose-trace")>=0||Array.IndexOf(args,"--vr-pose-loop-trace")>=0))
                throw new ArgumentException("Sparse continuity and legacy pose trace are separate diagnostic modes.");
        }
        public static void Install(GameObject owner,string role)
        {
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            if(Application.isEditor)return;var args=Environment.GetCommandLineArgs();ValidateOptions(args);
            var index=Array.IndexOf(args,"--vr-pose-continuity");if(index<0)return;
            if(active!=null||index+1>=args.Length||!Path.IsPathRooted(args[index+1])||role!="Client"&&role!="Server"&&role!="Host")throw new ArgumentException("Continuity requires a fresh absolute directory and native role.");
            var path=Path.GetFullPath(args[index+1]);if(Directory.Exists(path)||File.Exists(path))throw new IOException("Continuity directory exists.");
            Directory.CreateDirectory(path);active=owner.AddComponent<NativePoseContinuity>();active.directory=path;active.role=role;
            active.startedAtUtc=DateTime.UtcNow.ToString("O",System.Globalization.CultureInfo.InvariantCulture);active.clock.Start();
            active.previous=OwnThreadCounters.Read(()=>active.clock.Elapsed.TotalSeconds);active.sampled=true;
            if(Array.IndexOf(args,"--vr-pose-continuity-loop")>=0)
            {
                var instance=active;instance.loop=new NativePoseLoopTrace(()=>instance.clock.Elapsed.TotalSeconds,()=>DateTime.UtcNow.Ticks,()=>Time.frameCount);
                PlayerLoop.SetPlayerLoop(instance.loop.Decorate(PlayerLoop.GetCurrentPlayerLoop()));
            }
#endif
        }
        internal void Record(string point,ulong connection,int source,double duration=0)
        {if(!finished)buffer.Add(point,connection,source,clock.Elapsed.TotalSeconds,DateTime.UtcNow.Ticks,Time.frameCount,Time.realtimeSinceStartupAsDouble,duration);}
        public static void Event(string point,ulong connection,int source,double duration=0){if(Enabled)active.Record(point,connection,source,duration);}
        public static void Body(ulong connection,bool connected)
        {if(Enabled)active.buffer.Connection(connection,connected,active.clock.Elapsed.TotalSeconds,DateTime.UtcNow.Ticks,Time.frameCount);}
        private void Update()
        {
            if(finished)return;
            try
            {
                var current=OwnThreadCounters.Read(()=>clock.Elapsed.TotalSeconds);samples++;
                if(sampled)
                {
                    if(!OwnThreadCounters.Follows(previous,current))throw new InvalidOperationException("Main-thread identity or counters changed.");
                    clockStep=Math.Max(clockStep,Math.Abs((current.fromUtcTicks-previous.toUtcTicks)/10000000.0-(current.fromSeconds-previous.toSeconds)));
                    if(current.fromSeconds-previous.toSeconds>.2)
                    {if(windows.Count==4096)truncated=true;else windows.Add(new ThreadWindow{before=previous,after=current});}
                }
                previous=current;sampled=true;
                var now=clock.Elapsed.TotalSeconds;
                if(now>=1200){Finish(false,"Duration limit");return;}
                if(now<nextCheck)return;nextCheck=now+.25;
                if(File.Exists(Path.Combine(directory,"finish.request")))Finish(true,"Explicit local diagnostic stop");
            }
            catch(Exception exception){Finish(false,"Counter failure",exception.GetType().Name);}
        }
        private void Finish(bool complete,string reason,string error="")
        {
            if(finished)return;finished=true;NativePoseLoopTrace.Report loopReport=null;
            if(loop!=null){PlayerLoop.SetPlayerLoop(loop.Remove(PlayerLoop.GetCurrentPlayerLoop()));loopReport=loop.Stop(complete,true);}
            var overflow=truncated||buffer.Truncated;
            var report=new Report{role=role,startedAtUtc=startedAtUtc,stopReason=reason,error=error,truncated=overflow,
                complete=complete&&!overflow&&samples>0&&(loopReport==null||loopReport.complete),endedSeconds=clock.Elapsed.TotalSeconds,
                maximumClockStepSeconds=clockStep,mainThreadSamples=samples,mainThreadId=previous.threadId,stopwatchFrequency=Stopwatch.Frequency,
                streams=buffer.Streams(),gaps=buffer.Gaps(),bodies=buffer.Bodies(),threadWindows=windows.ToArray(),playerLoop=loopReport};
            // Collection and loop instrumentation stop before serialization / IO.
            var target=Path.Combine(directory,"report.json");var temporary=target+".tmp";
            File.WriteAllText(temporary,JsonUtility.ToJson(report));File.Move(temporary,target);
        }
        private void OnApplicationQuit(){if(directory!=null&&!finished)Finish(false,"Application quit");}
        private void OnDestroy(){if(directory!=null&&!finished)Finish(false,"Owner destroyed");if(active==this)active=null;}
    }
}
