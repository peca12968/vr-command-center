using System;
using NUnit.Framework;
using UnityEngine;
using Unity.Collections;
using Unity.Netcode;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class PlayerFireTests
    {
        [Test] public void PlayerProfileReusesFrozenWeaponAndPulseWithNoCollisionOrNetworkObjects()
        {
            var data=FiringRifleModels.Read();Assert.AreEqual(1.2f,data.pulseScale);Assert.AreEqual(3,data.flashTicks);
            using(var pool=new FiringRifleModels())
            {
                var v=pool.Create();try
                {
                    Assert.IsEmpty(v.Root.GetComponentsInChildren<Collider>(true));Assert.IsEmpty(v.Root.GetComponentsInChildren<NetworkObject>(true));
                    Assert.IsEmpty(v.Flash.GetComponentsInChildren<Collider>(true));Assert.AreEqual(32,v.Flash.GetComponent<MeshFilter>().sharedMesh.triangles.Length/3);
                    Assert.AreSame(v.Root.GetComponent<MeshFilter>().sharedMesh,v.RecoilVisual.GetChild(0).GetComponent<MeshFilter>().sharedMesh);
                    Assert.IsFalse(v.HiddenBody.enabled);Assert.IsNull(v.Flash.parent);
                }
                finally{v.Dispose();UnityEngine.Object.DestroyImmediate(v.Root);}
            }
        }
        [Test] public void AvatarLeasesSharePulseAndWeaponWithoutReleasingAnotherPlayersResources()
        {
            var first=new FiringRifleModels();var second=new FiringRifleModels();var a=first.Create();var b=second.Create();
            try
            {
                Assert.AreSame(a.Flash.GetComponent<MeshFilter>().sharedMesh,b.Flash.GetComponent<MeshFilter>().sharedMesh);
                Assert.AreSame(a.Flash.GetComponent<MeshRenderer>().sharedMaterial,b.Flash.GetComponent<MeshRenderer>().sharedMaterial);
                Assert.AreSame(a.Root.GetComponent<MeshFilter>().sharedMesh,b.Root.GetComponent<MeshFilter>().sharedMesh);
                a.Dispose();UnityEngine.Object.DestroyImmediate(a.Root);first.Dispose();
                b.Apply(0,100,true,true,false,0,new PlayerFireState(1,1,new Vec3(0,1.5f,0),new Vec3(0,0,1)));
                Assert.IsNotNull(b.Flash.GetComponent<MeshFilter>().sharedMesh);Assert.IsTrue(b.Flash.gameObject.activeSelf);
            }
            finally{a.Dispose();if(a.Root!=null)UnityEngine.Object.DestroyImmediate(a.Root);b.Dispose();UnityEngine.Object.DestroyImmediate(b.Root);first.Dispose();second.Dispose();}
        }
        [Test] public void ActualRecoilKeepsPointerGunAndGripTransformsWhileFlashStaysInWorldSpace()
        {
            var pointer=new GameObject("Tracked pointer test");var parent=new GameObject("Avatar parent test");
            using(var pool=new FiringRifleModels())
            {
                var v=pool.Create();try
                {
                    pointer.transform.position=new Vector3(2,1.5f,-1);pointer.transform.rotation=Quaternion.Euler(10,30,5);
                    var position=pointer.transform.position;var rotation=pointer.transform.rotation;v.Root.transform.SetParent(parent.transform,false);
                    ServiceRifleModels.Align(v.Root.transform,pointer.transform);var gun=v.Root.transform.position;
                    var ray=new Vec3(1,.2f,-1).Normalized();var fire=new PlayerFireState(1,1,new Vec3(0,1.5f,3),ray);v.HiddenBody.enabled=true;
                    v.Apply(0,100,true,true,false,0,fire);
                    Assert.IsFalse(v.HiddenBody.enabled);Assert.AreEqual(-.014f,v.RecoilVisual.localPosition.z,.000001f);
                    Assert.AreEqual(gun,v.Root.transform.position);Assert.AreEqual(position,pointer.transform.position);Assert.Less(Quaternion.Angle(rotation,pointer.transform.rotation),.0001f);
                    Assert.Less(Vector3.Distance(gun,position+pointer.transform.forward*AvatarPose.MuzzleOffset),.00001f);
                    Assert.AreEqual(new Vector3(0,-.15f,-.535f),v.Action.RightHand.localPosition);Assert.AreEqual(new Vector3(0,0,-.22f),v.Action.LeftHand.localPosition);
                    Assert.AreEqual(new Vector3(0,1.5f,3),v.Flash.position);Assert.Less(Vector3.Distance(v.Flash.forward,new Vector3(ray.X,ray.Y,ray.Z)),.00001f);
                    parent.transform.position=new Vector3(5,0,0);pointer.transform.position+=Vector3.right;
                    Assert.AreEqual(new Vector3(0,1.5f,3),v.Flash.position); // Even before another align/apply.
                    v.Apply(8,100,true,true,false,0,fire);Assert.IsFalse(v.Flash.gameObject.activeSelf);Assert.AreEqual(Vector3.zero,v.RecoilVisual.localPosition);
                    v.Apply(0,100,true,false,false,0,fire);Assert.IsTrue(v.Flash.gameObject.activeSelf);Assert.IsFalse(v.Action.LeftHand.gameObject.activeSelf);Assert.IsFalse(v.Action.RightHand.gameObject.activeSelf);
                    Assert.AreEqual(position+Vector3.right,pointer.transform.position);Assert.Less(Quaternion.Angle(rotation,pointer.transform.rotation),.0001f);
                }
                finally{v.Dispose();UnityEngine.Object.DestroyImmediate(v.Root);UnityEngine.Object.DestroyImmediate(pointer);UnityEngine.Object.DestroyImmediate(parent);}
            }
        }
        [Test] public void ReloadAndDisconnectedStateComposeWithoutMovingHandsOrRestartingAnOldShot()
        {
            using(var pool=new FiringRifleModels())
            {
                var v=pool.Create();try
                {
                    var fire=new PlayerFireState(1,4,new Vec3(0,1.5f,0),new Vec3(0,0,1));v.Apply(3,100,true,true,true,33,fire);
                    Assert.IsTrue(v.Flash.gameObject.activeSelf);Assert.AreEqual(Vector3.zero,v.RecoilVisual.localPosition);Assert.AreSame(v.RecoilVisual,v.Action.Magazine.parent);
                    v.Apply(11,100,true,true,true,33,fire);var expected=WeaponPresentation.Pose(11,100,true,true,true,33);
                    Assert.Less(Vector3.Distance(v.Action.Magazine.localPosition,new Vector3(0,-.075f,-.4025f)+new Vector3(expected.MagazineOffset.X,expected.MagazineOffset.Y,expected.MagazineOffset.Z)),.00001f);
                    Assert.IsFalse(v.Flash.gameObject.activeSelf);v.Apply(3,100,false,true,true,33,fire);Assert.IsFalse(v.Flash.gameObject.activeSelf);Assert.AreEqual(Vector3.zero,v.RecoilVisual.localPosition);
                    v.Apply(3,0,true,true,true,33,fire);Assert.IsFalse(v.Flash.gameObject.activeSelf);
                }
                finally{v.Dispose();UnityEngine.Object.DestroyImmediate(v.Root);}
            }
        }
        [Test] public void PlayerShotUsesTheAtomicActorRayFieldsAndTheirEqualityFence()
        {
            var expected=new CombatActorState{id=System.Guid.Parse("6bcd2409-6172-43af-8307-88255c0959f8"),enemy=false,connected=true,health=100,room=3,fireSequence=1,fireTickPlusOne=1,presentationTick=0,
                fireOrigin=new Vector3(0,1.5f,-3),fireDirection=Vector3.forward};
            using(var writer=new FastBufferWriter(1024,Allocator.Temp))
            {
                writer.WriteValueSafe(expected);using(var reader=new FastBufferReader(writer.ToArray(),Allocator.Temp))
                {reader.ReadValueSafe(out CombatActorState actual);Assert.IsTrue(expected.Equals(actual));actual.fireSequence++;Assert.IsFalse(expected.Equals(actual));}
            }
            var changed=expected;changed.fireDirection=Vector3.right;Assert.IsFalse(expected.Equals(changed));
        }
        [Test] public void CodecPreservesLegacyPlayersAndRequiresTheExplicitNewFireFlag()
        {
            var world=new ArenaWorld(new[]{3},new WorldProp[0]);world.AddPlayer(Guid.NewGuid(),3,new Vec3(0,1.65f,-3));
            RecordedRig Rig(Guid id)=>new RecordedRig{kind="Simulated",left=new RecordedVector(new Vec3(-.2f,1.35f,-2.8f)),right=new RecordedVector(new Vec3(0,1.65f,-3))};
            var codec=new UnityWorldCodec();var packet=WorldRecordingPacket.Capture(world,1,0,1,0,0,Rig,enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1);var json=codec.Packet(packet);
            foreach(var key in new[]{"fireOrigin","fireDirection"})json=json.Replace(",\""+key+"\":"+JsonUtility.ToJson(new RecordedVector()),"");
            json=json.Replace(",\"hasFireState\":false","").Replace(",\"fireSequence\":0","").Replace(",\"fireTickPlusOne\":0","");Assert.IsFalse(json.Contains("hasFireState"));
            var old=codec.ReadPacket(json);var header=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",new[]{3},new WorldProp[0],assetSet:WorldAssetSets.CombatEffects,enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1);
            WorldRecordingValidation.Packet(header,old,null);Assert.IsNotNull(old.frame.players[0].fireOrigin);Assert.IsFalse(old.frame.players[0].hasFireState);
            header.assetSet=WorldAssetSets.PlayerFire;header.playerFireVersion=1;Assert.Throws<ArgumentException>(()=>WorldRecordingValidation.Packet(header,old,null));
            var current=WorldRecordingPacket.Capture(world,1,0,1,0,0,Rig,enemyPresentationVersion:1,weaponPresentationVersion:1,enemyFireVersion:1,playerFireVersion:1);
            WorldRecordingValidation.Packet(header,codec.ReadPacket(codec.Packet(current)),null);
        }
    }
}
