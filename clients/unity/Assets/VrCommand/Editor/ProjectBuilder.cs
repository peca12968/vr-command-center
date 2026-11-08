using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
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
using UnityEngine.XR.OpenXR.Features.CompositionLayers;
using UnityEngine.XR.OpenXR.Features.Interactions;
using UnityEngine.XR.OpenXR.Features.Meta;
using UnityEngine.XR.OpenXR.Features.MetaQuestSupport;

namespace VrCommand.Unity.Editor
{
    public static class ProjectBuilder
    {
        private const string Generated = "Assets/VrCommand/Generated";
        private const string ScenePath = Generated + "/Arena.unity";
        private const ushort ProtocolVersion = 31;

        [MenuItem("VR Command/Prepare Quest 3 Project")]
        public static void Prepare() => PrepareAssets(false);

        [MenuItem("VR Command/Rebuild Arena (rebuild ALL players afterwards)")]
        public static void RebuildArena() => PrepareAssets(true);

        private static void PrepareAssets(bool rebuild)
        {
            Directory.CreateDirectory(Generated);
            AssetDatabase.Refresh();
            ConfigureQuest();
            PrepareCombatAudio();
            using (var fieldProps = new FieldPropModels()) { }
            using (var rifle = new ServiceRifleModels()) { }
            using(var body=new PlayerBodyModels()){}
            using (var opponents = new EnemyModels()) { }
            using (var actions = new AnimatedRifleModels()) { }
            if (rebuild || !File.Exists(ScenePath)) CreateScene();
            // Reload saved objects so NGO validates persistent GlobalObjectIds, then keep
            // their local file IDs identical for desktop and Android builds.
            AssetDatabase.ImportAsset(Generated + "/PlayerAvatar.prefab", ImportAssetOptions.ForceUpdate);
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var state = GameObject.Find("Scene Authority");
            var network = GameObject.Find("Network Manager");
            var bootstrap = network == null ? null : network.GetComponent<VenueBootstrap>();
            var manager = network == null ? null : network.GetComponent<NetworkManager>();
            if (state == null || state.GetComponent<UnityWeatherView>() == null || bootstrap == null || manager == null
                || bootstrap.sceneAuthority != state.GetComponent<SceneAuthority>() || (manager.NetworkConfig.ProtocolVersion < 16 || manager.NetworkConfig.ProtocolVersion > ProtocolVersion)
                || manager.NetworkConfig.PlayerPrefab == null)
                throw new BuildFailedException("Generated arena is incompatible. Rebuild Arena, then rebuild ALL player targets together.");
            manager.NetworkConfig.ProtocolVersion = ProtocolVersion;
            RequireNetworkIdentity(state.GetComponent<NetworkObject>());
            RequireNetworkIdentity(manager.NetworkConfig.PlayerPrefab.GetComponent<NetworkObject>());
            if (PrefabUtility.SavePrefabAsset(manager.NetworkConfig.PlayerPrefab) == null)
                throw new BuildFailedException("Validated player prefab could not be saved.");
            EditorSceneManager.MarkSceneDirty(scene);
            if (!EditorSceneManager.SaveScene(scene, ScenePath)) throw new BuildFailedException("Prepared scene could not be saved.");
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            AssetDatabase.SaveAssets();
            Debug.Log("VR Command project prepared. Hardware and multiplayer validation remain required.");
        }

        private static void PrepareCombatAudio()
        {
            AudioClip Clip(string name)
            {
                var path="Assets/VrCommand/Audio/"+name;
                var importer=AssetImporter.GetAtPath(path) as AudioImporter;if(importer==null)throw new BuildFailedException("Missing combat PCM: "+name);
                var settings=importer.defaultSampleSettings;
                if(settings.loadType!=AudioClipLoadType.DecompressOnLoad || settings.compressionFormat!=AudioCompressionFormat.PCM
                    || settings.sampleRateSetting!=AudioSampleRateSetting.PreserveSampleRate || !settings.preloadAudioData || !importer.forceToMono)
                {settings.loadType=AudioClipLoadType.DecompressOnLoad;settings.compressionFormat=AudioCompressionFormat.PCM;settings.sampleRateSetting=AudioSampleRateSetting.PreserveSampleRate;
                    importer.defaultSampleSettings=settings;settings.preloadAudioData=true;importer.defaultSampleSettings=settings;importer.forceToMono=true;importer.SaveAndReimport();}
                return AssetDatabase.LoadAssetAtPath<AudioClip>(path);
            }
            const string destination="Assets/VrCommand/Resources/VrCommand/CombatAudioAssets.asset";
            var assets=AssetDatabase.LoadAssetAtPath<CombatAudioAssets>(destination);
            if(assets==null){assets=ScriptableObject.CreateInstance<CombatAudioAssets>();AssetDatabase.CreateAsset(assets,destination);}
            assets.rifle=Clip("rifle-shot-v1.wav");assets.pistol=Clip("pistol-shot-v1.wav");
            if(assets.rifle==null||assets.pistol==null)throw new BuildFailedException("Combat PCM import failed.");EditorUtility.SetDirty(assets);
        }
        private static void RequireNetworkIdentity(NetworkObject value)
        {
            if (value == null || new SerializedObject(value).FindProperty("GlobalObjectIdHash").uintValue == 0)
                throw new BuildFailedException("Generated network object has no persistent NGO identity. Reopen/import the generated assets before building.");
        }

