// Runs the shipped WinForms handlers with a real packaged child and a missing OpenXR runtime.
using System;
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
        var package = Path.GetFullPath(args[0]).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        var domain = AppDomain.CreateDomain("Extracted player", null, new AppDomainSetup { ApplicationBase = package });
        try
        {
            var runner = (ReleaseFormChecks)domain.CreateInstanceFromAndUnwrap(typeof(ReleaseFormChecks).Assembly.Location,
                typeof(ReleaseFormChecks).FullName);
            var report = runner.Run(args[1], args[2], args[3], args[4]);
            using (var stream = new FileStream(Path.Combine(args[1], "release-form-checks.json"), FileMode.CreateNew))
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
                Check(play.Enabled && !records.Visible, "Ordinary graphical mode remains available without a report");
                release.Text = otherRelease;
                Check(!play.Enabled, "An edited release path invalidates the previous selection");
                Enter(form, release);
                Check(!play.Enabled, "Another authentic release cannot authorize the package");
                release.Text = releaseCopy;
                Enter(form, release);
                Check(play.Enabled, "Matching reviewed release enables play");
                File.AppendAllText(releaseCopy, "\n");
                play.PerformClick();
                Check(!play.Enabled && Field<Process>(form, "child") == null, "Modified report is rejected before spawning a game");
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
}
