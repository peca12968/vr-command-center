using UnityEngine;

namespace VrCommand.Unity
{
    [System.Serializable] public sealed class CombatAudioDefinition
    {public string soundSet;public int combatAudioVersion,maximumAgeTicks,maximumGapTicks,voices;public float minimumDistance,maximumDistance,rifleVolume,pistolVolume;}
    public sealed class CombatAudioAssets : ScriptableObject
    {
        public AudioClip rifle,pistol;
        public static void ValidateProfile()
        {
            var text=Resources.Load<TextAsset>("VrCommand/combat-audio-v1");if(text==null)throw new System.InvalidOperationException("Combat sound profile is missing.");
            var p=JsonUtility.FromJson<CombatAudioDefinition>(text.text);
            if(p==null||p.soundSet!="combat-audio-v1"||p.combatAudioVersion!=1||p.maximumAgeTicks!=VrCommand.Simulation.CombatAudioPresentation.MaximumAge
                ||p.maximumGapTicks!=VrCommand.Simulation.CombatAudioPresentation.MaximumGap||p.voices!=VrCommand.Simulation.CombatAudioPresentation.Voices
                ||p.minimumDistance!=VrCommand.Simulation.CombatAudioPresentation.MinimumDistance||p.maximumDistance!=VrCommand.Simulation.CombatAudioPresentation.MaximumDistance
                ||p.rifleVolume!=VrCommand.Simulation.CombatAudioPresentation.RifleVolume||p.pistolVolume!=VrCommand.Simulation.CombatAudioPresentation.PistolVolume)
                throw new System.InvalidOperationException("Unsupported combat sound profile.");
        }
    }
}