        private static void ConfigureQuest()
        {
            PlayerSettings.companyName = "VR Command";
            PlayerSettings.productName = "VR Command Quest";
            PlayerSettings.bundleVersion = "0.48.0";
            PlayerSettings.Android.bundleVersionCode = 61;
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
            var arSession = openXR.GetFeature<ARSessionFeature>();
            var passthrough = openXR.GetFeature<ARCameraFeature>();
            var composition = openXR.GetFeature<OpenXRCompositionLayersFeature>();
            if (quest == null || controllers == null || arSession == null || passthrough == null || composition == null)
                throw new BuildFailedException("Quest OpenXR feature profiles are missing.");
            quest.enabled = true;
            quest.ForceRemoveInternetPermission = false;
            controllers.enabled = true;
            arSession.enabled = true;
            passthrough.enabled = true;
            composition.enabled = true;
            openXR.renderMode = OpenXRSettings.RenderMode.SinglePassInstanced;
            EditorUtility.SetDirty(openXR);
            EditorUtility.SetDirty(quest);
            EditorUtility.SetDirty(controllers);
            EditorUtility.SetDirty(arSession);
            EditorUtility.SetDirty(passthrough);
            EditorUtility.SetDirty(composition);
            EditorUtility.SetDirty(settings);
            EditorUtility.SetDirty(settings.AssignedSettings);
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
                ConnectionApproval = true, EnableSceneManagement = true, ForceSamePrefabs = true, ProtocolVersion = ProtocolVersion };
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
            var receipt = new PlayerBuildReceipt { target = target.ToString(), outputPath = path, unityVersion = Application.unityVersion,
                sourceFingerprint = SourceFingerprint(),
                sceneNetworkId = GlobalObjectId.GetGlobalObjectIdSlow(GameObject.Find("Scene Authority").GetComponent<NetworkObject>()).ToString(),
                playerPrefabId = GlobalObjectId.GetGlobalObjectIdSlow(GameObject.Find("Network Manager").GetComponent<NetworkManager>().NetworkConfig.PlayerPrefab.GetComponent<NetworkObject>()).ToString() };
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { ScenePath }, locationPathName = path,
                target = target, options = BuildOptions.Development });
            if (report.summary.result != BuildResult.Succeeded) throw new BuildFailedException("VR Command player build failed.");
            receipt.completedAtUtc = DateTime.UtcNow.ToString("O", System.Globalization.CultureInfo.InvariantCulture);
            receipt.totalBytes = (long)report.summary.totalSize;
            File.WriteAllText(Path.Combine(Path.GetDirectoryName(path), "build-receipt.json"), JsonUtility.ToJson(receipt, true));
        }

        [Serializable] private sealed class PlayerBuildReceipt
        {
            public int schemaVersion = 1;
            public string target, outputPath, completedAtUtc, unityVersion, sourceFingerprint, sceneNetworkId, playerPrefabId;
            public long totalBytes;
        }

        private static string SourceFingerprint()
        {
            var project = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            var files = Directory.GetFiles(Path.Combine(project, "Assets/VrCommand"), "*", SearchOption.AllDirectories)
                .Concat(Directory.GetFiles(Path.Combine(project, "Packages/com.vrcommand.simulation"), "*", SearchOption.AllDirectories))
                .Concat(Directory.GetFiles(Path.Combine(project, "Packages/com.unity.transport"), "*", SearchOption.AllDirectories))
                .Where(file => file.EndsWith(".cs", StringComparison.Ordinal) || file.EndsWith(".asmdef", StringComparison.Ordinal))
                .Concat(Directory.GetFiles(Path.Combine(project, "Assets/VrCommand/Resources"), "*", SearchOption.AllDirectories)
                    .Where(file => file.EndsWith(".json", StringComparison.Ordinal) || file.EndsWith(".shader", StringComparison.Ordinal) || file.EndsWith(".asset", StringComparison.Ordinal) || file.EndsWith(".asset.meta", StringComparison.Ordinal) || file.EndsWith(".otf", StringComparison.Ordinal) || file.EndsWith(".otf.meta", StringComparison.Ordinal) || file.EndsWith(".txt", StringComparison.Ordinal) || file.EndsWith(".txt.meta", StringComparison.Ordinal)))
                .Concat(Directory.GetFiles(Path.Combine(project,"Assets/VrCommand/Audio"),"*",SearchOption.AllDirectories)
                    .Where(file=>file.EndsWith(".wav",StringComparison.Ordinal)||file.EndsWith(".wav.meta",StringComparison.Ordinal)))
                .Concat(new[] { Path.Combine(project, "Packages/manifest.json"), Path.Combine(project, "Packages/packages-lock.json"), Path.Combine(project, "Packages/com.unity.transport/UPSTREAM.json"), Path.Combine(project, "ProjectSettings/ProjectVersion.txt") })
                .Concat(new[] { Path.Combine(project, "Assets/Settings/Mobile_RPAsset.asset"), Path.Combine(project, "Assets/Settings/Mobile_Renderer.asset") })
                .OrderBy(file => Path.GetRelativePath(project, file).Replace('\\', '/'), StringComparer.Ordinal);
            using (var memory = new MemoryStream())
            using (var writer = new BinaryWriter(memory))
            using (var hash = SHA256.Create())
            {
                foreach (var file in files) { writer.Write(Path.GetRelativePath(project, file).Replace('\\', '/')); var bytes = File.ReadAllBytes(file); writer.Write(bytes.Length); writer.Write(bytes); }
                writer.Flush(); return BitConverter.ToString(hash.ComputeHash(memory.ToArray())).Replace("-", "").ToLowerInvariant();
            }
        }
    }
}
