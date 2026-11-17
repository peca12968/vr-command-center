using System.Net;
using System.Net.Sockets;

internal static class LocalRehearsalSocket
{
    private const string DirectoryVariable = "VR_COMMAND_HARDWARE_IPC_DIRECTORY";

    internal static string? DirectoryPath()
    {
        var directory = Environment.GetEnvironmentVariable(DirectoryVariable);
        if (directory is null) return null;
        if (!Path.IsPathFullyQualified(directory) || !Directory.Exists(directory))
            throw new ArgumentException("Use an existing absolute directory for the local rehearsal sockets.");
        return Path.GetFullPath(directory);
    }

    internal static EndPoint Management(string directory, Uri address)
    {
        if (address.Scheme != "http" || address.Host != "127.0.0.1")
            throw new ArgumentException("The local rehearsal socket requires a loopback HTTP management origin.");
        return Endpoint(directory, "management", address.Port);
    }

    internal static EndPoint Mock(int port) => DirectoryPath() is { } directory
        ? Endpoint(directory, "mock", port) : new IPEndPoint(IPAddress.Loopback, port);

    private static UnixDomainSocketEndPoint Endpoint(string directory, string purpose, int port) =>
        new(Path.Combine(directory, FormattableString.Invariant($"{purpose}-{port}.sock")));
}
