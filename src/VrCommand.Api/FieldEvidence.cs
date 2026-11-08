using System.IO.Compression;
using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

internal sealed record FieldEvidence(SessionView Session, SessionStatistics Statistics, ConnectionEndpoint Endpoint)
{
    public byte[] Encode()
    {
        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            Write("session.json", Session);
            Write("statistics.json", Statistics);
            Write("endpoint.json", Endpoint);

            void Write<T>(string name, T value)
            {
                using var entry = archive.CreateEntry(name).Open();
                JsonSerializer.Serialize(entry, value, JsonFormat.Options);
            }
        }
        return output.ToArray();
    }
}

public sealed partial class WorldRecordings
{
    internal FieldEvidence ReadFieldEvidence(Guid id, OperatorIdentity actor)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role != OperatorRole.Master)
            throw new AccessDeniedException("Field evidence requires the master control desk.");

        lock (gate)
        {
            var session = manager.Get(id, actor);
            if (session.State != SessionState.Ended || session.StartedAtUtc is null || session.EndedAtUtc is null
                || session.CombatStream is not { Sealed: true } stream)
                throw new InvalidOperationException("Start, end and seal the mission before exporting field evidence.");

            var world = Info(id, actor);
            if (!world.Complete || world.AcceptedSequence <= 0 || world.Header.sessionId != id.ToString("D")
                || world.Header.streamId != stream.StreamId.ToString("D") || world.Header.origin != stream.Origin.ToString()
                || !world.Header.roomIds.SequenceEqual(session.RoomIds))
                throw new InvalidOperationException("The sealed world does not match this session's combat source.");

            var endpoint = EndpointRow(session)
                ?? throw new InvalidOperationException("The game source did not publish connection settings.");
            var statistics = manager.Statistics(id, actor);
            if (statistics.PendingTelemetry || statistics.ThroughSequence != session.Sequence
                || (statistics.Origin is { } origin ? origin != stream.Origin : stream.AcceptedSequence != 0)
                || session.Players.Length == 0 || !session.Players.Select(p => (p.Id, p.RoomId)).ToHashSet()
                    .SetEquals(statistics.Players.Select(p => (p.PlayerId, p.RoomId))))
                throw new InvalidOperationException("Field evidence requires sealed statistics matching the final roster.");

            return new(session, statistics, endpoint);
        }
    }
}
