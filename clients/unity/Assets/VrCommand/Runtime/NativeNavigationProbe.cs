using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    [Serializable] public struct NavigationProbeRow
    {public long tick,observedSequence;public double seconds;public string id;public int room,health;public Vector3 feet;}
    public sealed class NavigationProbeBuffer
    {
        private readonly int capacity;private readonly List<NavigationProbeRow> rows=new List<NavigationProbeRow>();
        public int Samples {get;private set;} public long FirstTick {get;private set;}=-1;public long LastTick {get;private set;}=-1;
        public long LastObservedSequence {get;private set;}=-1;public bool Truncated {get;private set;}
        private double lastSeconds;
        public NavigationProbeBuffer(int capacity=4096){if(capacity<1||capacity>4096)throw new ArgumentOutOfRangeException(nameof(capacity));this.capacity=capacity;}
        public void Add(WorldFrame frame,long observed,double seconds=0)
        {
            if(Truncated||frame.Phase!=WorldPhase.Running)return;
            if(frame.Tick<1||observed<0||double.IsNaN(seconds)||double.IsInfinity(seconds)||seconds<lastSeconds)throw new ArgumentException("Invalid navigation observation clock.");
            if(frame.Tick==LastTick)return;
            if(LastTick>=0&&frame.Tick!=LastTick+1||observed<LastObservedSequence)throw new InvalidOperationException("Navigation observation rewound or skipped an active tick.");
            if(rows.Count+frame.Enemies.Length>capacity){Truncated=true;return;}
            foreach(var e in frame.Enemies)rows.Add(new NavigationProbeRow{tick=frame.Tick,observedSequence=observed,seconds=seconds,id=e.Id.ToString("D"),room=e.RoomId,health=e.Health,feet=new Vector3(e.Feet.X,e.Feet.Y,e.Feet.Z)});
            if(FirstTick<0)FirstTick=frame.Tick;LastTick=frame.Tick;LastObservedSequence=observed;lastSeconds=seconds;Samples++;
        }
        public NavigationProbeRow[] Snapshot()=>rows.ToArray();
    }
    // Explicit local authority observations. No input, network messages, journal
    // cadence, GPU, PCM, player poses, credentials or game policy changes.
    public sealed class NativeNavigationProbe:MonoBehaviour
    {
        [Serializable] public sealed class Report
        {
            public int schemaVersion=1,maximumSeconds=180,maximumRows=4096,samples;public string source="NativeAuthorityTick",sessionId,streamId,reason;
            public bool complete,truncated;public double endedSeconds;public long firstTick,lastTick;public NavigationProbeRow[] rows;
        }
        private readonly NavigationProbeBuffer buffer=new NavigationProbeBuffer();private readonly Stopwatch clock=new Stopwatch();
        private string directory,sessionId,streamId;private bool finished;
        public static NativeNavigationProbe Install(GameObject owner,string sessionId,string streamId)
        {
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            if(Application.isEditor)return null;
            var args=Environment.GetCommandLineArgs();var index=Array.IndexOf(args,"--vr-navigation-probe");if(index<0)return null;
            if(index+1>=args.Length||!Path.IsPathFullyQualified(args[index+1]))throw new ArgumentException("Navigation probe requires a fresh absolute directory.");
            if(!Guid.TryParse(sessionId,out var session)||session==Guid.Empty||!Guid.TryParse(streamId,out var stream)||stream==Guid.Empty)throw new ArgumentException("Navigation probe source identity missing.");
            var path=Path.GetFullPath(args[index+1]);if(Directory.Exists(path)||File.Exists(path))throw new IOException("Navigation probe directory exists.");
            Directory.CreateDirectory(path);var p=owner.AddComponent<NativeNavigationProbe>();p.directory=path;p.sessionId=session.ToString("D");p.streamId=stream.ToString("D");p.clock.Start();
            p.Write("ready.json",false,"Ready");return p;
#else
            return null;
#endif
        }
        public void Sample(ArenaWorld world,long observed)
        {
            if(finished)return;
            if(clock.Elapsed.TotalSeconds>=180){Finish(false,"Duration limit");return;}
            try{buffer.Add(world.Snapshot(),observed,clock.Elapsed.TotalSeconds);if(buffer.Truncated)Finish(false,"Row limit");}
            catch(Exception e){Finish(false,e.GetType().Name);}
        }
        private void Update()
        {
            if(finished||directory==null)return;
            if(File.Exists(Path.Combine(directory,"finish.request")))Finish(true,"Explicit diagnostic stop");
            else if(clock.Elapsed.TotalSeconds>=180)Finish(false,"Duration limit");
        }
        private void Write(string name,bool complete,string reason)=>File.WriteAllText(Path.Combine(directory,name),JsonUtility.ToJson(new Report{sessionId=sessionId,streamId=streamId,complete=complete&&!buffer.Truncated,
            truncated=buffer.Truncated,reason=reason,endedSeconds=clock.Elapsed.TotalSeconds,samples=buffer.Samples,firstTick=buffer.FirstTick,lastTick=buffer.LastTick,rows=buffer.Snapshot()},true));
        private void Finish(bool complete,string reason)
        {
            if(finished)return;finished=true;clock.Stop();
            try{Write("report.json",complete,reason);}catch(Exception e){UnityEngine.Debug.LogError("VR_NAVIGATION_PROBE_REPORT_FAILED type="+e.GetType().Name);}
        }
        private void OnDestroy(){if(directory!=null&&!finished)Finish(false,"Owner stopped before diagnostic finish");}
    }
}
