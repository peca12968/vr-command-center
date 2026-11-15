using VrCommand.Core;

namespace VrCommand.Api;

internal static class QuestSeatDeployment
{
    internal sealed record Files(byte[] ConnectionFile, byte[]? AlignmentFile = null);

    internal static async Task<Files> ReadFiles(HttpRequest request, CancellationToken cancellation)
    {
        const string message = "Provide one original Quest connection file and, for MR, its original alignment file.";
        var files = await DeploymentJson.Read<Files>(request, 25 * 1024, message, cancellation);
        if (files.ConnectionFile is not { Length: > 0 and <= 2048 }
            || files.AlignmentFile is { Length: 0 or > RoomAlignment.MaxFileBytes })
            throw new ArgumentException(message);
        return files;
    }

    internal static VrVenueTickets.SeatFileResult Check(SessionView session, Player player, Files files,
        ConnectionEndpoint? endpoint, bool sourceLive, PlayerJoinTicketSigner signer)
    {
        VrVenueTickets.SeatFileResult Result(string status, DateTimeOffset? expiry = null) =>
            new(status, player.RoomId, player.Seat, expiry, endpoint?.Address, endpoint?.Port);

        if (player.Headset != HeadsetKind.Quest3) return Result("headset-mismatch");
        var mr = session.Environment.Mode == ExperienceMode.MR;
        if (mr != (files.AlignmentFile is not null)) return Result("mode-mismatch");
        if (!mr)
            return VrVenueTickets.CheckSeatFile(session.Id, player, new(files.ConnectionFile), endpoint, sourceLive, signer);

        var hash = session.RoomAlignment?.ForRoom(player.RoomId);
        if (hash is null) return Result("alignment-not-locked");
        if (endpoint is null) return Result("endpoint-unpublished");
        if (!sourceLive) return Result("source-stale");
        var verified = MrDeploymentCheck.CheckFiles(session.Id, player, files.ConnectionFile,
            MrDeploymentCheck.ReadAlignment(files.AlignmentFile!), hash, signer, endpoint);
        return Result(verified.Status, verified.ExpiresAtUtc);
    }
}
