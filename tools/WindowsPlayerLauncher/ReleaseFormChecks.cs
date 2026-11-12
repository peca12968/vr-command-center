// Runs shipped WinForms handlers with real packaged children.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

public sealed class ReleaseFormChecks : MarshalByRefObject
{
    private int checks;
    private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

    [STAThread]
    private static int Main(string[] args)
    {
        var measured = args[0] == "--measured-session";
        var offset = measured ? 1 : 0;
        var package = Path.GetFullPath(args[offset]).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        var output = args[offset + 1];
        var domain = AppDomain.CreateDomain("Extracted player", null, new AppDomainSetup { ApplicationBase = package });
        try
        {
            var runner = (ReleaseFormChecks)domain.CreateInstanceFromAndUnwrap(typeof(ReleaseFormChecks).Assembly.Location,
                typeof(ReleaseFormChecks).FullName);
            var report = measured ? runner.RunMeasured(output, args[3], args[4]) : runner.Run(output, args[2], args[3], args[4]);
            using (var stream = new FileStream(Path.Combine(output, "release-form-checks.json"), FileMode.CreateNew))
            using (var writer = new StreamWriter(stream)) writer.WriteLine(report);
            return 0;
        }
        finally { AppDomain.Unload(domain); }
    }

    private void Check(bool condition, string label)
    {
        if (!condition) throw new InvalidOperationException(label);
        checks++;
    }

    private static T Field<T>(Form form, string name)
    {
        return (T)form.GetType().GetField(name, BindingFlags.NonPublic | BindingFlags.Instance).GetValue(form);
    }

    private static void Enter(Form form, TextBox field)
    {
        var message = Message.Create(field.Handle, 0x100, (IntPtr)Keys.Enter, IntPtr.Zero);
        form.GetType().GetMethod("ProcessCmdKey", BindingFlags.NonPublic | BindingFlags.Instance)
            .Invoke(form, new object[] { message, Keys.Enter });
    }

