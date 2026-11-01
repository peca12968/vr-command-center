using System;
using System.Linq;
using NUnit.Framework;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class NavigationTests
    {
        private static ArenaWorld Rotated(int room,out Vec3 start,out Vec3 end,out ArenaWalkSurface surface)
        {
            var origin=ArenaWorld.RoomOrigin(room);var props=new[]{new WorldProp(Guid.NewGuid(),room,PropKind.Barrel,origin+new Vec3(.25f,0,.25f),45)};
            var world=new ArenaWorld(room==3?new[]{3}:new[]{1,2,3,4,5},props);
            world.AddPlayer(Guid.NewGuid(),room,origin+new Vec3(-4,1.65f,-4));start=origin+new Vec3(-2,0,1);end=origin+new Vec3(2,0,1);
            world.AddEnemy(Guid.NewGuid(),room,start,end);world.SetPolicy(AiBehavior.Patrol,false,Visibility.Clear,false);world.SetPhase(WorldPhase.Running);
            surface=new ArenaWalkSurface(origin,props);return world;
        }
        [Test] public void RotatedCoverPatrolCompletesBothDirectionsWithOriginalMovementClearance()
        {
            var world=Rotated(3,out var start,out var end,out var surface);var reached=false;var returned=false;var previous=start;
            for(var i=0;i<320;i++)
            {
                world.Tick();var feet=world.Snapshot().Enemies[0].Feet;
                Assert.IsTrue(surface.ClearSegment(previous,feet));Assert.LessOrEqual(Vec3.Distance(previous,feet),.1001f);
                reached|=Vec3.Distance(feet,end)<.15f;returned|=reached&&Vec3.Distance(feet,start)<.15f;previous=feet;
            }
            Assert.IsTrue(reached,"The old point-only route stops at the rotated corner.");Assert.IsTrue(returned);
        }
        [Test] public void CachedNavigationCannotMoveDuringPauseOrOperatorHold()
        {
            var world=Rotated(3,out _,out _,out _);for(var i=0;i<35;i++)world.Tick();
            world.SetPhase(WorldPhase.Paused);var tick=world.TickNumber;var feet=world.Snapshot().Enemies[0].Feet;
            for(var i=0;i<20;i++)world.Tick();Assert.AreEqual(tick,world.TickNumber);Assert.AreEqual(feet,world.Snapshot().Enemies[0].Feet);
            world.SetPhase(WorldPhase.Running);world.SetPolicy(AiBehavior.Hold,false,Visibility.Clear,false);
            for(var i=0;i<20;i++)world.Tick();Assert.AreEqual(feet,world.Snapshot().Enemies[0].Feet);
        }
        [TestCase(1)] [TestCase(5)] public void RotatedRouteUsesTheSelectedOuterRoomOrigin(int room)
        {
            var world=Rotated(room,out _,out var end,out _);var reached=false;
            for(var i=0;i<160;i++){world.Tick();reached|=Vec3.Distance(world.Snapshot().Enemies[0].Feet,end)<.15f;}
            Assert.IsTrue(reached);
        }
        [Test] public void NoRouteThroughACompleteWallDoesNotInventAMovementFallback()
        {
            var props=Enumerable.Range(-2,5).Select(x=>new WorldProp(Guid.NewGuid(),3,PropKind.Sandbag,new Vec3(x*2.4f,0,0),0)).ToArray();
            var world=new ArenaWorld(new[]{3},props);world.AddPlayer(Guid.NewGuid(),3,new Vec3(-4,1.65f,-4));var start=new Vec3(0,0,-3);
            world.AddEnemy(Guid.NewGuid(),3,start,new Vec3(0,0,3));world.SetPolicy(AiBehavior.Patrol,false,Visibility.Clear,false);world.SetPhase(WorldPhase.Running);
            for(var i=0;i<160;i++)world.Tick();Assert.AreEqual(start,world.Snapshot().Enemies[0].Feet);
        }
        private static void Exercise(ArenaWorld world,Guid id,ArenaWalkSurface surface,Vec3 start,Vec3 end,bool requireReturn)
        {
            var reached=false;var returned=false;var previous=start;
            for(var i=0;i<320;i++)
            {
                world.Tick();var feet=world.Snapshot().Enemies.Single(e=>e.Id==id).Feet;
                Assert.IsTrue(surface.ClearSegment(previous,feet));Assert.LessOrEqual(Vec3.Distance(previous,feet),.1001f);
                reached|=Vec3.Distance(feet,end)<.15f;returned|=reached&&Vec3.Distance(feet,start)<.15f;previous=feet;
            }
            Assert.IsTrue(reached);if(requireReturn)Assert.IsTrue(returned);
        }
        private static void Generated(bool goal,int room,bool linked)
        {
            var source=new ArenaSession();source.Apply(new ManagementSnapshot{id=Guid.NewGuid().ToString(),state="Preparing",sequence=1,roomIds=linked?new[]{1,2,3,4,5}:new[]{room},
                mission=new ManagedMission{id=Guid.NewGuid().ToString(),definition=new ManagedDefinition{name="Non-grid navigation",briefing="Generator regression",durationSeconds=180,
                    props=new[]{new ManagedProp{assetId="barrel",position=new ManagedPosition{x=goal?5.1f:-4.6f,z=goal?5:-1}}}}},
                environment=new ManagedEnvironment{mode="VR",weather="Clear",timeOfDay="Day"},enemies=new ManagedEnemies{count=linked?5:1,behavior="Patrol",autoAttack=false},
                players=new[]{new ManagedPlayer{id=Guid.NewGuid().ToString(),admissionId=Guid.NewGuid().ToString(),roomId=room,seat=0}}});
            var enemy=source.World.Snapshot().Enemies.Single(e=>e.RoomId==room);var origin=ArenaWorld.RoomOrigin(room);
            Assert.AreEqual(origin+new Vec3(goal?-4.5f:-3.75f,0,-1),enemy.Feet);
            source.World.SetPhase(WorldPhase.Running);
            Exercise(source.World,enemy.Id,new ArenaWalkSurface(origin,source.Props.Where(p=>p.RoomId==room).ToArray()),enemy.Feet,origin+new Vec3(goal?3.75f:4.5f,0,5),true);
        }
        [TestCase(false)] [TestCase(true)] public void GeneratedPatrolKeepsNonGridEndpointsAndReturnsWithOriginalClearance(bool goal)=>Generated(goal,3,false);
        [TestCase(1)] [TestCase(5)] public void NonGridConnectionsRespectLinkedOuterRoomOrigins(int room)=>Generated(room==5,room,true);
        [TestCase(false)] [TestCase(true)] public void SameCellLinksReachTheOriginalGoalAndCannotCutBlockedCorners(bool blocked)
        {
            var props=blocked?new[]{new WorldProp(Guid.NewGuid(),3,PropKind.Barrel,new Vec3(.25f,0,.15f),45)}:new WorldProp[0];
            var start=blocked?new Vec3(.05f,0,.9f):new Vec3(.1f,0,.1f);var end=blocked?new Vec3(.45f,0,.9f):new Vec3(.24f,0,.24f);
            var world=new ArenaWorld(new[]{3},props);world.AddPlayer(Guid.NewGuid(),3,new Vec3(-3,1.65f,-3));var id=Guid.NewGuid();world.AddEnemy(id,3,start,end);
            world.SetPolicy(AiBehavior.Patrol,false,Visibility.Clear,false);world.SetPhase(WorldPhase.Running);
            Exercise(world,id,new ArenaWalkSurface(new Vec3(),props),start,end,false);
        }
    }
}
