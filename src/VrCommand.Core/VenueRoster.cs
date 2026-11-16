using System.Text.Json.Serialization;

namespace VrCommand.Core;

public sealed record VenueRosterSeat(Guid SessionId, Guid RequestId, Guid PlayerId, string Name, int RoomId,
    [property: JsonRequired] int Seat, [property: JsonRequired] HeadsetKind Headset);
public sealed record VenueRosterAdmission(Guid SessionId, Guid RequestId, long AppliedAtSequence, Player Player);
public sealed record VenueRosterReceipt(VenueRosterAdmission[] Admissions, bool Duplicate);
public sealed class VenueRosterSeatConflict(int roomId, int seat)
    : InvalidOperationException("The original preparing seat is unavailable.")
{
    public int RoomId { get; } = roomId;
    public int Seat { get; } = seat;
}

public sealed partial class SessionManager
{
    public VenueRosterReceipt JoinVenueRoster(VenueRosterSeat[] seats, OperatorIdentity actor)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Only the master may register venue seats in a batch.");
        if (seats is not { Length: >= 1 and <= MaxPlayers } || seats.Any(seat => seat is null
                || seat.SessionId == Guid.Empty || seat.RequestId == Guid.Empty || seat.PlayerId == Guid.Empty
                || seat.RoomId is < 1 or > RoomCount || seat.Seat is < 0 or >= PlayersPerRoom)
            || seats.Select(seat => seat.RequestId).Distinct().Count() != seats.Length
            || seats.Select(seat => seat.PlayerId).Distinct().Count() != seats.Length
            || seats.Select(seat => (seat.RoomId, seat.Seat)).Distinct().Count() != seats.Length)
            throw new ArgumentException("Provide 1–25 distinct room seats, request IDs and player IDs.");

        lock (gate)
        {
            var previous = seats.Select(seat => Request(seat.RequestId, SessionEventKind.PlayerJoined, actor)).ToArray();
            if (previous.Any(entry => entry is not null))
            {
                if (previous.Any(entry => entry is null) || !seats.Zip(previous, MatchesRosterAdmission).All(matches => matches))
                    throw new InvalidOperationException("Roster retry does not match its original seat admissions.");
                return VenueRosterResult(previous.Select(entry => entry!), duplicate: true);
            }
            if (eventStore is not IAtomicSessionEventStore store)
                throw new InvalidOperationException("Venue roster admission requires a transactional session store.");

            var activePlayers = Active().SelectMany(session => session.Players).Select(player => player.Id).ToHashSet();
            var projected = new Dictionary<Guid, SessionView>();
            var additions = new List<(SessionEvent Entry, SessionView View, Action ApplyCombat)>();
            foreach (var seat in seats)
            {
                var history = Find(seat.SessionId);
                var view = projected.GetValueOrDefault(seat.SessionId, history.View);
                var label = $"Room {seat.RoomId}, seat {seat.Seat + 1}";
                if (view.State != SessionState.Preparing || !view.RoomIds.Contains(seat.RoomId)
                    || view.Players.Any(player => player.RoomId == seat.RoomId && player.Seat == seat.Seat))
                    throw new VenueRosterSeatConflict(seat.RoomId, seat.Seat);
                if (activePlayers.Contains(seat.PlayerId))
                    throw new InvalidOperationException($"{label}: player already belongs to a session.");
                if (view.Environment.Mode == ExperienceMode.MR && seat.Headset != HeadsetKind.Quest3)
                    throw new InvalidOperationException($"{label}: MR sessions currently require Quest 3 players.");
                var entry = SessionEvent.Create(view.Id, view.Sequence + 1, SessionEventKind.PlayerJoined,
                    new Player(seat.PlayerId, seat.Name, seat.RoomId, seat.Headset, seat.Seat), actor, seat.RequestId);
                var next = SessionProjection.Apply(view, entry);
                var applyCombat = history.Combat.Prepare(CombatBefore(view, entry, history.Authority), entry);
                projected[view.Id] = next;
                additions.Add((entry, next, applyCombat));
            }
            var entries = additions.Select(row => row.Entry).ToArray();
            store.AppendBatch(entries);
            foreach (var (entry, view, applyCombat) in additions)
            {
                var history = Find(entry.SessionId);
                applyCombat();
                RememberCommitted(history, entry, view, history.Combat, history.Authority);
            }
            return VenueRosterResult(entries, duplicate: false);
        }
    }

    private static bool MatchesRosterAdmission(VenueRosterSeat seat, SessionEvent? entry)
    {
        if (entry is null || entry.SessionId != seat.SessionId) return false;
        var player = entry.Read<Player>();
        return player.Id == seat.PlayerId && player.Name == seat.Name && player.RoomId == seat.RoomId
            && player.Seat == seat.Seat && player.Headset == seat.Headset;
    }

    private static VenueRosterReceipt VenueRosterResult(IEnumerable<SessionEvent> entries, bool duplicate) => new(
        entries.Select(entry => new VenueRosterAdmission(entry.SessionId, entry.RequestId!.Value, entry.Sequence, entry.Read<Player>())).ToArray(), duplicate);
}
