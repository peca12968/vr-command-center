using Unity.XR.CompositionLayers.Layers;
using UnityEngine;
#if UNITY_ANDROID
using Unity.XR.CompositionLayers.Services;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
using UnityEngine.XR.Management;
using UnityEngine.XR.OpenXR.CompositionLayers;
using UnityEngine.XR.OpenXR.Features.Meta;
#endif

[assembly: System.Runtime.CompilerServices.InternalsVisibleTo("VrCommand.Tests")]

namespace VrCommand.Unity
{
    // Meta owns the camera images and submits them directly to the OpenXR compositor.
    internal sealed class QuestPassthroughView : MonoBehaviour
    {
        private QuestPassthroughSurface surface;
#if UNITY_ANDROID
        private ARSession arSession;
        private ARCameraManager arCamera;
        private bool suspended;
#endif
        internal bool Visible => surface?.Visible == true;

        internal static QuestPassthroughView Attach(Camera camera)
        {
            var view = camera.gameObject.AddComponent<QuestPassthroughView>();
            var floors = new Renderer[5];
            for (var i = 0; i < floors.Length; i++)
            {
                floors[i] = GameObject.Find("Room " + (i + 1) + " Floor")?.GetComponent<Renderer>();
                if (floors[i] == null) return view;
            }
            view.surface = new QuestPassthroughSurface(camera, floors);
            return view;
        }

        internal bool UpdateAvailability()
        {
#if UNITY_ANDROID
            var composition = CompositionLayerManager.Instance;
            var projection = composition?.DefaultSceneCompositionLayer?.LayerData;
            var loader = XRGeneralSettings.Instance?.Manager?.activeLoader;
            if (suspended || surface == null || projection == null || composition.LayerProvider is not OpenXRLayerProvider
                || loader?.GetLoadedSubsystem<XRCameraSubsystem>() is not MetaOpenXRCameraSubsystem cameraSubsystem
                || loader.GetLoadedSubsystem<XRSessionSubsystem>() is not MetaOpenXRSessionSubsystem)
            {
                Stop();
                return false;
            }
            if (surface.Projection != projection)
            {
                Stop();
                surface.TrackProjection(projection);
            }

            if (arSession == null)
            {
                var root = new GameObject("Quest AR Session");
                root.transform.SetParent(transform, false);
                root.SetActive(false);
                arSession = root.AddComponent<ARSession>();
                arSession.attemptUpdate = false;
                arSession.matchFrameRateRequested = false;
                root.SetActive(true);
            }
            if (arCamera == null) arCamera = gameObject.AddComponent<ARCameraManager>();
            if (!arSession.enabled) arSession.enabled = true;
            if (!arCamera.enabled) arCamera.enabled = true;

            var present = false;
            if (cameraSubsystem.running)
                foreach (var layer in composition.CompositionLayers)
                    if (layer != null && layer.isActiveAndEnabled && layer.LayerData is PassthroughLayerData)
                    { present = true; break; }
            surface.SetVisible(present);
            return present;
#else
            return false;
#endif
        }

        internal void Stop()
        {
            surface?.SetVisible(false);
#if UNITY_ANDROID
            if (arCamera != null) arCamera.enabled = false;
            if (arSession != null) arSession.enabled = false;
            surface?.ReleaseProjection();
#endif
        }

        private void OnDisable() => Stop();
#if UNITY_ANDROID
        private void OnApplicationPause(bool paused) { suspended = paused; if (paused) Stop(); }
        private void OnDestroy()
        {
            if (arCamera != null) Destroy(arCamera);
            if (arSession != null) Destroy(arSession.gameObject);
        }
#endif
    }

    internal sealed class QuestPassthroughSurface
    {
        private readonly Camera camera;
        private readonly Renderer[] floors;
        private readonly bool[] hidden;
        private CameraClearFlags previousClear;
        private Color previousBackground;
        private BlendType originalBlend;
        internal bool Visible { get; private set; }
        internal LayerData Projection { get; private set; }

        internal QuestPassthroughSurface(Camera camera, Renderer[] floors)
        {
            this.camera = camera;
            this.floors = floors;
            hidden = new bool[floors.Length];
        }

        internal void TrackProjection(LayerData projection)
        {
            Projection = projection;
            originalBlend = projection.BlendTypeDirectly;
        }

        internal void ReleaseProjection()
        {
            if (Projection == null) return;
            Projection.BlendType = originalBlend;
            Projection = null;
        }

        internal void SetVisible(bool visible)
        {
            if (visible == Visible) return;
            Visible = visible;
            if (visible)
            {
                previousClear = camera.clearFlags;
                previousBackground = camera.backgroundColor;
                ApplySky(camera, Color.clear, true);
            }
            else if (camera != null)
            {
                camera.clearFlags = previousClear;
                camera.backgroundColor = previousBackground;
            }
            for (var i = 0; i < floors.Length; i++)
            {
                if (floors[i] == null) continue;
                if (visible) hidden[i] = floors[i].forceRenderingOff;
                floors[i].forceRenderingOff = visible || hidden[i];
            }
        }

        internal static void ApplySky(Camera camera, Color sky, bool passthrough)
        {
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = passthrough ? Color.clear : sky;
        }
    }
}
