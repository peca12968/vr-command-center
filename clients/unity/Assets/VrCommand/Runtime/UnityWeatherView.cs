using UnityEngine;
using UnityEngine.Rendering;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    // One batched rain mesh and two reusable audio sources; no gameplay collisions or local weather RNG.
    public sealed class UnityWeatherView : MonoBehaviour
    {
        public Light sun;
        public Material rainMaterial;
        public AudioClip rainClip, thunderClip;
        public EnvironmentStyle LastApplied { get; private set; }
        public string AppliedPhase { get; private set; } = "Preparing";
        private readonly EnvironmentCueTracker cues = new EnvironmentCueTracker();
        private readonly Vector3[] vertices = new Vector3[1280];
        private readonly int[] indices = new int[1280];
        private Mesh mesh;
        private Material material;
        private MeshRenderer rainRenderer;
        private AudioSource rain, thunder;
        private int previousCount = -1;
        private void Awake()
        {
            var drops = new GameObject("Weather Rain"); drops.transform.SetParent(transform, false);
            mesh = new Mesh { name = "Weather Rain v1" }; mesh.MarkDynamic();
            drops.AddComponent<MeshFilter>().sharedMesh = mesh;
            rainRenderer = drops.AddComponent<MeshRenderer>(); rainRenderer.shadowCastingMode = ShadowCastingMode.Off; rainRenderer.receiveShadows = false;
            material = rainMaterial != null ? new Material(rainMaterial) : new Material(Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Sprites/Default"));
            rainRenderer.sharedMaterial = material;
            for (var index = 0; index < indices.Length; index++) indices[index] = index;
            rain = gameObject.AddComponent<AudioSource>(); thunder = gameObject.AddComponent<AudioSource>();
            rain.playOnAwake = thunder.playOnAwake = false; rain.loop = true;
            rain.spatialBlend = thunder.spatialBlend = 0; rain.clip = rainClip; thunder.clip = thunderClip;
        }
        public void Apply(long tick, string weather, bool night, bool lightning, string phase, int roomMask)
        {
            var style = EnvironmentPresentation.Sample(tick, weather, night, lightning, phase);
            LastApplied = style; AppliedPhase = phase;
            var sound = cues.Advance(tick, weather, night, lightning, phase);
            var sky = new Color(style.SkyR, style.SkyG, style.SkyB);
            RenderSettings.fog = style.Fog > 0; RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = style.Fog; RenderSettings.fogColor = sky;
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(.55f, .60f, .68f) * style.Ambient;
            if (sun != null)
            {
                sun.intensity = style.Sun; sun.color = night && !style.Flash ? new Color(.6f, .72f, 1) : Color.white;
                sun.transform.rotation = Quaternion.Euler(night ? 30 : 48, night ? 145 : -35, 0);
            }
            var camera = Camera.main;
            if (camera != null) { camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = sky; }
            var count = 0; var perRoom = style.Rain > .75f ? 128 : style.Rain > 0 ? 64 : 0;
            for (var room = 1; room <= 5; room++)
            {
                if ((roomMask & (1 << (room - 1))) == 0) continue;
                for (var index = 0; index < perRoom; index++)
                {
                    var point = EnvironmentPresentation.RainPoint(room, index, tick);
                    vertices[count++] = new Vector3(point.X, point.Y, point.Z);
                    vertices[count++] = new Vector3(point.X, Mathf.Max(0, point.Y - .32f), point.Z);
                }
            }
            rainRenderer.enabled = count > 0;
            if (count > 0)
            {
                if (count != previousCount) { mesh.Clear(); mesh.SetVertices(vertices, 0, count); mesh.SetIndices(indices, 0, count, MeshTopology.Lines, 0, false); }
                else mesh.SetVertices(vertices, 0, count);
                mesh.bounds = new Bounds(new Vector3(0, 3, 0), new Vector3(72, 7, 14));
                material.color = night ? new Color(.35f, .48f, .65f) : new Color(.6f, .72f, .8f);
            }
            previousCount = count;
            rain.volume = style.Rain * .35f; thunder.volume = .5f;
            if (style.Running && style.Rain > 0 && rainClip != null) { if (!rain.isPlaying) rain.Play(); }
            else rain.Stop();
            if (!style.Running) thunder.Stop();
            else if (sound && thunderClip != null) { thunder.Stop(); thunder.Play(); }
        }
        public void Clear()
        {
            LastApplied = default; AppliedPhase = "Cleared";
            cues.Reset(); if (rain != null) rain.Stop(); if (thunder != null) thunder.Stop();
            if (rainRenderer != null) rainRenderer.enabled = false;
            RenderSettings.fog = false; if (sun != null) sun.intensity = 1.15f;
        }
        private void OnDisable() => Clear();
        private void OnDestroy()
        {
            if (mesh != null) { if (Application.isPlaying) Destroy(mesh); else DestroyImmediate(mesh); }
            if (material != null) { if (Application.isPlaying) Destroy(material); else DestroyImmediate(material); }
        }
    }
}
