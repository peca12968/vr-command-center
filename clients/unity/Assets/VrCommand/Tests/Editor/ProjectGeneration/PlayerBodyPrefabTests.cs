using System.Reflection;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
namespace VrCommand.Unity.Tests
{
    public sealed class PlayerBodyPrefabTests
    {
        [Test] public void SavedPrefabChildVisualMarkersCanBeHiddenWithoutMovingTrackedJoints()
        {
            var source=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/VrCommand/Generated/PlayerAvatar.prefab");var root=Object.Instantiate(source);
            try{var a=root.GetComponent<NetworkAvatar>();foreach(var joint in new[]{a.head,a.leftHand,a.rightHand}){var position=joint.localPosition;var rotation=joint.localRotation;var scale=joint.localScale;var renderers=joint.GetComponentsInChildren<Renderer>(true);Assert.IsNotEmpty(renderers);Assert.IsNull(joint.GetComponent<Renderer>());
                typeof(NetworkAvatar).GetMethod("HideJoint",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{joint});foreach(var renderer in renderers)Assert.IsFalse(renderer.enabled);Assert.AreEqual(position,joint.localPosition);Assert.AreEqual(rotation,joint.localRotation);Assert.AreEqual(scale,joint.localScale);}}
            finally{Object.DestroyImmediate(root);}
        }
    }
}
