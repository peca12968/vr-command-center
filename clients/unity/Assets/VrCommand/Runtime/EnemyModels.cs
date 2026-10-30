using System;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    [Serializable] public sealed class EnemyModelDefinition
    { public string assetSet, units, origin, forward; public int enemyPresentationVersion; public FieldPropMesh[] parts; public float[] headPivot, leftHip, rightHip; }
    public sealed class EnemyView
    {
        public readonly GameObject Root;
        public readonly Transform Head, LeftLeg, RightLeg;
        internal EnemyView(GameObject root, Transform head, Transform left, Transform right)
        { Root = root; Head = head; LeftLeg = left; RightLeg = right; }
        public void Apply(Vec3 forward, bool walking, long tick)
        {
            var pose = EnemyPresentation.Pose(forward, walking, tick);
            Root.transform.rotation = Quaternion.Euler(0, pose.Yaw, 0);
            Head.localRotation = Quaternion.Euler(pose.Pitch, 0, 0);
            LeftLeg.localRotation = Quaternion.Euler(pose.Stride, 0, 0);
            RightLeg.localRotation = Quaternion.Euler(-pose.Stride, 0, 0);
        }
    }
    // Shared decorative parts only. The existing axis-aligned authority box,
    // shot origin and AI rules remain independent of this animated silhouette.
    public sealed class EnemyModels : IDisposable
    {
        private readonly Mesh[] meshes = new Mesh[3];
        private readonly EnemyModelDefinition data;
        private Material material;
        public static EnemyModelDefinition Read()
        {
            var asset = Resources.Load<TextAsset>("VrCommand/combatants-v1");
            if (asset == null) throw new InvalidOperationException("Opponent geometry is missing.");
            var value = JsonUtility.FromJson<EnemyModelDefinition>(asset.text);
            if (value == null || value.assetSet != WorldAssetSets.Combatants || value.units != "metres" || value.origin != "feet" || value.forward != "+Z"
                || value.enemyPresentationVersion != EnemyPresentation.Version || value.parts == null || value.parts.Length != 3
                || value.parts[0].kind != "Torso" || value.parts[1].kind != "Head" || value.parts[2].kind != "Leg")
                throw new InvalidOperationException("Unsupported opponent geometry.");
            Point(value.headPivot); Point(value.leftHip); Point(value.rightHip); return value;
        }
        private static Vector3 Point(float[] value)
        {
            if (value == null || value.Length != 3 || !float.IsFinite(value[0]) || !float.IsFinite(value[1]) || !float.IsFinite(value[2])
                || Mathf.Abs(value[0]) > 2 || Mathf.Abs(value[1]) > 2 || Mathf.Abs(value[2]) > 2) throw new ArgumentException("Invalid opponent rig pivot.");
            return new Vector3(value[0], value[1], value[2]);
        }
        public EnemyModels()
        {
            try
            {
                data = Read();
                for (var i = 0; i < meshes.Length; i++) meshes[i] = FieldPropModels.BuildMesh(data.parts[i], WorldAssetSets.Combatants);
                var shader = Resources.Load<Shader>("VrCommand/FieldProps");
                if (shader == null) throw new InvalidOperationException("Opponent vertex-colour shader is missing.");
                material = new Material(shader) { name = WorldAssetSets.Combatants, enableInstancing = true };
            }
            catch { Dispose(); throw; }
        }
        public EnemyView Create()
        {
            if (material == null) throw new ObjectDisposedException(nameof(EnemyModels));
            var root = new GameObject("Opponent / combatants-v1");
            Part(root.transform, 0, Vector3.zero);
            return new EnemyView(root, Part(root.transform, 1, Point(data.headPivot)), Part(root.transform, 2, Point(data.leftHip)), Part(root.transform, 2, Point(data.rightHip)));
        }
        private Transform Part(Transform root, int index, Vector3 position)
        {
            var part = new GameObject(data.parts[index].kind); part.transform.SetParent(root, false); part.transform.localPosition = position;
            part.AddComponent<MeshFilter>().sharedMesh = meshes[index]; part.AddComponent<MeshRenderer>().sharedMaterial = material;
            return part.transform;
        }
        public void Dispose() { foreach (var mesh in meshes) Release(mesh); Release(material); material = null; }
        private static void Release(UnityEngine.Object value)
        { if (value == null) return; if (Application.isPlaying) UnityEngine.Object.Destroy(value); else UnityEngine.Object.DestroyImmediate(value); }
    }
}
