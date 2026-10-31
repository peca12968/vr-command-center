using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Threading;
using Unity.Collections;
using Unity.Netcode;
using Unity.Netcode.Transports.UTP;
using UnityEngine;

namespace VrCommand.Unity
{
    // Explicit, bounded local observations only. Never sends messages or changes
    // authority / input / pose / network configuration. No credentials in output.
    public sealed class NativeReplicationProbe : MonoBehaviour
    {
        [Serializable] public sealed class Avatar
        {
            public string playerId;
            public ulong connection;
            public bool owner,accepted;
            public int source;
            public Vector3 head;
        }
        [Serializable] public sealed class Snapshot
        {
            public int request;
            public long utcTicks;
            public double seconds;
            public string role,phase;
            public WeatherObservation presentation;
            public bool listening,ready;
            public int packetQueueCapacity,actorListSerializedBytes;
            public ulong localConnection;
            public Actor[] actors;
            public Avatar[] avatars;
        }
        [Serializable] public sealed class WeatherObservation
        {
            public long tick;
            public int phase,weather,rooms;
            public bool night,lightning;
            public static WeatherObservation From(WeatherState state)=>new WeatherObservation{tick=state.tick,phase=state.phase,
                weather=state.weather,rooms=state.rooms,night=state.night,lightning=state.lightning};
        }
        [Serializable] public sealed class Actor
        {
            public string id;
            public Vector3 position;
            public int room,health,magazine,reserve;
            public bool enemy,connected,reloading;
            public long presentationTick,fireSequence;
        }
        [Serializable] public struct Row
        {
            public long utcTicks,tick,minimumActorTick,maximumActorTick;
            public double seconds;
            public int phase,players,connected,health;
            public bool ready,coherent;
        }
        [Serializable] public struct QueueError
        {
            public long utcTicks,tick;
            public double seconds;
            public int phase;
        }
        [Serializable] public sealed class Report
        {
            public int schemaVersion=1,maximumSeconds=240,maximumRows=4096,maximumErrors=4096;
            public string role,source="NativeLocalReplicatedState",reason;
            public bool complete,truncated;
            public double endedSeconds;
            public Row[] rows;
            public QueueError[] sendQueueErrors;
        }
        private readonly Stopwatch clock=new Stopwatch();
        private readonly List<Row> rows=new List<Row>();
        private readonly List<QueueError> errors=new List<QueueError>();
        private readonly object errorGate=new object();
        private string directory,role;
        private VenueBootstrap owner;
        private double nextCheck;
        private int request,phase=-1;
        private long tick=-1,lastTick=-1;
        private int lastPhase=-1;
        private bool finished,truncated;
        public static void Install(VenueBootstrap owner,string role)
        {
#if UNITY_STANDALONE_WIN && DEVELOPMENT_BUILD
            if(Application.isEditor)return;
            var args=Environment.GetCommandLineArgs();var index=Array.IndexOf(args,"--vr-replication-probe");if(index<0)return;
            if(index+1>=args.Length || !Path.IsPathRooted(args[index+1]))throw new ArgumentException("Replication probe requires a fresh absolute directory.");
            var path=Path.GetFullPath(args[index+1]);if(Directory.Exists(path)||File.Exists(path))throw new IOException("Replication probe directory exists.");
            Directory.CreateDirectory(path);var probe=owner.gameObject.AddComponent<NativeReplicationProbe>();
            probe.directory=path;probe.owner=owner;probe.role=role;probe.clock.Start();
            Application.logMessageReceivedThreaded+=probe.Log;
            probe.Save("ready.json",new Report{role=role,reason="Ready"});
#endif
        }
        private void Log(string message,string stack,LogType type)
        {
            if(message==null || message.IndexOf("send queue full",StringComparison.OrdinalIgnoreCase)<0)return;
            lock(errorGate)
            {
                if(finished)return;
                if(errors.Count>=4096){truncated=true;return;}
                errors.Add(new QueueError{utcTicks=DateTime.UtcNow.Ticks,seconds=clock.Elapsed.TotalSeconds,
                    phase=Volatile.Read(ref phase),tick=Interlocked.Read(ref tick)});
            }
        }
        private void Update()
        {
            if(finished||directory==null)return;
            if(clock.Elapsed.TotalSeconds>=240){Finish(false,"Timeout");return;}
            var scene=owner.sceneAuthority;var combat=owner.combatAuthority;
            if(scene!=null && scene.IsSpawned && combat!=null && combat.IsSpawned)
            {
                var state=scene.Presentation.Value;Volatile.Write(ref phase,state.phase);Interlocked.Exchange(ref tick,state.tick);
                // Capture after NGO updates, at most one row per changed tick / phase.
                // Coherence is evidence, never a reason to hide a bad observation.
                if(lastTick!=state.tick || lastPhase!=state.phase)
                {
                    var row=new Row{utcTicks=DateTime.UtcNow.Ticks,seconds=clock.Elapsed.TotalSeconds,tick=state.tick,phase=state.phase,
                        minimumActorTick=long.MaxValue,maximumActorTick=long.MinValue,ready=combat.Ready.Value};
                    for(var i=0;i<combat.Actors.Count;i++)
                    {
                        var actor=combat.Actors[i];row.minimumActorTick=Math.Min(row.minimumActorTick,actor.presentationTick);
                        row.maximumActorTick=Math.Max(row.maximumActorTick,actor.presentationTick);
                        if(!actor.enemy){row.players++;row.connected+=actor.connected?1:0;row.health+=actor.health;}
                    }
                    row.coherent=combat.Actors.Count>0 && row.minimumActorTick==state.tick && row.maximumActorTick==state.tick;
                    if(rows.Count<4096)rows.Add(row);else truncated=true;
                    lastTick=state.tick;lastPhase=state.phase;
                }
            }
            if(clock.Elapsed.TotalSeconds<nextCheck)return;nextCheck=clock.Elapsed.TotalSeconds+.1;
            if(File.Exists(Path.Combine(directory,"finish.request"))){Finish(true,"Requested");return;}
            var command=Path.Combine(directory,"capture.request");if(!File.Exists(command))return;
            // Reader closes the file before any snapshot output. A partially written
            // integer is ignored, not interpreted as a game command.
            if(!int.TryParse(File.ReadAllText(command),out var number)||number<=request||number>64)return;
            request=number;
            var snapshot=new Snapshot{request=number,utcTicks=DateTime.UtcNow.Ticks,seconds=clock.Elapsed.TotalSeconds,role=role,
                listening=owner.networkManager.IsListening,localConnection=owner.networkManager.LocalClientId,
                phase=scene!=null&&scene.IsSpawned?scene.Phase.Value.ToString():"Unavailable",
                presentation=WeatherObservation.From(scene!=null&&scene.IsSpawned?scene.Presentation.Value:default),
                ready=combat!=null&&combat.IsSpawned&&combat.Ready.Value};
            snapshot.packetQueueCapacity=((UnityTransport)owner.networkManager.NetworkConfig.NetworkTransport).MaxPacketQueueSize;
            if(combat!=null&&combat.IsSpawned)
                using(var writer=new FastBufferWriter(65536,Allocator.Temp))
                {combat.Actors.WriteField(writer);snapshot.actorListSerializedBytes=writer.Length;}
            var actors=new List<Actor>();if(combat!=null&&combat.IsSpawned)for(var i=0;i<combat.Actors.Count;i++)
            {
                var actor=combat.Actors[i];actors.Add(new Actor{id=actor.id.ToString(),position=actor.position,room=actor.room,health=actor.health,
                    magazine=actor.magazine,reserve=actor.reserve,enemy=actor.enemy,connected=actor.connected,reloading=actor.reloading,
                    presentationTick=actor.presentationTick,fireSequence=actor.fireSequence});
            }
            snapshot.actors=actors.ToArray();var avatars=new List<Avatar>();
            foreach(var avatar in FindObjectsByType<NetworkAvatar>(FindObjectsSortMode.None))
                if(avatar.IsSpawned)avatars.Add(new Avatar{playerId=avatar.PlayerId.Value.ToString(),connection=avatar.OwnerClientId,owner=avatar.IsOwner,
                    accepted=avatar.PoseAccepted.Value,source=avatar.Pose.Value.source,head=avatar.transform.TransformPoint(avatar.Pose.Value.head)});
            snapshot.avatars=avatars.ToArray();Save("capture-"+number+".json",snapshot);
        }
        private void Save(string name,object value)
        {
            var path=Path.Combine(directory,name);var temporary=path+".tmp";
            using(var output=new StreamWriter(new FileStream(temporary,FileMode.CreateNew,FileAccess.Write,FileShare.Read)))output.Write(JsonUtility.ToJson(value));
            File.Move(temporary,path); // Every observation has a unique name, no replacement.
        }
        private void Finish(bool complete,string reason)
        {
            QueueError[] captured;
            lock(errorGate){if(finished)return;finished=true;captured=errors.ToArray();}
            Application.logMessageReceivedThreaded-=Log;
            Save("report.json",new Report{role=role,reason=reason,complete=complete&&!truncated,truncated=truncated,
                endedSeconds=clock.Elapsed.TotalSeconds,rows=rows.ToArray(),sendQueueErrors=captured});
        }
        private void OnApplicationQuit(){if(directory!=null)Finish(false,"Application quit");}
        private void OnDestroy(){if(directory!=null)Finish(false,"Owner destroyed");}
    }
}
