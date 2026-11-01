using System;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class NavigationProbeTests
    {
        private static ArenaWorld World(int count=1)
        {
            var world=new ArenaWorld(new[]{3},new WorldProp[0]);world.AddPlayer(Guid.NewGuid(),3,new Vec3(-3,1.65f,-3));
            for(var i=0;i<count;i++)world.AddEnemy(Guid.NewGuid(),3,new Vec3(-2+i,0,0),new Vec3(2,0,0));
            world.SetPolicy(AiBehavior.Patrol,false,Visibility.Clear,false);world.SetPhase(WorldPhase.Running);return world;
        }
        [Test] public void EachActualTickKeepsItsOriginalEnemyPositionIncludingTheTransientEndpoint()
        {
            var world=World();var buffer=new NavigationProbeBuffer();
            for(var i=0;i<100;i++){world.Tick();buffer.Add(world.Snapshot(),7);}
            var rows=buffer.Snapshot();Assert.AreEqual(100,buffer.Samples);Assert.AreEqual(1,buffer.FirstTick);Assert.AreEqual(100,buffer.LastTick);
            Assert.IsTrue(rows.Select((r,i)=>r.tick==i+1&&r.observedSequence==7&&r.room==3).All(v=>v));
            Assert.IsTrue(rows.Any(r=>Vector3.Distance(r.feet,new Vector3(2,0,0))<.15f));
        }
        [Test] public void RowLimitRetainsOnlyWholeEarliestTicksAndMarksTruncation()
        {
            var world=World(2);var buffer=new NavigationProbeBuffer(3);
            world.Tick();buffer.Add(world.Snapshot(),7);world.Tick();buffer.Add(world.Snapshot(),7);
            Assert.IsTrue(buffer.Truncated);Assert.AreEqual(1,buffer.Samples);Assert.AreEqual(2,buffer.Snapshot().Length);
            Assert.IsTrue(buffer.Snapshot().All(r=>r.tick==1));
        }
        [Test] public void DuplicateTickDoesNotAddRowsAndMissingOrRewoundObservationsCannotPass()
        {
            var world=World();var buffer=new NavigationProbeBuffer();world.Tick();buffer.Add(world.Snapshot(),7);buffer.Add(world.Snapshot(),7);
            Assert.AreEqual(1,buffer.Samples);world.Tick();world.Tick();Assert.Throws<InvalidOperationException>(()=>buffer.Add(world.Snapshot(),7));
            var other=new NavigationProbeBuffer();other.Add(world.Snapshot(),8);world.Tick();Assert.Throws<InvalidOperationException>(()=>other.Add(world.Snapshot(),7));
        }
        [Test] public void EditorNeverInstallsTheNativeAuthorityCollector()
        {
            var owner=new GameObject("Navigation probe installation test");
            try{Assert.IsNull(NativeNavigationProbe.Install(owner,"invalid","invalid"));}finally{UnityEngine.Object.DestroyImmediate(owner);}
        }
    }
}
