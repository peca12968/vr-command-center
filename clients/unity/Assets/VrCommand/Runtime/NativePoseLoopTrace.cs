using System;
using System.Collections.Generic;
using UnityEngine.LowLevel;

namespace VrCommand.Unity
{
    // Optional diagnostic only. Insert sibling observers, never replace an
    // engine / NGO delegate, native function, loop condition or existing order.
    public sealed class NativePoseLoopTrace
    {
        [Serializable] public struct BoundaryStats
        {
            public string path,system,side;
            public long calls;
            public double maximumIncomingGapSeconds;
        }
        [Serializable] public struct Gap
        {
            public int fromBoundary,toBoundary,fromFrame,toFrame;
            public double fromSeconds,toSeconds;
            public long fromUtcTicks,toUtcTicks;
        }
        [Serializable] public sealed class Report
        {
            public int version=1,capacity=4096,maximumNodes=512;
            public string source="NativeWindowsPlayerLoopBoundaries";
            public bool complete,truncated,detached;
            public long callbacks,firstUtcTicks,lastUtcTicks;
            public double firstSeconds,lastSeconds,maximumClockStepSeconds;
            public BoundaryStats[] boundaries;
            public Gap[] gaps;
        }
        private sealed class Marker
        {
            public readonly NativePoseLoopTrace owner;
            private readonly int index;
            public Marker(NativePoseLoopTrace owner,int index){this.owner=owner;this.index=index;}
            public void Tick()=>owner.Observe(index);
        }
        private readonly Func<double> seconds;
        private readonly Func<long> utcTicks;
        private readonly Func<int> frame;
        private readonly int capacity;
        private readonly List<BoundaryStats> boundaries=new List<BoundaryStats>();
        private readonly List<Gap> gaps=new List<Gap>();
        private bool decorated,stopped,truncated;
        private int previous=-1,previousFrame;
        private long callbacks,firstUtc,lastUtc;
        private double first,last,clockStep;
        public NativePoseLoopTrace(Func<double> seconds,Func<long> utcTicks,Func<int> frame,int capacity=4096)
        {
            this.seconds=seconds??throw new ArgumentNullException(nameof(seconds));
            this.utcTicks=utcTicks??throw new ArgumentNullException(nameof(utcTicks));
            this.frame=frame??throw new ArgumentNullException(nameof(frame));
            if(capacity<1||capacity>4096)throw new ArgumentOutOfRangeException(nameof(capacity));this.capacity=capacity;
        }
        public PlayerLoopSystem Decorate(PlayerLoopSystem current)
        {
            if(decorated||stopped)throw new InvalidOperationException("Loop trace already used.");
            var count=0;Count(current,0,ref count);
            if(count==0)throw new InvalidOperationException("Player loop has no systems.");
            decorated=true;return AddChildren(current,"");
        }
        private static void Count(PlayerLoopSystem node,int depth,ref int count)
        {
            if(depth>32)throw new InvalidOperationException("Player loop nesting exceeds diagnostic bounds.");
            if(node.subSystemList==null)return;
            foreach(var child in node.subSystemList)
            {if(++count>512)throw new InvalidOperationException("Player loop exceeds diagnostic bounds.");Count(child,depth+1,ref count);}
        }
        private PlayerLoopSystem AddChildren(PlayerLoopSystem node,string path)
        {
            if(node.subSystemList==null)return node;
            var original=node.subSystemList;var result=new PlayerLoopSystem[original.Length*3];
            for(var i=0;i<original.Length;i++)
            {
                var childPath=path+"/"+i;var child=original[i];
                result[i*3]=NewMarker(childPath,child.type,"before");
                result[i*3+1]=AddChildren(child,childPath);
                result[i*3+2]=NewMarker(childPath,child.type,"after");
            }
            node.subSystemList=result;return node;
        }
        private PlayerLoopSystem NewMarker(string path,Type system,string side)
        {
            var index=boundaries.Count;boundaries.Add(new BoundaryStats{path=path,system=system?.FullName??"<untyped>",side=side});
            var marker=new Marker(this,index);return new PlayerLoopSystem{type=typeof(Marker),updateDelegate=marker.Tick};
        }
        private void Observe(int index)
        {
            if(stopped)return;
            var now=seconds();var utc=utcTicks();var currentFrame=frame();
            if(double.IsNaN(now)||double.IsInfinity(now)||now<0||utc<0||currentFrame<0||previous>=0&&now<last)
                throw new InvalidOperationException("Invalid loop observation clock.");
            var stats=boundaries[index];stats.calls++;callbacks++;
            if(previous>=0)
            {
                var delta=now-last;stats.maximumIncomingGapSeconds=Math.Max(stats.maximumIncomingGapSeconds,delta);
                clockStep=Math.Max(clockStep,Math.Abs((utc-lastUtc)/10000000.0-delta));
                if(delta>.1)
                {
                    if(gaps.Count==capacity)truncated=true;
                    else gaps.Add(new Gap{fromBoundary=previous,toBoundary=index,fromSeconds=last,toSeconds=now,
                        fromUtcTicks=lastUtc,toUtcTicks=utc,fromFrame=previousFrame,toFrame=currentFrame});
                }
            }
            else {first=now;firstUtc=utc;}
            boundaries[index]=stats;previous=index;last=now;lastUtc=utc;previousFrame=currentFrame;
        }
        // Remove only markers owned by this instance from the CURRENT tree.
        // Never restore an old snapshot and erase later NGO / other changes.
        public PlayerLoopSystem Remove(PlayerLoopSystem current)
        {
            if(current.subSystemList==null)return current;
            var kept=new List<PlayerLoopSystem>();
            foreach(var child in current.subSystemList)
            {
                if(child.type==typeof(Marker)&&child.updateDelegate?.Target is Marker m&&ReferenceEquals(m.owner,this))continue;
                kept.Add(Remove(child));
            }
            current.subSystemList=kept.ToArray();return current;
        }
        public Report Stop(bool complete,bool detached)
        {
            stopped=true;return new Report{capacity=capacity,complete=complete&&decorated&&callbacks>0&&!truncated&&detached,
                truncated=truncated,detached=detached,callbacks=callbacks,firstSeconds=first,lastSeconds=last,
                firstUtcTicks=firstUtc,lastUtcTicks=lastUtc,maximumClockStepSeconds=clockStep,
                boundaries=boundaries.ToArray(),gaps=gaps.ToArray()};
        }
    }
}
