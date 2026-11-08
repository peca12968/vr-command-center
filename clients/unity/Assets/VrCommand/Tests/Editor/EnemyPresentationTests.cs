using System;
using NUnit.Framework;
using UnityEngine;
using Unity.Collections;
using Unity.Netcode;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class EnemyPresentationTests
    {
        [Test] public void OriginalHumanoidHasFiniteOutwardFacesAndAFixedBudget()
        {
            var data=EnemyModels.Read(); var count=0;
            foreach(var part in data.parts)
            {
                var mesh=FieldPropModels.BuildMesh(part,WorldAssetSets.Combatants);
                try
                {
                    count+=mesh.triangles.Length/3*(part.kind=="Leg"?2:1);
                    var p=mesh.vertices;var n=mesh.normals;var t=mesh.triangles;
                    for(var i=0;i<t.Length;i+=3) Assert.Greater(Vector3.Dot(Vector3.Cross(p[t[i+1]]-p[t[i]],p[t[i+2]]-p[t[i]]),n[t[i]]),.0000001f);
                }
                finally{UnityEngine.Object.DestroyImmediate(mesh);}
            }
            Assert.AreEqual(404,count);Assert.AreEqual(1,data.enemyPresentationVersion);
        }
        [Test] public void OpponentsShareThreeMeshesAndOneMaterialWithoutChangingAuthorityGeometry()
        {
            using(var models=new EnemyModels())
            {
                var a=models.Create();var b=models.Create();
                try
                {
                    var first=a.Root.GetComponentsInChildren<MeshFilter>();var second=b.Root.GetComponentsInChildren<MeshFilter>();
                    Assert.AreEqual(4,first.Length);for(var i=0;i<4;i++)Assert.AreSame(first[i].sharedMesh,second[i].sharedMesh);
                    Assert.AreSame(first[2].sharedMesh,first[3].sharedMesh);
                    Assert.AreSame(a.Head.GetComponent<MeshRenderer>().sharedMaterial,b.RightLeg.GetComponent<MeshRenderer>().sharedMaterial);
                    Assert.IsEmpty(a.Root.GetComponentsInChildren<Collider>());Assert.IsEmpty(a.Root.GetComponentsInChildren<NetworkObject>());
                    UnityEngine.Object.DestroyImmediate(a.Root);Assert.IsTrue(second[0].sharedMesh!=null);
                }
                finally{if(a.Root!=null)UnityEngine.Object.DestroyImmediate(a.Root);UnityEngine.Object.DestroyImmediate(b.Root);}
            }
        }
        [Test] public void SavedTickDrivesActualTransformsAndDirectSeekRestoresTheSamePose()
        {
            using(var models=new EnemyModels())
            {
                var a=models.Create();try
                {
                    var direction=new Vec3(1,.2f,1).Normalized();a.Apply(direction,true,3);
                    var root=a.Root.transform.rotation;var head=a.Head.localRotation;var left=a.LeftLeg.localRotation;
                    Assert.Less(Quaternion.Angle(left,Quaternion.Euler(18,0,0)),.001f);
                    Assert.Less(Quaternion.Angle(a.RightLeg.localRotation,Quaternion.Euler(-18,0,0)),.001f);
                    a.Apply(direction,true,9);a.Apply(direction,true,3);
                    Assert.Less(Quaternion.Angle(root,a.Root.transform.rotation),.001f);Assert.Less(Quaternion.Angle(head,a.Head.localRotation),.001f);
                    Assert.Less(Quaternion.Angle(left,a.LeftLeg.localRotation),.001f);
                    a.Apply(direction,false,3);Assert.Less(Quaternion.Angle(a.LeftLeg.localRotation,Quaternion.identity),.001f);
                }
                finally{UnityEngine.Object.DestroyImmediate(a.Root);}
            }
        }
        [Test] public void EnemyPoseAndTickTravelAtomicallyInTheNetworkActorRow()
        {
            var expected=new CombatActorState{id=System.Guid.Parse("6bcd2409-6172-43af-8307-88255c0959f8"),enemy=true,room=3,health=100,
                position=new Vector3(2,0,3),facing=new Vector3(0,0,-1),walking=true,presentationTick=9};
            using(var writer=new FastBufferWriter(512,Allocator.Temp))
            {
                writer.WriteValueSafe(expected);using(var reader=new FastBufferReader(writer.ToArray(),Allocator.Temp))
                {reader.ReadValueSafe(out CombatActorState actual);Assert.IsTrue(expected.Equals(actual));actual.presentationTick++;Assert.IsFalse(expected.Equals(actual));}
            }
        }
        [Test] public void CodecKeepsLegacyEnemiesUnanimatedAndRejectsMissingVersionedFacing()
        {
            var world=new ArenaWorld(new[]{3},new WorldProp[0]);world.AddEnemy(Guid.NewGuid(),3,new Vec3(0,0,3),new Vec3(2,0,3));
            var codec=new UnityWorldCodec();var packet=WorldRecordingPacket.Capture(world,1,0,1,0,0,_=>new RecordedRig());
            var json=codec.Packet(packet);var forward="\"forward\":"+JsonUtility.ToJson(packet.frame.enemies[0].forward)+",";
            Assert.IsTrue(json.Contains(forward));
            json=json.Replace(forward,"").Replace(",\"hasPresentation\":false","").Replace(",\"walking\":false","");
            var old=codec.ReadPacket(json);Assert.IsFalse(old.frame.enemies[0].hasPresentation);Assert.IsFalse(old.frame.enemies[0].walking);
            Assert.IsNotNull(old.frame.enemies[0].forward);Assert.AreEqual(0,old.frame.enemies[0].forward.ToVector().Length);
            var legacy=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",new[]{3},new WorldProp[0]);
            WorldRecordingValidation.Packet(legacy,old,null);
            var header=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",new[]{3},new WorldProp[0],assetSet:WorldAssetSets.Combatants,enemyPresentationVersion:1);
            Assert.Throws<ArgumentException>(()=>WorldRecordingValidation.Packet(header,old,null));
            var current=WorldRecordingPacket.Capture(world,1,0,1,0,0,_=>new RecordedRig(),enemyPresentationVersion:1);
            WorldRecordingValidation.Packet(header,codec.ReadPacket(codec.Packet(current)),null);
        }
    }
}
