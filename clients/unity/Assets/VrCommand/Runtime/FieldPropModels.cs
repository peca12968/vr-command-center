using System;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    [Serializable] public sealed class FieldPropDefinition
    { public string assetSet, units, origin; public FieldPropMesh[] props; }
    [Serializable] public sealed class FieldPropMesh
    { public string kind; public float[] positions, normals, colors; public int[] triangles; }

    // Original, fixed geometry shared byte-for-byte with the replay viewer's
    // generated data. Visual meshes never become authoritative colliders.
    public sealed class FieldPropModels : IDisposable
    {
        private readonly Mesh[] meshes = new Mesh[2];
        private Material material;
        public static FieldPropDefinition Read()
        {
            var asset = Resources.Load<TextAsset>("VrCommand/field-props-v1");
            if (asset == null) throw new InvalidOperationException("Field prop geometry is missing.");
            var data = JsonUtility.FromJson<FieldPropDefinition>(asset.text);
            if (data == null || data.assetSet != WorldAssetSets.FieldProps || data.units != "metres" || data.origin != "feet"
                || data.props == null || data.props.Length != 2 || data.props[0].kind != "Sandbag" || data.props[1].kind != "Barrel")
                throw new InvalidOperationException("Unsupported field prop geometry.");
            return data;
        }
        public FieldPropModels()
        {
            try
            {
                var data = Read();
                for (var i = 0; i < 2; i++) meshes[i] = BuildMesh(data.props[i]);
                var shader = Resources.Load<Shader>("VrCommand/FieldProps");
                if (shader == null) throw new InvalidOperationException("Field prop shader is missing.");
                material = new Material(shader) { name = WorldAssetSets.FieldProps, enableInstancing = true };
            }
            catch { Dispose(); throw; }
        }
        public static Mesh BuildMesh(FieldPropMesh source, string assetSet = WorldAssetSets.FieldProps)
        {
            if (source == null || source.positions == null || source.positions.Length == 0 || source.positions.Length % 3 != 0
                || source.positions.Length > 6000 || source.normals == null || source.normals.Length != source.positions.Length
                || source.colors == null || source.colors.Length != source.positions.Length / 3 * 4
                || source.triangles == null || source.triangles.Length == 0 || source.triangles.Length % 3 != 0 || source.triangles.Length > 1800)
                throw new ArgumentException("Invalid field prop mesh arrays.");
            var count = source.positions.Length / 3; var positions = new Vector3[count]; var normals = new Vector3[count]; var colors = new Color[count];
            for (var i = 0; i < count; i++)
            {
                positions[i] = new Vector3(source.positions[i * 3], source.positions[i * 3 + 1], source.positions[i * 3 + 2]);
                normals[i] = new Vector3(source.normals[i * 3], source.normals[i * 3 + 1], source.normals[i * 3 + 2]);
                colors[i] = new Color(source.colors[i * 4], source.colors[i * 4 + 1], source.colors[i * 4 + 2], source.colors[i * 4 + 3]);
                if (!float.IsFinite(positions[i].sqrMagnitude) || positions[i].sqrMagnitude > 9 || !float.IsFinite(normals[i].sqrMagnitude)
                    || Mathf.Abs(normals[i].magnitude - 1) > .001f || !ValidColor(colors[i])) throw new ArgumentException("Invalid field prop vertex.");
            }
            foreach (var index in source.triangles) if (index < 0 || index >= count) throw new ArgumentException("Invalid field prop triangle.");
            var mesh = new Mesh { name = source.kind + " / " + assetSet, vertices = positions, normals = normals, colors = colors, triangles = source.triangles };
            mesh.RecalculateBounds(); return mesh;
        }
        private static bool ValidColor(Color value) => float.IsFinite(value.r) && float.IsFinite(value.g) && float.IsFinite(value.b)
            && value.r >= 0 && value.r <= 1 && value.g >= 0 && value.g <= 1 && value.b >= 0 && value.b <= 1 && value.a == 1;
        public GameObject Create(bool barrel)
        {
            var root = new GameObject(barrel ? "Fuel Drum / field-props-v1" : "Sandbag Wall / field-props-v1");
            root.AddComponent<MeshFilter>().sharedMesh = meshes[barrel ? 1 : 0];
            root.AddComponent<MeshRenderer>().sharedMaterial = material;
            return root;
        }
        public void Dispose()
        {
            foreach (var mesh in meshes) Release(mesh);
            Release(material); material = null;
        }
        private static void Release(UnityEngine.Object value)
        { if (value == null) return; if (Application.isPlaying) UnityEngine.Object.Destroy(value); else UnityEngine.Object.DestroyImmediate(value); }
    }
}
