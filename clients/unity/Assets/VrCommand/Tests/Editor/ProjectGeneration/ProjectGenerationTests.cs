using NUnit.Framework;
using Unity.Netcode;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.XR.Management;
using UnityEngine.XR.OpenXR;
using UnityEngine.XR.OpenXR.Features.Interactions;
using UnityEngine.XR.OpenXR.Features.MetaQuestSupport;
using VrCommand.Unity.Editor;

namespace VrCommand.Unity.Tests
{
    public sealed class ProjectGenerationTests
    {
        private const string ScenePath = "Assets/VrCommand/Generated/Arena.unity";

        [Test] public void PreparePreservesNetworkIdentitiesAcrossPlayerBuilds()
        {
            ProjectBuilder.Prepare();
            var sceneId = GlobalObjectId.GetGlobalObjectIdSlow(GameObject.Find("Scene Authority").GetComponent<NetworkObject>());
            var prefabId = GlobalObjectId.GetGlobalObjectIdSlow(GameObject.Find("Network Manager").GetComponent<NetworkManager>().NetworkConfig.PlayerPrefab.GetComponent<NetworkObject>());
            ProjectBuilder.Prepare();
            Assert.AreEqual(sceneId, GlobalObjectId.GetGlobalObjectIdSlow(GameObject.Find("Scene Authority").GetComponent<NetworkObject>()));
            Assert.AreEqual(prefabId, GlobalObjectId.GetGlobalObjectIdSlow(GameObject.Find("Network Manager").GetComponent<NetworkManager>().NetworkConfig.PlayerPrefab.GetComponent<NetworkObject>()));
        }

        [Test] public void GeneratedSceneAndPrefabRetainValidSerializedNetworkObjects()
        {
            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var state = GameObject.Find("Scene Authority");
            var bootstrap = GameObject.Find("Network Manager").GetComponent<VenueBootstrap>();
            var manager = bootstrap.networkManager;
            Assert.AreEqual(29, manager.NetworkConfig.ProtocolVersion);
            Assert.AreSame(state.GetComponent<SceneAuthority>(), bootstrap.sceneAuthority);
            Assert.AreSame(state.GetComponent<CombatAuthority>(), bootstrap.combatAuthority);
            Assert.Greater(new SerializedObject(state.GetComponent<NetworkObject>()).FindProperty("GlobalObjectIdHash").uintValue, 0);
            Assert.Greater(new SerializedObject(manager.NetworkConfig.PlayerPrefab.GetComponent<NetworkObject>()).FindProperty("GlobalObjectIdHash").uintValue, 0);
            Assert.AreEqual(1, manager.NetworkConfig.Prefabs.NetworkPrefabsLists.Count);
            Assert.AreEqual(1, manager.NetworkConfig.Prefabs.NetworkPrefabsLists[0].PrefabList.Count);
            var weather = state.GetComponent<UnityWeatherView>();
            Assert.IsNotNull(weather.sun);
            Assert.AreEqual("Universal Render Pipeline/Unlit", weather.rainMaterial.shader.name);
            foreach (var clip in new[] { weather.rainClip, weather.thunderClip })
            { Assert.IsNotNull(clip); Assert.AreEqual(22050, clip.frequency); Assert.AreEqual(88200, clip.samples); }
            foreach (var root in UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects())
                foreach (var child in root.GetComponentsInChildren<Transform>(true))
                    Assert.AreEqual(0, GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(child.gameObject));
        }

        [Test] public void PreparedQuestProfileHasOpenXrLoaderAndControllerFeatures()
        {
            Assert.IsTrue(EditorBuildSettings.TryGetConfigObject(XRGeneralSettings.k_SettingsKey, out UnityEditor.XR.Management.XRGeneralSettingsPerBuildTarget settings));
            var android = settings.SettingsForBuildTarget(BuildTargetGroup.Android);
            Assert.IsTrue(android.InitManagerOnStart);
            Assert.IsTrue(System.Linq.Enumerable.Any(android.AssignedSettings.activeLoaders, loader => loader.GetType().FullName == "UnityEngine.XR.OpenXR.OpenXRLoader"));
            var openXR = OpenXRSettings.GetSettingsForBuildTargetGroup(BuildTargetGroup.Android);
            var quest = openXR.GetFeature<MetaQuestFeature>();
            Assert.IsTrue(quest.enabled); Assert.IsFalse(quest.ForceRemoveInternetPermission);
            Assert.IsTrue(openXR.GetFeature<OculusTouchControllerProfile>().enabled);
            Assert.IsNotNull(UnityEngine.Rendering.GraphicsSettings.defaultRenderPipeline);
            Assert.AreEqual(AndroidArchitecture.ARM64, PlayerSettings.Android.targetArchitectures);
        }
    }
}
