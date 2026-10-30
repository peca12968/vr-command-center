using NUnit.Framework;
using UnityEngine;
using VrCommand.Unity.Editor;
namespace VrCommand.Unity.Tests { public sealed class CombatAudioGenerationTests {
        [Test] public void PreparePreservesTheSoundLibraryGuidAndWaveReferencesAcrossRepeatedUse()
        {
            const string path="Assets/VrCommand/Resources/VrCommand/CombatAudioAssets.asset";
            var before=UnityEditor.AssetDatabase.AssetPathToGUID(path);var rifle=Resources.Load<CombatAudioAssets>("VrCommand/CombatAudioAssets").rifle;
            ProjectBuilder.Prepare();Assert.AreEqual(before,UnityEditor.AssetDatabase.AssetPathToGUID(path));Assert.AreSame(rifle,Resources.Load<CombatAudioAssets>("VrCommand/CombatAudioAssets").rifle);
        }
} }
