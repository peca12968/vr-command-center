using System.Net;
using VrCommand.Core;

internal static class OperatorNetworkChecks
{
    internal static void Run(Action<bool, string> check)
    {
        var proof = new OperatorNetworkProof();
        var challenge = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        var master = new OperatorIdentity("master", OperatorRole.Master);
        var room = new OperatorIdentity("room", OperatorRole.RoomController, 1);
        var listener = IPAddress.Parse("192.168.50.10");
        var masterPeer = new OperatorNetworkPeer(listener, listener, 8443);
        var addresses = Enumerable.Range(21, 5).Select(i => $"192.168.50.{i}").ToArray();
        var inventory = new OperatorNetworkInventory(listener.ToString(), addresses);
        OperatorNetworkWitness[] receipts = [proof.Issue(master, challenge, masterPeer, now),
            .. addresses.Select((address, index) => proof.Issue(room with { RoomId = index + 1 }, challenge,
                new OperatorNetworkPeer(IPAddress.Parse(address).MapToIPv6(), listener, 8443), now))];
        var result = proof.Verify(master, challenge, masterPeer, inventory, receipts.Reverse().ToArray(), now.AddMinutes(1));
        check(result.WorkstationAddresses.SequenceEqual(new[] { inventory.MasterAddress }.Concat(addresses)),
            "Six signed workstation witnesses verify against the declared private addresses in role order");
        void Reject<T>(Action action, string name) where T : Exception
        {
            try { action(); }
            catch (T) { check(true, name); return; }
            throw new InvalidOperationException("Expected rejection: " + name);
        }
        Reject<AccessDeniedException>(() => proof.Issue(new("game", OperatorRole.GameServer), challenge, masterPeer, now),
            "Game server cannot issue a workstation witness");
        Reject<AccessDeniedException>(() => proof.Verify(room, challenge, masterPeer, inventory, receipts, now),
            "Room credentials cannot verify the whole venue");
        Reject<ArgumentException>(() => proof.Verify(master, Guid.NewGuid(), masterPeer, inventory, receipts, now),
            "Different workstation check challenge rejects the original reports");
        Reject<ArgumentException>(() => new OperatorNetworkProof().Verify(master, challenge, masterPeer, inventory, receipts, now),
            "A new management process cannot verify another process's reports");
        Reject<ArgumentException>(() => proof.Verify(master, challenge, masterPeer, inventory, receipts, now.AddMinutes(16)),
            "Old workstation reports cannot be presented as current evidence");
        Reject<ArgumentException>(() => proof.Verify(master, challenge, masterPeer, inventory, receipts, now.AddSeconds(-1)),
            "Future workstation reports are rejected");
        Reject<ArgumentException>(() => proof.Verify(master, challenge, masterPeer with { Port = 8444 }, inventory, receipts, now),
            "Workstation reports cannot be moved between management listeners");
        Reject<ArgumentException>(() => proof.Verify(master, challenge, masterPeer with { Source = IPAddress.Parse(addresses[0]) }, inventory, receipts, now),
            "Venue verification must be submitted from the declared master source");
        Reject<ArgumentException>(() => proof.Verify(master, challenge, masterPeer, inventory,
            [.. receipts[..^1], receipts[1]], now), "A duplicate room witness cannot fill a missing room");
        var altered = receipts.ToArray();
        altered[1] = altered[1] with { Signature = new string('0', 64) };
        Reject<ArgumentException>(() => proof.Verify(master, challenge, masterPeer, inventory, altered, now),
            "A changed workstation signature cannot be used as evidence");
        var moved = inventory with { RoomAddresses = ["192.168.50.30", .. addresses[1..]] };
        altered[1] = receipts[1] with { Source = moved.RoomAddresses[0] };
        Reject<ArgumentException>(() => proof.Verify(master, challenge, masterPeer, moved, altered, now),
            "Editing a signed source to match the inventory is detected");
        Reject<ArgumentException>(() => proof.Verify(master, challenge, masterPeer,
            inventory with { RoomAddresses = [addresses[0], .. addresses[..^1]] }, receipts, now),
            "Two operators behind one source cannot satisfy a direct six-workstation inventory");
        Reject<ArgumentException>(() => proof.Issue(room, challenge, masterPeer with { Source = IPAddress.Loopback }, now),
            "Loopback cannot stand in for a direct venue workstation");
        Reject<ArgumentException>(() => proof.Issue(room, challenge, masterPeer with { Source = IPAddress.Parse("100.64.0.5") }, now),
            "An overlay address cannot stand in for a direct private LAN workstation");
        var oldRoom = proof.Issue(room with { RoomId = 2 }, challenge,
            new(IPAddress.Parse(addresses[1]), listener, 8443), now.AddMinutes(-16));
        try
        {
            proof.Verify(master, challenge, masterPeer, moved,
                [receipts[0], receipts[1], oldRoom, receipts[3], receipts[3], receipts[5]], now);
            check(false, "Mixed workstation issues reject the complete submission");
        }
        catch (OperatorNetworkWitnessException error)
        {
            check(error.Issues.SequenceEqual(new OperatorNetworkIssue[] {
                new(1, "source-mismatch"), new(2, "expired"), new(3, "duplicate-role"), new(4, "missing-role") }),
                "A single rejection identifies each affected role in room order without witness data");
        }
    }
}
