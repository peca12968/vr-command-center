using System;
using NUnit.Framework;
using UnityEngine;
using Unity.Collections;
using Unity.Netcode;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class EnemyFireTests
    {
        [Test] public void ImportedFlashHasOutwardFacesAndItsDedicatedShader()
        {
            var data=EnemyFireModels.Read();var mesh=FieldPropModels.BuildMesh(data.mesh,WorldAssetSets.CombatEffects);
            try
            {
                Assert.AreEqual(32,mesh.triangles.Length/3);var p=mesh.vertices;var n=mesh.normals;var t=mesh.triangles;
                for(var i=0;i<t.Length;i+=3)Assert.Greater(Vector3.Dot(Vector3.Cross(p[t[i+1]]-p[t[i]],p[t[i+2]]-p[t[i]]),n[t[i]]),.0000001f);
                Assert.IsNotNull(Resources.Load<Shader>("VrCommand/EnemyFire"));
                Assert.Greater(mesh.bounds.max.z,.23f);Assert.GreaterOrEqual(mesh.bounds.min.z,0);
            }
            finally{UnityEngine.Object.DestroyImmediate(mesh);}
        }
        [Test] public void FirePoolBorrowsFrozenSidearmAndSharesOneFlashMeshAndMaterial()
        {
            using(var pool=new EnemyFireModels())
            {
                var a=pool.Create();var b=pool.Create();try
                {
                    Assert.AreSame(a.Flash.GetComponent<MeshFilter>().sharedMesh,b.Flash.GetComponent<MeshFilter>().sharedMesh);
                    Assert.AreSame(a.Flash.GetComponent<MeshRenderer>().sharedMaterial,b.Flash.GetComponent<MeshRenderer>().sharedMaterial);
                    Assert.AreSame(a.Body.Gun.GetComponent<MeshFilter>().sharedMesh,a.RecoilVisual.GetComponent<MeshFilter>().sharedMesh);
                    Assert.IsFalse(a.Body.Gun.GetComponent<MeshRenderer>().enabled);Assert.IsFalse(a.Flash.gameObject.activeSelf);
                    Assert.IsEmpty(a.Root.GetComponentsInChildren<Collider>(true));Assert.IsEmpty(a.Root.GetComponentsInChildren<NetworkObject>(true));
                    UnityEngine.Object.DestroyImmediate(a.Root);Assert.IsNotNull(b.RecoilVisual.GetComponent<MeshFilter>().sharedMesh);
                }
                finally{if(a.Root!=null)UnityEngine.Object.DestroyImmediate(a.Root);UnityEngine.Object.DestroyImmediate(b.Root);}
            }
        }
        [Test] public void ActualFlashUsesHistoricalRayWhileOnlyTheSidearmRendererRecoils()
        {
            using(var pool=new EnemyFireModels())
            {
                var v=pool.Create();try
                {
                    var ray=new Vec3(.3f,-.1f,-1).Normalized();var fire=new EnemyFireState(5,11,new Vec3(-1,1.4f,2),ray);
                    v.Root.transform.position=new Vector3(0,0,3);v.Apply(new Vec3(1,0,0),false,10,80,fire);
                    Assert.AreEqual(10,v.AppliedTick);Assert.AreEqual(5,v.AppliedFire.Sequence);
                    Assert.IsTrue(v.Flash.gameObject.activeSelf);Assert.Less(Vector3.Distance(new Vector3(-1,1.4f,2),v.Flash.position),.00001f);
                    Assert.Less(Vector3.Distance(v.Flash.forward,new Vector3(ray.X,ray.Y,ray.Z)),.00001f);
                    Assert.AreEqual(new Vector3(0,1.4f,3),v.Body.Gun.position);Assert.AreEqual(new Vector3(0,1.4f,0),v.Body.Gun.localPosition);
                    Assert.AreEqual(-.012f,v.RecoilVisual.localPosition.z,.000001f);Assert.AreEqual(new Vector3(0,-.085f,-.035f),v.Body.LeftHand.localPosition);
                    v.Root.transform.position+=new Vector3(.1f,0,0);v.Apply(new Vec3(0,0,-1),true,11,80,fire);
                    Assert.Less(Vector3.Distance(v.Flash.position,new Vector3(-1,1.4f,2)),.00001f);Assert.AreEqual(-.018f,v.RecoilVisual.localPosition.z,.000001f);
                    Assert.Less(Vector3.Distance(v.Body.Gun.position,new Vector3(.1f,1.4f,3)),.00001f);
                }
                finally{UnityEngine.Object.DestroyImmediate(v.Root);}
            }
        }
        [Test] public void RealPausedWorldAndDirectSeekRestoreActualFlashAndRecoilTransforms()
        {
            var world=new ArenaWorld(new[]{3},new WorldProp[0]);world.AddPlayer(Guid.NewGuid(),3,new Vec3(0,1.65f,-3));world.AddEnemy(Guid.NewGuid(),3,new Vec3(0,0,3),new Vec3(3,0,3));
            world.SetPolicy(AiBehavior.Hold,true,Visibility.Clear,false);world.SetPhase(WorldPhase.Running);world.Tick();var npc=world.Snapshot().Enemies[0];
            using(var pool=new EnemyFireModels())
            {
                var v=pool.Create();try
                {
                    v.Apply(npc.Forward,false,1,100,npc.Fire);var recoil=v.RecoilVisual.localPosition;
                    world.SetPhase(WorldPhase.Paused);for(var i=0;i<100;i++)world.Tick();v.Apply(npc.Forward,false,world.TickNumber,100,npc.Fire);
                    Assert.IsTrue(v.Flash.gameObject.activeSelf);Assert.AreEqual(recoil,v.RecoilVisual.localPosition);
                    world.SetPhase(WorldPhase.Running);world.SetPolicy(AiBehavior.Hold,false,Visibility.Clear,false);for(var i=0;i<8;i++)world.Tick();v.Apply(npc.Forward,false,world.TickNumber,100,npc.Fire);
                    Assert.IsFalse(v.Flash.gameObject.activeSelf);Assert.AreEqual(Vector3.zero,v.RecoilVisual.localPosition);
                    v.Apply(npc.Forward,false,1,100,npc.Fire);Assert.IsTrue(v.Flash.gameObject.activeSelf);Assert.AreEqual(recoil,v.RecoilVisual.localPosition);
                    v.Apply(npc.Forward,false,1,0,npc.Fire);Assert.IsFalse(v.Flash.gameObject.activeSelf);Assert.AreEqual(Vector3.zero,v.RecoilVisual.localPosition);
                }
                finally{UnityEngine.Object.DestroyImmediate(v.Root);}
            }
        }
        [Test] public void SavedShotClockAndRayTravelAtomicallyInTheNetworkActor()
        {
            var expected=new CombatActorState{id=System.Guid.Parse("6bcd2409-6172-43af-8307-88255c0959f8"),enemy=true,health=80,room=3,fireSequence=5,fireTickPlusOne=11,
                presentationTick=10,fireOrigin=new Vector3(0,1.4f,3),fireDirection=new Vector3(0,0,-1)};
            using(var writer=new FastBufferWriter(1024,Allocator.Temp))
            {
                writer.WriteValueSafe(expected);using(var reader=new FastBufferReader(writer.ToArray(),Allocator.Temp))
                {reader.ReadValueSafe(out CombatActorState actual);Assert.IsTrue(expected.Equals(actual));actual.fireSequence++;Assert.IsFalse(expected.Equals(actual));}
            }
            var changed=expected;changed.fireOrigin.x+=.1f;Assert.IsFalse(expected.Equals(changed));changed=expected;changed.fireTickPlusOne++;Assert.IsFalse(expected.Equals(changed));
        }
        [Test] public void CodecRetainsOldUnfiredMetadataAndRejectsAnOmittedNewFlag()
        {
            var world=new ArenaWorld(new[]{3},new WorldProp[0]);world.AddEnemy(Guid.NewGuid(),3,new Vec3(0,0,3),new Vec3(3,0,3));var codec=new UnityWorldCodec();
            var packet=WorldRecordingPacket.Capture(world,1,0,1,0,0,_=>new RecordedRig(),enemyPresentationVersion:1,weaponPresentationVersion:1);
            var json=codec.Packet(packet);foreach(var field in new[]{"fireOrigin","fireDirection"})json=json.Replace(",\""+field+"\":"+JsonUtility.ToJson(new RecordedVector()),"");
            json=json.Replace(",\"hasFireState\":false","").Replace(",\"fireSequence\":0","").Replace(",\"fireTickPlusOne\":0","");Assert.IsFalse(json.Contains("hasFireState"));
            var old=codec.ReadPacket(json);var header=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",new[]{3},new WorldProp[0],assetSet:WorldAssetSets.ArmedCombatants,enemyPresentationVersion:1,weaponPresentationVersion:1);
            WorldRecordingValidation.Packet(header,old,null);Assert.IsFalse(old.frame.enemies[0].hasFireState);Assert.IsNotNull(old.frame.enemies[0].fireOrigin);
            header.assetSet=WorldAssetSets.CombatEffects;header.enemyFireVersion=1;Assert.Throws<ArgumentException>(()=>WorldRecordingValidation.Packet(header,old,null));
            var current=WorldRecordingPacket.Capture(world,1,0,1,0,0,_=>new RecordedRig(),enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1);
            WorldRecordingValidation.Packet(header,codec.ReadPacket(codec.Packet(current)),null);
        }
    }
}
