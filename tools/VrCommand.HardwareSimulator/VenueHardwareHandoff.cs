using System.IO.Compression;
using System.Text.Json;
using VrCommand.Core;

internal static partial class LiveHardwareGateway
{
    private const int MaxHandoffEntries = 2 + SessionManager.RoomCount * 2;
    private const long MaxHandoffBytes = (long)SessionManager.RoomCount * MaxRoomReportBytes + 1024 * 1024;

    internal static int PackVenueHandoff(string manifestPath, string directory, string output)
    {
        var parent = Path.GetDirectoryName(output);
        if (parent is null || !Directory.Exists(parent) || Path.Exists(output) || !output.EndsWith(".zip", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Use a new ZIP in an existing output directory.");
        var staging = Path.Combine(parent, $".vr-hardware-handoff-{Guid.NewGuid():N}.tmp");
        var created = false;
        try
        {
            object review;
            using (var file = new FileStream(staging, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                created = true;
                using (var archive = new ZipArchive(file, ZipArchiveMode.Create, leaveOpen: true))
                {
                    review = ReviewVenueRun((name, limit) =>
                    {
                        var bytes = ReadVenueRunFile(manifestPath, directory, name, limit);
                        var entry = archive.CreateEntry(name);
                        entry.LastWriteTime = new DateTimeOffset(1980, 1, 1, 0, 0, 0, TimeSpan.Zero);
                        using var stream = entry.Open();
                        stream.Write(bytes);
                        return bytes;
                    });
                }
                file.Flush(true);
            }
            File.Move(staging, output);
            created = false;
            Console.WriteLine(JsonSerializer.Serialize(review, Wire));
            return 0;
        }
        finally { if (created) File.Delete(staging); }
    }

    internal static int ReviewVenueHandoff(string input, string? eventsDirectory)
    {
        using var file = File.OpenRead(input);
        if (file.Length is < 1 or > MaxHandoffBytes) throw new InvalidDataException("Unexpected venue ZIP size.");
        using var archive = new ZipArchive(file, ZipArchiveMode.Read);
        if (archive.Entries.Count is < 2 or > MaxHandoffEntries) throw new InvalidDataException("Unexpected venue ZIP entries.");
        var entries = new Dictionary<string, ZipArchiveEntry>(StringComparer.Ordinal);
        foreach (var entry in archive.Entries)
            if (!entries.TryAdd(entry.FullName, entry)) throw new InvalidDataException("Duplicate venue ZIP entry.");
        var review = ReviewVenueRun((name, limit) =>
        {
            if (!entries.Remove(name, out var entry)) throw new InvalidDataException("Missing venue ZIP entry.");
            using var stream = entry.Open();
            return ReadReportBytes(stream, entry.Length, limit);
        }, eventsDirectory);
        if (entries.Count != 0) throw new InvalidDataException("Unexpected venue ZIP entry.");
        Console.WriteLine(JsonSerializer.Serialize(review, Wire));
        return 0;
    }
}
