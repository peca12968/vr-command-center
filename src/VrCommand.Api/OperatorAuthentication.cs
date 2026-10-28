using System.Security.Cryptography;
using System.Text;
using VrCommand.Core;

// Console credentials for the LAN prototype, separate from future human-account authentication.
internal sealed class OperatorAuthentication
{
    private readonly List<(byte[] Digest, OperatorIdentity Identity)> identities = [];

    public OperatorAuthentication(IConfiguration configuration)
    {
        var knownNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "Master", "GameServer" };
        foreach (var room in Enumerable.Range(1, SessionManager.RoomCount)) knownNames.Add($"Room{room}");
        foreach (var item in configuration.GetSection("OperatorKeys").GetChildren())
        {
            if (!knownNames.Contains(item.Key)) throw new InvalidOperationException("Unknown OperatorKeys configuration name.");
        }
        Add("Master", new("master", OperatorRole.Master), required: true);
        Add("GameServer", new("game-server", OperatorRole.GameServer));
        foreach (var room in Enumerable.Range(1, SessionManager.RoomCount))
            Add($"Room{room}", new($"room-{room}", OperatorRole.RoomController, room));

        void Add(string name, OperatorIdentity identity, bool required = false)
        {
            var key = configuration[$"OperatorKeys:{name}"];
            if (string.IsNullOrEmpty(key) && !required) return;
            if (key is null || key.Length is < 32 or > 512 || key.Any(char.IsWhiteSpace))
                throw new InvalidOperationException($"OperatorKeys:{name} must be a unique credential of 32–512 non-whitespace characters.");
            var digest = SHA256.HashData(Encoding.UTF8.GetBytes(key));
            if (identities.Any(item => CryptographicOperations.FixedTimeEquals(item.Digest, digest)))
                throw new InvalidOperationException("Operator credentials must be distinct across consoles.");
            identities.Add((digest, identity));
        }
    }

    public OperatorIdentity? Authenticate(string authorization)
    {
        const string prefix = "Bearer ";
        if (!authorization.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)) return null;
        var key = authorization[prefix.Length..];
        if (key.Length is < 32 or > 512) return null;
        var digest = SHA256.HashData(Encoding.UTF8.GetBytes(key));
        OperatorIdentity? result = null;
        foreach (var item in identities)
            if (CryptographicOperations.FixedTimeEquals(item.Digest, digest)) result = item.Identity;
        return result;
    }
}
