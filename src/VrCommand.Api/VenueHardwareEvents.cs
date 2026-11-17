using System.IO.Compression;
using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

internal static class VenueHardwareEvents
{
    private const int MaxSessionBytes = 32 * 1024 * 1024;

    internal static byte[] Export(SessionManager manager, OperatorIdentity actor, string?[] requested, CancellationToken cancellation)
    {
        AccessPolicy.Validate(actor);
        if (actor.Role != OperatorRole.Master)
            throw new AccessDeniedException("Original venue event export requires the master operator.");
        if (requested.Length is not (1 or SessionManager.RoomCount))
            throw new ArgumentException("Provide one linked session ID or five independent session IDs in room order.");

        var ids = requested.Select(ParseSessionId).ToArray();
        if (ids.Distinct().Count() != ids.Length)
            throw new ArgumentException("Original session IDs must be distinct.");
        var sessions = ids.Select(id => manager.Get(id, actor)).ToArray();
        var roomIds = Enumerable.Range(1, SessionManager.RoomCount).ToArray();
        var valid = sessions.Length == 1
            ? sessions[0].Mode == SessionMode.Linked && sessions[0].RoomIds.SequenceEqual(roomIds)
            : sessions.Select((session, index) => session.Mode == SessionMode.Independent
                && session.RoomIds is [var room] && room == roomIds[index]).All(matches => matches);
        if (!valid)
            throw new ArgumentException("Original sessions must match the five-room topology and room order.");
        if (sessions.Any(session => session.State != SessionState.Ended || session.CombatStream is not { Sealed: true }))
            throw new InvalidOperationException("Every original session must be ended with a sealed combat stream.");

        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            foreach (var session in sessions)
            {
                cancellation.ThrowIfCancellationRequested();
                using var entry = FieldEvidence.Entry(archive, $"{session.Id:D}.json").Open();
                WriteEvents(manager, actor, session, entry, cancellation);
            }
        }
        return output.ToArray();
    }

    private static Guid ParseSessionId(string? value) => Guid.TryParseExact(value, "D", out var id) && id != Guid.Empty
        ? id : throw new ArgumentException("Use the original session UUIDs.");

    private static void WriteEvents(SessionManager manager, OperatorIdentity actor, SessionView session,
        Stream output, CancellationToken cancellation)
    {
        using var writer = new Utf8JsonWriter(output);
        writer.WriteStartArray();
        long through = 0;
        while (through < session.Sequence)
        {
            cancellation.ThrowIfCancellationRequested();
            var page = manager.Events(session.Id, through, (int)Math.Min(500, session.Sequence - through), actor);
            if (page.Length == 0)
                throw new InvalidOperationException("The original event history is incomplete.");
            foreach (var item in page)
            {
                if (item.SchemaVersion < 6 || item.SessionId != session.Id || item.Sequence != through + 1)
                    throw new InvalidOperationException("The original event history has an invalid sequence or schema.");
                JsonSerializer.Serialize(writer, item, JsonFormat.Options);
                through++;
            }
            writer.Flush();
            if (writer.BytesCommitted >= MaxSessionBytes)
                throw new InvalidOperationException("An original event file exceeds the 32 MiB handoff limit.");
        }
        writer.WriteEndArray();
    }
}
