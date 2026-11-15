using System.IO.Compression;
using System.Text.Json;
using VrCommand.Core;

namespace VrCommand.Api;

internal sealed record FieldEvidence(SessionView Session, SessionStatistics Statistics, ConnectionEndpoint Endpoint,
    WorldTrackedVrStart? TrackedVrStart = null, RosterDepartureEvidence? RosterDepartures = null)
{
    private static readonly DateTimeOffset ArchiveTime = new(1980, 1, 1, 0, 0, 0, TimeSpan.Zero);

    internal static ZipArchiveEntry Entry(ZipArchive archive, string name, CompressionLevel compression = CompressionLevel.Optimal)
    {
        var entry = archive.CreateEntry(name, compression);
        entry.LastWriteTime = ArchiveTime;
        return entry;
    }

    public byte[] Encode()
    {
        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            Write("session.json", Session);
            Write("statistics.json", Statistics);
            Write("endpoint.json", Endpoint);
            if (TrackedVrStart is not null)
                Write("tracked-vr-start.json", new { version = 1, trackedVrStart = TrackedVrStart });
            if (RosterDepartures is not null)
                Write("roster-departures.json", RosterDepartures);

            void Write<T>(string name, T value)
            {
                using var entry = Entry(archive, name).Open();
                JsonSerializer.Serialize(entry, value, JsonFormat.Options);
            }
        }
        return output.ToArray();
    }
}

internal sealed record VenueFieldEvidence(VenueClosureBatch Batch, FieldEvidence[] Sessions, VenueDebriefExport? Receipts)
{
    public byte[] Encode()
    {
        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            using (var closure = FieldEvidence.Entry(archive, "closure.json").Open())
                JsonSerializer.Serialize(closure, new { batch = Batch }, JsonFormat.Options);
            foreach (var item in Sessions)
            {
                var name = item.Session.Mode == SessionMode.Linked ? "linked.zip" : $"room-{item.Session.RoomIds[0]:00}.zip";
                using var entry = FieldEvidence.Entry(archive, name, CompressionLevel.NoCompression).Open();
                entry.Write(item.Encode());
            }
            if (Receipts is not null)
            {
                using var receipts = FieldEvidence.Entry(archive, "debrief-receipts.json").Open();
                JsonSerializer.Serialize(receipts, Receipts, JsonFormat.Options);
            }
        }
        return output.ToArray();
    }
}

internal sealed class VenueFieldEvidenceNotReadyException(int[] roomIds, bool waitingForReceipts = false)
    : InvalidOperationException(waitingForReceipts ? "All original players must have confirmed debrief receipts."
        : "All original sessions must provide sealed field evidence.")
{
    public int[] RoomIds { get; } = roomIds;
    public string Code { get; } = waitingForReceipts ? "venue-field-receipts-not-confirmed" : "venue-field-evidence-not-ready";
}

public sealed partial class WorldRecordings
{
    internal FieldEvidence ReadFieldEvidence(Guid id, OperatorIdentity actor, bool includeTrackedVrStart = false)
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

            var (evidence, problem) = BuildFieldEvidence(session, stream, actor, allowDepartures: true);
            if (evidence is null) throw new InvalidOperationException(problem);
            if (evidence.RosterDepartures is { } departures && (Frame(id, world.AcceptedSequence, actor) is not { Packet: var packet }
                || packet.observedSequence < departures.EndedAtSequence))
                throw new InvalidOperationException("The original world must observe the End after the recorded roster departures.");
            if (!includeTrackedVrStart) return evidence;
            var start = ReadWorldTrackedVrStart(session, world, actor)
                ?? throw new InvalidOperationException("No verified tracked VR opening frame for this sealed session.");
            return evidence with { TrackedVrStart = start };
        }
    }

    internal VenueFieldEvidence ReadVenueFieldEvidence(Guid id, OperatorIdentity actor, bool includeDebriefReceipts)
    {
        lock (gate)
        {
            var (batch, evidence) = ReadVenueClosureData(actor, id) ?? throw new KeyNotFoundException("No venue End batch with that ID.");
            var waiting = batch.Sessions.Where(row => !row.FieldEvidenceReady).SelectMany(row => row.RoomIds).Order().ToArray();
            if (waiting.Length > 0) throw new VenueFieldEvidenceNotReadyException(waiting);
            var sessions = evidence.OfType<FieldEvidence>().ToArray();
            VenueDebriefExport? receipts = null;
            if (includeDebriefReceipts)
            {
                var rows = sessions.Select(item => BuildDebriefExportSession(item.Session, item.Session.CombatStream!,
                    batch.Sessions.Single(row => row.SessionId == item.Session.Id).Replay!.ThroughSequence)).ToArray();
                var unconfirmed = rows.SelectMany(row => row.Players).Where(player => !player.Acknowledged)
                    .Select(player => player.RoomId).Distinct().Order().ToArray();
                if (unconfirmed.Length > 0) throw new VenueFieldEvidenceNotReadyException(unconfirmed, waitingForReceipts: true);
                receipts = new(1, batch.RequestId, rows);
            }
            return new(batch, sessions, receipts);
        }
    }

    private (FieldEvidence? Evidence, string? Problem) BuildFieldEvidence(SessionView session, CombatStreamView stream, OperatorIdentity actor,
        bool allowDepartures = false)
    {
        if (session.State != SessionState.Ended || session.StartedAtUtc is null || session.EndedAtUtc is null)
            return (null, "Start and end the mission before exporting field evidence.");
        var endpoint = EndpointRow(session);
        if (endpoint is null) return (null, "The game source did not publish connection settings.");
        var statistics = manager.Statistics(session.Id, actor);
        var roster = session.Players.Select(player => (player.Id, player.RoomId)).ToHashSet();
        var ledger = statistics.Players.Select(player => (player.PlayerId, player.RoomId)).ToHashSet();
        if (statistics.PendingTelemetry || statistics.ThroughSequence != session.Sequence
            || (statistics.Origin is { } origin ? origin != stream.Origin : stream.AcceptedSequence != 0)
            || ledger.Count == 0 || !roster.IsSubsetOf(ledger))
            return (null, "Field evidence requires sealed statistics matching the final roster.");
        if (roster.SetEquals(ledger)) return (new(session, statistics, endpoint), null);
        if (!allowDepartures) return (null, "Field evidence requires sealed statistics matching the final roster.");
        var departures = manager.ReadRosterDepartures(session.Id, session.Sequence, actor);
        return ledger.Except(roster).ToHashSet().SetEquals(departures.Players.Select(player => (player.PlayerId, player.RoomId)))
            ? (new(session, statistics, endpoint, RosterDepartures: departures), null)
            : (null, "Field evidence requires original roster departures recorded before End.");
    }
}
