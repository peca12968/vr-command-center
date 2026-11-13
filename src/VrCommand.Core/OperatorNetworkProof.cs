using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;

namespace VrCommand.Core;

public sealed record OperatorNetworkPeer(IPAddress Source, IPAddress Listener, int Port);
public sealed record OperatorNetworkWitness(int Version, Guid Challenge, int Workstation, string Source,
    string Listener, int Port, long ObservedAtUnixSeconds, string Signature);
public sealed record OperatorNetworkInventory(string MasterAddress, string[] RoomAddresses);
public sealed record OperatorNetworkCheck(Guid Challenge, string Listener, int Port, string[] WorkstationAddresses);
public sealed record OperatorNetworkIssue(int Workstation, string Reason);
public sealed class OperatorNetworkWitnessException(OperatorNetworkIssue[] issues)
    : ArgumentException("A workstation witness is invalid, expired, duplicated or differs from this venue and expected source.")
{
    public OperatorNetworkIssue[] Issues { get; } = issues;
}

// One verifier per running management service. Reports can be assembled without
// storing any challenge, source address or validation result in the database.
public sealed class OperatorNetworkProof
{
    private const int LifetimeSeconds = 15 * 60;
    private readonly byte[] key = RandomNumberGenerator.GetBytes(32);

    public OperatorNetworkWitness Issue(OperatorIdentity actor, Guid challenge, OperatorNetworkPeer peer, DateTimeOffset now)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role is not (OperatorRole.Master or OperatorRole.RoomController))
            throw new AccessDeniedException("Workstation evidence requires a control-desk identity.");
        RequireChallenge(challenge);
        var (source, listener) = Addresses(peer);
        var witness = new OperatorNetworkWitness(1, challenge, actor.RoomId ?? 0, source, listener, peer.Port, now.ToUnixTimeSeconds(), "");
        return witness with { Signature = Convert.ToHexStringLower(Sign(witness)) };
    }

    public OperatorNetworkCheck Verify(OperatorIdentity actor, Guid challenge, OperatorNetworkPeer peer,
        OperatorNetworkInventory? inventory, OperatorNetworkWitness[]? witnesses, DateTimeOffset now)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role != OperatorRole.Master) throw new AccessDeniedException("Workstation verification requires the master control desk.");
        RequireChallenge(challenge);
        var (source, listener) = Addresses(peer);
        if (inventory?.RoomAddresses is not { Length: SessionManager.RoomCount } || witnesses is not { Length: SessionManager.RoomCount + 1 })
            throw new ArgumentException("Provide one master and five room workstation addresses and witnesses.");

        string[] addresses = [inventory.MasterAddress, .. inventory.RoomAddresses];
        if (addresses.Any(address => !IsPrivateAddress(address)) || addresses.Distinct(StringComparer.Ordinal).Count() != addresses.Length
            || inventory.RoomAddresses.Contains(listener, StringComparer.Ordinal) || addresses[0] != source)
            throw new ArgumentException("Require distinct private IPv4 workstations, five room sources separate from the management listener, and submission from the declared master address.");

        if (witnesses.Any(witness => witness is null || witness.Workstation is < 0 or > SessionManager.RoomCount))
            throw new ArgumentException("Provide one master and five room workstation addresses and witnesses.");
        var groups = witnesses.ToLookup(witness => witness.Workstation);
        var latest = now.ToUnixTimeSeconds();
        var issues = new List<OperatorNetworkIssue>();
        for (var workstation = 0; workstation < addresses.Length; workstation++)
        {
            var entries = groups[workstation].ToArray();
            var reason = entries.Length switch
            {
                0 => "missing-role",
                1 => Rejection(entries[0], challenge, listener, peer.Port, addresses[workstation], latest),
                _ => "duplicate-role"
            };
            if (reason is not null) issues.Add(new(workstation, reason));
        }
        if (issues.Count != 0) throw new OperatorNetworkWitnessException([.. issues]);
        return new OperatorNetworkCheck(challenge, listener, peer.Port, addresses);
    }

    private string? Rejection(OperatorNetworkWitness witness, Guid challenge, string listener, int port, string source, long latest)
    {
        if (!IsPrivateAddress(witness.Source) || !IsPrivateAddress(witness.Listener) || witness.Port is < 1 or > 65535)
            return "invalid-witness";
        if (witness.Version != 1 || witness.Signature is not { Length: 64 }
            || !witness.Signature.All(char.IsAsciiHexDigitLower)
            || !CryptographicOperations.FixedTimeEquals(Sign(witness), Convert.FromHexString(witness.Signature)))
            return "invalid-signature";
        if (witness.Challenge != challenge) return "challenge-mismatch";
        if (witness.ObservedAtUnixSeconds < latest - LifetimeSeconds) return "expired";
        if (witness.ObservedAtUnixSeconds > latest) return "clock-ahead";
        if (witness.Listener != listener || witness.Port != port) return "listener-mismatch";
        return witness.Source == source ? null : "source-mismatch";
    }

    private byte[] Sign(OperatorNetworkWitness value) => HMACSHA256.HashData(key, Encoding.ASCII.GetBytes(
        string.Create(CultureInfo.InvariantCulture, $"vr-workstation\n{value.Version}\n{value.Challenge:D}\n{value.Workstation}\n{value.Source}\n{value.Listener}\n{value.Port}\n{value.ObservedAtUnixSeconds}")));

    private static void RequireChallenge(Guid challenge)
    {
        if (challenge == Guid.Empty) throw new ArgumentException("Use a nonempty workstation check challenge.");
    }

    private static (string Source, string Listener) Addresses(OperatorNetworkPeer peer)
    {
        var source = AddressText(peer.Source);
        var listener = AddressText(peer.Listener);
        if (!IsPrivateAddress(source) || !IsPrivateAddress(listener) || peer.Port is < 1 or > 65535)
            throw new ArgumentException("Workstation evidence requires direct HTTPS with private IPv4 endpoints.");
        return (source, listener);
    }

    private static string AddressText(IPAddress address) => (address.IsIPv4MappedToIPv6 ? address.MapToIPv4() : address).ToString();

    private static bool IsPrivateAddress(string? value)
    {
        if (!IPAddress.TryParse(value, out var address) || address.AddressFamily != AddressFamily.InterNetwork || address.ToString() != value)
            return false;
        var bytes = address.GetAddressBytes();
        return bytes[0] == 10 || bytes[0] == 172 && bytes[1] is >= 16 and <= 31 || bytes[0] == 192 && bytes[1] == 168;
    }
}
