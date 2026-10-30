using System;
using NUnit.Framework;
using UnityEngine;
using Unity.Netcode;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class ArmedEnemyTests
    {
        [Test] public void OriginalArmedMeshesHaveOutwardFiniteFacesAndFixedBudget()
        {
            var count=0;var data=ArmedEnemyModels.Read();
            foreach(var part in data.parts)
            {
                var mesh=FieldPropModels.BuildMesh(part,WorldAssetSets.ArmedCombatants);
                try
                {
                    count+=mesh.triangles.Length/3*(part.kind=="Leg"||part.kind=="UpperArm"||part.kind=="LowerArm"?2:1);
                    var p=mesh.vertices;var n=mesh.normals;var t=mesh.triangles;
                    for(var i=0;i<t.Length;i+=3)Assert.Greater(Vector3.Dot(Vector3.Cross(p[t[i+1]]-p[t[i]],p[t[i+2]]-p[t[i]]),n[t[i]]),.0000001f);
                }
                finally{UnityEngine.Object.DestroyImmediate(mesh);}
            }
            Assert.AreEqual(728,count);
        }
        [Test] public void ArmedPoolSharesEightMeshesAndOneMaterialWithNoCollisionOrNetworkObjects()
        {
            using(var pool=new ArmedEnemyModels())
            {
                var a=pool.Create();var b=pool.Create();
                try
                {
                    var first=a.Root.GetComponentsInChildren<MeshFilter>();var second=b.Root.GetComponentsInChildren<MeshFilter>();
                    Assert.AreEqual(11,first.Length);for(var i=0;i<first.Length;i++)Assert.AreSame(first[i].sharedMesh,second[i].sharedMesh);
                    var meshes=new System.Collections.Generic.HashSet<Mesh>();foreach(var filter in first)meshes.Add(filter.sharedMesh);Assert.AreEqual(8,meshes.Count);
                    foreach(var renderer in a.Root.GetComponentsInChildren<MeshRenderer>())Assert.AreSame(renderer.sharedMaterial,b.Head.GetComponent<MeshRenderer>().sharedMaterial);
                    Assert.IsEmpty(a.Root.GetComponentsInChildren<Collider>());Assert.IsEmpty(a.Root.GetComponentsInChildren<NetworkObject>());
                    UnityEngine.Object.DestroyImmediate(a.Root);Assert.IsNotNull(second[0].sharedMesh);
                }
                finally{if(a.Root!=null)UnityEngine.Object.DestroyImmediate(a.Root);UnityEngine.Object.DestroyImmediate(b.Root);}
            }
        }
        [Test] public void MuzzleAndDirectionMatchAuthorityWithActualFixedLengthArmTransforms()
        {
            using(var pool=new ArmedEnemyModels())
            {
                var view=pool.Create();try
                {
                    view.Root.transform.position=new Vector3(28,0,3);
                    foreach(var direction in new[]{new Vec3(0,0,1),new Vec3(1,.2f,-1).Normalized(),new Vec3(0,1,0),new Vec3(0,-1,0),new Vec3(0,.501f,.87f)})
                    {
                        view.Apply(direction,true,3);
                        Assert.Less(Vector3.Distance(view.Gun.position,view.Root.transform.position+new Vector3(0,1.4f,0)),.00001f);
                        Assert.Less(Vector3.Distance(view.Gun.forward,new Vector3(direction.X,direction.Y,direction.Z).normalized),.00001f);
                        foreach(var pair in new[]{new[]{view.LeftUpper,view.LeftLower},new[]{view.RightUpper,view.RightLower}})
                        {
                            Assert.AreEqual(.22f,pair[0].localScale.y,.00001f);Assert.AreEqual(.25f,pair[1].localScale.y,.00001f);
                            Assert.Less(Vector3.Distance(pair[0].TransformPoint(Vector3.up),pair[1].position),.00001f);
                        }
                        var pose=ArmedEnemyPresentation.Pose(direction,true,3);
                        Assert.Less(Vector3.Distance(view.LeftLower.TransformPoint(Vector3.up),view.Gun.TransformPoint(new Vector3(-.07f,-.085f,-.035f))),.00001f);
                        Assert.Less(Vector3.Distance(view.RightLower.TransformPoint(Vector3.up),view.Gun.TransformPoint(new Vector3(.07f,-.11f,-.075f))),.00001f);
                    }
                }
                finally{UnityEngine.Object.DestroyImmediate(view.Root);}
            }
        }
        [Test] public void DirectSeeksRestoreArmsAndDoNotMoveRecordedFeetOrGunRoot()
        {
            using(var pool=new ArmedEnemyModels())
            {
                var v=pool.Create();try
                {
                    var f=new Vec3(-1,.6f,1).Normalized();var position=new Vector3(14,0,-2);v.Root.transform.position=position;v.Apply(f,true,3);
                    var elbow=v.LeftLower.position;var rotation=v.Gun.rotation;v.Apply(new Vec3(0,0,-1),true,9);v.Apply(f,true,3);
                    Assert.AreEqual(position,v.Root.transform.position);Assert.Less(Vector3.Distance(elbow,v.LeftLower.position),.00001f);
                    Assert.Less(Quaternion.Angle(rotation,v.Gun.rotation),.001f);Assert.AreEqual(new Vector3(0,1.4f,0),v.Gun.localPosition);
                    Assert.Less(Quaternion.Angle(v.LeftLeg.localRotation,Quaternion.Euler(18,0,0)),.001f);
                    Assert.AreEqual(new Vector3(0,-.085f,-.035f),v.LeftHand.localPosition);
                }
                finally{UnityEngine.Object.DestroyImmediate(v.Root);}
            }
        }
    }
}
