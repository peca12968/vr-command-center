using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using UnityEngine;
namespace VrCommand.Unity
{
    // Explicit local framebuffer / applied transform evidence. Never drives input.
    public sealed class NativePlayerBodyProbe:MonoBehaviour
    {
        [Serializable] public sealed class Capture{public string file,phase;public PlayerBodyObservation[] players;public PlayerBodyObservation firstPerson;}
        [Serializable] public sealed class Report{public string mode="player-body",source="NativeWindowsFramebuffer",error="",stopReason="";public bool complete;public int audioSamples,callbackCount;public Capture[] captures;}
        private string directory;private double started;private bool finished;private readonly List<Capture> captures=new List<Capture>();private readonly HashSet<string> seen=new HashSet<string>();
        public static void Install(GameObject owner)
        {
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            var args=Environment.GetCommandLineArgs();var index=Array.IndexOf(args,"--vr-player-body-probe");if(index<0)return;
            if(Application.isEditor||Application.isBatchMode||owner.GetComponent<AudioListener>()==null)return;
            foreach(var flag in new[]{"--vr-weather-probe","--vr-hud-probe","--vr-hud-trace","--vr-enemy-fire-probe","--vr-player-fire-probe","--vr-combat-audio-probe"})if(Array.IndexOf(args,flag)>=0)throw new ArgumentException("Select one player body / audio / GPU diagnostic.");
            if(index+1>=args.Length||!Path.IsPathRooted(args[index+1]))throw new ArgumentException("Player body probe requires a fresh absolute directory.");var path=Path.GetFullPath(args[index+1]);if(Directory.Exists(path)||File.Exists(path))throw new IOException("Player body probe directory exists.");
            Directory.CreateDirectory(path);var p=owner.AddComponent<NativePlayerBodyProbe>();p.directory=path;p.started=Time.realtimeSinceStartupAsDouble;p.StartCoroutine(p.Observe());
#endif
        }
        private IEnumerator Observe()
        {
            while(!finished){yield return new WaitForEndOfFrame();try{
                if(File.Exists(Path.Combine(directory,"finish.request"))){Finish(true,"Explicit diagnostic stop");continue;}
                var request=Path.Combine(directory,"capture.request");if(File.Exists(request)){
                    string name;using(var stream=new FileStream(request,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var reader=new StreamReader(stream))name=reader.ReadToEnd().Trim();
                    if(!Regex.IsMatch(name,"^[a-z0-9-]{1,48}$"))throw new ArgumentException("Invalid local capture label.");
                    if(!seen.Contains(name)){if(captures.Count>=8)throw new InvalidOperationException("Eight frame limit reached.");var scene=CombatAuthority.Instance?.GetComponent<SceneAuthority>();
                        if(scene!=null){var rows=new List<PlayerBodyObservation>();PlayerBodyObservation own=null;foreach(var avatar in FindObjectsByType<NetworkAvatar>(FindObjectsSortMode.None)){var r=avatar.ObservePlayerBody();if(r!=null)rows.Add(r);var local=avatar.ObserveFirstPersonBody();if(local!=null)own=local;}var ready=name!="walking";foreach(var row in rows)if(row.visible&&row.walking&&Math.Abs(row.stride)>.5f)ready=true;if((rows.Count>0||own!=null)&&ready){Save(name,scene.Phase.Value.ToString(),rows.ToArray(),own);seen.Add(name);}}}
                }
                if(Time.realtimeSinceStartupAsDouble-started>600)Finish(false,"Duration limit");
            }catch(Exception e){Finish(false,e.GetType().Name+": "+e.Message);}}
        }
        private void Save(string name,string phase,PlayerBodyObservation[] rows,PlayerBodyObservation own)
        {
            if((long)Screen.width*Screen.height>9000000)throw new InvalidOperationException("Framebuffer exceeds diagnostic limit.");var texture=new Texture2D(Screen.width,Screen.height,TextureFormat.RGB24,false);
            try{texture.ReadPixels(new Rect(0,0,Screen.width,Screen.height),0,0);texture.Apply();File.WriteAllBytes(Path.Combine(directory,name+".png"),texture.EncodeToPNG());captures.Add(new Capture{file=name+".png",phase=phase,players=rows,firstPerson=own});Write(false,"");}finally{Destroy(texture);}
        }
        private void Write(bool complete,string reason)=>File.WriteAllText(Path.Combine(directory,finished?"report.json":"status.json"),JsonUtility.ToJson(new Report{complete=complete,error=complete?"":reason,stopReason=reason,captures=captures.ToArray()},true));
        private void Finish(bool complete,string reason){if(finished)return;finished=true;Write(complete,reason);}
        private void OnDestroy(){if(directory!=null&&!finished)Finish(false,"Owner despawned before diagnostic finish");}
    }
}
