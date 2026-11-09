using System.IO.Compression;
using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

internal sealed record TicketAdmission(Guid PlayerId, Guid AdmissionId);
internal sealed record RoomTicketRequest(string? Address, int Port, TicketAdmission?[]? Players);

internal static class RoomTicketBundles
{
    public static byte[] Create(SessionView session, int roomId, RoomTicketRequest request, OperatorIdentity actor, PlayerJoinTicketSigner signer)
    {
        AccessPolicy.Player(actor, session, roomId);
        if (!session.RoomIds.Contains(roomId)) throw new ArgumentException("Room is outside the session.");
        if (session.State == SessionState.Ended) throw new InvalidOperationException("Session has ended.");
        if (!ConnectionDestination.IsValid(request.Address, request.Port))
            throw new ArgumentException("Use a canonical unicast IPv4 address and port 1024–65535.");
        var players = ValidateAdmissions(session, roomId, request.Players);
        return Encode(session, roomId, players, request.Address!, request.Port, signer);
    }

    internal static Player[] ValidateAdmissions(SessionView session, int roomId, TicketAdmission?[]? admissions)
    {
        if (admissions is not { Length: >= 1 and <= SessionManager.PlayersPerRoom })
            throw new ArgumentException("Provide the current admissions for one occupied room.");

        var expected = new Dictionary<Guid, Guid>();
        foreach (var entry in admissions)
        {
            if (entry is null || entry.PlayerId == Guid.Empty || entry.AdmissionId == Guid.Empty || !expected.TryAdd(entry.PlayerId, entry.AdmissionId))
                throw new ArgumentException("Provide a unique player and admission for each occupied seat.");
        }

        // The session is one roster snapshot. Validate the entire room before issuing any tickets.
        var players = session.Players.Where(player => player.RoomId == roomId).OrderBy(player => player.Seat).ToArray();
        if (players.Length != expected.Count || players.Any(player => !expected.TryGetValue(player.Id, out var admission) || admission != player.AdmissionId))
            throw new InvalidOperationException("Room roster changed; reload it before downloading connection files.");
        return players;
    }

    internal static byte[] Encode(SessionView session, int roomId, Player[] players, string address, int port, PlayerJoinTicketSigner signer)
    {
        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            foreach (var player in players)
            {
                var ticket = signer.Issue(session, player);
                using var file = archive.CreateEntry(FormattableString.Invariant($"room-{roomId:00}-seat-{player.Seat + 1:00}.json")).Open();
                var config = new Dictionary<string, object?> { ["role"] = "Client", ["address"] = address,
                    ["port"] = port, ["joinTicket"] = ticket.Ticket };
                if (ticket.RoomAlignmentSha256 is { } hash) config["roomAlignmentSha256"] = hash;
                JsonSerializer.Serialize(file, config);
            }
        }
        return output.ToArray();
    }
}
