using System;
using NUnit.Framework;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class ServiceRifleTests
    {
        [Test] public void OriginalRifleHasAMuzzleOriginFiniteFacesAndABoundedMesh()
        {
            var source = ServiceRifleModels.Read(); var mesh = FieldPropModels.BuildMesh(source.mesh, WorldAssetSets.ServiceRifle);
            try
            {
                Assert.AreEqual("muzzle", source.origin); Assert.AreEqual("+Z", source.forward);
                Assert.AreEqual(0, mesh.bounds.max.z, .00001f); Assert.AreEqual(.735f, mesh.bounds.size.z, .00001f);
                Assert.AreEqual(264, mesh.triangles.Length / 3); Assert.LessOrEqual(mesh.triangles.Length / 3, 400);
                var vertices = mesh.vertices; var normals = mesh.normals; var triangles = mesh.triangles;
                for (var i = 0; i < triangles.Length; i += 3)
                    Assert.Greater(Vector3.Dot(Vector3.Cross(vertices[triangles[i + 1]] - vertices[triangles[i]], vertices[triangles[i + 2]] - vertices[triangles[i]]), normals[triangles[i]]), .0000001f);
            }
            finally { UnityEngine.Object.DestroyImmediate(mesh); }
        }
        [Test] public void AvatarsShareOneMeshAndReleasingOneLeasePreservesTheOthers()
        {
            var first = new ServiceRifleModels(); var second = new ServiceRifleModels();
            var a = first.Create(); var b = second.Create();
            try
            {
                var geometry = b.GetComponent<MeshFilter>().sharedMesh;
                Assert.AreSame(a.GetComponent<MeshFilter>().sharedMesh, geometry);
                Assert.AreSame(a.GetComponent<MeshRenderer>().sharedMaterial, b.GetComponent<MeshRenderer>().sharedMaterial);
                first.Dispose(); first.Dispose(); Assert.IsTrue(geometry != null);
                Assert.IsEmpty(b.GetComponentsInChildren<Collider>()); Assert.IsNull(b.GetComponent<global::Unity.Netcode.NetworkObject>());
                Assert.Throws<ObjectDisposedException>(() => first.Create());
            }
            finally { UnityEngine.Object.DestroyImmediate(a); UnityEngine.Object.DestroyImmediate(b); first.Dispose(); second.Dispose(); }
        }
        [Test] public void FullSizeSiblingPreservesTheScaledPointerAndAlignsItsTipAndRoll()
        {
            var root = new GameObject("Room player"); root.transform.position = new Vector3(-28, 0, 0);
            var pointer = new GameObject("Right aim pointer"); pointer.transform.SetParent(root.transform, false);
            pointer.transform.localPosition = new Vector3(.3f, 1.3f, .4f); pointer.transform.localRotation = Quaternion.Euler(10, 45, 25);
            pointer.transform.localScale = new Vector3(.12f, .12f, .2f);
            var saved = pointer.transform.localPosition; var rotation = pointer.transform.localRotation;
            using (var models = new ServiceRifleModels())
            {
                var rifle = models.Create(); rifle.transform.SetParent(root.transform, false);
                try
                {
                    ServiceRifleModels.Align(rifle.transform, pointer.transform);
                    Assert.Less(Vector3.Distance(rifle.transform.TransformPoint(Vector3.zero), pointer.transform.position + pointer.transform.forward * AvatarPose.MuzzleOffset), .00001f);
                    Assert.Less(Quaternion.Angle(rifle.transform.rotation, pointer.transform.rotation), .001f);
                    Assert.Less(Vector3.Distance(Vector3.one, rifle.transform.lossyScale), .00001f); Assert.AreEqual(saved, pointer.transform.localPosition);
                    Assert.AreEqual(rotation, pointer.transform.localRotation); Assert.AreEqual(new Vector3(.12f, .12f, .2f), pointer.transform.localScale);
                }
                finally { UnityEngine.Object.DestroyImmediate(rifle); UnityEngine.Object.DestroyImmediate(root); }
            }
        }
        [Test] public void CorruptGeometryCannotEnterTheWeaponRenderer()
        {
            var data = ServiceRifleModels.Read().mesh; data.positions[0] = float.NaN;
            Assert.Throws<ArgumentException>(() => FieldPropModels.BuildMesh(data, WorldAssetSets.ServiceRifle));
            data = ServiceRifleModels.Read().mesh; data.triangles[0] = int.MaxValue;
            Assert.Throws<ArgumentException>(() => FieldPropModels.BuildMesh(data, WorldAssetSets.ServiceRifle));
        }
        [Test] public void SyntheticDesktopMuzzleAndFrontBarrelRemainVisibleWithoutMovingTheHead()
        {
            var cameraRoot = new GameObject("Desktop view"); var camera = cameraRoot.AddComponent<Camera>();
            camera.fieldOfView = 60; camera.aspect = 1100f / 760; camera.nearClipPlane = .05f;
            var head = new Vector3(0, 1.65f, 0); cameraRoot.transform.position = head;
            try
            {
                foreach (var pitch in new[] { -70f, 0, 70f }) foreach (var yaw in new[] { 0f, 90, 225 })
                {
                    var rotation = Quaternion.Euler(pitch, yaw, 0); cameraRoot.transform.rotation = rotation;
                    var muzzle = head + rotation * (DesktopPreviewControls.RightOffset + Vector3.forward * AvatarPose.MuzzleOffset);
                    foreach (var offset in new[] { Vector3.zero, new Vector3(0, .04f, -.29f) })
                    {
                        var screen = camera.WorldToViewportPoint(muzzle + rotation * offset);
                        Assert.That(screen.x, Is.InRange(.05f, .95f)); Assert.That(screen.y, Is.InRange(.05f, .95f)); Assert.Greater(screen.z, .05f);
                    }
                    Assert.Less(Vector3.Distance(head, muzzle), 1.2f); Assert.That(muzzle.y, Is.InRange(.1f, 2.6f));
                }
                Assert.AreEqual(head, cameraRoot.transform.position);
            }
            finally { UnityEngine.Object.DestroyImmediate(cameraRoot); }
        }
    }
}
