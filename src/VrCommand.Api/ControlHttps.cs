using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using Microsoft.AspNetCore.Connections;
using VrCommand.Core;

namespace VrCommand.Api;

internal sealed record OperatorNetworkSubmission(Guid Challenge, OperatorNetworkInventory Inventory, OperatorNetworkWitness[] Witnesses);

// Private launch settings. A packaged TLS deployment has exactly one local HTTP
// listener for the game server and one explicitly configured HTTPS listener.
internal sealed class ControlHttps(IPAddress address, int port, int localPort,
    X509Certificate2 certificate, X509Certificate2Collection intermediates) : IDisposable
{
    private const string Address = "VR_COMMAND_MANAGED_TLS_ADDRESS";
    private const string Port = "VR_COMMAND_MANAGED_TLS_PORT";
    private const string LocalPort = "VR_COMMAND_MANAGED_TLS_LOCAL_PORT";
    private const string Password = "VR_COMMAND_CONTROL_PFX_PASSWORD";

    public static ControlHttps? Load()
    {
        var addressText = Environment.GetEnvironmentVariable(Address);
        if (addressText is null) return null;

        var password = Environment.GetEnvironmentVariable(Password);
        Environment.SetEnvironmentVariable(Password, null);
        if (string.IsNullOrEmpty(Environment.GetEnvironmentVariable("ControlPipeToken")) || string.IsNullOrEmpty(password)
            || !IPAddress.TryParse(addressText, out var address) || address.AddressFamily != AddressFamily.InterNetwork
            || address.ToString() != addressText || address.GetAddressBytes()[0] is 0 or >= 224
            || !int.TryParse(Environment.GetEnvironmentVariable(Port), out var port) || (port != 443 && port is < 1024 or > 65535)
            || !int.TryParse(Environment.GetEnvironmentVariable(LocalPort), out var localPort) || localPort is < 1024 or > 65535
            || port == localPort)
            throw new InvalidOperationException("Invalid packaged management HTTPS settings.");

        X509Certificate2Collection certificates;
        try
        {
            // Windows Schannel needs a usable native key handle. Do not request
            // ephemeral import or persist the imported private key.
            certificates = X509CertificateLoader.LoadPkcs12CollectionFromFile(
                Path.Combine(Directory.GetCurrentDirectory(), "control-https.pfx"), password);
        }
        catch (Exception error) when (error is CryptographicException or IOException or UnauthorizedAccessException)
        {
            throw new InvalidOperationException("Unable to load the management HTTPS PFX.");
        }

        var identities = certificates.OfType<X509Certificate2>().Where(value => value.HasPrivateKey).ToArray();
        var now = DateTime.UtcNow;
        if (identities.Length != 1 || identities[0].NotBefore.ToUniversalTime() > now
            || identities[0].NotAfter.ToUniversalTime() <= now
            || identities[0].Extensions.OfType<X509BasicConstraintsExtension>().Any(value => value.CertificateAuthority))
        {
            foreach (var value in certificates) value.Dispose();
            throw new InvalidOperationException("The management HTTPS PFX needs one current server certificate with its private key.");
        }

        var leaf = identities[0];
        certificates.Remove(leaf);
        return new ControlHttps(address, port, localPort, leaf, certificates);
    }

    public void Configure(WebApplicationBuilder builder)
    {
        builder.WebHost.PreferHostingUrls(false).ConfigureKestrel(server =>
        {
            // In this mode instance settings own the listeners. Ambient endpoint
            // configuration must not open a second plaintext LAN listener.
            server.Configure(new ConfigurationBuilder().Build(), reloadOnChange: false);
            server.Listen(IPAddress.Loopback, localPort);
            server.Listen(address, port, endpoint =>
            {
                endpoint.UseHttps(https =>
                {
                    https.ServerCertificate = certificate;
                    https.ServerCertificateChain = intermediates;
                });
                endpoint.Use(next => connection =>
                {
                    if (connection.RemoteEndPoint is IPEndPoint remote && connection.LocalEndPoint is IPEndPoint local)
                        connection.Features.Set(new OperatorNetworkPeer(remote.Address, local.Address, local.Port));
                    return next(connection);
                });
            });
        });
    }

    public void Dispose()
    {
        certificate.Dispose();
        foreach (var value in intermediates) value.Dispose();
    }
}
