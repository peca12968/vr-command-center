using System.Security.Cryptography;

internal static class PlayerTicketKey
{
    internal static byte[] Load(string directory, string? configured)
    {
        if (!string.IsNullOrWhiteSpace(configured)) return Convert.FromBase64String(configured);
        Directory.CreateDirectory(directory);
        var path = Path.Combine(directory, "player-ticket-signing.key");
        if (File.Exists(path)) return Convert.FromBase64String(File.ReadAllText(path));
        var key = RandomNumberGenerator.GetBytes(32);
        using var file = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        var bytes = System.Text.Encoding.UTF8.GetBytes(Convert.ToBase64String(key));
        file.Write(bytes);
        file.Flush(flushToDisk: true);
        return key;
    }
}
