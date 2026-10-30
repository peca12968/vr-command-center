using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using UnityEngine;

namespace VrCommand.Unity
{
    // Explicit development evidence from THIS AudioListener mix. No microphone,
    // OS loopback, GPU, pose or weapon injection. Never installed by default.
    public sealed class NativeCombatAudioProbe : MonoBehaviour
    {
        [Serializable] public sealed class Window {public double seconds,rms;public float peak;public int samples;}
        [Serializable] public sealed class Cue {public double seconds;public CombatSoundObservation shot;}
        [Serializable] public sealed class Report
        {public string mode="combat-audio",source="NativeWindowsAudioListener",error="",stopReason="";public bool complete,truncated,formatChanged;public int sampleRate,channels,audioSamples,callbackCount;public Window[] audio;public Cue[] cues;}
        private static NativeCombatAudioProbe current;
        private readonly object gate=new object();
        private readonly Stopwatch clock=new Stopwatch();
        private readonly List<Window> audio=new List<Window>();
        private readonly List<Cue> cues=new List<Cue>();
        private string directory;private float[] pcm;private int count,channels,callbacks,rate;private bool recording,finished,truncated,formatChanged;private double next;
        public static void Install(GameObject owner)
        {
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            var args=Environment.GetCommandLineArgs();var index=Array.IndexOf(args,"--vr-combat-audio-probe");if(index<0)return;
            if(Application.isEditor||Application.isBatchMode||owner.GetComponent<AudioListener>()==null)return;
            foreach(var flag in new[]{"--vr-weather-probe","--vr-hud-probe","--vr-hud-trace","--vr-enemy-fire-probe","--vr-player-fire-probe"})
                if(Array.IndexOf(args,flag)>=0)throw new ArgumentException("Select one combat audio / weather / HUD / GPU probe.");
            if(index+1>=args.Length||!Path.IsPathRooted(args[index+1]))throw new ArgumentException("Combat audio probe requires a fresh absolute directory.");
            var path=Path.GetFullPath(args[index+1]);if(Directory.Exists(path)||File.Exists(path))throw new IOException("Combat audio probe directory exists.");
            var rate=AudioSettings.outputSampleRate;if(rate<8000||rate>192000)throw new InvalidOperationException("No usable native audio output format.");
            Directory.CreateDirectory(path);var p=owner.AddComponent<NativeCombatAudioProbe>();p.directory=path;p.rate=rate;p.pcm=new float[16000000];p.clock.Start();p.recording=true;current=p;
#endif
        }
        public static void Observe(CombatSoundObservation shot)
        {if(current!=null&&!current.finished){if(current.cues.Count<1024)current.cues.Add(new Cue{seconds=current.clock.Elapsed.TotalSeconds,shot=shot});else current.truncated=true;}}
        private void OnAudioFilterRead(float[] data,int channelCount)
        {
            lock(gate)
            {
                if(!recording||data.Length==0)return;if(channels==0)channels=channelCount;if(channels!=channelCount){formatChanged=true;return;}
                var amount=Math.Min(data.Length,pcm.Length-count);Array.Copy(data,0,pcm,count,amount);count+=amount;callbacks++;
                if(amount<data.Length)truncated=true;
                double sum=0;float peak=0;foreach(var value in data){sum+=value*value;peak=Math.Max(peak,Math.Abs(value));}
                if(audio.Count<12000)audio.Add(new Window{seconds=clock.Elapsed.TotalSeconds,rms=Math.Sqrt(sum/data.Length),peak=peak,samples=data.Length});else truncated=true;
            }
        }
        private void Update()
        {
            if(finished||directory==null)return;
            if(AudioSettings.outputSampleRate!=rate)formatChanged=true;
            if(clock.Elapsed.TotalSeconds>180){Finish(false,"Duration limit");return;}
            if(clock.Elapsed.TotalSeconds<next)return;next=clock.Elapsed.TotalSeconds+.25;
            if(File.Exists(Path.Combine(directory,"finish.request"))){Finish(true,"Explicit local diagnostic stop");return;}
            Write(false,"");
        }
        private Report Snapshot(bool complete,string reason)
        {lock(gate)return new Report{complete=complete&&!truncated&&!formatChanged,truncated=truncated,formatChanged=formatChanged,sampleRate=rate,channels=channels,audioSamples=count,callbackCount=callbacks,stopReason=reason,audio=audio.ToArray(),cues=cues.ToArray()};}
        private void Write(bool complete,string reason)=>File.WriteAllText(Path.Combine(directory,finished?"report.json":"status.json"),JsonUtility.ToJson(Snapshot(complete,reason)));
        private void Finish(bool complete,string reason)
        {
            if(finished)return;lock(gate)recording=false;finished=true;
            using(var writer=new BinaryWriter(File.Create(Path.Combine(directory,"audio.wav"))))
            {writer.Write(System.Text.Encoding.ASCII.GetBytes("RIFF"));writer.Write(36+count*2);writer.Write(System.Text.Encoding.ASCII.GetBytes("WAVEfmt "));writer.Write(16);writer.Write((short)1);writer.Write((short)channels);writer.Write(rate);writer.Write(rate*channels*2);writer.Write((short)(channels*2));writer.Write((short)16);writer.Write(System.Text.Encoding.ASCII.GetBytes("data"));writer.Write(count*2);
                for(var i=0;i<count;i++)writer.Write((short)(Math.Max(-1,Math.Min(1,pcm[i]))*32767));}
            Write(complete,reason);pcm=null;
        }
        private void OnDestroy(){if(directory!=null&&!finished)Finish(false,"Owner despawned before explicit finish");if(current==this)current=null;}
    }
}
