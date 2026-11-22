using System.Text.Json.Serialization;

namespace VrCommand.Core;

public record RoomHardwareSignal(Guid EventId, long EventSequence, long StreamSequence, long ObservedSequence,
    Guid ReportId, CombatKind Kind, Guid PlayerId, Guid AdmissionId, int Seat, int Damage, DateTimeOffset AcceptedAtUtc);

public record RoomHardwareSeat(Guid PlayerId, Guid AdmissionId, [property: JsonRequired] int Seat);
public record VenueHardwareRoom(int RoomId, Guid SessionId, long SessionSequence, RoomHardwareSeat[] Bindings);
public record VenueHardwareBindings(int Version, SessionMode Mode, VenueHardwareRoom[] Rooms);
public record CurrentRoomHardwareEnvironment(int Version, int RoomId, RoomHardwareEnvironment? Session);
public record RoomHardwareEnvironment(int Version, Guid SessionId, int RoomId, SessionState State,
    long ThroughSequence, long PhaseSinceSequence, long EnvironmentSinceSequence, EnvironmentSettings? Environment);

public record RoomHardwareFeedback(int Version, Guid SessionId, int RoomId, Guid? StreamId, CombatOrigin? CombatOrigin,
    SessionState State, long ThroughSequence, long? RunningSinceSequence, DateTimeOffset CheckedAtUtc,
    string? ResetReason, RoomHardwareSignal[] Signals)
{
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public RoomHardwareSeat[]? Bindings { get; init; }
}

public sealed partial class SessionManager
{
    private const int MaxHardwareFeedbackEvents = 256;
    private static readonly TimeSpan HardwareFeedbackAcceptedAge = TimeSpan.FromSeconds(2);

    public VenueHardwareBindings ReadVenueHardwareBindings(OperatorIdentity actor)
    {
        RequireVenueMaster(actor);
        var sessions = List(false, actor);
        var mode = sessions.FirstOrDefault()?.Mode;
        var rooms = sessions.SelectMany(session => session.RoomIds.Select(room =>
                new VenueHardwareRoom(room, session.Id, session.Sequence, HardwareSeats(session, room))))
            .OrderBy(room => room.RoomId).ToArray();
        if (mode is null || sessions.Length != (mode == SessionMode.Linked ? 1 : RoomCount)
            || sessions.Any(session => session.Mode != mode)
            || !rooms.Select(room => room.RoomId).SequenceEqual(Enumerable.Range(1, RoomCount)))
            throw new InvalidOperationException("Five current rooms must belong to one linked or five independent sessions.");
        return new(1, mode.Value, rooms);
    }

    private static RoomHardwareSeat[] HardwareSeats(SessionView session, int roomId) => session.Players.Where(player => player.RoomId == roomId)
        .OrderBy(player => player.Seat).Select(player => new RoomHardwareSeat(player.Id, player.AdmissionId, player.Seat)).ToArray();

    public RoomHardwareEnvironment ReadHardwareEnvironment(Guid id, int roomId, OperatorIdentity actor)
    {
        lock (gate)
        {
            var history = Find(id);
            var session = history.View;
            AccessPolicy.Player(actor, session, roomId);
            if (!session.RoomIds.Contains(roomId)) throw new ArgumentException("Room is outside this session.");
            return HardwareEnvironment(history, roomId);
        }
    }

    public CurrentRoomHardwareEnvironment ReadCurrentHardwareEnvironment(int roomId, OperatorIdentity actor)
    {
        if (roomId is < 1 or > RoomCount) throw new ArgumentException("Room number is outside the venue.");
        AccessPolicy.Read(actor, [roomId]);
        if (actor.Role == OperatorRole.GameServer) throw new AccessDeniedException("Room hardware requires a controller.");
        lock (gate)
        {
            var current = Active().SingleOrDefault(session => session.RoomIds.Contains(roomId));
            return new(1, roomId, current is null ? null : HardwareEnvironment(Find(current.Id), roomId));
        }
    }

    private static RoomHardwareEnvironment HardwareEnvironment(History history, int roomId)
    {
        var session = history.View;
        return new(1, session.Id, roomId, session.State, session.Sequence, history.PhaseSinceSequence,
            history.EnvironmentSinceSequence, session.State == SessionState.Running ? session.Environment : null);
    }

    public RoomHardwareFeedback ReadHardwareFeedback(Guid id, int roomId, long? after, OperatorIdentity actor, bool includeBindings = false)
    {
        if (after < 0) throw new ArgumentException("Use a non-negative hardware feedback cursor.");
        lock (gate)
        {
            var history = Find(id);
            var session = history.View;
            AccessPolicy.Player(actor, session, roomId);
            if (!session.RoomIds.Contains(roomId)) throw new ArgumentException("Room is outside this session.");
            if (after > session.Sequence) throw new ArgumentException("Hardware feedback cursor is ahead of this session.");

            var now = clock.GetUtcNow();
            var stream = session.CombatStream;
            var running = session.State == SessionState.Running ? history.PhaseSinceSequence : (long?)null;
            var bindings = includeBindings ? HardwareSeats(session, roomId) : null;
            RoomHardwareFeedback Page(string? reset, RoomHardwareSignal[] signals) => new(includeBindings ? 2 : 1, id, roomId, stream?.StreamId,
                stream?.Origin, session.State, session.Sequence, running, now, reset, signals) { Bindings = bindings };
            // New readers and slow readers take a fresh cursor instead of replaying a backlog as live feedback.
            if (!after.HasValue) return Page("attached", []);
            if (running is null || stream is null || stream.Sealed) return Page("inactive", []);
            if (session.Sequence - after.Value > MaxHardwareFeedbackEvents) return Page("backlog", []);

            var signals = new List<RoomHardwareSignal>();
            for (var index = (int)Math.Max(after.Value, running.Value - 1); index < history.Events.Count; index++)
            {
                var entry = history.Events[index];
                var acceptedAge = now - entry.RecordedAtUtc;
                if (entry.Kind != SessionEventKind.StreamCombatRecorded || acceptedAge < TimeSpan.Zero || acceptedAge >= HardwareFeedbackAcceptedAge)
                    continue;
                var record = entry.Read<StreamCombatRecord>();
                if (record.ObservedSequence < running || record.Report.Kind is not (CombatKind.ShotFired or CombatKind.PlayerDamaged)) continue;
                var player = session.Players.SingleOrDefault(p => p.RoomId == roomId && p.Id == record.Report.PlayerId);
                if (player is null || ObserveAuthority(history.Authority, record.ObservedSequence)?.Players.Any(p =>
                    p.Id == player.Id && p.AdmissionId == player.AdmissionId && p.RoomId == roomId) != true) continue;
                signals.Add(new(entry.EventId, entry.Sequence, record.StreamSequence, record.ObservedSequence, record.Report.ReportId,
                    record.Report.Kind, player.Id, player.AdmissionId, player.Seat, record.Report.Damage, entry.RecordedAtUtc));
            }
            return Page(null, [.. signals]);
        }
    }
}
