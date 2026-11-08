using System;
using System.IO;
using System.Linq;
using NUnit.Framework;
using Unity.Collections;
using Unity.Netcode;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class CombatAudioTests
    {
        [Test] public void ImportedPcmClipsRetainExactMonoWaveSamplesAndResourceReferences()
        {
            var assets=Resources.Load<CombatAudioAssets>("VrCommand/CombatAudioAssets");Assert.IsNotNull(assets);
            foreach(var pair in new[]{(assets.rifle,"rifle-shot-v1.wav",5292),(assets.pistol,"pistol-shot-v1.wav",3969)})
            {
                Assert.AreEqual(22050,pair.Item1.frequency);Assert.AreEqual(1,pair.Item1.channels);Assert.AreEqual(pair.Item3,pair.Item1.samples);
                var samples=new float[pair.Item3];Assert.IsTrue(pair.Item1.GetData(samples,0));
                using(var reader=new BinaryReader(File.OpenRead("Assets/VrCommand/Audio/"+pair.Item2)))
                {reader.ReadBytes(44);for(var i=0;i<samples.Length;i++)Assert.AreEqual(reader.ReadInt16()/32768f,samples[i],.000001f);}
                Assert.Greater(samples.Max(Mathf.Abs),.6f);Assert.LessOrEqual(samples.Max(Mathf.Abs),.672f);
            }
        }
        [Test] public void VoicePoolIsBoundedSpatialAndDetachedWithoutNewGameplayColliders()
        {
            var root=new GameObject("Audio owner test",typeof(NetworkObject),typeof(NetworkAvatar),typeof(AudioListener));
            try
            {
                CombatAudioView.Install(root,root.GetComponent<NetworkAvatar>());
                var sources=UnityEngine.Object.FindObjectsByType<AudioSource>(FindObjectsSortMode.None).Where(s=>s.name=="Accepted combat sound").ToArray();
                Assert.AreEqual(32,sources.Length);
                foreach(var source in sources){Assert.IsFalse(source.playOnAwake);Assert.IsFalse(source.loop);Assert.AreEqual(1,source.spatialBlend);Assert.AreEqual(0,source.dopplerLevel);
                    Assert.AreEqual(AudioRolloffMode.Linear,source.rolloffMode);Assert.AreEqual(1,source.minDistance);Assert.AreEqual(25,source.maxDistance);Assert.IsNull(source.transform.parent);Assert.IsNull(source.GetComponent<Collider>());Assert.IsNull(source.GetComponent<NetworkObject>());}
            }
            finally{root.GetComponent<CombatAudioView>()?.Dispose();UnityEngine.Object.DestroyImmediate(root);}
            Assert.IsFalse(UnityEngine.Object.FindObjectsByType<AudioSource>(FindObjectsSortMode.None).Any(s=>s.name=="Accepted combat sound"));
        }
        [Test] public void AtomicActorRunningFlagSurvivesNgoAndItsEqualityFence()
        {
            var value=new CombatActorState{id=System.Guid.Parse("8b5d920d-65ee-4df8-adf8-bdb7be537cfe"),presentationTick=1,presentationRunning=true,fireSequence=2,fireTickPlusOne=2,fireDirection=Vector3.forward};
            using(var writer=new FastBufferWriter(1024,Allocator.Temp))
            {writer.WriteValueSafe(value);using(var reader=new FastBufferReader(writer.ToArray(),Allocator.Temp)){reader.ReadValueSafe(out CombatActorState read);Assert.IsTrue(read.Equals(value));read.presentationRunning=false;Assert.IsFalse(read.Equals(value));}}
        }
        [Test] public void CursorSuppressesJoinPauseSeekAndStaleCatchupWithoutLocalTime()
        {
            var c=new CombatAudioCursor();Assert.IsFalse(c.Advance(0,"Preparing",0,0,true));Assert.IsTrue(c.Advance(0,"Running",1,1,true));Assert.IsFalse(c.Advance(0,"Running",1,1,true));
            Assert.IsFalse(c.Advance(0,"Paused",1,1,true));Assert.IsFalse(c.Advance(0,"Running",1,1,true));Assert.IsTrue(c.Advance(4,"Running",2,5,true));
            Assert.IsFalse(c.Advance(30,"Running",3,31,true));Assert.IsTrue(c.Advance(31,"Running",4,32,true));Assert.IsFalse(c.Advance(0,"Running",1,1,true));
        }
        [Test] public void LegacyHeaderKeepsZeroAudioWhileNewJsonUtilityHeaderRetainsOne()
        {
            var codec=new UnityWorldCodec();var h=WorldRecordingHeader.Create(Guid.NewGuid(),Guid.NewGuid(),"Simulation",new[]{3},new WorldProp[0]);
            var old=codec.Header(h).Replace(",\"combatAudioVersion\":0","");Assert.AreEqual(0,codec.ReadHeader(old).combatAudioVersion);
            h.assetSet=WorldAssetSets.PlayerFire;h.enemyPresentationVersion=h.weaponPresentationVersion=h.enemyFireVersion=h.playerFireVersion=h.combatAudioVersion=1;
            WorldRecordingValidation.Header(codec.ReadHeader(codec.Header(h)));h.combatAudioVersion=2;Assert.Throws<ArgumentException>(()=>WorldRecordingValidation.Header(h));
        }
    }
}
