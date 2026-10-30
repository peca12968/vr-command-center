using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace VrCommand.Unity
{
    [Serializable] public sealed class PlayerFireObservation
    {
        public string id;public long tick,fireSequence,fireTickPlusOne;public bool visible;public float recoil;
        public Vector3 acceptedOrigin,acceptedDirection,gun,pointer,pointerDirection,flashOrigin,flashDirection;
    }
    // Explicit local development evidence. Only the game's framebuffer and
    // applied player renderer state; no input, PCM, OS capture or game mutation.
    public sealed class NativePlayerFireProbe : MonoBehaviour
    {
        [Serializable] public sealed class Capture
        {public string file,phase;public PlayerFireObservation[] players;}
        [Serializable] public sealed class Report
        {public string mode="player-fire",source="NativeWindowsFramebuffer",rig="Simulated",error="",stopReason="";public int audioSamples,callbackCount;public bool complete,observedEnd;public Capture[] captures;}
        private string directory,stopReason="";
        private double started;
        private bool finished,observedEnd;
        private readonly List<Capture> captures=new List<Capture>();
        private readonly HashSet<string> seen=new HashSet<string>();
        public static void Install(GameObject owner)
        {
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            var args=Environment.GetCommandLineArgs();var index=Array.IndexOf(args,"--vr-player-fire-probe");if(index<0)return;
            if(Application.isBatchMode || Application.isEditor || owner.GetComponent<AudioListener>()==null)return;
            foreach(var flag in new[]{"--vr-weather-probe","--vr-hud-probe","--vr-hud-trace","--vr-enemy-fire-probe"})
                if(Array.IndexOf(args,flag)>=0)throw new ArgumentException("Select only one player fire / enemy fire / weather / HUD diagnostic.");
            if(index+1>=args.Length || !Path.IsPathRooted(args[index+1]))throw new ArgumentException("Player fire probe requires a fresh absolute directory.");
            var path=Path.GetFullPath(args[index+1]);if(Directory.Exists(path)||File.Exists(path))throw new IOException("Player fire probe directory exists.");
            Directory.CreateDirectory(path);var probe=owner.AddComponent<NativePlayerFireProbe>();probe.directory=path;probe.started=Time.realtimeSinceStartupAsDouble;probe.StartCoroutine(probe.Observe());
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
                        var rows=new List<PlayerFireObservation>();
                        foreach(var avatar in FindObjectsByType<NetworkAvatar>(FindObjectsSortMode.None)){var row=avatar.ObservePlayerFire();if(row!=null)rows.Add(row);}
                        string key=null;foreach(var row in rows)if(row.visible){key="shot-"+row.id+"-"+row.fireSequence;break;}
                        var phase=scene.Phase.Value.ToString();if(phase=="Paused")key="paused-"+(rows.Count>0?rows[0].tick:0);
                        if(captures.Count<8 && key!=null && seen.Add(key))Save(key,phase,rows.ToArray());
                        if(phase=="Ended"){observedEnd=true;stopReason="Observed End";Finish(true);continue;}
                    }
                    if(Time.realtimeSinceStartupAsDouble-started>300)Finish(false,"Player fire probe exceeded 300 seconds.");
                }
                catch(Exception error){Finish(false,error.GetType().Name+": "+error.Message);}
            }
        }
        private void Save(string name,string phase,PlayerFireObservation[] rows)
        {
            if((long)Screen.width*Screen.height>9000000)throw new InvalidOperationException("Probe framebuffer is too large.");
            var texture=new Texture2D(Screen.width,Screen.height,TextureFormat.RGB24,false);
            try
            {
                using(NativePoseTrace.Measure("PlayerGpuReadback")){texture.ReadPixels(new Rect(0,0,Screen.width,Screen.height),0,0);texture.Apply();}
                byte[] encoded;using(NativePoseTrace.Measure("PlayerPngEncode"))encoded=texture.EncodeToPNG();
                using(NativePoseTrace.Measure("PlayerPngWrite"))File.WriteAllBytes(Path.Combine(directory,name+".png"),encoded);
                captures.Add(new Capture{file=name+".png",phase=phase,players=rows});Write(false,"");
            }
            finally{Destroy(texture);}
        }
        private void Write(bool complete,string error)=>File.WriteAllText(Path.Combine(directory,complete||finished?"report.json":"status.json"),JsonUtility.ToJson(new Report{complete=complete,observedEnd=observedEnd,stopReason=stopReason,error=error,captures=captures.ToArray()},true));
        private void Finish(bool complete,string error=""){if(finished)return;finished=true;Write(complete,error);}
        private void OnDestroy(){if(directory!=null&&!finished)Finish(false,"Probe owner despawned before collection finished.");}
    }
}
