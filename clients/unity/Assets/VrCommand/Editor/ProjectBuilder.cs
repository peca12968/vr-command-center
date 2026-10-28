using System;
using System.IO;
using Unity.Netcode;
using Unity.Netcode.Transports.UTP;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEditor.XR.OpenXR.Features;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR.Management;
using UnityEngine.XR.OpenXR;
using UnityEngine.XR.OpenXR.Features.Interactions;
using UnityEngine.XR.OpenXR.Features.MetaQuestSupport;

namespace VrCommand.Unity.Editor
{
    public static class ProjectBuilder
    {
        private const string Generated = "Assets/VrCommand/Generated";
        private const string ScenePath = Generated + "/Arena.unity";

        [MenuItem("VR Command/Prepare Quest 3 Project")]
        public static void Prepare()
        {
            Directory.CreateDirectory(Generated);
            AssetDatabase.Refresh();
            ConfigureQuest();
            CreateScene();
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            AssetDatabase.SaveAssets();
            Debug.Log("VR Command project prepared. Hardware and multiplayer validation remain required.");
        }

        private static void ConfigureQuest()
        {
            PlayerSettings.companyName = "VR Command";
            PlayerSettings.productName = "VR Command Quest";
            PlayerSettings.bundleVersion = "0.16.0";
            PlayerSettings.Android.bundleVersionCode = 16;
            PlayerSettings.insecureHttpOption = InsecureHttpOption.DevelopmentOnly;
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, "com.vrcommand.quest");
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel32;
            PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevel35;
            PlayerSettings.Android.forceInternetPermission = true;
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.Vulkan });
            PlayerSettings.colorSpace = ColorSpace.Linear;
            QualitySettings.SetQualityLevel(0);
            GraphicsSettings.defaultRenderPipeline = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>("Assets/Settings/Mobile_RPAsset.asset");
            var playerSettings = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset")[0]);
            var input = playerSettings.FindProperty("activeInputHandler");
            if (input != null) { input.intValue = 1; playerSettings.ApplyModifiedPropertiesWithoutUndo(); }

            if (!EditorBuildSettings.TryGetConfigObject(XRGeneralSettings.k_SettingsKey, out XRGeneralSettingsPerBuildTarget xr))
            {
                xr = ScriptableObject.CreateInstance<XRGeneralSettingsPerBuildTarget>();
                AssetDatabase.CreateAsset(xr, Generated + "/XRSettings.asset");
                EditorBuildSettings.AddConfigObject(XRGeneralSettings.k_SettingsKey, xr, true);
            }
            if (!xr.HasSettingsForBuildTarget(BuildTargetGroup.Android)) xr.CreateDefaultSettingsForBuildTarget(BuildTargetGroup.Android);
            if (!xr.HasManagerSettingsForBuildTarget(BuildTargetGroup.Android)) xr.CreateDefaultManagerSettingsForBuildTarget(BuildTargetGroup.Android);
            var settings = xr.SettingsForBuildTarget(BuildTargetGroup.Android);
            settings.InitManagerOnStart = true;
            if (!XRPackageMetadataStore.AssignLoader(settings.AssignedSettings, "UnityEngine.XR.OpenXR.OpenXRLoader", BuildTargetGroup.Android))
                throw new BuildFailedException("OpenXR loader could not be assigned.");
            FeatureHelpers.RefreshFeatures(BuildTargetGroup.Android);
            var openXR = OpenXRSettings.GetSettingsForBuildTargetGroup(BuildTargetGroup.Android);
            if (openXR == null) throw new BuildFailedException("Android OpenXR settings are unavailable.");
            var quest = openXR.GetFeature<MetaQuestFeature>();
            var controllers = openXR.GetFeature<OculusTouchControllerProfile>();
            if (quest == null || controllers == null) throw new BuildFailedException("Quest OpenXR feature profiles are missing.");
            quest.enabled = true;
            quest.ForceRemoveInternetPermission = false;
            controllers.enabled = true;
            openXR.renderMode = OpenXRSettings.RenderMode.SinglePassInstanced;
            EditorUtility.SetDirty(openXR);
            EditorUtility.SetDirty(xr);
        }

        private static void CreateScene()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var concrete = Material("Concrete", new Color(0.25f, 0.27f, 0.26f));
            var steel = Material("Steel", new Color(0.19f, 0.23f, 0.24f));
            var avatarMaterial = Material("Players", new Color(0.24f, 0.67f, 0.38f));
            for (var room = 1; room <= 5; room++)
            {
                var origin = VenueBootstrap.RoomOrigin(room);
                Primitive("Room " + room + " Floor", PrimitiveType.Cube, origin + new Vector3(0, -0.15f, 0), new Vector3(12, 0.3f, 12), concrete);
            }
            var lightObject = new GameObject("Sun", typeof(Light));
            var sun = lightObject.GetComponent<Light>();
            sun.type = LightType.Directional;
            sun.shadows = LightShadows.Soft;
            lightObject.transform.rotation = Quaternion.Euler(48, -35, 0);
            var spectator = new GameObject("Desktop Spectator", typeof(Camera), typeof(AudioListener));
            spectator.tag = "MainCamera";
            spectator.transform.position = new Vector3(0, 18, -18);
            spectator.transform.LookAt(new Vector3(0, 0, 1));

            var state = new GameObject("Scene Authority", typeof(NetworkObject), typeof(SceneAuthority), typeof(CombatAuthority), typeof(UnityWeatherView));
            var weatherView = state.GetComponent<UnityWeatherView>(); weatherView.sun = sun;
            weatherView.rainClip = AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/VrCommand/Audio/rain-loop.wav");
            weatherView.thunderClip = AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/VrCommand/Audio/thunder.wav");
            if (weatherView.rainClip == null || weatherView.thunderClip == null) throw new InvalidOperationException("Weather audio assets are missing.");
            var rainMaterial = AssetDatabase.LoadAssetAtPath<Material>(Generated + "/Rain.mat");
            if (rainMaterial == null) { rainMaterial = new Material(Shader.Find("Universal Render Pipeline/Unlit")); AssetDatabase.CreateAsset(rainMaterial, Generated + "/Rain.mat"); }
            weatherView.rainMaterial = rainMaterial; state.GetComponent<SceneAuthority>().environmentView = weatherView;
            var network = new GameObject("Network Manager", typeof(NetworkManager), typeof(UnityTransport), typeof(VenueBootstrap));
            var manager = network.GetComponent<NetworkManager>();
            var bootstrap = network.GetComponent<VenueBootstrap>();
            manager.NetworkConfig = new NetworkConfig { NetworkTransport = network.GetComponent<UnityTransport>(), TickRate = 30,
                ConnectionApproval = true, EnableSceneManagement = true, ForceSamePrefabs = true, ProtocolVersion = 16 };
            manager.NetworkConfig.PlayerPrefab = CreateAvatar(avatarMaterial, steel);
            var list = AssetDatabase.LoadAssetAtPath<NetworkPrefabsList>(Generated + "/NetworkPrefabs.asset");
            if (list == null)
            {
                list = ScriptableObject.CreateInstance<NetworkPrefabsList>();
                AssetDatabase.CreateAsset(list, Generated + "/NetworkPrefabs.asset");
            }
            while (list.PrefabList.Count > 0) list.Remove(list.PrefabList[0]);
            list.Add(new NetworkPrefab { Prefab = manager.NetworkConfig.PlayerPrefab });
            manager.NetworkConfig.Prefabs.NetworkPrefabsLists.Add(list);
            EditorUtility.SetDirty(list);
            bootstrap.networkManager = manager;
            bootstrap.sceneAuthority = state.GetComponent<SceneAuthority>();
            bootstrap.combatAuthority = state.GetComponent<CombatAuthority>();
            if (!EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), ScenePath))
                throw new BuildFailedException("Generated arena scene could not be saved.");
        }

        private static GameObject CreateAvatar(Material material, Material weapon)
        {
            var root = new GameObject("Player Avatar", typeof(NetworkObject), typeof(NetworkAvatar));
            var avatar = root.GetComponent<NetworkAvatar>();
            avatar.head = Joint(root.transform, "Head", new Vector3(0, 1.65f, 0), PrimitiveType.Sphere, Vector3.one * 0.24f, material);
            avatar.leftHand = Joint(root.transform, "Left Hand", new Vector3(-0.3f, 1.3f, 0.3f), PrimitiveType.Cube, new Vector3(0.12f, 0.12f, 0.2f), material);
            avatar.rightHand = Joint(root.transform, "Right Hand", new Vector3(0.3f, 1.3f, 0.3f), PrimitiveType.Cube, new Vector3(0.12f, 0.12f, 0.2f), material);
            Joint(avatar.rightHand, "Weapon", new Vector3(0, -.035f, .12f), PrimitiveType.Cube, new Vector3(.08f, .08f, .38f), weapon);
            var prefab = PrefabUtility.SaveAsPrefabAsset(root, Generated + "/PlayerAvatar.prefab");
            UnityEngine.Object.DestroyImmediate(root);
            return prefab;
        }

        private static Transform Joint(Transform parent, string name, Vector3 position, PrimitiveType type, Vector3 scale, Material material)
        {
            var joint = new GameObject(name).transform;
            joint.SetParent(parent, false);
            joint.localPosition = position;
            var visual = Primitive("Visual", type, Vector3.zero, scale, material);
            visual.transform.SetParent(joint, false);
            UnityEngine.Object.DestroyImmediate(visual.GetComponent<Collider>());
            return joint;
        }
        private static GameObject Primitive(string name, PrimitiveType type, Vector3 position, Vector3 scale, Material material)
        {
            var obj = GameObject.CreatePrimitive(type);
            obj.name = name;
            obj.transform.position = position;
            obj.transform.localScale = scale;
            obj.GetComponent<Renderer>().sharedMaterial = material;
            return obj;
        }
        private static Material Material(string name, Color color)
        {
            var path = Generated + "/" + name + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material != null) return material;
            material = new Material(Shader.Find("Universal Render Pipeline/Lit")) { color = color };
            AssetDatabase.CreateAsset(material, path);
            return material;
        }

        public static void BuildQuest()
        {
            Prepare();
            Build(BuildTarget.Android, "artifacts/quest/VrCommand.apk");
        }
        public static void BuildDesktop()
        {
            Prepare();
            Build(BuildTarget.StandaloneWindows64, "artifacts/desktop/VrCommand.exe");
        }
        private static void Build(BuildTarget target, string relativePath)
        {
            var path = Path.GetFullPath(Path.Combine(Application.dataPath, "../../..", relativePath));
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { ScenePath }, locationPathName = path,
                target = target, options = BuildOptions.Development });
            if (report.summary.result != BuildResult.Succeeded) throw new BuildFailedException("VR Command player build failed.");
        }
    }
}
