using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace VrCommand.Unity
{
    [Serializable] public sealed class EnemyFireObservation
    {
        public string id; public long tick,fireSequence,fireTickPlusOne; public bool visible; public float recoil;
        public Vector3 acceptedOrigin,acceptedDirection,gun,flashOrigin,flashDirection;
    }
    // Explicit Windows Development / untracked local player only. Own rendered
    // framebuffer, no microphone, PCM, OS capture, input or simulation mutation.
    public sealed class NativeEnemyFireProbe : MonoBehaviour
    {
        [Serializable] public sealed class Capture
        { public string file,phase; public EnemyFireObservation[] enemies; }
        [Serializable] public sealed class Report
        { public string mode="enemy-fire",source="NativeWindowsFramebuffer",rig="Simulated",error="";public int audioSamples,callbackCount;public bool complete,observedEnd;public string stopReason;public Capture[] captures; }
        private string directory;
        private double started;
        private bool finished,observedEnd;
        private string stopReason="";
        private readonly List<Capture> captures=new List<Capture>();
        private readonly HashSet<string> seen=new HashSet<string>();
        public static void Install(GameObject owner)
        {
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            var args=Environment.GetCommandLineArgs();var index=Array.IndexOf(args,"--vr-enemy-fire-probe");if(index<0)return;
            if(Application.isBatchMode || Application.isEditor || owner.GetComponent<AudioListener>()==null)return;
            foreach(var flag in new[]{"--vr-weather-probe","--vr-hud-probe","--vr-hud-trace"})
                if(Array.IndexOf(args,flag)>=0)throw new ArgumentException("Enemy fire probe is exclusive with weather/HUD probes.");
            if(index+1>=args.Length || !Path.IsPathRooted(args[index+1]))throw new ArgumentException("Enemy fire probe needs a fresh absolute directory.");
            var path=Path.GetFullPath(args[index+1]);if(Directory.Exists(path)||File.Exists(path))throw new IOException("Enemy fire probe directory already exists.");
            Directory.CreateDirectory(path);var probe=owner.AddComponent<NativeEnemyFireProbe>();probe.directory=path;probe.started=Time.realtimeSinceStartupAsDouble;probe.StartCoroutine(probe.Observe());
#endif
        }
        private IEnumerator Observe()
        {
            while(!finished)
            {
                yield return new WaitForEndOfFrame();
                try
                {
                    if(File.Exists(Path.Combine(directory,"finish.request"))){stopReason="Explicit local diagnostic stop";Finish(true);continue;}
                    var authority=CombatAuthority.Instance;var scene=authority==null?null:authority.GetComponent<SceneAuthority>();
                    if(authority!=null && authority.IsSpawned && scene!=null)
                    {
                        var rows=authority.ObserveEnemyFire();string key=null;
                        foreach(var row in rows)if(row.visible){key="shot-"+row.id+"-"+row.fireSequence;break;}
                        if(scene.Phase.Value.ToString()=="Paused")key=(rows.Length>0 && Array.Exists(rows,r=>r.visible)?"paused-flash-":"paused-")+(rows.Length>0?rows[0].tick:0);
                        if(captures.Count<8 && key!=null && seen.Add(key))Save(key,scene.Phase.Value.ToString(),rows);
                        if(scene.Phase.Value.ToString()=="Ended"){observedEnd=true;stopReason="Observed End";Finish(true);continue;}
                    }
                    if(Time.realtimeSinceStartupAsDouble-started>180)Finish(false,"Enemy fire probe exceeded 180 seconds.");
                }
                catch(Exception error){Finish(false,error.GetType().Name+": "+error.Message);}
            }
        }
        private void Save(string name,string phase,EnemyFireObservation[] rows)
        {
            if((long)Screen.width*Screen.height>9000000)throw new InvalidOperationException("Probe framebuffer is too large.");
            var texture=new Texture2D(Screen.width,Screen.height,TextureFormat.RGB24,false);
            try
            {
                texture.ReadPixels(new Rect(0,0,Screen.width,Screen.height),0,0);texture.Apply();
                File.WriteAllBytes(Path.Combine(directory,name+".png"),texture.EncodeToPNG());captures.Add(new Capture{file=name+".png",phase=phase,enemies=rows});Write(false,"");
            }
            finally{Destroy(texture);}
        }
        private void Write(bool complete,string error)=>File.WriteAllText(Path.Combine(directory,complete||finished?"report.json":"status.json"),JsonUtility.ToJson(new Report{complete=complete,observedEnd=observedEnd,stopReason=stopReason,error=error,captures=captures.ToArray()},true));
        private void Finish(bool complete,string error="") {if(finished)return;finished=true;Write(complete,error);}
        private void OnDestroy(){if(directory!=null&&!finished)Finish(false,"Probe owner despawned before collection finished.");}
    }
}