    private static string Hash(string path)
    {
        using (var source = File.OpenRead(path))
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(source)).Replace("-", "").ToLowerInvariant();
    }

    public string Run(string output, string config, string originalRelease, string otherRelease)
    {
        var root = AppDomain.CurrentDomain.BaseDirectory;
        if (!root.EndsWith(Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal))
            throw new InvalidOperationException("Framework fixture must use the executable's normal directory shape");
        var launcher = Assembly.LoadFrom(Path.Combine(root, "Launch-Player.exe"));
        var formType = launcher.GetType("PlayerLauncher+PlayerForm", true);
        var releaseCopy = Path.Combine(output, "reviewed-release.json");
        File.Copy(originalRelease, releaseCopy);
        var releaseHash = Hash(originalRelease);
        var configHash = Hash(config);
        var reportHash = Hash(Path.Combine(root, "player-package.json"));
        var runs = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VrCommand", "PlayerRuns");
        var before = Directory.Exists(runs) ? Directory.GetDirectories(runs) : new string[0];
        var oldRuntime = Environment.GetEnvironmentVariable("XR_RUNTIME_JSON");
        Environment.SetEnvironmentVariable("XR_RUNTIME_JSON", Path.Combine(output, "missing-openxr-runtime.json"));
        Process owned = null;
        try
        {
            using (var form = (Form)Activator.CreateInstance(formType, new object[] { config, null, null }))
            {
                form.ShowInTaskbar = false; form.Opacity = 0; form.Show();
                var path = Field<TextBox>(form, "path");
                var release = Field<TextBox>(form, "releasePath");
                var play = Field<Button>(form, "play");
                var records = Field<LinkLabel>(form, "records");
                var measureLink = Field<CheckBox>(form, "measureLink");
                Check(play.Enabled && !records.Visible, "Ordinary graphical mode remains available without a report");
                Check(!Field<Label>(form, "linkStatus").Visible, "Ordinary launches have no measurement status");
                Check(!measureLink.Enabled && !measureLink.Checked, "Measurement requires a reviewed release and starts unchecked");
                release.Text = otherRelease;
                Check(!play.Enabled, "An edited release path invalidates the previous selection");
                Enter(form, release);
                Check(!play.Enabled, "Another authentic release cannot authorize the package");
                release.Text = releaseCopy;
                Enter(form, release);
                Check(play.Enabled, "Matching reviewed release enables play");
                Check(measureLink.Enabled && !measureLink.Checked, "Matching reviewed release offers opt-in measurement");
                measureLink.Checked = true;
                File.AppendAllText(releaseCopy, "\n");
                play.PerformClick();
                Check(!play.Enabled && Field<Process>(form, "child") == null, "Modified report is rejected before spawning a game");
                Check(!measureLink.Enabled && !measureLink.Checked, "A modified release clears the opted-in measurement");
                Check(!Directory.Exists(runs) || Directory.GetDirectories(runs).Except(before).Count() == 0,
                    "A refused launch publishes no session records");
                Enter(form, path);
                Check(!play.Enabled, "Rechecking the config does not bypass the changed release");
                release.Text = "";
                Check(play.Enabled, "Removing the optional path enables ordinary launch");
                release.Text = originalRelease;
                Enter(form, release);
                Check(play.Enabled, "The original release can be loaded again");
                Field<RadioButton>(form, "openXR").Checked = true;
                play.PerformClick();
                var child = owned = Field<Process>(form, "child");
                Check(child != null && !release.Enabled && !path.Enabled && !play.Enabled, "Owned child freezes the reviewed selection");
                var pid = child.Id;
                form.Close();
                Check(!form.IsDisposed, "Closing the launcher during a bound run preserves its final-report writer");
                var wait = Stopwatch.StartNew();
                while (Field<Process>(form, "child") != null && wait.Elapsed < TimeSpan.FromSeconds(45))
                { Application.DoEvents(); Thread.Sleep(20); }
                if (Field<Process>(form, "child") == null) owned = null;
                Check(owned == null && release.Enabled && records.Visible, "Normal terminal UI publishes the records link");
                var directory = Directory.GetDirectories(runs).Except(before).Single();
                var log = Path.Combine(directory, "player.log");
                var report = Path.Combine(directory, "launch-report.json");
                var value = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(report));
                Check((string)value["status"] == "exited" && (int)value["processId"] == pid && (int)value["exitCode"] == 2,
                    "Terminal report belongs to the actual original OpenXR process");
                Check((string)value["playerManifestSha256"] == reportHash && (string)value["playerLogSha256"] == Hash(log),
                    "Terminal report binds the original package and log bytes");
                var messages = File.ReadAllText(log);
                Check(messages.Contains("VR_OPENXR_STARTUP status=") && !messages.Contains("VR_CLIENT_CONNECTED"),
                    "Actual child fails OpenXR setup before admission");
                Check(!File.Exists(Path.Combine(directory, "player-evidence.zip")), "Failed startup publishes no player evidence archive");
                Check(Hash(originalRelease) == releaseHash && Hash(config) == configHash, "Original input files are preserved");
                return Json.Serialize(new { complete = true, checks, processId = pid, recordsDirectory = directory });
            }
        }
        finally
        {
            Environment.SetEnvironmentVariable("XR_RUNTIME_JSON", oldRuntime);
            if (owned != null)
            {
                if (!owned.HasExited) { owned.Kill(); owned.WaitForExit(5000); }
                owned.Dispose();
            }
        }
    }

    public string RunMeasured(string output, string config, string originalRelease)
    {
        var launcher = Assembly.LoadFrom(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Launch-Player.exe"));
        var formType = launcher.GetType("PlayerLauncher+PlayerForm", true);
        var log = Path.Combine(output, "player.log");
        var report = Path.Combine(output, "launch-report.json");
        Process owned = null;
        try
        {
            using (var form = (Form)Activator.CreateInstance(formType, new object[] { config, log, report }))
            {
                form.ShowInTaskbar = false; form.Opacity = 0; form.Show();
                var release = Field<TextBox>(form, "releasePath");
                var measureLink = Field<CheckBox>(form, "measureLink");
                release.Text = originalRelease;
                Enter(form, release);
                Check(measureLink.Enabled && !measureLink.Checked, "Reviewed package offers measurement for the current game");
                measureLink.Checked = true;
                Field<Button>(form, "play").PerformClick();
                owned = Field<Process>(form, "child");
                Check(owned != null && !measureLink.Enabled && measureLink.Checked, "The actual graphical child owns the measurement selection");
                var pid = owned.Id;
                var finish = Path.Combine(output, "finish.request");
                var metrics = Path.Combine(output, "link-metrics.json");
                var linkStatus = Field<Label>(form, "linkStatus");
                Check(linkStatus.Visible && linkStatus.Text.Contains("等候"), "Measured launch starts waiting before a report exists");
                var wait = Stopwatch.StartNew();
                var closed = false;
                var previewSaved = false;
                while (Field<Process>(form, "child") != null && wait.Elapsed < TimeSpan.FromSeconds(145))
                {
                    if (!previewSaved && linkStatus.Text.StartsWith("連線量測已完成", StringComparison.Ordinal))
                    {
                        var saved = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(metrics));
                        var samples = ((IList)saved["samples"]).Cast<Dictionary<string, object>>().ToArray();
                        var replies = samples.Count(sample => (string)sample["result"] == "Reply");
                        var timeouts = samples.Count(sample => (string)sample["result"] == "Timeout");
                        var interrupted = samples.Count(sample => (string)sample["result"] == "Interrupted");
                        var expected = "連線量測已完成（30／30）　回覆 " + replies + "、逾時 " + timeouts + "、中斷 " + interrupted + "。";
                        Check(linkStatus.Text == expected && samples.Length == 30 && (bool)saved["complete"]
                            && (int)saved["processId"] == pid && !owned.HasExited, "Live form displays the original outcomes while the game is open");
                        CheckMeasurementPreview(launcher, output, metrics, pid, saved);
                        var previewProof = Path.Combine(output, "link-preview-ready.json");
                        File.WriteAllText(previewProof + ".tmp", Json.Serialize(new { processId = pid, replies, timeouts, interrupted, metricsSha256 = Hash(metrics) }));
                        File.Move(previewProof + ".tmp", previewProof);
                        previewSaved = true;
                    }
                    if (!closed && File.Exists(finish))
                    {
                        owned.Refresh();
                        closed = owned.HasExited || owned.CloseMainWindow();
                        if (closed)
                        {
                            Check(owned.WaitForExit(5000), "The original graphical child exits before the sharing test");
                            using (var lease = new FileStream(log, FileMode.Open, FileAccess.ReadWrite, FileShare.ReadWrite | FileShare.Delete))
                            {
                                var waitForSharing = Stopwatch.StartNew();
                                var terminalStatus = Field<Label>(form, "status");
                                while (!terminalStatus.Text.Contains("解除占用") && waitForSharing.Elapsed < TimeSpan.FromSeconds(2))
                                { Application.DoEvents(); Thread.Sleep(20); }
                                var pending = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(report));
                                Check(terminalStatus.Text.Contains("解除占用") && (string)pending["status"] == "started"
                                    && !Field<LinkLabel>(form, "records").Visible, "The form waits without replacing the original launch report during a sharing violation");
                            }
                        }
                    }
                    Application.DoEvents(); Thread.Sleep(20);
                }
                if (Field<Process>(form, "child") == null) owned = null;
                Check(owned == null, "Graphical player exits and the form completes its terminal report");
                Check(Field<LinkLabel>(form, "records").Visible && measureLink.Enabled && !measureLink.Checked,
                    "The record folder is available and the next launch starts unchecked");
                Check(previewSaved && File.Exists(metrics) && File.Exists(Path.Combine(output, "player-evidence.zip")),
                    "The form publishes the original measurement and measured ZIP");
                var result = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(report));
                var proof = (Dictionary<string, object>)result["linkMetrics"];
                Check((string)result["status"] == "exited" && (int)result["processId"] == pid && (int)result["exitCode"] == 0
                    && (string)proof["logSha256"] == Hash(log) && (string)proof["metricsSha256"] == Hash(metrics),
                    "The form binds both original files to the exited graphical child");
                return Json.Serialize(new { complete = true, checks, processId = pid, deferredSharing = true });
            }
        }
        finally
        {
            if (owned != null)
            {
                if (!owned.HasExited) { owned.Kill(); owned.WaitForExit(5000); }
                owned.Dispose();
            }
        }
    }

    private void CheckMeasurementPreview(Assembly launcher, string output, string metrics, int pid, Dictionary<string, object> report)
    {
        var type = launcher.GetType("PlayerLauncher+LinkMeasurement", true);
        var read = type.GetMethod("ReadReport");
        var preview = read.Invoke(null, new object[] { metrics, pid });
        var describe = type.GetMethod("Describe");
        var previous = Convert.ToUInt64(report["connection"]);
        Check(((string)describe.Invoke(preview, new object[] { previous == 0 ? 1UL : 0UL, false })).Contains("目前連線不符"),
            "A later connection cannot inherit the first connection's status");
        Check(((string)describe.Invoke(preview, new object[] { previous, true })).Contains("未涵蓋目前連線"),
            "A later admission cannot inherit the measurement even if a connection number is reused");
        Check(RejectMeasurement(read, metrics, 0), "A report for another process cannot become the current preview");
        var early = Path.Combine(output, "link-preview-early-fixture.json");
        report["complete"] = false;
        report["reason"] = "Ended";
        var last = (Dictionary<string, object>)((IList)report["samples"])[29];
        last["result"] = "Interrupted";
        File.WriteAllText(early, Json.Serialize(report));
        var stopped = read.Invoke(null, new object[] { early, pid });
        Check(((string)describe.Invoke(stopped, new object[] { previous, false })).StartsWith("連線量測已停止（30／30）", StringComparison.Ordinal),
            "An interrupted last attempt is not reported as a completed measurement");
        last["sequence"] = 29;
        var invalid = Path.Combine(output, "link-preview-invalid-fixture.json");
        File.WriteAllText(invalid, Json.Serialize(report));
        Check(RejectMeasurement(read, invalid, pid), "A repeated sample sequence cannot become the current preview");
    }

    private static bool RejectMeasurement(MethodInfo read, string file, int pid)
    {
        try { read.Invoke(null, new object[] { file, pid }); }
        catch (TargetInvocationException error)
        {
            if (!(error.InnerException is InvalidDataException)) throw;
            return true;
        }
        return false;
    }
}
