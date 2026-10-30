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
        public Vector3 facing,fireOrigin,fireDirection;
        public long fireSequence,fireTickPlusOne;
        public bool walking;
        public long presentationTick, reloadUntilTick;
        public int room, health, magazine, reserve;
        public bool enemy, connected, reloading;
        public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T : IReaderWriter
        {
            serializer.SerializeValue(ref id); serializer.SerializeValue(ref position); serializer.SerializeValue(ref room);
            serializer.SerializeValue(ref health); serializer.SerializeValue(ref magazine); serializer.SerializeValue(ref reserve);
            serializer.SerializeValue(ref enemy); serializer.SerializeValue(ref connected); serializer.SerializeValue(ref reloading);
            serializer.SerializeValue(ref facing); serializer.SerializeValue(ref walking); serializer.SerializeValue(ref presentationTick); serializer.SerializeValue(ref reloadUntilTick);
            serializer.SerializeValue(ref fireSequence);serializer.SerializeValue(ref fireTickPlusOne);serializer.SerializeValue(ref fireOrigin);serializer.SerializeValue(ref fireDirection);
        }
        public bool Equals(CombatActorState other) => id.Equals(other.id) && position == other.position && room == other.room
            && health == other.health && magazine == other.magazine && reserve == other.reserve && enemy == other.enemy
            && connected == other.connected && reloading == other.reloading && facing == other.facing && walking == other.walking && presentationTick == other.presentationTick && reloadUntilTick == other.reloadUntilTick && fireSequence==other.fireSequence && fireTickPlusOne==other.fireTickPlusOne && fireOrigin==other.fireOrigin && fireDirection==other.fireDirection;
    }
    public struct CombatPropState : INetworkSerializable, IEquatable<CombatPropState>
    {
        public FixedString64Bytes id;
        public int room;
        public Vector3 center, half;
        public float yaw;
        public bool barrel;
        public void NetworkSerialize<T>(BufferSerializer<T> serializer) where T : IReaderWriter
        {
            serializer.SerializeValue(ref id); serializer.SerializeValue(ref room); serializer.SerializeValue(ref center); serializer.SerializeValue(ref half);
            serializer.SerializeValue(ref yaw); serializer.SerializeValue(ref barrel);
        }
        public bool Equals(CombatPropState other) => id.Equals(other.id) && room == other.room && center == other.center && half == other.half
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
        private readonly Dictionary<string, EnemyFireView> enemyViews = new Dictionary<string, EnemyFireView>();
        private EnemyFireModels enemies;
        private FieldPropModels fieldProps;
        private float accumulator, nextPublish;
        private double lastManagement = double.NegativeInfinity;
        private bool geometryDirty = true, geometryPublished, serverReady;
        private long observedSequence;
        private bool journalFault;
        public TelemetryOutbox Outbox { get; private set; }
        public WorldOutbox Recording { get; private set; }
        private ManagementSnapshot management;
        private double recordingStart, nextRecording;
        private bool managementSuspended;
        private sealed class AcceptedRig { internal ulong Connection; internal RecordedRig Rig; }
        private readonly Dictionary<Guid, AcceptedRig> rigs = new Dictionary<Guid, AcceptedRig>();
        private readonly DesktopResumeCache desktopResume = new DesktopResumeCache();
        private readonly Dictionary<int, ArenaWalkSurface> walkSurfaces = new Dictionary<int, ArenaWalkSurface>();

        public void InitializeRecording(string path)
        {
            if (Outbox == null || management == null || session.World.Phase != WorldPhase.Preparing) throw new InvalidOperationException("Initialize a preparing world and combat source first.");
            recordingStart = Time.realtimeSinceStartupAsDouble;
            var header = WorldRecordingHeader.Create(Guid.Parse(management.id), Outbox.StreamId, Outbox.Origin, management.roomIds, session.Props,
                DateTimeOffset.UtcNow.ToString("O", System.Globalization.CultureInfo.InvariantCulture), assetSet: WorldAssetSets.PlayerFire, enemyPresentationVersion: EnemyPresentation.Version, weaponPresentationVersion: WeaponPresentation.Version, enemyFireVersion: EnemyFirePresentation.Version, playerFireVersion: PlayerFirePresentation.Version);
            Recording = WorldOutbox.Create(path, header, new UnityWorldCodec());
            if (!CaptureWorld(true)) throw new InvalidOperationException("Initial world frame could not be saved.");
        }
        private bool CaptureWorld(bool force = false)
        {
            if (journalFault) return false;
            if (Recording == null || Recording.Complete || management == null) return true;
            var now = Time.realtimeSinceStartupAsDouble;
            if (!force && now < nextRecording) return true;
            try
            {
                var packet = WorldRecordingPacket.Capture(session.World, Recording.LastSequence + 1,
                    Recording.LastSequence == 0 ? 0 : (long)((now - recordingStart) * 1000), observedSequence, Outbox.LastSequence,
                    Recording.ThroughWorldSequence, RecordedRigFor, management.environment.weather, management.environment.lightning, managementSuspended, EnemyPresentation.Version, WeaponPresentation.Version, EnemyFirePresentation.Version, PlayerFirePresentation.Version);
                Recording.Append(packet); nextRecording = now + .1;
                if (session.World.Phase == WorldPhase.Ended) Recording.Finish();
                return true;
            }
            catch (Exception exception) when (exception is System.IO.IOException || exception is ArgumentException || exception is InvalidOperationException || exception is UnauthorizedAccessException)
            { TelemetryFault(); return false; }
        }
        private RecordedRig RecordedRigFor(Guid player)
        {
            if (!session.World.PlayerSnapshot(player).Connected) return new RecordedRig();
            if (!rigs.TryGetValue(player, out var accepted)) throw new InvalidOperationException("Connected world body has no accepted rig.");
            return accepted.Rig;
        }

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
            fieldProps = new FieldPropModels(); enemies = new EnemyFireModels();
            if (IsServer) { Ready.Value = serverReady; Publish(); }
        }
        private void GeometryChanged(NetworkListEvent<CombatPropState> change) { geometryDirty = true; walkSurfaces.Clear(); }
        public void ApplyManagement(ManagementSnapshot snapshot)
        {
            if (!Capture()) throw new InvalidOperationException("Telemetry is faulted.");
            var changed = management == null || snapshot.sequence != observedSequence || managementSuspended;
            if (changed && !CaptureWorld(true)) throw new InvalidOperationException("World recording is faulted.");
            session.Apply(snapshot); desktopResume.Retain(snapshot.players); observedSequence = snapshot.sequence;
            management = snapshot; managementSuspended = false;
            if (session.World.Phase == WorldPhase.Ended && Outbox != null)
            {
                try { Outbox.Finish(session.World); }
                catch (Exception exception) when (exception is System.IO.IOException || exception is System.IO.InvalidDataException || exception is UnauthorizedAccessException)
                { TelemetryFault(); throw new InvalidOperationException("Telemetry completion could not be persisted.", exception); }
            }
            if (changed && !CaptureWorld(true)) throw new InvalidOperationException("World recording is faulted.");
            lastManagement = Time.realtimeSinceStartupAsDouble; serverReady = true;
            if (IsSpawned && IsServer) { Ready.Value = true; Publish(); }
        }
        public void Suspend()
        {
            var first = !managementSuspended; managementSuspended = true; session.Suspend(); serverReady = false;
            if (first && !journalFault) CaptureWorld(true);
            if (IsSpawned && IsServer) Ready.Value = false;
        }
        public bool Bind(ulong client, TicketApproval admission) => serverReady && Guid.TryParse(admission.playerId, out var id)
            && Guid.TryParse(admission.admissionId, out var epoch) && session.Connect(client, id, admission.roomId, admission.seat, epoch);
        public void Unbind(ulong client)
        {
            session.Disconnect(client);
            foreach (var id in new List<Guid>(rigs.Keys)) if (rigs[id].Connection == client) rigs.Remove(id);
        }
        private static Vec3 Vector(Vector3 value) => new Vec3(value.x, value.y, value.z);
        private static Vector3 Vector(Vec3 value) => new Vector3(value.X, value.Y, value.Z);
        public AvatarPose DesktopSpawnPose(ulong client)
        {
            var admission = VenueBootstrap.Instance?.Admission(client);
            if (admission != null && Guid.TryParse(admission.playerId, out var player) && Guid.TryParse(admission.admissionId, out var epoch)
                && desktopResume.TryRestore(player, epoch, out var saved)) return saved;
            return new AvatarPose { source = 1, head = new Vector3(0, 1.65f, 0), left = new Vector3(-.3f, 1.3f, .4f), right = new Vector3(0, 1.65f, 0) + DesktopPreviewControls.RightOffset,
                headRotation = Quaternion.identity, leftRotation = Quaternion.identity, rightRotation = Quaternion.identity };
        }
        public bool AcceptPose(ulong client, AvatarPose pose, Vector3 root, Quaternion rotation)
        {
            if (!IsServer || !serverReady || !pose.Valid()) return false;
            var admission = VenueBootstrap.Instance?.Admission(client);
            if (admission == null || !Guid.TryParse(admission.playerId, out var player)) return false;
            var forward = rotation * pose.rightRotation * Vector3.forward;
            if (!session.Pose(client, Vector(root + rotation * pose.head), Vector(root + rotation * pose.right + forward * AvatarPose.MuzzleOffset), Vector(forward.normalized), Time.realtimeSinceStartupAsDouble)) return false;
            desktopResume.Remember(player, Guid.Parse(admission.admissionId), pose);
            rigs[player] = new AcceptedRig { Connection = client, Rig = new RecordedRig { kind = pose.source == 2 ? "Tracked" : "Simulated",
                left = new RecordedVector(Vector(root + rotation * pose.left)), right = new RecordedVector(Vector(root + rotation * pose.right)),
                headRotation = Rotation(rotation * pose.headRotation), leftRotation = Rotation(rotation * pose.leftRotation), rightRotation = Rotation(rotation * pose.rightRotation) } };
            return true;
        }
        private static RecordedRotation Rotation(Quaternion value) => new RecordedRotation { x = value.x, y = value.y, z = value.z, w = value.w };
        public bool Weapon(ulong client, ulong input, bool reload, AvatarPose pose, Vector3 root, Quaternion rotation)
        {
            if (Outbox == null || Recording == null || journalFault || !AcceptPose(client, pose, root, rotation)) return false;
            var accepted = session.Weapon(client, input, reload, Time.realtimeSinceStartupAsDouble);
            return Capture() && accepted;
        }
        public bool Player(string id, out CombatActorState state)
        {
            if (Actors != null) for (var index = 0; index < Actors.Count; index++)
                if (!Actors[index].enemy && Actors[index].id.ToString() == id) { state = Actors[index]; return true; }
            state = default; return false;
        }
        public bool ConstrainDesktop(int room, Vector3 from, Vector3 desired, out Vector3 result)
        {
            result = from;
            if (!IsSpawned || !Ready.Value || room < 1 || room > 5) return false;
            if (!walkSurfaces.TryGetValue(room, out var surface))
            {
                var geometry = new List<WorldProp>();
                foreach (var prop in Props)
                {
                    if (prop.room != room) continue;
                    var item = new WorldProp(Guid.Parse(prop.id.ToString()), room, prop.barrel ? PropKind.Barrel : PropKind.Sandbag,
                        Vector(prop.center - Vector3.up * prop.half.y), prop.yaw);
                    if (Vector3.Distance(Vector(item.HalfSize), prop.half) > .0001f) return false;
                    geometry.Add(item);
                }
                surface = new ArenaWalkSurface(Vector(VenueBootstrap.RoomOrigin(room)), geometry.ToArray());
                walkSurfaces[room] = surface;
            }
            result = Vector(surface.Constrain(Vector(from), Vector(desired))); return true;
        }
        // Display prediction only: the server still casts its own accepted weapon intent.
        public Vector3 PreviewAimPoint(Vector3 origin, Vector3 forward, string ignorePlayer)
        {
            var distance = 30f;
            var start = Vector(origin); var direction = Vector(forward);
            foreach (var prop in Props) Consider(prop.center, prop.half, prop.yaw);
            foreach (var actor in Actors)
            {
                if (actor.health <= 0 || !actor.connected || actor.id.ToString() == ignorePlayer) continue;
                var height = actor.enemy ? 1.8f : actor.position.y + .15f;
                Consider(new Vector3(actor.position.x, height / 2, actor.position.z), new Vector3(actor.enemy ? .3f : .25f, height / 2, actor.enemy ? .3f : .25f), 0);
            }
            return origin + forward * distance;
            void Consider(Vector3 center, Vector3 half, float yaw)
            {
                var hit = ArenaGeometry.RayBox(start, direction, Vector(center), Vector(half), yaw, distance);
                if (hit.HasValue) distance = Mathf.Min(distance, hit.Value);
            }
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
                if (!journalFault && CaptureWorld() && Time.unscaledTime >= nextPublish) { nextPublish = Time.unscaledTime + .1f; Publish(); }
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
                foreach (var prop in session.Props) Props.Add(new CombatPropState { id = prop.Id.ToString("D"), room = prop.RoomId, center = Vector(prop.Center), half = Vector(prop.HalfSize), yaw = prop.Yaw, barrel = prop.Kind == PropKind.Barrel });
            }
            var frame = session.World.Snapshot();
            GetComponent<SceneAuthority>()?.PublishTick(frame.Tick, frame.Phase.ToString());
            var actors = new List<CombatActorState>();
            foreach (var player in frame.Players) actors.Add(new CombatActorState { id = player.Id.ToString("D"), room = player.RoomId, position = Vector(player.Head),
                health = player.Health, magazine = player.Magazine, reserve = player.Reserve, connected = player.Connected, reloading = player.Reloading, presentationTick = frame.Tick, reloadUntilTick = player.ReloadUntilTick, fireSequence=player.Fire.Sequence,fireTickPlusOne=player.Fire.TickPlusOne,fireOrigin=Vector(player.Fire.Origin),fireDirection=Vector(player.Fire.Direction) });
            foreach (var npc in frame.Enemies) actors.Add(new CombatActorState { id = npc.Id.ToString("D"), room = npc.RoomId, position = Vector(npc.Feet), health = npc.Health, enemy = true, connected = true,
                facing = Vector(npc.Forward), walking = npc.Walking, presentationTick = frame.Tick,fireSequence=npc.Fire.Sequence,fireTickPlusOne=npc.Fire.TickPlusOne,fireOrigin=Vector(npc.Fire.Origin),fireDirection=Vector(npc.Fire.Direction) });
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
                    var prop = Props[index]; var view = fieldProps.Create(prop.barrel);
                    view.transform.position = prop.center - Vector3.up * prop.half.y; view.transform.rotation = Quaternion.Euler(0, prop.yaw, 0);
                    var original = prop.barrel ? new Vector3(.35f, .6f, .35f) : new Vector3(1, .45f, .35f);
                    view.transform.localScale = new Vector3(prop.half.x / original.x, prop.half.y / original.y, prop.half.z / original.z);
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
                    view = enemies.Create(); view.Root.name = "Opponent " + id;
                    view.Root.transform.position = actor.position; enemyViews.Add(id, view);
                }
                view.Root.SetActive(actor.health > 0);
                view.Root.transform.position = actor.position;
                view.Apply(Vector(actor.facing), actor.walking, actor.presentationTick, actor.health,new EnemyFireState(actor.fireSequence,actor.fireTickPlusOne,Vector(actor.fireOrigin),Vector(actor.fireDirection)));
            }
            foreach (var id in new List<string>(enemyViews.Keys)) if (!live.Contains(id)) { Destroy(enemyViews[id].Root); enemyViews.Remove(id); }
        }
        internal EnemyFireObservation[] ObserveEnemyFire()
        {
            var rows=new List<EnemyFireObservation>();
            foreach(var pair in enemyViews)
            {
                var view=pair.Value;var fire=view.AppliedFire;
                rows.Add(new EnemyFireObservation{id=pair.Key,tick=view.AppliedTick,fireSequence=fire.Sequence,fireTickPlusOne=fire.TickPlusOne,
                    acceptedOrigin=Vector(fire.Origin),acceptedDirection=Vector(fire.Direction),visible=view.Root.activeInHierarchy && view.Flash.gameObject.activeInHierarchy,
                    recoil=-view.RecoilVisual.localPosition.z,gun=view.Body.Gun.position,flashOrigin=view.Flash.position,flashDirection=view.Flash.forward});
            }
            return rows.ToArray();
        }
        public override void OnNetworkDespawn()
        {
            Props.OnListChanged -= GeometryChanged;
            foreach (var view in propViews.Values) Destroy(view); foreach (var view in enemyViews.Values) Destroy(view.Root);
            propViews.Clear(); enemyViews.Clear(); geometryDirty = true; geometryPublished = false;
            fieldProps?.Dispose(); fieldProps = null; enemies?.Dispose(); enemies = null;
            if (Instance == this) Instance = null;
        }
    }
}
