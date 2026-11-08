using NUnit.Framework;
using Unity.XR.CompositionLayers.Layers;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class QuestPassthroughTests
    {
        private GameObject room;
        private Camera camera;
        private GameObject floor, hiddenFloor, prop;
        private QuestPassthroughSurface surface;

        [SetUp]
        public void Setup()
        {
            room = new GameObject("Passthrough test room");
            camera = room.AddComponent<Camera>();
            camera.backgroundColor = Color.gray;
            camera.clearFlags = CameraClearFlags.Skybox;
            floor = Cube();
            hiddenFloor = Cube();
            prop = Cube();
            var hidden = hiddenFloor.GetComponent<Renderer>();
            hidden.forceRenderingOff = true;
            surface = new QuestPassthroughSurface(camera, new[] { floor.GetComponent<Renderer>(), hidden });
        }

        [TearDown]
        public void Cleanup() => Object.DestroyImmediate(room);

        [Test]
        public void TransparentCameraHidesFloorPixelsAndKeepsCollidersAndProps()
        {
            surface.SetVisible(true);
            Assert.That(camera.backgroundColor, Is.EqualTo(Color.clear));
            Assert.That(camera.clearFlags, Is.EqualTo(CameraClearFlags.SolidColor));
            Assert.That(floor.GetComponent<Renderer>().forceRenderingOff, Is.True);
            Assert.That(floor.GetComponent<Collider>().enabled, Is.True);
            Assert.That(prop.GetComponent<Renderer>().forceRenderingOff, Is.False);

            surface.SetVisible(true);
            surface.SetVisible(false);
            Assert.That(camera.backgroundColor, Is.EqualTo(Color.gray));
            Assert.That(camera.clearFlags, Is.EqualTo(CameraClearFlags.Skybox));
            Assert.That(floor.GetComponent<Renderer>().forceRenderingOff, Is.False);
            Assert.That(hiddenFloor.GetComponent<Renderer>().forceRenderingOff, Is.True);
        }

        [Test]
        public void DayNightAndLightningDoNotPaintOverPassthrough()
        {
            surface.SetVisible(true);
            foreach (var sky in new[] { Color.blue, Color.black, Color.white })
            {
                QuestPassthroughSurface.ApplySky(camera, sky, surface.Visible);
                Assert.That(camera.backgroundColor.a, Is.Zero);
            }

            surface.SetVisible(false);
            QuestPassthroughSurface.ApplySky(camera, Color.blue, surface.Visible);
            Assert.That(camera.backgroundColor, Is.EqualTo(Color.blue));
        }

        [Test]
        public void ReleasingCameraRestoresProjectionBlendBeforeAnotherSession()
        {
            var projection = new DefaultLayerData { BlendType = BlendType.Alpha };
            surface.TrackProjection(projection);
            projection.BlendType = BlendType.Premultiply;
            surface.ReleaseProjection();
            Assert.That(projection.BlendTypeDirectly, Is.EqualTo(BlendType.Alpha));
            Assert.That(surface.Projection, Is.Null);
            surface.ReleaseProjection();
        }

        private GameObject Cube()
        {
            var value = GameObject.CreatePrimitive(PrimitiveType.Cube);
            value.transform.SetParent(room.transform);
            return value;
        }
    }
}
