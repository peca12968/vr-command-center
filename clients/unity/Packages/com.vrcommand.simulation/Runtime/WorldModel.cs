using System;

namespace VrCommand.Simulation
{
    public enum WorldPhase { Preparing, Running, Paused, Ended }
    public enum AiBehavior { Hold, Patrol, Advance }
    public enum Visibility { Clear, Fog, Storm }
    public enum PropKind { Sandbag, Barrel }
    public enum HitKind { Miss, Cover, Friendly, Enemy }
    public enum WorldEventKind { ShotFired, ShotHit, EnemyEliminated, EnemyShot, PlayerDamaged, ReloadStarted, ReloadCompleted }

    public sealed class WorldProp
    {
        public Guid Id { get; }
        public int RoomId { get; }
        public PropKind Kind { get; }
        public Vec3 Feet { get; }
        public float Yaw { get; }
        public Vec3 HalfSize => Kind == PropKind.Sandbag ? new Vec3(1, .45f, .35f) : new Vec3(.35f, .6f, .35f);
        public Vec3 Center => Feet + new Vec3(0, HalfSize.Y, 0);
        public WorldProp(Guid id, int roomId, PropKind kind, Vec3 feet, float yaw)
        { Id = id; RoomId = roomId; Kind = kind; Feet = feet; Yaw = yaw; }
    }
    public sealed class PlayerFrame
    {
        public Guid Id { get; }
        public int RoomId { get; }
        public Vec3 Head { get; }
        public Vec3 Muzzle { get; }
        public Vec3 Forward { get; }
        public int Health { get; }
        public int Magazine { get; }
        public int Reserve { get; }
        public bool Reloading { get; }
        internal PlayerFrame(Guid id, int room, Vec3 head, Vec3 muzzle, Vec3 forward, int health, int magazine, int reserve, bool reloading)
        { Id = id; RoomId = room; Head = head; Muzzle = muzzle; Forward = forward; Health = health; Magazine = magazine; Reserve = reserve; Reloading = reloading; }
    }
    public sealed class EnemyFrame
    {
        public Guid Id { get; }
        public int RoomId { get; }
        public Vec3 Feet { get; }
        public int Health { get; }
        internal EnemyFrame(Guid id, int room, Vec3 feet, int health) { Id = id; RoomId = room; Feet = feet; Health = health; }
    }
    public sealed class WorldFrame
    {
        public long Tick { get; }
        public WorldPhase Phase { get; }
        public long ThroughSequence { get; }
        public PlayerFrame[] Players { get; }
        public EnemyFrame[] Enemies { get; }
        internal WorldFrame(long tick, WorldPhase phase, long throughSequence, PlayerFrame[] players, EnemyFrame[] enemies)
        { Tick = tick; Phase = phase; ThroughSequence = throughSequence; Players = players; Enemies = enemies; }
    }
    public sealed class WorldEvent
    {
        public long Sequence { get; }
        public Guid EventId { get; }
        public long Tick { get; }
        public WorldEventKind Kind { get; }
        public Guid PlayerId { get; }
        public Guid? ShotId { get; }
        public Guid? EnemyId { get; }
        public int Damage { get; }
        internal WorldEvent(long sequence, long tick, WorldEventKind kind, Guid playerId, Guid? shotId, Guid? enemyId, int damage)
        { Sequence = sequence; EventId = Guid.NewGuid(); Tick = tick; Kind = kind; PlayerId = playerId; ShotId = shotId; EnemyId = enemyId; Damage = damage; }
    }
    public sealed class ShotResult
    {
        public Guid ShotId { get; }
        public Guid PlayerId { get; }
        public HitKind Hit { get; }
        public Guid? TargetId { get; }
        public float Distance { get; }
        public bool Eliminated { get; }
        internal ShotResult(Guid shot, Guid player, HitKind hit, Guid? target, float distance, bool eliminated)
        { ShotId = shot; PlayerId = player; Hit = hit; TargetId = target; Distance = distance; Eliminated = eliminated; }
    }
}
