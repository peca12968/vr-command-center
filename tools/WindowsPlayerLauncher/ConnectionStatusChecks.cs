// Runs the actual launcher monitor class; fixture markers are not native admission evidence.
using System;
using System.IO;
using System.Text;

internal static class LauncherStateChecks
{
    private const string Session = "47379fa9-94af-4efb-8b75-5cd756a2b47e";
    private const string Pending = "VR_CLIENT_DEBRIEF_PENDING " + Session;
    private const string Final = "VR_CLIENT_DEBRIEF_FINAL {\"version\":1,\"roomId\":1,\"health\":80,"
        + "\"sessionId\":\"" + Session + "\",\"playerId\":\"1936d92f-a54b-499c-b53a-ea295242e423\","
        + "\"admissionId\":\"c1dbc468-bdfc-43b0-b6f3-16977164875a\",\"origin\":\"Simulation\","
        + "\"streamId\":\"a9dfdd94-ac80-4cb7-9761-613e0391db78\",\"throughSequence\":12,\"finalStreamSequence\":3,"
        + "\"worldSequence\":202,\"ammoUsed\":2,\"shotsHit\":1,\"kills\":1,\"hitsReceived\":1,\"damageTaken\":20,\"accuracyPercent\":50.0}";
    private const string Disconnect = "VR_CLIENT_DISCONNECTED";
    private static int checks;
    private static void Check(bool value) { if (!value) throw new InvalidOperationException("Launcher monitor check " + (checks + 1) + " failed."); checks++; }
    private static int Main(string[] args)
    {
        var root = Path.GetFullPath(args[0]); Directory.CreateDirectory(root);
        var monitor = new PlayerConnectionMonitor(Path.Combine(root, "missing.log")); monitor.Poll();
        Check(monitor.State == "Waiting" && !monitor.LogAvailable);
        monitor.WaitingSeconds(30); Check(monitor.State == "Unconfirmed");
        monitor.Observe("VR_CLIENT_CONNECTED id=1"); Check(monitor.State == "Connected");
        monitor.Observe("VR_CLIENT_DISCONNECTED"); Check(monitor.State == "Disconnected");
        monitor.Observe("VR_CLIENT_ADMISSION_REJECTED"); Check(monitor.State == "Rejected");
        monitor.Observe("VR_CLIENT_CONNECTED id=2"); monitor.Observe(Pending); monitor.Observe(Final);
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
        var result = new PlayerConnectionMonitor("unused");
        result.Observe(Pending); Check(result.State == "Waiting");
        result.Observe("VR_CLIENT_CONNECTED id=9");
        result.Observe(Pending + " extra"); result.Observe("VR_CLIENT_DEBRIEF_PENDING 00000000-0000-0000-0000-000000000000");
        Check(result.State == "Connected");
        result.Observe(Pending); result.Observe(Pending);
        Check(result.State == "ResultPending" && result.Transitions.Count == 3 && !result.Message.Contains("47379fa9"));
        result.Observe("VR_CLIENT_DEBRIEF_FINAL {\"version\":1}");
        Check(result.State == "ResultPending");
        result.Observe("VR_CLIENT_DISCONNECTED"); result.Observe("VR_CLIENT_DISCONNECTED");
        result.Observe(Final); result.Observe(Pending);
        Check(result.State == "ResultInterrupted" && result.Transitions.Count == 4);
        result.Observe("VR_CLIENT_CONNECTED id=10"); result.Observe(Pending); result.Observe(Final);
        result.Observe("VR_CLIENT_DISCONNECTED"); Check(result.State == "Final" && result.Transitions.Count == 7);

        var exitLog = Path.Combine(root, "exit.log");
        File.WriteAllText(exitLog, "VR_CLIENT_CONNECTED id=11\n" + Pending + "\n");
        var afterExit = new PlayerConnectionMonitor(exitLog); afterExit.Poll(exited: true);
        Check(afterExit.State == "ResultInterrupted" && afterExit.LogAvailable);
        File.AppendAllText(exitLog, new string('x', 140000) + "\n" + Final + "\nVR_CLIENT_DISCONNECTED\n");
        var drained = new PlayerConnectionMonitor(exitLog, verifyEvidence: true); drained.Poll(); Check(drained.State == "ResultPending");
        drained.Poll(exited: true); Check(drained.State == "Final" && drained.CanArchiveEvidence && !drained.Truncated);
        var partialFinal = Path.Combine(root, "partial-final.log");
        File.WriteAllText(partialFinal, "VR_CLIENT_CONNECTED id=12\n" + Pending + "\n" + Final);
        var incomplete = new PlayerConnectionMonitor(partialFinal); incomplete.Poll(exited: true);
        Check(incomplete.State == "ResultInterrupted");

        var connected = "VR_CLIENT_CONNECTED id=41\n";
        var reconnect = "VR_CLIENT_CONNECTED id=42\n";
        var resultLines = Pending + "\n" + Final + "\n";
        var oneResult = resultLines + Disconnect + "\n";
        var archive = new PlayerConnectionMonitor("unused", verifyEvidence: true);
        archive.Feed(connected + Disconnect + "\n" + reconnect + resultLines);
        Check(archive.State == "Final" && !archive.CanArchiveEvidence);
        archive.Feed(Disconnect + "\n");
        Check(archive.CanArchiveEvidence);
        archive.Feed("VR_CLIENT_CONNECTED id=43\n" + oneResult);
        Check(archive.State == "Final" && !archive.CanArchiveEvidence);

        foreach (var invalid in new[] {
            Final.Replace(Session, "d62ab0f8-742b-4098-9b30-5315cc107b61"),
            Final.Replace("\"worldSequence\":202", "\"worldSequence\":0"),
            Final.Replace("\"hitsReceived\":1", "\"hitsReceived\":\"1\""),
            Final.Replace("\"version\":1", "\"version\":1,\"version\":1"),
            Final.Replace("\"ammoUsed\":2", "\"ammoUsed\":null"),
            Final.Substring(0, Final.Length - 1) + new string(' ', 4096) + "}"
        })
        {
            var rejected = new PlayerConnectionMonitor("unused", verifyEvidence: true);
            rejected.Feed(connected + Pending + "\n" + invalid + "\n");
            Check(rejected.State == "ResultPending" && !rejected.CanArchiveEvidence);
            rejected.Feed(Final + "\n" + Disconnect + "\n");
            Check(rejected.State == "Final" && !rejected.CanArchiveEvidence);
        }
        foreach (var markers in new[] {
            connected + Final + "\n" + Disconnect + "\n",
            connected + Disconnect + "\n" + connected + oneResult,
            connected + reconnect + oneResult,
            connected + resultLines + Final + "\n" + Disconnect + "\n"
        })
        {
            var rejected = new PlayerConnectionMonitor("unused", verifyEvidence: true);
            rejected.Feed(markers);
            Check(!rejected.CanArchiveEvidence);
        }
        Console.WriteLine("{\"complete\":true,\"checks\":" + checks + ",\"scope\":\"Actual compiled Windows monitor; fixture markers, no native admission or GUI proof\"}");
        return 0;
    }
}
