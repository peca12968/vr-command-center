using System;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    [Serializable] public sealed class ServiceRifleDefinition
    { public string assetSet, units, origin, forward; public FieldPropMesh mesh; }

    // Decorative only. Every view has a muzzle origin and never contributes to
    // physics, hit prediction, pose validation or authoritative weapon input.
    public sealed class ServiceRifleModels : IDisposable
    {
        private sealed class Shared
        {
            internal Mesh Mesh;
            internal Material Material;
            internal int Leases;
        }
        private static Shared shared;
        private Shared lease;
        public static ServiceRifleDefinition Read()
        {
            var asset = Resources.Load<TextAsset>("VrCommand/service-rifle-v1");
            if (asset == null) throw new InvalidOperationException("Service rifle geometry is missing.");
            var data = JsonUtility.FromJson<ServiceRifleDefinition>(asset.text);
            if (data == null || data.assetSet != WorldAssetSets.ServiceRifle || data.units != "metres" || data.origin != "muzzle"
                || data.forward != "+Z" || data.mesh == null || data.mesh.kind != "ServiceRifle")
                throw new InvalidOperationException("Unsupported service rifle geometry.");
            return data;
        }
        public ServiceRifleModels()
        {
            if (shared == null)
            {
                var resources = new Shared();
                try
                {
                    resources.Mesh = FieldPropModels.BuildMesh(Read().mesh, WorldAssetSets.ServiceRifle);
                    var bounds = resources.Mesh.bounds;
                    if (bounds.max.z > .0001f || bounds.min.z < -.8f || bounds.size.z < .6f || bounds.size.x > .2f || bounds.size.y > .5f)
                        throw new InvalidOperationException("Rifle geometry does not preserve its muzzle anchor.");
                    var shader = Resources.Load<Shader>("VrCommand/FieldProps");
                    if (shader == null) throw new InvalidOperationException("Rifle vertex-colour shader is missing.");
                    resources.Material = new Material(shader) { name = WorldAssetSets.ServiceRifle, enableInstancing = true };
                    shared = resources;
                }
                catch { Release(resources.Mesh); Release(resources.Material); throw; }
            }
            lease = shared; lease.Leases++;
        }
        public GameObject Create()
        {
            if (lease == null) throw new ObjectDisposedException(nameof(ServiceRifleModels));
            var view = new GameObject("Service Rifle / muzzle / service-rifle-v1");
            view.AddComponent<MeshFilter>().sharedMesh = lease.Mesh;
            view.AddComponent<MeshRenderer>().sharedMaterial = lease.Material;
            return view;
        }
        public static void Align(Transform view, Transform muzzle)
        { view.SetPositionAndRotation(muzzle.position + muzzle.forward * AvatarPose.MuzzleOffset, muzzle.rotation); }
        public void Dispose()
        {
            if (lease == null) return;
            var resources = lease; lease = null;
            if (--resources.Leases != 0) return;
            if (ReferenceEquals(shared, resources)) shared = null;
            Release(resources.Mesh); Release(resources.Material);
        }
        private static void Release(UnityEngine.Object value)
        { if (value == null) return; if (Application.isPlaying) UnityEngine.Object.Destroy(value); else UnityEngine.Object.DestroyImmediate(value); }
    }
}
