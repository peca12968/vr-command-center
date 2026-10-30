using System;
using System.Collections.Generic;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    [Serializable] public sealed class CombatSoundObservation
    {public string id;public long sequence,tick,tickPlusOne;public bool enemy;public Vector3 origin;public double startedSeconds;}
    // All voices stay at the accepted world muzzle. No local trigger prediction.
    public sealed class CombatAudioView : MonoBehaviour,IDisposable
    {
        private sealed class Cursor
        {internal readonly CombatAudioCursor Value=new CombatAudioCursor();internal long Tick=-1,Sequence=-1;internal bool Running;internal double Observed;}
        private readonly Dictionary<string,Cursor> cursors=new Dictionary<string,Cursor>();
        private readonly List<CombatActorState> pending=new List<CombatActorState>();
        private AudioSource[] voices;
        private CombatAudioAssets assets;
        private NetworkAvatar owner;
        private int nextVoice;
        private bool disposed;
        public CombatSoundObservation LastPlayed {get;private set;}
        public long PlayedCount {get;private set;}
        public static void Install(GameObject listener,NetworkAvatar owner)
        {
            CombatAudioAssets.ValidateProfile();
            var view=listener.AddComponent<CombatAudioView>();view.owner=owner;
            view.assets=Resources.Load<CombatAudioAssets>("VrCommand/CombatAudioAssets");
            if(view.assets==null||view.assets.rifle==null||view.assets.pistol==null)throw new InvalidOperationException("Combat audio assets are missing.");
            view.voices=new AudioSource[CombatAudioPresentation.Voices];
            for(var i=0;i<view.voices.Length;i++)
            {
                var sound=new GameObject("Accepted combat sound");var source=sound.AddComponent<AudioSource>();
                source.playOnAwake=false;source.loop=false;source.spatialBlend=1;source.dopplerLevel=0;source.rolloffMode=AudioRolloffMode.Linear;
                source.minDistance=CombatAudioPresentation.MinimumDistance;source.maxDistance=CombatAudioPresentation.MaximumDistance;view.voices[i]=source;
            }
        }
        private void Update()
        {
            if(disposed)return;
            var authority=CombatAuthority.Instance;var scene=SceneAuthorityForAudio();
            if(authority==null||scene==null||owner==null||!authority.Player(owner.PlayerId.Value.ToString(),out var local)) {Stop();return;}
            var running=scene.AudioRunning && authority.Ready.Value && local.connected;
            if(!running)Stop();pending.Clear();var present=new HashSet<string>();var now=Time.realtimeSinceStartupAsDouble;
            foreach(var actor in authority.Actors)
            {
                var key=actor.id.ToString();present.Add(key);
                if(!cursors.TryGetValue(key,out var cursor)){cursor=new Cursor();cursors.Add(key,cursor);}
                if(cursor.Tick!=actor.presentationTick||cursor.Sequence!=actor.fireSequence||cursor.Running!=actor.presentationRunning)
                {cursor.Observed=now;cursor.Tick=actor.presentationTick;cursor.Sequence=actor.fireSequence;cursor.Running=actor.presentationRunning;}
                var continuous=running&&now-cursor.Observed<=1.5&&actor.room==local.room;
                if(cursor.Value.Advance(actor.presentationTick,actor.presentationRunning?"Running":"Paused",actor.fireSequence,actor.fireTickPlusOne,continuous)
                    &&Vector3.Distance(transform.position,actor.fireOrigin)<CombatAudioPresentation.MaximumDistance)pending.Add(actor);
            }
            foreach(var key in new List<string>(cursors.Keys))if(!present.Contains(key))cursors.Remove(key);
            pending.Sort((a,b)=>{var d=(a.fireOrigin-transform.position).sqrMagnitude.CompareTo((b.fireOrigin-transform.position).sqrMagnitude);return d!=0?d:string.CompareOrdinal(a.id.ToString(),b.id.ToString());});
            for(var i=0;i<Math.Min(pending.Count,voices.Length);i++)Play(pending[i]);
        }
        private static SceneAuthority SceneAuthorityForAudio()=>CombatAuthority.Instance==null?null:CombatAuthority.Instance.GetComponent<SceneAuthority>();
        private void Play(CombatActorState actor)
        {
            var source=voices[nextVoice++%voices.Length];source.Stop();source.transform.position=actor.fireOrigin;
            source.clip=actor.enemy?assets.pistol:assets.rifle;source.volume=actor.enemy?CombatAudioPresentation.PistolVolume:CombatAudioPresentation.RifleVolume;source.Play();PlayedCount++;
            LastPlayed=new CombatSoundObservation{id=actor.id.ToString(),sequence=actor.fireSequence,tick=actor.presentationTick,tickPlusOne=actor.fireTickPlusOne,
                enemy=actor.enemy,origin=actor.fireOrigin,startedSeconds=Time.realtimeSinceStartupAsDouble};
            NativeCombatAudioProbe.Observe(LastPlayed);
        }
        private void Stop(){if(voices!=null)foreach(var source in voices)if(source!=null)source.Stop();}
        private void OnDisable(){Stop();foreach(var cursor in cursors.Values)cursor.Value.Reset();}
        public void Dispose(){if(disposed)return;disposed=true;Stop();if(voices!=null)foreach(var source in voices)if(source!=null){if(Application.isPlaying)Destroy(source.gameObject);else DestroyImmediate(source.gameObject);}voices=null;}
        private void OnDestroy()=>Dispose();
    }
}
