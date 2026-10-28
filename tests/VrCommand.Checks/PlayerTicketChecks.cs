using VrCommand.Core;

internal static class PlayerTicketChecks
{
    internal static void Run(Action<bool, string> check, Mission mission)
    {
        var clock = new ManualClock();
        var key = Enumerable.Repeat((byte)42, 32).ToArray();
        var signer = new PlayerJoinTicketSigner(key, clock);
        var session = Guid.NewGuid();
        var player = new Player(Guid.NewGuid(), "Quest3", 1, HeadsetKind.Quest3, 0, Guid.NewGuid());
        var issued = signer.Issue(session, player);
        check(issued.Ticket.Length < 256 && signer.Validate(issued.Ticket, session).PlayerId == player.Id,
            "Headset ticket is compact and bound to its player/session");
        check(signer.Issue(session, player).Ticket != issued.Ticket, "Independent ticket issues include fresh random nonces");
        void Reject(string ticket, Guid target, string message, PlayerJoinTicketSigner? validator = null)
        {
            try { (validator ?? signer).Validate(ticket, target); }
            catch (AccessDeniedException) { check(true, message); return; }
            throw new Exception(message);
        }
        Reject(issued.Ticket, Guid.NewGuid(), "Ticket cannot be used for another session");
        Reject(issued.Ticket[..10] + "!" + issued.Ticket[11..], session, "Malformed ticket rejected");
        Reject(issued.Ticket[..^5] + "AAAAA", session, "Modified ticket signature rejected");
        Reject(issued.Ticket, session, "Another signing key cannot validate the ticket",
            new PlayerJoinTicketSigner(Enumerable.Repeat((byte)23, 32).ToArray(), clock));
        clock.Now = clock.Now.AddMinutes(5);
        Reject(issued.Ticket, session, "Ticket expires at the server's five-minute boundary");
        var store = new MemorySessionEventStore();
        var manager = new SessionManager(store);
        var id = manager.Create(SessionMode.Independent, [1], mission).Id;
        var alpha = Guid.NewGuid();
        var bravo = Guid.NewGuid();
        var charlie = Guid.NewGuid();
        manager.Join(id, alpha, "Alpha", 1, HeadsetKind.Quest3);
        manager.Join(id, bravo, "Bravo", 1, HeadsetKind.Quest3);
        manager.Leave(id, alpha);
        manager.Join(id, charlie, "Charlie", 1, HeadsetKind.Quest3);
        check(manager.Get(id).Players.Single(p => p.Id == bravo).Seat == 1 && manager.Get(id).Players.Single(p => p.Id == charlie).Seat == 0,
            "A released spawn seat is reused without shifting existing players");
        var legacy = manager.Events(id).Select(entry => entry.Kind != SessionEventKind.PlayerJoined ? entry : entry with
        {
            SchemaVersion = 5, Payload = System.Text.Json.JsonSerializer.SerializeToElement(new { id = entry.Read<Player>().Id, name = entry.Read<Player>().Name,
                roomId = entry.Read<Player>().RoomId, headset = entry.Read<Player>().Headset.ToString() }, JsonFormat.Options)
        }).ToArray();
        var legacyStore = new MemorySessionEventStore();
        legacyStore.Seed(id, legacy);
        var recovered = new SessionManager(legacyStore);
        check(recovered.Get(id).Players.Single(p => p.Id == bravo).Seat == 1 && recovered.Get(id).Players.Single(p => p.Id == charlie).Seat == 0,
            "Histories from before spawn seats were stored reconstruct stable seat assignments");
    }

    private sealed class ManualClock : TimeProvider
    {
        internal DateTimeOffset Now = new(2026, 10, 29, 0, 0, 0, TimeSpan.Zero);
        public override DateTimeOffset GetUtcNow() => Now;
    }
}
