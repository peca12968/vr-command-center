using System;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    [Serializable] public sealed class AnimatedRifleDefinition
    { public string assetSet,units,origin,forward; public int weaponPresentationVersion; public float[] magazinePivot; public FieldPropMesh[] parts; }
    public sealed class AnimatedRifleView
    {
        public readonly GameObject Root;
        public readonly Transform Magazine,RightHand,LeftHand;
        private readonly Vector3 pivot;
        internal AnimatedRifleView(GameObject root,Transform mag,Transform right,Transform left,Vector3 magazinePivot)
        {Root=root;Magazine=mag;RightHand=right;LeftHand=left;pivot=magazinePivot;}
        public void Apply(long tick,int health,bool connected,bool simulated,bool reloading,long until)
        {
            var pose=WeaponPresentation.Pose(tick,health,connected,simulated,reloading,until);
            Magazine.localPosition=pivot+Vector(pose.MagazineOffset);Magazine.localRotation=Quaternion.Euler(0,0,pose.MagazineRoll);Magazine.gameObject.SetActive(pose.MagazineVisible);
            RightHand.localPosition=Vector(WeaponPresentation.RightGrip);LeftHand.localPosition=Vector(pose.LeftHand);LeftHand.localRotation=Quaternion.Euler(0,0,pose.LeftRoll);
            RightHand.gameObject.SetActive(pose.HandsVisible);LeftHand.gameObject.SetActive(pose.HandsVisible);
        }
        private static Vector3 Vector(Vec3 v)=>new Vector3(v.X,v.Y,v.Z);
    }
    public sealed class AnimatedRifleModels : IDisposable
    {
        private sealed class Shared {internal readonly Mesh[] Meshes=new Mesh[4];internal Material Material;internal AnimatedRifleDefinition Data;internal int Leases;}
        private static Shared shared;private Shared lease;
        public static AnimatedRifleDefinition Read()
        {
            var text=Resources.Load<TextAsset>("VrCommand/weapon-actions-v1");if(text==null)throw new InvalidOperationException("Weapon action geometry is missing.");
            var data=JsonUtility.FromJson<AnimatedRifleDefinition>(text.text);
            if(data==null || data.assetSet!=WorldAssetSets.WeaponActions || data.units!="metres" || data.origin!="muzzle" || data.forward!="+Z"
                || data.weaponPresentationVersion!=1 || data.parts==null || data.parts.Length!=4 || data.magazinePivot==null || data.magazinePivot.Length!=3)
                throw new InvalidOperationException("Unsupported weapon action geometry.");
            for(var i=0;i<4;i++)if(data.parts[i]==null || data.parts[i].kind!=new[]{"Body","Magazine","RightGlove","LeftGlove"}[i])throw new InvalidOperationException("Unsupported weapon action part.");
            for(var i=0;i<3;i++)if(!float.IsFinite(data.magazinePivot[i]) || Mathf.Abs(data.magazinePivot[i])>1)throw new InvalidOperationException("Invalid magazine pivot.");
            return data;
        }
        public AnimatedRifleModels()
        {
            if(shared==null)
            {
                var value=new Shared();try
                {
                    value.Data=Read();for(var i=0;i<4;i++)value.Meshes[i]=FieldPropModels.BuildMesh(value.Data.parts[i],WorldAssetSets.WeaponActions);
                    var shader=Resources.Load<Shader>("VrCommand/FieldProps");if(shader==null)throw new InvalidOperationException("Weapon action shader is missing.");
                    value.Material=new Material(shader){name=WorldAssetSets.WeaponActions,enableInstancing=true};shared=value;
                }
                catch{foreach(var mesh in value.Meshes)Release(mesh);Release(value.Material);throw;}
            }
            lease=shared;lease.Leases++;
        }
        public AnimatedRifleView Create()
        {
            if(lease==null)throw new ObjectDisposedException(nameof(AnimatedRifleModels));
            var root=new GameObject("Action Rifle / muzzle / weapon-actions-v1");SetMesh(root,0);
            var pivot=new Vector3(lease.Data.magazinePivot[0],lease.Data.magazinePivot[1],lease.Data.magazinePivot[2]);
            var view=new AnimatedRifleView(root,Part(root,1),Part(root,2),Part(root,3),pivot);view.Apply(0,100,false,false,false,0);return view;
        }
        private Transform Part(GameObject root,int index)
        {var part=new GameObject(lease.Data.parts[index].kind);part.transform.SetParent(root.transform,false);SetMesh(part,index);return part.transform;}
        private void SetMesh(GameObject root,int index)
        {root.AddComponent<MeshFilter>().sharedMesh=lease.Meshes[index];root.AddComponent<MeshRenderer>().sharedMaterial=lease.Material;}
        public void Dispose()
        {
            if(lease==null)return;var value=lease;lease=null;if(--value.Leases!=0)return;if(ReferenceEquals(shared,value))shared=null;
            foreach(var mesh in value.Meshes)Release(mesh);Release(value.Material);
        }
        private static void Release(UnityEngine.Object value){if(value==null)return;if(Application.isPlaying)UnityEngine.Object.Destroy(value);else UnityEngine.Object.DestroyImmediate(value);}
    }
}
