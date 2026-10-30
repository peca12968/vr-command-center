using System;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    [Serializable] public sealed class ArmedEnemyModelDefinition
    {
        public string assetSet, units, origin, forward;
        public int enemyPresentationVersion;
        public FieldPropMesh[] parts;
        public float[] headPivot, leftHip, rightHip, muzzle, leftGrip, rightGrip;
    }
    public sealed class ArmedEnemyView
    {
        public readonly GameObject Root;
        public readonly Transform Head, LeftLeg, RightLeg, Gun, LeftUpper, LeftLower, RightUpper, RightLower, LeftHand, RightHand;
        internal ArmedEnemyView(GameObject root, Transform[] parts)
        {
            Root=root; Head=parts[0]; LeftLeg=parts[1]; RightLeg=parts[2]; Gun=parts[3];
            LeftUpper=parts[4]; LeftLower=parts[5]; RightUpper=parts[6]; RightLower=parts[7]; LeftHand=parts[8]; RightHand=parts[9];
        }
        public void Apply(Vec3 forward, bool walking, long tick)
        {
            var pose=ArmedEnemyPresentation.Pose(forward,walking,tick);
            Root.transform.rotation=Quaternion.Euler(0,pose.Body.Yaw,0);
            Head.localRotation=Quaternion.Euler(pose.Body.Pitch,0,0);
            LeftLeg.localRotation=Quaternion.Euler(pose.Body.Stride,0,0); RightLeg.localRotation=Quaternion.Euler(-pose.Body.Stride,0,0);
            Gun.localRotation=Quaternion.Euler(pose.GunPitch,0,0);
            Bone(LeftUpper,pose.Left.Shoulder,pose.Left.Elbow); Bone(LeftLower,pose.Left.Elbow,pose.Left.Wrist);
            Bone(RightUpper,pose.Right.Shoulder,pose.Right.Elbow); Bone(RightLower,pose.Right.Elbow,pose.Right.Wrist);
        }
        private static void Bone(Transform part,Vec3 start,Vec3 end)
        {
            var from=ArmedEnemyModels.Point(start); var delta=ArmedEnemyModels.Point(end)-from;
            part.localPosition=from; part.localRotation=Quaternion.FromToRotation(Vector3.up,delta.normalized); part.localScale=new Vector3(1,delta.magnitude,1);
        }
    }
    // One scene pool owns eight meshes/one material; all NPCs borrow these resources.
    public sealed class ArmedEnemyModels : IDisposable
    {
        private readonly Mesh[] meshes=new Mesh[8];
        private ArmedEnemyModelDefinition data;
        private Material material;
        public static ArmedEnemyModelDefinition Read()
        {
            var asset=Resources.Load<TextAsset>("VrCommand/armed-combatants-v1");
            if(asset==null)throw new InvalidOperationException("Armed opponent geometry is missing.");
            var value=JsonUtility.FromJson<ArmedEnemyModelDefinition>(asset.text);
            var kinds=new[]{"Torso","Head","Leg","UpperArm","LowerArm","Sidearm","RightGlove","LeftGlove"};
            if(value==null || value.assetSet!=WorldAssetSets.ArmedCombatants || value.units!="metres" || value.origin!="feet" || value.forward!="+Z"
                || value.enemyPresentationVersion!=EnemyPresentation.Version || value.parts==null || value.parts.Length!=kinds.Length)
                throw new InvalidOperationException("Unsupported armed opponent metadata.");
            for(var i=0;i<kinds.Length;i++)if(value.parts[i]?.kind!=kinds[i])throw new InvalidOperationException("Unsupported armed opponent part.");
            Require(value.headPivot,new Vec3(0,1.51f,-.26f)); Require(value.leftHip,new Vec3(-.11f,.82f,-.08f)); Require(value.rightHip,new Vec3(.11f,.82f,-.08f));
            Require(value.muzzle,ArmedEnemyPresentation.Muzzle); Require(value.leftGrip,ArmedEnemyPresentation.LeftGrip); Require(value.rightGrip,ArmedEnemyPresentation.RightGrip);
            return value;
        }
        private static void Require(float[] value,Vec3 expected)
        {
            if(value==null || value.Length!=3 || !float.IsFinite(value[0]) || !float.IsFinite(value[1]) || !float.IsFinite(value[2])
                || Vector3.Distance(new Vector3(value[0],value[1],value[2]),Point(expected))>.000001f)throw new ArgumentException("Armed rig differs from its fixed presentation contract.");
        }
        internal static Vector3 Point(Vec3 p)=>new Vector3(p.X,p.Y,p.Z);
        private static Vector3 Point(float[] p)=>new Vector3(p[0],p[1],p[2]);
        public ArmedEnemyModels()
        {
            try
            {
                data=Read();for(var i=0;i<meshes.Length;i++)meshes[i]=FieldPropModels.BuildMesh(data.parts[i],WorldAssetSets.ArmedCombatants);
                var shader=Resources.Load<Shader>("VrCommand/FieldProps");if(shader==null)throw new InvalidOperationException("Armed opponent shader is missing.");
                material=new Material(shader){name=WorldAssetSets.ArmedCombatants,enableInstancing=true};
            }
            catch {Dispose();throw;}
        }
        public ArmedEnemyView Create()
        {
            if(material==null)throw new ObjectDisposedException(nameof(ArmedEnemyModels));
            var root=new GameObject("Opponent / armed-combatants-v1");Part(root.transform,0,Vector3.zero);
            var head=Part(root.transform,1,Point(data.headPivot));var left=Part(root.transform,2,Point(data.leftHip));var right=Part(root.transform,2,Point(data.rightHip));
            var gun=Part(root.transform,5,Point(data.muzzle));
            var parts=new[]{head,left,right,gun,Part(root.transform,3,Vector3.zero),Part(root.transform,4,Vector3.zero),
                Part(root.transform,3,Vector3.zero),Part(root.transform,4,Vector3.zero),Part(gun,7,Point(data.leftGrip)),Part(gun,6,Point(data.rightGrip))};
            var view=new ArmedEnemyView(root,parts);view.Apply(new Vec3(0,0,1),false,0);return view;
        }
        private Transform Part(Transform parent,int index,Vector3 position)
        {
            var part=new GameObject(data.parts[index].kind);part.transform.SetParent(parent,false);part.transform.localPosition=position;
            part.AddComponent<MeshFilter>().sharedMesh=meshes[index];part.AddComponent<MeshRenderer>().sharedMaterial=material;return part.transform;
        }
        public void Dispose(){foreach(var mesh in meshes)Release(mesh);Release(material);material=null;}
        private static void Release(UnityEngine.Object value)
        {if(value==null)return;if(Application.isPlaying)UnityEngine.Object.Destroy(value);else UnityEngine.Object.DestroyImmediate(value);}
    }
}
