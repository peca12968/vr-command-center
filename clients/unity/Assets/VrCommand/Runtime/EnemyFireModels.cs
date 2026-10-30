using System;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    [Serializable] public sealed class EnemyFireDefinition
    { public string assetSet,units,origin,forward; public int enemyFireVersion; public FieldPropMesh mesh; }
    public sealed class EnemyFireView
    {
        public readonly ArmedEnemyView Body;
        public readonly Transform RecoilVisual,Flash;
        public GameObject Root=>Body.Root;
        public long AppliedTick { get; private set; }
        public EnemyFireState AppliedFire { get; private set; }
        internal EnemyFireView(ArmedEnemyView body,Transform recoil,Transform flash) { Body=body;RecoilVisual=recoil;Flash=flash; }
        public void Apply(Vec3 facing,bool walking,long tick,int health,EnemyFireState fire)
        {
            Body.Apply(facing,walking,tick);var pose=EnemyFirePresentation.Pose(tick,health,fire);
            AppliedTick=tick;AppliedFire=fire;
            RecoilVisual.localPosition=Vector3.back*pose.Recoil;Flash.gameObject.SetActive(pose.Flash);
            if(fire.Sequence>0)
            {
                Flash.position=new Vector3(fire.Origin.X,fire.Origin.Y,fire.Origin.Z);
                Flash.rotation=Quaternion.FromToRotation(Vector3.forward,new Vector3(fire.Direction.X,fire.Direction.Y,fire.Direction.Z).normalized);
            }
        }
    }
    public sealed class EnemyFireModels : IDisposable
    {
        private ArmedEnemyModels bodies;
        private Mesh flash;
        private Material material;
        public static EnemyFireDefinition Read()
        {
            var asset=Resources.Load<TextAsset>("VrCommand/combat-effects-v1");if(asset==null)throw new InvalidOperationException("Enemy fire mesh is missing.");
            var data=JsonUtility.FromJson<EnemyFireDefinition>(asset.text);
            if(data==null || data.assetSet!=WorldAssetSets.CombatEffects || data.units!="metres" || data.origin!="accepted-enemy-shot" || data.forward!="+Z"
                || data.enemyFireVersion!=1 || data.mesh?.kind!="EnemyMuzzleFlash")throw new InvalidOperationException("Unsupported enemy fire metadata.");
            return data;
        }
        public EnemyFireModels()
        {
            try
            {
                bodies=new ArmedEnemyModels();flash=FieldPropModels.BuildMesh(Read().mesh,WorldAssetSets.CombatEffects);
                var shader=Resources.Load<Shader>("VrCommand/EnemyFire");if(shader==null)throw new InvalidOperationException("Enemy fire shader is missing.");
                material=new Material(shader){name=WorldAssetSets.CombatEffects,enableInstancing=true};
            }
            catch{Dispose();throw;}
        }
        public EnemyFireView Create()
        {
            if(material==null)throw new ObjectDisposedException(nameof(EnemyFireModels));
            var body=bodies.Create();
            // Keep the authority-aligned Gun transform and gloves untouched.
            // Only a child renderer recoils; the original renderer is disabled.
            var renderer=body.Gun.GetComponent<MeshRenderer>();renderer.enabled=false;
            var recoil=new GameObject("Cosmetic sidearm recoil");recoil.transform.SetParent(body.Gun,false);
            recoil.AddComponent<MeshFilter>().sharedMesh=body.Gun.GetComponent<MeshFilter>().sharedMesh;recoil.AddComponent<MeshRenderer>().sharedMaterial=renderer.sharedMaterial;
            var pulse=new GameObject("Accepted enemy shot flash");pulse.transform.SetParent(body.Root.transform,false);
            pulse.AddComponent<MeshFilter>().sharedMesh=flash;pulse.AddComponent<MeshRenderer>().sharedMaterial=material;pulse.SetActive(false);
            return new EnemyFireView(body,recoil.transform,pulse.transform);
        }
        public void Dispose(){bodies?.Dispose();bodies=null;Release(flash);Release(material);flash=null;material=null;}
        private static void Release(UnityEngine.Object value)
        {if(value==null)return;if(Application.isPlaying)UnityEngine.Object.Destroy(value);else UnityEngine.Object.DestroyImmediate(value);}
    }
}
