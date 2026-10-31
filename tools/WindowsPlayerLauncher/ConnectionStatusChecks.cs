// Runs the actual launcher monitor class; fixture markers are not native admission evidence.
using System;
using System.IO;
using System.Text;

internal static class LauncherStateChecks
{
    private static int checks;
    private static void Check(bool value) { if (!value) throw new InvalidOperationException("Launcher monitor check failed."); checks++; }
    private static int Main(string[] args)
    {
        var root = Path.GetFullPath(args[0]); Directory.CreateDirectory(root);
        var monitor = new PlayerConnectionMonitor(Path.Combine(root, "missing.log")); monitor.Poll();
        Check(monitor.State == "Waiting" && !monitor.LogAvailable);
        monitor.WaitingSeconds(30); Check(monitor.State == "Unconfirmed");
        monitor.Observe("VR_CLIENT_CONNECTED id=1"); Check(monitor.State == "Connected");
        monitor.Observe("VR_CLIENT_DISCONNECTED"); Check(monitor.State == "Disconnected");
        monitor.Observe("VR_CLIENT_ADMISSION_REJECTED"); Check(monitor.State == "Rejected");
        monitor.Observe("VR_CLIENT_CONNECTED id=2"); monitor.Observe("VR_CLIENT_DEBRIEF_FINAL {\"version\":1}");
        monitor.Observe("VR_CLIENT_DISCONNECTED"); monitor.Observe("VR_CLIENT_ADMISSION_REJECTED"); Check(monitor.State == "Final");
        monitor.Observe("VR_CLIENT_CONNECTED id=3"); Check(monitor.State == "Connected");
        var partial = new PlayerConnectionMonitor("unused"); partial.Feed("VR_CLIENT_CONNE"); Check(partial.State == "Waiting");
        partial.Feed("CTED id=4\r\n"); Check(partial.State == "Connected");
        var noise = new PlayerConnectionMonitor("unused");
        noise.Feed("prefix VR_CLIENT_CONNECTED id=1\nVR_CLIENT_CONNECTED id=secret\nVR_CLIENT_DEBRIEF_FINAL {}\n"); Check(noise.State == "Waiting");
        noise.Feed(new string('x', 4097) + "VR_CLIENT_CONNECTED id=1\nVR_CLIENT_CONNECTED id=5\n"); Check(noise.State == "Connected");
        var utf = Path.Combine(root, "utf.log"); var bytes = Encoding.UTF8.GetBytes("繁"); File.WriteAllBytes(utf, new byte[] { bytes[0], bytes[1] });
        var decoder = new PlayerConnectionMonitor(utf); decoder.Poll();
        using (var file = new FileStream(utf, FileMode.Append)) { file.WriteByte(bytes[2]); var suffix = Encoding.UTF8.GetBytes("\nVR_CLIENT_CONNECTED id=6\n"); file.Write(suffix, 0, suffix.Length); }
        decoder.Poll(); Check(decoder.State == "Connected" && decoder.LogAvailable);
        File.WriteAllText(utf, "x"); decoder.Poll(); Check(decoder.Truncated && !decoder.LogAvailable);
        File.WriteAllText(utf, "VR_CLIENT_ADMISSION_REJECTED\n"); decoder.Poll(); Check(decoder.State == "Connected" && !decoder.LogAvailable);
        var large = Path.Combine(root, "large.log"); using (var file = File.Create(large)) file.SetLength(2 * 1024 * 1024 + 1);
        var bounded = new PlayerConnectionMonitor(large); bounded.Poll(); Check(bounded.Truncated && bounded.State == "Waiting");
        for (var i = 0; i < 70; i++) { monitor.Observe("VR_CLIENT_DISCONNECTED"); monitor.Observe("VR_CLIENT_CONNECTED id=1"); }
        Check(monitor.Truncated && monitor.Transitions.Count == 64);
        Check(!String.Join(",", monitor.Transitions.ToArray()).Contains("secret") && !monitor.Message.Contains("id="));
        Console.WriteLine("{\"complete\":true,\"checks\":" + checks + ",\"scope\":\"Actual compiled Windows monitor; fixture markers, no native admission or GUI proof\"}");
        return 0;
    }
}
