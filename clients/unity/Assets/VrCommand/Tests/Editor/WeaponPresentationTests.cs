using System;
using NUnit.Framework;
using UnityEngine;
using Unity.Collections;
using Unity.Netcode;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class WeaponPresentationTests
    {
        [Test] public void SplitRifleRetainsItsOriginalMuzzleAndOutwardGeometry()
        {
            var data=AnimatedRifleModels.Read();var triangles=0;
            foreach(var part in data.parts)
            {
                var mesh=FieldPropModels.BuildMesh(part,WorldAssetSets.WeaponActions);
                try{triangles+=mesh.triangles.Length/3;var p=mesh.vertices;var n=mesh.normals;var t=mesh.triangles;
                    for(var i=0;i<t.Length;i+=3)Assert.Greater(Vector3.Dot(Vector3.Cross(p[t[i+1]]-p[t[i]],p[t[i+2]]-p[t[i]]),n[t[i]]),.0000001f);
                    if(part.kind=="Body"){Assert.AreEqual(0,mesh.bounds.max.z,.00001f);Assert.AreEqual(-.735f,mesh.bounds.min.z,.00001f);}}
                finally{UnityEngine.Object.DestroyImmediate(mesh);}
            }
            Assert.AreEqual(504,triangles);
        }
        [Test] public void SharedPartsSurviveOneAvatarLeaseAndNeverAddColliders()
        {
            var a=new AnimatedRifleModels();var b=new AnimatedRifleModels();var first=a.Create();var second=b.Create();
            try{Assert.AreSame(first.Root.GetComponent<MeshFilter>().sharedMesh,second.Root.GetComponent<MeshFilter>().sharedMesh);
                var geometry=second.Magazine.GetComponent<MeshFilter>().sharedMesh;a.Dispose();a.Dispose();Assert.IsTrue(geometry!=null);
                Assert.IsEmpty(second.Root.GetComponentsInChildren<Collider>(true));Assert.IsEmpty(second.Root.GetComponentsInChildren<NetworkObject>(true));
                Assert.Throws<ObjectDisposedException>(()=>a.Create());}
            finally{UnityEngine.Object.DestroyImmediate(first.Root);UnityEngine.Object.DestroyImmediate(second.Root);a.Dispose();b.Dispose();}
        }
        [Test] public void ReloadTransformsFollowSavedTimeAndLeaveTheMuzzleRootUnchanged()
        {
            using(var models=new AnimatedRifleModels())
            {
                var view=models.Create();try{view.Root.transform.SetPositionAndRotation(new Vector3(2,1.5f,3),Quaternion.Euler(15,30,20));var pos=view.Root.transform.position;var rot=view.Root.transform.rotation;
                    view.Apply(8,100,true,true,true,30);var mag=view.Magazine.localPosition;var hand=view.LeftHand.localPosition;
                    Assert.Less(mag.y,-.2f);Assert.IsTrue(view.LeftHand.gameObject.activeSelf);Assert.AreEqual(pos,view.Root.transform.position);Assert.AreEqual(rot,view.Root.transform.rotation);
                    view.Apply(14,100,true,true,true,30);Assert.IsFalse(view.Magazine.gameObject.activeSelf);
                    view.Apply(8,100,true,true,true,30);Assert.AreEqual(mag,view.Magazine.localPosition);Assert.AreEqual(hand,view.LeftHand.localPosition);
                    view.Apply(30,100,true,true,false,0);Assert.AreEqual(-.075f,view.Magazine.localPosition.y,.00001f);Assert.IsTrue(view.Magazine.gameObject.activeSelf);}
                finally{UnityEngine.Object.DestroyImmediate(view.Root);}
            }
        }
        [Test] public void TrackedJointsAreNeverReplacedByCosmeticGloves()
        {
            using(var models=new AnimatedRifleModels())
            {
                var view=models.Create();var pointer=new GameObject("Actual tracked pointer");pointer.transform.SetPositionAndRotation(new Vector3(1,1.3f,.4f),Quaternion.Euler(10,40,25));
                try{var pos=pointer.transform.position;var rot=pointer.transform.rotation;ServiceRifleModels.Align(view.Root.transform,pointer.transform);
                    view.Apply(8,100,true,false,true,30);Assert.IsFalse(view.RightHand.gameObject.activeSelf);Assert.IsFalse(view.LeftHand.gameObject.activeSelf);
                    Assert.AreEqual(pos,pointer.transform.position);Assert.AreEqual(rot,pointer.transform.rotation);Assert.Less(Vector3.Distance(view.Root.transform.position,pos+pointer.transform.forward*AvatarPose.MuzzleOffset),.00001f);}
                finally{UnityEngine.Object.DestroyImmediate(view.Root);UnityEngine.Object.DestroyImmediate(pointer);}
            }
        }
        [Test] public void ReloadClockIsAtomicWithThePlayerNetworkStateAndJsonCapture()
        {
            var expected=new CombatActorState{id="6bcd2409-6172-43af-8307-88255c0959f8",health=100,magazine=29,reserve=90,reloading=true,presentationTick=8,reloadUntilTick=30};
            using(var writer=new FastBufferWriter(512,Allocator.Temp))
            {writer.WriteValueSafe(expected);using(var reader=new FastBufferReader(writer.ToArray(),Allocator.Temp)){reader.ReadValueSafe(out CombatActorState actual);Assert.IsTrue(expected.Equals(actual));actual.reloadUntilTick++;Assert.IsFalse(expected.Equals(actual));}}
            var world=new ArenaWorld(new[]{3},new WorldProp[0]);var id=Guid.NewGuid();world.AddPlayer(id,3,new Vec3(0,1.65f,-3));world.SetPhase(WorldPhase.Running);world.Fire(id,Guid.NewGuid());world.Reload(id,Guid.NewGuid());
            var packet=WorldRecordingPacket.Capture(world,1,0,1,1,0,_=>new RecordedRig(),weaponPresentationVersion:1);var codec=new UnityWorldCodec();var read=codec.ReadPacket(codec.Packet(packet));
            Assert.IsTrue(read.frame.players[0].hasWeaponPresentation);Assert.AreEqual(30,read.frame.players[0].reloadUntilTick);
            var old=codec.ReadPacket(codec.Packet(WorldRecordingPacket.Capture(world,1,0,1,1,0,_=>new RecordedRig())).Replace(",\"hasWeaponPresentation\":false","").Replace(",\"reloadUntilTick\":0",""));
            Assert.IsFalse(old.frame.players[0].hasWeaponPresentation);Assert.AreEqual(0,old.frame.players[0].reloadUntilTick);
        }
    }
}
