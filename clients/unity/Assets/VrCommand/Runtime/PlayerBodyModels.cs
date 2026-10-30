using System;
using UnityEngine;
using VrCommand.Simulation;
namespace VrCommand.Unity
{
    [Serializable] public sealed class PlayerBodyDefinition
    {public string assetSet,units,origin,forward,retainedAssetSet,retainedSha256;public int playerPresentationVersion;public float referenceEyeHeight;public FieldPropMesh[] parts;}
    [Serializable] public sealed class PlayerBodyObservation
    {public string id;public long tick;public bool visible,walking,arms,simulated;public float yaw,heightScale,stride;public Vector3 head,feet,leftElbow,leftWrist,rightElbow,rightWrist;}
    public sealed class PlayerBodyView:IDisposable
    {
        public readonly GameObject Root;public readonly Transform Body,Head,LeftLeg,RightLeg,LeftUpper,LeftLower,RightUpper,RightLower;
        public PlayerBodyObservation Observation {get;private set;}
        internal PlayerBodyView(GameObject root,Transform body,Transform head,Transform left,Transform right,Transform lu,Transform ll,Transform ru,Transform rl)
        {Root=root;Body=body;Head=head;LeftLeg=left;RightLeg=right;LeftUpper=lu;LeftLower=ll;RightUpper=ru;RightLower=rl;}
        public void Apply(string id,Vector3 head,Quaternion rotation,Vector3 muzzle,Vector3 forward,CombatActorState state,bool simulated,bool visible)
        {
            if(!visible){Root.SetActive(false);Observation=null;return;}
            rotation=Quaternion.Normalize(rotation);
            var p=PlayerPresentation.Pose(V(head),V(rotation*Vector3.forward),V(muzzle),V(forward),state.walking,state.presentationTick,state.health,state.connected,simulated,state.reloading,state.reloadUntilTick);
            Root.SetActive(visible&&state.connected&&state.health>0);Body.position=P(p.Feet);Body.rotation=Quaternion.Euler(0,p.Yaw,0);Body.localScale=new Vector3(1,p.HeightScale,1);
            Head.SetPositionAndRotation(head,rotation);LeftLeg.localRotation=Quaternion.Euler(p.Stride,0,0);RightLeg.localRotation=Quaternion.Euler(-p.Stride,0,0);
            foreach(var bone in new[]{LeftUpper,LeftLower,RightUpper,RightLower})bone.gameObject.SetActive(p.Arms);
            if(p.Arms){Bone(LeftUpper,p.Left.Shoulder,p.Left.Elbow);Bone(LeftLower,p.Left.Elbow,p.Left.Wrist);Bone(RightUpper,p.Right.Shoulder,p.Right.Elbow);Bone(RightLower,p.Right.Elbow,p.Right.Wrist);}
            Observation=new PlayerBodyObservation{id=id,tick=state.presentationTick,visible=Root.activeInHierarchy,walking=state.walking,arms=p.Arms,simulated=simulated,
                yaw=Mathf.DeltaAngle(0,Body.eulerAngles.y),heightScale=Body.localScale.y,stride=Mathf.DeltaAngle(0,LeftLeg.localEulerAngles.x),head=Head.position,feet=Body.position,
                leftElbow=p.Arms?LeftUpper.TransformPoint(Vector3.up):Vector3.zero,leftWrist=p.Arms?LeftLower.TransformPoint(Vector3.up):Vector3.zero,
                rightElbow=p.Arms?RightUpper.TransformPoint(Vector3.up):Vector3.zero,rightWrist=p.Arms?RightLower.TransformPoint(Vector3.up):Vector3.zero};
        }
        private static Vec3 V(Vector3 p)=>new Vec3(p.x,p.y,p.z);
        private static Vector3 P(Vec3 p)=>new Vector3(p.X,p.Y,p.Z);
        private static void Bone(Transform t,Vec3 a,Vec3 b){var delta=P(b-a);t.position=P(a);t.rotation=Quaternion.FromToRotation(Vector3.up,delta.normalized);t.localScale=new Vector3(1,delta.magnitude,1);}
        public void Dispose(){if(Root!=null){if(Application.isPlaying)UnityEngine.Object.Destroy(Root);else UnityEngine.Object.DestroyImmediate(Root);}}
    }
    public sealed class PlayerBodyModels:IDisposable
    {
        private sealed class Shared{internal Mesh[] Meshes;internal Material Material;internal int Leases;}
        private static Shared shared;private Shared lease;
        public static PlayerBodyDefinition Read()
        {
            var asset=Resources.Load<TextAsset>("VrCommand/player-body-v1");if(asset==null)throw new InvalidOperationException("Player body geometry missing.");var d=JsonUtility.FromJson<PlayerBodyDefinition>(asset.text);
            var kinds=new[]{"Torso","Head","Leg","UpperArm","LowerArm"};
            if(d==null||d.assetSet!=WorldAssetSets.PlayerBody||d.units!="metres"||d.origin!="floor-below-head"||d.forward!="+Z"||d.playerPresentationVersion!=1||d.referenceEyeHeight!=1.65f
                ||d.retainedAssetSet!=WorldAssetSets.PlayerFire||d.retainedSha256!="187c7df5346419edadafa1cc74a04db0763dda268650e066dbbcaf8304e60ff0"||d.parts?.Length!=5)throw new InvalidOperationException("Unsupported player body profile.");
            for(var i=0;i<5;i++)if(d.parts[i]?.kind!=kinds[i])throw new InvalidOperationException("Invalid player body part.");return d;
        }
        public PlayerBodyModels()
        {
            if(shared==null){var s=new Shared{Meshes=new Mesh[5]};try{var d=Read();for(var i=0;i<5;i++)s.Meshes[i]=FieldPropModels.BuildMesh(d.parts[i],WorldAssetSets.PlayerBody);
                var shader=Resources.Load<Shader>("VrCommand/FieldProps");if(shader==null)throw new InvalidOperationException("Player body shader missing.");s.Material=new Material(shader){name=WorldAssetSets.PlayerBody,enableInstancing=true};shared=s;}catch{foreach(var m in s.Meshes)Release(m);Release(s.Material);throw;}}
            lease=shared;lease.Leases++;
        }
        public PlayerBodyView Create()
        {
            if(lease==null)throw new ObjectDisposedException(nameof(PlayerBodyModels));var root=new GameObject("Player / player-body-v1");var body=new GameObject("Body frame").transform;body.SetParent(root.transform,false);
            Part(body,0,Vector3.zero);var head=Part(root.transform,1,Vector3.zero);var left=Part(body,2,new Vector3(-.11f,.82f,0));var right=Part(body,2,new Vector3(.11f,.82f,0));
            return new PlayerBodyView(root,body,head,left,right,Part(root.transform,3,Vector3.zero),Part(root.transform,4,Vector3.zero),Part(root.transform,3,Vector3.zero),Part(root.transform,4,Vector3.zero));
        }
        private Transform Part(Transform parent,int i,Vector3 at){var p=new GameObject(new[]{"Torso","Head","Leg","UpperArm","LowerArm"}[i]);p.transform.SetParent(parent,false);p.transform.localPosition=at;p.AddComponent<MeshFilter>().sharedMesh=lease.Meshes[i];p.AddComponent<MeshRenderer>().sharedMaterial=lease.Material;return p.transform;}
        public void Dispose(){if(lease==null)return;var s=lease;lease=null;if(--s.Leases!=0)return;if(ReferenceEquals(shared,s))shared=null;foreach(var m in s.Meshes)Release(m);Release(s.Material);}
        private static void Release(UnityEngine.Object o){if(o==null)return;if(Application.isPlaying)UnityEngine.Object.Destroy(o);else UnityEngine.Object.DestroyImmediate(o);}
    }
}
