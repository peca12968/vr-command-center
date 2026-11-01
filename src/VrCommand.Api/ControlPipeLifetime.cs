using System.Text;

namespace VrCommand.Api;

// Opt-in, private parent/child pipe. It adds no HTTP shutdown or key endpoint.
internal static class ControlPipeLifetime
{
    public static void Attach(WebApplication app, string? token)
    {
        if (token is null) return;
        if (token.Length != 64 || token.Any(c => !char.IsAsciiHexDigitLower(c)))
            throw new InvalidOperationException("ControlPipeToken must be 64 lower-case hexadecimal characters.");
        app.Lifetime.ApplicationStarted.Register(() =>
        {
            try
            {
                Console.Out.WriteLine("VR_CONTROL_READY " + token);
                Console.Out.Flush();
            }
            catch (IOException) { app.Lifetime.StopApplication(); }
            _ = ObserveInput(app.Lifetime, token);
        });
    }

    private static async Task ObserveInput(IHostApplicationLifetime lifetime, string token)
    {
        try
        {
            using var input = Console.OpenStandardInput();
            var bytes = new byte[1];
            var line = new StringBuilder(80);
            while (!lifetime.ApplicationStopping.IsCancellationRequested)
            {
                var count = await input.ReadAsync(bytes, lifetime.ApplicationStopping);
                if (count == 0) break; // An exited parent closes its owned pipe.
                var c = (char)bytes[0];
                if (c == '\n')
                {
                    if (line.ToString() == "STOP " + token) break;
                    line.Clear(); // Unknown input never authorizes a stop.
                }
                else if (c != '\r')
                {
                    if (c < 32 || c > 126 || line.Length == 128) break;
                    line.Append(c);
                }
            }
        }
        catch (OperationCanceledException) when (lifetime.ApplicationStopping.IsCancellationRequested) { return; }
        catch (IOException) { }
        lifetime.StopApplication();
    }
}
