using System;
using System.Linq;
using NUnit.Framework;
using Unity.Collections;
using Unity.Netcode;
using UnityEngine;
using VrCommand.Simulation;
namespace VrCommand.Unity.Tests
{
    public sealed class PlayerBodyTests
    {
        private static CombatActorState State()=>new CombatActorState{presentationTick=3,health=100,connected=true,walking=true};
        [Test] public void BodyMeshesBorrowOnePoolAndReleaseOnlyAfterLastLease()
        {
            var a=new PlayerBodyModels();var b=new PlayerBodyModels();var av=a.Create();var bv=b.Create();var mesh=av.Head.GetComponent<MeshFilter>().sharedMesh;
            try{Assert.AreSame(mesh,bv.Head.GetComponent<MeshFilter>().sharedMesh);Assert.AreSame(av.Head.GetComponent<Renderer>().sharedMaterial,bv.Head.GetComponent<Renderer>().sharedMaterial);a.Dispose();Assert.IsTrue(mesh!=null);Assert.IsEmpty(bv.Root.GetComponentsInChildren<Collider>());Assert.IsEmpty(bv.Root.GetComponentsInChildren<NetworkObject>());}
            finally{av.Dispose();bv.Dispose();a.Dispose();b.Dispose();}Assert.IsTrue(mesh==null);Assert.Throws<ObjectDisposedException>(()=>b.Create());
        }
        [Test] public void ActualHeadAndLegTransformsRestoreSavedPoseAtEveryHeight()
        {
            using(var pool=new PlayerBodyModels()){var v=pool.Create();try{foreach(var h in new[]{.45f,1.65f,2.4f}){var head=new Vector3(2,h,-3);var q=Quaternion.Euler(25,90,0);var s=State();v.Apply("test",head,q,head+q*new Vector3(.18f,-.12f,.9f),q*Vector3.forward,s,true,true);
                Assert.Less(Vector3.Distance(head,v.Head.position),.00001f);Assert.Less(Quaternion.Angle(q,v.Head.rotation),.001f);Assert.AreEqual(h/1.65f,v.Body.localScale.y,.00001f);Assert.AreEqual(18,Mathf.DeltaAngle(0,v.LeftLeg.localEulerAngles.x),.001f);Assert.AreEqual(-18,Mathf.DeltaAngle(0,v.RightLeg.localEulerAngles.x),.001f);
                var before=v.LeftLeg.localToWorldMatrix;v.Apply("test",head,q,head+q*new Vector3(.18f,-.12f,.9f),q*Vector3.forward,s,true,true);Assert.AreEqual(before,v.LeftLeg.localToWorldMatrix);}}
                finally{v.Dispose();}}
        }
        [Test] public void SimulatedArmsEndAtExistingGlovesAndTrackedModeHidesSyntheticArms()
        {
            using(var pool=new PlayerBodyModels()){var v=pool.Create();try{var head=new Vector3(0,1.65f,0);var muzzle=head+new Vector3(.18f,-.12f,.9f);var s=State();v.Apply("test",head,Quaternion.identity,muzzle,Vector3.forward,s,true,true);
                Assert.IsTrue(v.Observation.arms);Assert.AreEqual(v.RightLower.TransformPoint(Vector3.up),v.Observation.rightWrist);Assert.Less(Vector3.Distance(v.RightLower.TransformPoint(Vector3.up),muzzle+new Vector3(.06f,-.15f,-.595f)),.00001f);
                v.Apply("test",head,Quaternion.identity,muzzle,Vector3.forward,s,false,true);Assert.IsFalse(v.LeftUpper.gameObject.activeSelf);Assert.IsFalse(v.RightLower.gameObject.activeSelf);Assert.IsTrue(v.Root.activeSelf);Assert.AreEqual(head,v.Head.position);}
                finally{v.Dispose();}}
        }
        [Test] public void OwnerAndInactiveBodiesStayHiddenWithoutMovingAuthorityTransforms()
        {
            using(var pool=new PlayerBodyModels()){var v=pool.Create();try{var head=new Vector3(0,1.65f,0);var s=State();v.Apply("self",head,Quaternion.identity,head+Vector3.forward*.8f,Vector3.forward,s,true,false);Assert.IsFalse(v.Root.activeSelf);
                s.health=0;s.walking=false;v.Apply("dead",head,Quaternion.identity,head+Vector3.forward*.8f,Vector3.forward,s,true,true);Assert.IsFalse(v.Root.activeSelf);Assert.AreEqual(head,v.Head.position);}
                finally{v.Dispose();}}
        }
        [Test] public void PlayerWalkingSharesItsAtomicNgoClockAndEquality()
        {
            var state=State();state.id="7cb9976a-9bda-4dce-8e57-be203e0ca849";using(var w=new FastBufferWriter(1024,Allocator.Temp)){w.WriteValueSafe(state);using(var r=new FastBufferReader(w.ToArray(),Allocator.Temp)){r.ReadValueSafe(out CombatActorState copy);Assert.IsTrue(copy.walking);Assert.IsTrue(copy.Equals(state));copy.walking=false;Assert.IsFalse(copy.Equals(state));}}
        }
        [Test] public void JsonUtilityKeepsNewPlayerContractAndLegacyDefaults()
        {
            var codec=new UnityWorldCodec();var h=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",new[]{3},new WorldProp[0]);Assert.AreEqual(0,codec.ReadHeader(codec.Header(h)).playerPresentationVersion);
            h.assetSet=WorldAssetSets.PlayerBody;h.playerPresentationVersion=h.enemyPresentationVersion=h.weaponPresentationVersion=h.playerFireVersion=h.enemyFireVersion=1;WorldRecordingValidation.Header(codec.ReadHeader(codec.Header(h)));h.playerPresentationVersion=2;Assert.Throws<ArgumentException>(()=>WorldRecordingValidation.Header(h));
        }
        [Test] public void HiddenOwnerDoesNotValidateOrMoveLiveOutOfBoundsTrackedInput()
        {
            using(var pool=new PlayerBodyModels()){var view=pool.Create();try{Assert.DoesNotThrow(()=>view.Apply("owner",new Vector3(0,3,0),Quaternion.identity,new Vector3(0,3,1),Vector3.forward,State(),false,false));Assert.IsFalse(view.Root.activeSelf);Assert.IsNull(view.Observation);}finally{view.Dispose();}}
        }
        [Test] public void AcceptedNonUnitRigRotationNormalizesOnlyTheNewVisual()
        {
            using(var pool=new PlayerBodyModels()){var view=pool.Create();try{var unit=Quaternion.Euler(0,90,0);var saved=new Quaternion(unit.x*.97f,unit.y*.97f,unit.z*.97f,unit.w*.97f);var before=saved;
                Assert.DoesNotThrow(()=>view.Apply("remote",new Vector3(0,1.65f,0),saved,new Vector3(.8f,1.5f,0),Vector3.right,State(),false,true));Assert.AreEqual(before,saved);Assert.Less(Quaternion.Angle(unit,view.Head.rotation),.001f);Assert.AreEqual(90,view.Observation.yaw,.001f);}finally{view.Dispose();}}
        }
        [Test] public void DesktopFirstPersonKeepsOnlySleevesAndTheOriginalGloveEndpoints()
        {
            using(var pool=new PlayerBodyModels()){var view=pool.Create();try{var head=new Vector3(0,1.65f,0);var muzzle=head+new Vector3(.18f,-.12f,.9f);
                view.ApplyFirstPerson("self",head,Quaternion.identity,muzzle,Vector3.forward,State(),true);
                Assert.IsTrue(view.Root.activeSelf);Assert.IsTrue(view.Observation.firstPerson);Assert.IsTrue(view.Observation.arms);
                Assert.IsFalse(view.Body.gameObject.activeSelf);Assert.IsFalse(view.Head.gameObject.activeSelf);Assert.IsFalse(view.LeftLeg.gameObject.activeInHierarchy);
                Assert.IsTrue(view.LeftUpper.gameObject.activeInHierarchy);Assert.IsTrue(view.RightLower.gameObject.activeInHierarchy);
                Assert.Less(Vector3.Distance(view.RightLower.TransformPoint(Vector3.up),muzzle+new Vector3(.06f,-.15f,-.595f)),.00001f);
                Assert.IsEmpty(view.Root.GetComponentsInChildren<Collider>(true));Assert.IsEmpty(view.Root.GetComponentsInChildren<NetworkObject>(true));
            }finally{view.Dispose();}}
        }
        [Test] public void FirstPersonNeverEvaluatesAnUnboundedTrackedOwner()
        {
            using(var pool=new PlayerBodyModels()){var view=pool.Create();try{
                Assert.DoesNotThrow(()=>view.ApplyFirstPerson("xr",new Vector3(float.NaN,3,0),new Quaternion(0,0,0,0),Vector3.zero,Vector3.zero,State(),false));
                Assert.IsFalse(view.Root.activeSelf);Assert.IsNull(view.Observation);
            }finally{view.Dispose();}}
        }
        [Test] public void FirstPersonDisappearsWhenTheAcceptedPlayerIsDeadOrDisconnected()
        {
            using(var pool=new PlayerBodyModels()){var view=pool.Create();try{var head=new Vector3(0,1.65f,0);var muzzle=head+new Vector3(.18f,-.12f,.9f);
                foreach(var dead in new[]{false,true}){var state=State();state.health=dead?0:100;state.connected=dead;state.walking=false;
                    view.ApplyFirstPerson("self",head,Quaternion.identity,muzzle,Vector3.forward,state,true);
                    Assert.IsFalse(view.Root.activeInHierarchy);Assert.IsFalse(view.LeftLower.gameObject.activeInHierarchy);Assert.IsFalse(view.Observation.visible);}
            }finally{view.Dispose();}}
        }
        [Test] public void ChangingPresentationModeRestoresTheRemoteHeadTorsoAndLegs()
        {
            using(var pool=new PlayerBodyModels()){var view=pool.Create();try{var head=new Vector3(0,1.65f,0);var muzzle=head+new Vector3(.18f,-.12f,.9f);
                view.ApplyFirstPerson("self",head,Quaternion.identity,muzzle,Vector3.forward,State(),true);
                view.Apply("remote",head,Quaternion.identity,muzzle,Vector3.forward,State(),true,true);
                Assert.IsTrue(view.Root.activeSelf);Assert.IsTrue(view.Head.gameObject.activeInHierarchy);Assert.IsTrue(view.Body.gameObject.activeInHierarchy);Assert.IsTrue(view.LeftLeg.gameObject.activeInHierarchy);
                Assert.IsFalse(view.Observation.firstPerson);Assert.AreEqual(18,view.Observation.stride,.001f);
            }finally{view.Dispose();}}
        }
        [Test] public void FirstPersonReloadUsesTheSavedWristClockAndHoldsAcrossPause()
        {
            using(var pool=new PlayerBodyModels()){var view=pool.Create();try{var head=new Vector3(0,1.65f,0);var muzzle=head+new Vector3(.18f,-.12f,.9f);var state=State();state.presentationTick=12;
                view.ApplyFirstPerson("self",head,Quaternion.identity,muzzle,Vector3.forward,state,true);var idle=view.Observation.leftWrist;
                state.reloading=true;state.reloadUntilTick=30;view.ApplyFirstPerson("self",head,Quaternion.identity,muzzle,Vector3.forward,state,true);
                Assert.Greater(Vector3.Distance(idle,view.Observation.leftWrist),.01f);var left=view.LeftLower.localToWorldMatrix;var right=view.RightLower.localToWorldMatrix;
                view.ApplyFirstPerson("self",head,Quaternion.identity,muzzle,Vector3.forward,state,true);Assert.AreEqual(left,view.LeftLower.localToWorldMatrix);Assert.AreEqual(right,view.RightLower.localToWorldMatrix);
                Assert.AreEqual(12,view.Observation.tick);Assert.IsTrue(view.Observation.firstPerson);
            }finally{view.Dispose();}}
        }
    }
}
