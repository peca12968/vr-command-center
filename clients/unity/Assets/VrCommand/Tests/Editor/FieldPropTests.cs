using System;
using NUnit.Framework;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class FieldPropTests
    {
        [Test] public void ModelsFitTheAuthoritativeCoverEnvelopeWithLowTriangleBudget()
        {
            var data = FieldPropModels.Read();
            for (var i = 0; i < data.props.Length; i++)
            {
                var mesh = FieldPropModels.BuildMesh(data.props[i]);
                try
                {
                    var prop = new WorldProp(Guid.NewGuid(), 3, i == 0 ? PropKind.Sandbag : PropKind.Barrel, default, 0);
                    var half = prop.HalfSize; var bounds = mesh.bounds;
                    Assert.AreEqual(half.X * 2, bounds.size.x, .0001f);
                    Assert.AreEqual(half.Y * 2, bounds.size.y, .0001f);
                    Assert.AreEqual(half.Z * 2, bounds.size.z, .0001f);
                    Assert.AreEqual(0, bounds.min.y, .0001f);
                    Assert.LessOrEqual(mesh.triangles.Length / 3, 400); Assert.Greater(mesh.triangles.Length / 3, 12);
                }
                finally { UnityEngine.Object.DestroyImmediate(mesh); }
            }
        }
        [Test] public void MeshFacesHaveFiniteOutwardNormalsAndUsableVertexColours()
        {
            foreach (var data in FieldPropModels.Read().props)
            {
                var mesh = FieldPropModels.BuildMesh(data);
                try
                {
                    var vertices = mesh.vertices; var normals = mesh.normals; var indices = mesh.triangles;
                    Assert.AreEqual(mesh.vertexCount, mesh.colors.Length);
                    for (var i = 0; i < indices.Length; i += 3)
                    {
                        var cross = Vector3.Cross(vertices[indices[i + 1]] - vertices[indices[i]], vertices[indices[i + 2]] - vertices[indices[i]]);
                        Assert.Greater(Vector3.Dot(cross, normals[indices[i]]), .0000001f);
                    }
                }
                finally { UnityEngine.Object.DestroyImmediate(mesh); }
            }
        }
        [Test] public void PropViewsReuseGeometryWithoutAddingPhysicsColliders()
        {
            using (var models = new FieldPropModels())
            {
                var first = models.Create(true); var second = models.Create(true); var bags = models.Create(false);
                try
                {
                    Assert.AreSame(first.GetComponent<MeshFilter>().sharedMesh, second.GetComponent<MeshFilter>().sharedMesh);
                    Assert.AreSame(first.GetComponent<MeshRenderer>().sharedMaterial, bags.GetComponent<MeshRenderer>().sharedMaterial);
                    Assert.IsEmpty(first.GetComponentsInChildren<Collider>()); Assert.IsEmpty(bags.GetComponentsInChildren<Collider>());
                    Assert.AreEqual("VRCommand/FieldProps", first.GetComponent<MeshRenderer>().sharedMaterial.shader.name);
                }
                finally { UnityEngine.Object.DestroyImmediate(first); UnityEngine.Object.DestroyImmediate(second); UnityEngine.Object.DestroyImmediate(bags); }
            }
        }
        [Test] public void CorruptMeshCannotEnterTheRenderer()
        {
            var bad = FieldPropModels.Read().props[0]; bad.triangles[0] = int.MaxValue;
            Assert.Throws<ArgumentException>(() => FieldPropModels.BuildMesh(bad));
            bad = FieldPropModels.Read().props[0]; bad.positions[0] = float.NaN;
            Assert.Throws<ArgumentException>(() => FieldPropModels.BuildMesh(bad));
        }
    }
}
