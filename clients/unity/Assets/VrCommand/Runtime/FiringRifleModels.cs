using System;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    [Serializable] public sealed class PlayerFireDefinition
    {
        public string assetSet,units,origin,forward,weaponAssetSet,weaponDataSha256,pulseAssetSet,pulseDataSha256;
        public int playerFireVersion,flashTicks;
        public float pulseScale;
        public float[] recoilMetres;
    }
    public sealed class FiringRifleView : IDisposable
    {
        public readonly AnimatedRifleView Action;
        public readonly Transform RecoilVisual,Flash;
        public readonly MeshRenderer HiddenBody;
        public GameObject Root=>Action.Root;
        public long AppliedTick {get;private set;}
        public PlayerFireState AppliedFire {get;private set;}
        private bool disposed;
        internal FiringRifleView(AnimatedRifleView action,Transform recoil,Transform flash,MeshRenderer hidden)
        {Action=action;RecoilVisual=recoil;Flash=flash;HiddenBody=hidden;}
        public void Apply(long tick,int health,bool connected,bool simulated,bool reloading,long until,PlayerFireState fire)
        {
            HiddenBody.enabled=false;
            Action.Apply(tick,health,connected,simulated,reloading,until);
            var pose=PlayerFirePresentation.Pose(tick,health,connected,reloading,fire);AppliedTick=tick;AppliedFire=fire;
            RecoilVisual.localPosition=Vector3.back*pose.Recoil;Flash.gameObject.SetActive(pose.Flash);
            if(fire.Sequence>0)
            {
                Flash.position=new Vector3(fire.Origin.X,fire.Origin.Y,fire.Origin.Z);
                Flash.rotation=Quaternion.FromToRotation(Vector3.forward,new Vector3(fire.Direction.X,fire.Direction.Y,fire.Direction.Z).normalized);
            }
        }
        public void Dispose()
        {
            if(disposed)return;disposed=true;
            if(Flash!=null){if(Application.isPlaying)UnityEngine.Object.Destroy(Flash.gameObject);else UnityEngine.Object.DestroyImmediate(Flash.gameObject);}
        }
    }
    public sealed class FiringRifleModels : IDisposable
    {
        private sealed class Shared{internal Mesh Mesh;internal Material Material;internal int Leases;}
        private static Shared shared;
        private Shared lease;
        private AnimatedRifleModels rifles;
        public static PlayerFireDefinition Read()
        {
            var asset=Resources.Load<TextAsset>("VrCommand/player-fire-v1");if(asset==null)throw new InvalidOperationException("Player fire profile is missing.");
            var d=JsonUtility.FromJson<PlayerFireDefinition>(asset.text);
            if(d==null || d.assetSet!=WorldAssetSets.PlayerFire || d.units!="metres" || d.origin!="accepted-player-shot" || d.forward!="+Z" || d.playerFireVersion!=1
                || d.weaponAssetSet!=WorldAssetSets.WeaponActions || d.pulseAssetSet!=WorldAssetSets.CombatEffects || d.pulseScale!=PlayerFirePresentation.PulseScale || d.flashTicks!=3
                || d.weaponDataSha256!="517c3616ec12dad34f25cc50f5309eae1033b62bcbbb636b4a3f378a5c12cab3"
                || d.pulseDataSha256!="b8fe83d66781c2f65816d6873cc08ba01314418d42777a55e9eea2d1ee34a9bb"
                || d.recoilMetres==null || d.recoilMetres.Length!=4)throw new InvalidOperationException("Unsupported player fire profile.");
            var expected=new[]{.014f,.022f,.012f,.004f};for(var i=0;i<4;i++)if(d.recoilMetres[i]!=expected[i])throw new InvalidOperationException("Player recoil differs from its fixed contract.");
            return d;
        }
        public FiringRifleModels()
        {
            Read();rifles=new AnimatedRifleModels();
            if(shared==null)
            {
                var value=new Shared();try
                {
                    value.Mesh=FieldPropModels.BuildMesh(EnemyFireModels.Read().mesh,WorldAssetSets.PlayerFire);
                    var shader=Resources.Load<Shader>("VrCommand/EnemyFire");if(shader==null)throw new InvalidOperationException("Player fire shader is missing.");
                    value.Material=new Material(shader){name=WorldAssetSets.PlayerFire,enableInstancing=true};shared=value;
                }
                catch{Release(value.Mesh);Release(value.Material);rifles.Dispose();rifles=null;throw;}
            }
            lease=shared;lease.Leases++;
        }
        public FiringRifleView Create()
        {
            if(lease==null)throw new ObjectDisposedException(nameof(FiringRifleModels));
            var action=rifles.Create();var renderer=action.Root.GetComponent<MeshRenderer>();renderer.enabled=false;
            var recoil=new GameObject("Cosmetic rifle recoil");recoil.transform.SetParent(action.Root.transform,false);
            var body=new GameObject("Rifle body renderer");body.transform.SetParent(recoil.transform,false);
            body.AddComponent<MeshFilter>().sharedMesh=action.Root.GetComponent<MeshFilter>().sharedMesh;body.AddComponent<MeshRenderer>().sharedMaterial=renderer.sharedMaterial;
            action.Magazine.SetParent(recoil.transform,false);
            // A detached scene object cannot be shifted by XR before-render
            // tracking updates after the accepted historical ray was applied.
            var flash=new GameObject("Accepted player shot flash");flash.transform.localScale=Vector3.one*PlayerFirePresentation.PulseScale;
            flash.AddComponent<MeshFilter>().sharedMesh=lease.Mesh;flash.AddComponent<MeshRenderer>().sharedMaterial=lease.Material;flash.SetActive(false);
            var view=new FiringRifleView(action,recoil.transform,flash.transform,renderer);view.Apply(0,100,false,false,false,0,default);return view;
        }
        public void Dispose()
        {
            rifles?.Dispose();rifles=null;if(lease==null)return;var value=lease;lease=null;if(--value.Leases!=0)return;if(ReferenceEquals(shared,value))shared=null;
            Release(value.Mesh);Release(value.Material);
        }
        private static void Release(UnityEngine.Object value)
        {if(value==null)return;if(Application.isPlaying)UnityEngine.Object.Destroy(value);else UnityEngine.Object.DestroyImmediate(value);}
    }
}
