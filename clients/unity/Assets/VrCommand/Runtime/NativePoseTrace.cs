using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using UnityEngine;

namespace VrCommand.Unity
{
    [Serializable] public struct PoseTraceRow
    {
        public string point;
        public double seconds,engineSeconds,durationSeconds,poseAgeSeconds;
        public long utcTicks;
        public int frame,source;
        public ulong connection;
        public bool connected;
    }
    // Append-only bounded evidence. No pose coordinates, credentials, payload,
    // input, PCM or GPU readback. Overflow keeps the earliest evidence.
    public sealed class PoseTraceBuffer
    {
        private readonly int capacity;
        private readonly List<PoseTraceRow> rows=new List<PoseTraceRow>();
        public bool Truncated {get;private set;}
        public PoseTraceBuffer(int capacity=32768)
        {if(capacity<1||capacity>32768)throw new ArgumentOutOfRangeException(nameof(capacity));this.capacity=capacity;}
        public void Add(PoseTraceRow row)
        {
            if(string.IsNullOrEmpty(row.point) || row.point.Length>40 || !Finite(row.seconds) || row.seconds<0
                || !Finite(row.engineSeconds) || row.engineSeconds<0 || !Finite(row.durationSeconds) || row.durationSeconds<0 || !Finite(row.poseAgeSeconds)
                || row.poseAgeSeconds< -1 || row.frame<0 || row.utcTicks<0 || row.source<0 || row.source>255)
                throw new ArgumentException("Invalid pose trace observation.");
            if(rows.Count==capacity){Truncated=true;return;}rows.Add(row);
        }
        public PoseTraceRow[] Snapshot()=>rows.ToArray();
        private static bool Finite(double x)=>!double.IsNaN(x)&&!double.IsInfinity(x);
    }
    public sealed class NativePoseTrace : MonoBehaviour
    {
        [Serializable] public sealed class Report
        {
            public int schemaVersion=1,capacity=32768,maximumSeconds=240;
            public string source="NativeWindowsMonotonicTiming",role,startedAtUtc,stopReason,error="";
            public bool complete,truncated;
            public double endedSeconds;
            public long stopwatchFrequency;
            public PoseTraceRow[] rows;
        }
        private static NativePoseTrace active;
        private readonly PoseTraceBuffer buffer=new PoseTraceBuffer();
        private readonly Dictionary<ulong,double> accepted=new Dictionary<ulong,double>();
        private readonly Dictionary<ulong,bool> connections=new Dictionary<ulong,bool>();
        private readonly Dictionary<ulong,string> unavailable=new Dictionary<ulong,string>();
        private readonly Stopwatch clock=new Stopwatch();
        private string directory,role,startedAtUtc;
        private double lastFrame,nextCheck;
        private bool finished;
        public static bool Enabled=>active!=null && !active.finished;
        public static void Install(GameObject owner,string role)
        {
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            if(Application.isEditor)return;
            var args=Environment.GetCommandLineArgs();var index=Array.IndexOf(args,"--vr-pose-trace");if(index<0)return;
            if(active!=null)throw new InvalidOperationException("Pose trace is already installed.");
            if(index+1>=args.Length || !Path.IsPathRooted(args[index+1]))throw new ArgumentException("Pose trace requires a fresh absolute directory.");
            if(role!="Client" && role!="Server" && role!="Host")throw new ArgumentException("Unsupported pose trace role.");
            var path=Path.GetFullPath(args[index+1]);if(Directory.Exists(path)||File.Exists(path))throw new IOException("Pose trace directory exists.");
            Directory.CreateDirectory(path);active=owner.AddComponent<NativePoseTrace>();active.directory=path;active.role=role;
            active.startedAtUtc=DateTime.UtcNow.ToString("O",System.Globalization.CultureInfo.InvariantCulture);active.clock.Start();
#endif
        }
        public static void Event(string point,ulong connection=0,int source=0,double duration=0)
        {if(Enabled)active.Record(point,connection,source,duration,false);}
        public static void Accepted(ulong connection,int source)
        {
            if(!Enabled)return;active.accepted[connection]=active.clock.Elapsed.TotalSeconds;
            active.Record("PoseAccepted",connection,source,0,true);
        }
        public static void OwnerUnavailable(string point,ulong connection)
        {
            if(!Enabled)return;
            if(!active.unavailable.TryGetValue(connection,out var prior)||prior!=point)
            {active.unavailable[connection]=point;active.Record(point,connection,0,0,false);}
        }
        public static void Sending(ulong connection,int source)
        {if(Enabled){active.unavailable.Remove(connection);active.Record("PoseSend",connection,source,0,false);}}
        public static void Body(ulong connection,bool connected)
        {
            if(!Enabled)return;
            if(!active.connections.TryGetValue(connection,out var prior)||prior!=connected)
            {active.connections[connection]=connected;active.Record("BodyConnection",connection,0,0,connected);}
        }
        public readonly struct Span : IDisposable
        {
            private readonly NativePoseTrace owner;
            private readonly string point;
            private readonly long start;
            internal Span(NativePoseTrace owner,string point){this.owner=owner;this.point=point;start=Stopwatch.GetTimestamp();}
            public void Dispose()
            {if(owner!=null&&!owner.finished)owner.Record(point,0,0,(Stopwatch.GetTimestamp()-start)/(double)Stopwatch.Frequency,false);}
        }
        public static Span Measure(string point)=>Enabled?new Span(active,point):default;
        private void Record(string point,ulong connection,int source,double duration,bool connected)
        {
            var now=clock.Elapsed.TotalSeconds;
            buffer.Add(new PoseTraceRow{point=point,seconds=now,utcTicks=DateTime.UtcNow.Ticks,engineSeconds=Time.realtimeSinceStartupAsDouble,
                frame=Time.frameCount,durationSeconds=duration,connection=connection,source=source,connected=connected,
                poseAgeSeconds=accepted.TryGetValue(connection,out var last)?Math.Max(0,now-last):-1});
        }
        private void Update()
        {
            if(finished)return;
            var now=clock.Elapsed.TotalSeconds;if(lastFrame>0 && now-lastFrame>.1)Record("MainThreadGap",0,0,now-lastFrame,false);lastFrame=now;
            if(now>=240){Finish(false,"Duration limit");return;}
            if(now<nextCheck)return;nextCheck=now+.25;
            if(File.Exists(Path.Combine(directory,"finish.request")))Finish(true,"Explicit local diagnostic stop");
        }
        private void Finish(bool complete,string reason)
        {
            if(finished)return;finished=true;
            // End observation BEFORE report serialization / disk IO. That final
            // write can itself block the main thread and is outside this trace.
            var report=new Report{role=role,startedAtUtc=startedAtUtc,stopReason=reason,complete=complete&&!buffer.Truncated,
                truncated=buffer.Truncated,endedSeconds=clock.Elapsed.TotalSeconds,stopwatchFrequency=Stopwatch.Frequency,rows=buffer.Snapshot()};
            File.WriteAllText(Path.Combine(directory,"report.json"),JsonUtility.ToJson(report));
        }
        private void OnApplicationQuit(){if(directory!=null&&!finished)Finish(false,"Application quit");}
        private void OnDestroy(){if(directory!=null&&!finished)Finish(false,"Owner destroyed");if(active==this)active=null;}
    }
}
