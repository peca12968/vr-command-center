using System;
using System.Collections.Generic;
using Unity.Collections;
using Unity.Netcode;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    public struct CombatActorState : INetworkSerializable, IEquatable<CombatActorState>
    {
        public FixedString64Bytes id;
        public Vector3 position;
        public int room, health, magazine, reserve;
        public bool enemy, connected, reloading;
        public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T : IReaderWriter
        {
            serializer.SerializeValue(ref id); serializer.SerializeValue(ref position); serializer.SerializeValue(ref room);
            serializer.SerializeValue(ref health); serializer.SerializeValue(ref magazine); serializer.SerializeValue(ref reserve);
            serializer.SerializeValue(ref enemy); serializer.SerializeValue(ref connected); serializer.SerializeValue(ref reloading);
        }
        public bool Equals(CombatActorState other) => id.Equals(other.id) && position == other.position && room == other.room
            && health == other.health && magazine == other.magazine && reserve == other.reserve && enemy == other.enemy
            && connected == other.connected && reloading == other.reloading;
    }
    public struct CombatPropState : INetworkSerializable, IEquatable<CombatPropState>
    {
        public FixedString64Bytes id;
        public Vector3 center, half;
        public float yaw;
        public bool barrel;
        public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T : IReaderWriter
        {
            serializer.SerializeValue(ref id); serializer.SerializeValue(ref center); serializer.SerializeValue(ref half);
            serializer.SerializeValue(ref yaw); serializer.SerializeValue(ref barrel);
        }
        public bool Equals(CombatPropState other) => id.Equals(other.id) && center == other.center && half == other.half
            && yaw.Equals(other.yaw) && barrel == other.barrel;
    }

    // Server owns gameplay. NetworkLists are read-only on clients and include their initial state for late joiners.
    public sealed class CombatAuthority : NetworkBehaviour
    {
        public static CombatAuthority Instance { get; private set; }
        public NetworkList<CombatActorState> Actors;
        public NetworkList<CombatPropState> Props;
        public NetworkVariable<bool> Ready = new NetworkVariable<bool>(false);
        private readonly ArenaSession session = new ArenaSession();
        private readonly Dictionary<string, GameObject> propViews = new Dictionary<string, GameObject>();
        private readonly Dictionary<string, GameObject> enemyViews = new Dictionary<string, GameObject>();
        private Material sand, steel, enemy;
        private float accumulator, nextPublish;
        private double lastManagement = double.NegativeInfinity;
        private bool geometryDirty = true, geometryPublished, serverReady;
        private long observedSequence;
        private bool journalFault;
        public TelemetryOutbox Outbox { get; private set; }

        public void InitializeTelemetry(string path, Guid sessionId, string origin)
        {
            Outbox = TelemetryOutbox.OpenFile(path, sessionId, origin);
            if (Outbox.LastSequence != 0 || Outbox.Complete)
            { Outbox.Dispose(); Outbox = null; throw new InvalidOperationException("Recover the previous telemetry journal before restarting this world."); }
            serverReady = false;
        }
        public void TelemetryFault()
        { journalFault = true; Suspend(); Debug.LogError("Telemetry persistence or delivery failed. Combat paused; recover the journal."); }
        private bool Capture()
        {
            if (journalFault) return false;
            if (Outbox == null || session.World == null) return true;
            try { Outbox.Capture(session.World, observedSequence); return true; }
            catch (Exception exception) when (exception is System.IO.IOException || exception is System.IO.InvalidDataException || exception is UnauthorizedAccessException || exception is InvalidOperationException || exception is ArgumentException)
            { TelemetryFault(); return false; }
        }

        private void Awake() { Actors = new NetworkList<CombatActorState>(); Props = new NetworkList<CombatPropState>(); }
        public override void OnNetworkSpawn()
        {
            Instance = this;
            Props.OnListChanged += GeometryChanged;
            sand = Material(new Color(.58f, .51f, .29f)); steel = Material(new Color(.25f, .35f, .34f)); enemy = Material(new Color(.8f, .25f, .15f));
            if (IsServer) { Ready.Value = serverReady; Publish(); }
        }
        private void GeometryChanged(NetworkListEvent<CombatPropState> change) { geometryDirty = true; }
        private static Material Material(Color color)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            return new Material(shader) { color = color };
        }
        public void ApplyManagement(ManagementSnapshot snapshot)
        {
            if (!Capture()) throw new InvalidOperationException("Telemetry is faulted.");
            session.Apply(snapshot); observedSequence = snapshot.sequence;
            if (session.World.Phase == WorldPhase.Ended && Outbox != null)
            {
                try { Outbox.Finish(session.World); }
                catch (Exception exception) when (exception is System.IO.IOException || exception is System.IO.InvalidDataException || exception is UnauthorizedAccessException)
                { TelemetryFault(); throw new InvalidOperationException("Telemetry completion could not be persisted.", exception); }
            }
            lastManagement = Time.realtimeSinceStartupAsDouble; serverReady = true;
            if (IsSpawned && IsServer) { Ready.Value = true; Publish(); }
        }
        public void Suspend()
        {
            session.Suspend(); serverReady = false;
            if (IsSpawned && IsServer) Ready.Value = false;
        }
        public bool Bind(ulong client, TicketApproval admission) => serverReady && Guid.TryParse(admission.playerId, out var id)
            && session.Connect(client, id, admission.roomId, admission.seat);
        public void Unbind(ulong client) => session.Disconnect(client);
        private static Vec3 Vector(Vector3 value) => new Vec3(value.x, value.y, value.z);
        private static Vector3 Vector(Vec3 value) => new Vector3(value.X, value.Y, value.Z);
        public bool AcceptPose(ulong client, AvatarPose pose, Vector3 root)
        {
            if (!IsServer || !serverReady || !pose.Valid()) return false;
            var forward = pose.rightRotation * Vector3.forward;
            return session.Pose(client, Vector(root + pose.head), Vector(root + pose.right + forward * .15f), Vector(forward.normalized), Time.realtimeSinceStartupAsDouble);
        }
        public bool Weapon(ulong client, ulong input, bool reload, AvatarPose pose, Vector3 root)
        {
            if (Outbox == null || journalFault || !AcceptPose(client, pose, root)) return false;
            var accepted = session.Weapon(client, input, reload, Time.realtimeSinceStartupAsDouble);
            return Capture() && accepted;
        }
        public bool Player(string id, out CombatActorState state)
        {
            if (Actors != null) for (var index = 0; index < Actors.Count; index++)
                if (!Actors[index].enemy && Actors[index].id.ToString() == id) { state = Actors[index]; return true; }
            state = default; return false;
        }
        private void Update()
        {
            if (!IsSpawned) return;
            if (IsServer && session.World != null)
            {
                if (Time.realtimeSinceStartupAsDouble - lastManagement > 1.5)
                {
                    Suspend(); VenueBootstrap.Instance?.sceneAuthority.SuspendForManagementLoss();
                }
                accumulator += Mathf.Min(Time.unscaledDeltaTime, .2f);
                while (accumulator >= ArenaWorld.TickSeconds) { accumulator -= ArenaWorld.TickSeconds; session.Tick(Time.realtimeSinceStartupAsDouble); if (!Capture()) break; }
                if (!journalFault && Time.unscaledTime >= nextPublish) { nextPublish = Time.unscaledTime + .1f; Publish(); }
            }
            Draw();
        }
        private void Publish()
        {
            if (!IsSpawned || !IsServer || session.World == null) return;
            if (!geometryPublished)
            {
                geometryPublished = true;
                Props.Clear();
                foreach (var prop in session.Props) Props.Add(new CombatPropState { id = prop.Id.ToString("D"), center = Vector(prop.Center), half = Vector(prop.HalfSize), yaw = prop.Yaw, barrel = prop.Kind == PropKind.Barrel });
            }
            var frame = session.World.Snapshot();
            var actors = new List<CombatActorState>();
            foreach (var player in frame.Players) actors.Add(new CombatActorState { id = player.Id.ToString("D"), room = player.RoomId, position = Vector(player.Head),
                health = player.Health, magazine = player.Magazine, reserve = player.Reserve, connected = player.Connected, reloading = player.Reloading });
            foreach (var npc in frame.Enemies) actors.Add(new CombatActorState { id = npc.Id.ToString("D"), room = npc.RoomId, position = Vector(npc.Feet), health = npc.Health, enemy = true, connected = true });
            for (var index = 0; index < actors.Count; index++)
                if (index >= Actors.Count) Actors.Add(actors[index]); else if (!Actors[index].Equals(actors[index])) Actors[index] = actors[index];
            while (Actors.Count > actors.Count) Actors.RemoveAt(Actors.Count - 1);
        }
        private void Draw()
        {
            if (geometryDirty)
            {
                geometryDirty = false;
                foreach (var view in propViews.Values) Destroy(view);
                propViews.Clear();
                for (var index = 0; index < Props.Count; index++)
                {
                    var prop = Props[index]; var view = Primitive("Mission " + (prop.barrel ? "Barrel" : "Sandbag"), PrimitiveType.Cube, prop.barrel ? steel : sand);
                    view.transform.position = prop.center; view.transform.rotation = Quaternion.Euler(0, prop.yaw, 0); view.transform.localScale = prop.half * 2;
                    propViews.Add(prop.id.ToString(), view);
                }
            }
            var live = new HashSet<string>();
            for (var index = 0; index < Actors.Count; index++)
            {
                var actor = Actors[index]; if (!actor.enemy) continue;
                var id = actor.id.ToString(); live.Add(id);
                if (!enemyViews.TryGetValue(id, out var view))
                {
                    view = Primitive("Enemy " + id, PrimitiveType.Capsule, enemy); view.transform.localScale = new Vector3(.6f, .9f, .6f);
                    view.transform.position = actor.position + Vector3.up * .9f; enemyViews.Add(id, view);
                }
                view.SetActive(actor.health > 0);
                view.transform.position = Vector3.Lerp(view.transform.position, actor.position + Vector3.up * .9f, 1 - Mathf.Exp(-20 * Time.unscaledDeltaTime));
            }
            foreach (var id in new List<string>(enemyViews.Keys)) if (!live.Contains(id)) { Destroy(enemyViews[id]); enemyViews.Remove(id); }
        }
        private static GameObject Primitive(string name, PrimitiveType type, Material material)
        {
            var view = GameObject.CreatePrimitive(type); view.name = name; view.GetComponent<Renderer>().sharedMaterial = material;
            Destroy(view.GetComponent<Collider>()); return view;
        }
        public override void OnNetworkDespawn()
        {
            Props.OnListChanged -= GeometryChanged;
            foreach (var view in propViews.Values) Destroy(view); foreach (var view in enemyViews.Values) Destroy(view);
            propViews.Clear(); enemyViews.Clear(); geometryDirty = true; geometryPublished = false;
            Destroy(sand); Destroy(steel); Destroy(enemy);
            if (Instance == this) Instance = null;
        }
    }
}
