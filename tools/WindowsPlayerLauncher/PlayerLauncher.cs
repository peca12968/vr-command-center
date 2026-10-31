// Standalone Windows Forms entry point; no Unity, editor or management credentials.
// Built with the installed .NET Framework compiler by package-windows-player.py.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal static class PlayerLauncher
{
    private static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 4 * 1024 * 1024 };
    private static readonly string Root = AppDomain.CurrentDomain.BaseDirectory;
    private static string report;
    private static string statusReport;
    private static string lastStatusReport;
    private static bool SamePath(string a, string b) { return a != null && b != null && String.Equals(a, b, StringComparison.OrdinalIgnoreCase); }
    private static Dictionary<string, object> Map(object value) { return value as Dictionary<string, object>; }
    private static string Text(Dictionary<string, object> value, string key)
    { object result; return value.TryGetValue(key, out result) ? result as string : null; }
    private static int Number(Dictionary<string, object> value, string key)
    { object result; return value.TryGetValue(key, out result) && result is int ? (int)result : -1; }
    private static void Require(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }
    private static Dictionary<string, object> Read(string path, long max)
    {
        Require(new FileInfo(path).Length <= max, "檔案過大，請重新取得正確檔案。");
        var value = Map(Json.DeserializeObject(File.ReadAllText(path, Encoding.UTF8)));
        Require(value != null, "檔案格式不正確。"); return value;
    }
    private static void PlainPath(string path)
    {
        for (var current = new FileInfo(path) as FileSystemInfo; current != null; current = Directory.GetParent(current.FullName))
            Require((current.Attributes & FileAttributes.ReparsePoint) == 0, "請使用解壓後的實際資料夾，不要使用連結。");
    }
    private static string PackagePath(string name)
    {
        Require(!String.IsNullOrEmpty(name) && !Path.IsPathRooted(name) && name.IndexOf('\\') < 0 && name.IndexOf(':') < 0,
            "玩家包檔案路徑不正確。");
        foreach (var part in name.Split('/')) Require(part.Length > 0 && part != "." && part != "..", "玩家包檔案路徑不正確。");
        var path = Path.GetFullPath(Path.Combine(Root, name.Replace('/', Path.DirectorySeparatorChar)));
        Require(path.StartsWith(Root, StringComparison.OrdinalIgnoreCase), "玩家包檔案路徑不正確。");
        PlainPath(path); return path;
    }
    private static string Hash(string path)
    { using (var sha = SHA256.Create()) using (var file = File.OpenRead(path)) return BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "").ToLowerInvariant(); }
    private static void Verify()
    {
        PlainPath(Path.Combine(Root, "player-package.json"));
        var manifest = Read(Path.Combine(Root, "player-package.json"), 4 * 1024 * 1024);
        Require(Number(manifest, "version") == 1 && Text(manifest, "platform") == "Windows-x64", "玩家包版本不正確。");
        object rows; Require(manifest.TryGetValue("files", out rows) && rows is object[], "玩家包清單缺失。");
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var item in (object[])rows)
        {
            var row = Map(item); Require(row != null, "玩家包清單不正確。");
            var name = Text(row, "path"); var hash = Text(row, "sha256");
            Require(name != null && seen.Add(name) && hash != null && Regex.IsMatch(hash, "^[a-f0-9]{64}$"), "玩家包清單不正確。");
            var path = PackagePath(name); object size;
            Require(row.TryGetValue("bytes", out size) && (size is int || size is long), "玩家包大小不正確。");
            Require(new FileInfo(path).Length == Convert.ToInt64(size) && Hash(path) == hash, "玩家包不完整或已變更，請重新解壓完整檔案。");
        }
        Require(seen.Contains("VrCommand.exe") && seen.Contains("UnityPlayer.dll") && seen.Contains("Launch-Player.exe")
            && seen.Contains("VrCommand_Data/globalgamemanagers") && seen.Contains("build-receipt.json"), "玩家包缺少必要檔案。");
    }
    private static Dictionary<string, object> Config(string path)
    {
        PlainPath(path); var value = Read(path, 32768);
        Require(value.Count == 4 && value.ContainsKey("role") && value.ContainsKey("address") && value.ContainsKey("port") && value.ContainsKey("joinTicket"),
            "請選擇控制台下載的四欄玩家連線檔。");
        var address = Text(value, "address"); var ticket = Text(value, "joinTicket"); IPAddress parsed;
        Require(Text(value, "role") == "Client", "此啟動器只接受玩家連線檔。");
        Require(address != null && IPAddress.TryParse(address, out parsed) && parsed.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork
            && parsed.ToString() == address && parsed.GetAddressBytes()[0] > 0 && parsed.GetAddressBytes()[0] < 224,
            "連線地址須為完整 IPv4，請重新下載連線檔。");
        Require(Number(value, "port") >= 1024 && Number(value, "port") <= 65535 && !String.IsNullOrWhiteSpace(ticket) && ticket.Length <= 16384,
            "連線埠號或票券不正確，請重新下載連線檔。");
        return value; // Ticket validity, expiry and admission are verified by the game server.
    }
    private static string Quote(string value)
    {
        // Windows command-line escaping (including a trailing slash); no shell.
        var result = new StringBuilder("\""); int slashes = 0;
        foreach (var c in value)
        {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') result.Append('\\', slashes * 2 + 1); else result.Append('\\', slashes);
            result.Append(c); slashes = 0;
        }
        result.Append('\\', slashes * 2); return result.Append('"').ToString();
    }
    private static void Report(object value)
    {
        if (report == null) return;
        // Caller explicitly supplies this diagnostic path; never overwrite an input or package file.
        var temporary = report + "." + Guid.NewGuid().ToString("N") + ".tmp";
        File.WriteAllText(temporary, Json.Serialize(value), new UTF8Encoding(false));
        if (File.Exists(report)) File.Delete(report);
        File.Move(temporary, report);
    }
    private static void StatusReport(PlayerConnectionMonitor monitor, int processId, bool exited)
    {
        if (statusReport == null) return;
        var value = Json.Serialize(new { version = 1, processId = processId, exited = exited,
            state = monitor.State, logAvailable = monitor.LogAvailable, complete = !monitor.Truncated, transitions = monitor.Transitions });
        if (value == lastStatusReport) return;
        var temporary = statusReport + "." + Guid.NewGuid().ToString("N") + ".tmp";
        File.WriteAllText(temporary, value, new UTF8Encoding(false));
        if (File.Exists(statusReport)) File.Delete(statusReport);
        File.Move(temporary, statusReport);
        lastStatusReport = value;
    }
    private static Process Launch(string config, bool headless, string log)
    {
        Verify(); Config(config);
        var args = "--vr-config " + Quote(config) + " -job-worker-count 2";
        if (headless) args += " -batchmode -nographics";
        if (log != null) args += " -logFile " + Quote(log);
        var child = Process.Start(new ProcessStartInfo(Path.Combine(Root, "VrCommand.exe"), args)
        { UseShellExecute = false, WorkingDirectory = Root, CreateNoWindow = headless });
        Require(child != null, "無法啟動玩家程式。");
        try { Report(new { status = "started", processId = child.Id }); return child; }
        catch { if (!child.HasExited) { child.Kill(); child.WaitForExit(); } child.Dispose(); throw; }
    }
    [STAThread]
    private static int Main(string[] args)
    {
        string config = null, log = null; bool launch = false, wait = false, headless = false, verify = false;
        try
        {
            for (var i = 0; i < args.Length; i++)
            {
                if (args[i] == "--launch") launch = true;
                else if (args[i] == "--wait") wait = true;
                else if (args[i] == "--headless") headless = true;
                else if (args[i] == "--verify") verify = true;
                else if ((args[i] == "--config" || args[i] == "--log" || args[i] == "--report" || args[i] == "--status-report") && i + 1 < args.Length)
                {
                    var option = args[i++]; var path = Path.GetFullPath(args[i]);
                    if (option == "--config") config = path; else if (option == "--log") log = path; else if (option == "--report") report = path; else statusReport = path;
                }
                else throw new InvalidDataException("啟動選項不正確。");
            }
            Require(report == null || (!File.Exists(report) && !report.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !SamePath(report, config) && !SamePath(report, log)),
                "診斷報告須使用玩家包外的新路徑。");
            Require(log == null || (!File.Exists(log) && !log.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !SamePath(log, config)),
                "診斷記錄須使用玩家包外的新路徑。");
            Require(statusReport == null || (!verify && launch && wait && log != null && !File.Exists(statusReport) && !statusReport.StartsWith(Root, StringComparison.OrdinalIgnoreCase)
                && !SamePath(statusReport, config) && !SamePath(statusReport, log) && !SamePath(statusReport, report)), "連線狀態報告須搭配等待啟動及獨立的新記錄路徑。");
            Require((!headless && !wait || launch) && (!launch || config != null), "請提供玩家連線檔。");
            if (verify) { Verify(); Report(new { status = "verified" }); return 0; }
            if (launch)
            {
                using (var child = Launch(config, headless, log))
                {
                    if (!wait) return 0;
                    if (statusReport == null) child.WaitForExit();
                    else
                    {
                        var monitor = new PlayerConnectionMonitor(log);
                        while (!child.WaitForExit(200)) { monitor.Poll(); StatusReport(monitor, child.Id, false); }
                        monitor.Poll(); StatusReport(monitor, child.Id, true);
                    }
                    Report(new { status = "exited", processId = child.Id, exitCode = child.ExitCode }); return child.ExitCode;
                }
            }
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new PlayerForm(config, log)); return 0;
        }
        catch
        {
            // Serializer / IO exception text can contain input. Do not echo secrets or file contents.
            if (report != null && !File.Exists(report) && !report.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !SamePath(report, config) && !SamePath(report, log))
                try { Report(new { status = "rejected", reason = "Package, connection file or launch options are invalid." }); } catch { }
            if (report == null) MessageBox.Show("無法啟動。請確認玩家包已完整解壓，並重新選擇控制台下載的玩家連線檔。", "VR Command 玩家", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return 1;
        }
    }
    private sealed class PlayerForm : Form
    {
        private readonly Label selected = new Label { AutoSize = false, Dock = DockStyle.Top, Height = 75, UseMnemonic = false };
        private readonly Label status = new Label { AutoSize = false, Dock = DockStyle.Top, Height = 65 };
        private readonly Button play = new Button { Text = "開始遊戲", AutoSize = true, Enabled = false };
        private string config; private Process child; private PlayerConnectionMonitor monitor;
        public PlayerForm(string initial, string diagnosticLog)
        {
            Text = "VR Command 玩家"; ClientSize = new Size(560, 285); MinimumSize = new Size(576, 324);
            Font = new Font("Microsoft JhengHei UI", 11); Padding = new Padding(20); StartPosition = FormStartPosition.CenterScreen;
            var title = new Label { Text = "選擇控制台下載的玩家連線檔", Dock = DockStyle.Top, Height = 40 };
            var buttons = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 45 };
            var choose = new Button { Text = "選擇連線檔…", AutoSize = true };
            buttons.Controls.Add(choose); buttons.Controls.Add(play);
            var hint = new Label { Text = "票券過期或入場被拒絕時，請向控制人員重新取得連線檔。", Dock = DockStyle.Top, Height = 50 };
            Controls.Add(hint); Controls.Add(status); Controls.Add(buttons); Controls.Add(selected); Controls.Add(title);
            choose.Click += delegate
            {
                using (var dialog = new OpenFileDialog { Filter = "玩家連線檔 (*.json)|*.json", CheckFileExists = true, Multiselect = false })
                    if (dialog.ShowDialog(this) == DialogResult.OK) SelectConfig(dialog.FileName);
            };
            play.Click += delegate
            {
                play.Enabled = false; status.Text = "正在核對玩家包…"; Refresh();
                try
                {
                    var ownLog = diagnosticLog;
                    if (ownLog == null)
                    {
                        var directory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VrCommand", "PlayerRuns", Guid.NewGuid().ToString("N"));
                        Directory.CreateDirectory(directory); ownLog = Path.Combine(directory, "player.log");
                    }
                    child = Launch(config, false, ownLog); monitor = new PlayerConnectionMonitor(ownLog);
                    choose.Enabled = false; status.Text = monitor.Message;
                }
                catch { status.Text = "無法啟動，請重新解壓玩家包並選擇正確的玩家連線檔。"; play.Enabled = true; }
            };
            var timer = new Timer { Interval = 500 };
            timer.Tick += delegate
            {
                if (child == null) return;
                monitor.Poll(); status.Text = monitor.Message;
                if (child.HasExited)
                {
                    var final = monitor.State == "Final"; child.Dispose(); child = null; choose.Enabled = true; play.Enabled = config != null;
                    status.Text = final ? "遊戲已關閉；本次已收到最終戰績。" : "遊戲已關閉。" + monitor.Message;
                }
            };
            timer.Start(); FormClosed += delegate { timer.Dispose(); if (child != null) child.Dispose(); };
            selected.Text = "尚未選擇連線檔";
            if (initial != null) SelectConfig(initial);
        }
        private void SelectConfig(string file)
        {
            try { var value = Config(file); config = Path.GetFullPath(file); selected.Text = Path.GetFileName(file) + "\n伺服器 " + TextValue(value); play.Enabled = true; status.Text = "連線檔已選擇。按「開始遊戲」入場。"; }
            catch { config = null; play.Enabled = false; selected.Text = "未接受此連線檔"; status.Text = "請使用控制台下載的玩家連線檔。"; }
        }
        private static string TextValue(Dictionary<string, object> value) { return PlayerLauncher.Text(value, "address") + ":" + Number(value, "port"); }
    }
}

// Reads only the fresh log explicitly assigned to this launch. No global Player.log,
// network probe, payload parsing, process inspection or changes to game state.
internal sealed class PlayerConnectionMonitor
{
    private readonly string path;
    private readonly Stopwatch clock = Stopwatch.StartNew();
    private readonly Decoder decoder = Encoding.UTF8.GetDecoder();
    private readonly StringBuilder line = new StringBuilder();
    private long offset;
    private bool discardLine;
    private bool invalidLog;
    public string State { get; private set; }
    public bool LogAvailable { get; private set; }
    public bool Truncated { get; private set; }
    public readonly List<string> Transitions = new List<string>();
    public PlayerConnectionMonitor(string log) { path = log; Change("Waiting"); }
    private void Change(string state)
    {
        if (State == state) return;
        State = state;
        if (Transitions.Count < 64) Transitions.Add(state); else Truncated = true;
    }
    internal void Observe(string value)
    {
        // Exact markers only. Never serialize or display arbitrary log text / IDs.
        if (Regex.IsMatch(value, "^VR_CLIENT_CONNECTED id=[0-9]+$")) Change("Connected");
        else if (State == "Final") return;
        else if (value == "VR_CLIENT_ADMISSION_REJECTED") Change("Rejected");
        else if (value == "VR_CLIENT_DISCONNECTED" && State != "Final") Change("Disconnected");
        else if (value.StartsWith("VR_CLIENT_DEBRIEF_FINAL {", StringComparison.Ordinal) && State == "Connected") Change("Final");
    }
    internal void WaitingSeconds(double seconds) { if (State == "Waiting" && seconds >= 30) Change("Unconfirmed"); }
    internal void Feed(string value)
    {
        foreach (var c in value)
        {
            if (c == '\n') { if (!discardLine) Observe(line.ToString().TrimEnd('\r')); line.Clear(); discardLine = false; }
            else if (!discardLine)
            {
                if (line.Length < 4096) line.Append(c);
                else { line.Clear(); discardLine = true; }
            }
        }
    }
    public void Poll()
    {
        WaitingSeconds(clock.Elapsed.TotalSeconds);
        if (invalidLog) return;
        try
        {
            using (var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            {
                if (file.Length < offset || file.Length - offset > 2 * 1024 * 1024)
                { LogAvailable = false; Truncated = true; invalidLog = true; return; }
                file.Position = offset; var bytes = new byte[65536]; var chars = new char[65536];
                var length = file.Read(bytes, 0, bytes.Length); offset += length;
                Feed(new string(chars, 0, decoder.GetChars(bytes, 0, length, chars, 0, false))); LogAvailable = true;
            }
        }
        catch (IOException) { LogAvailable = false; }
        catch (UnauthorizedAccessException) { LogAvailable = false; }
    }
    public string Message
    {
        get
        {
            if (State == "Final") return "遊戲回報已收到最終戰績。結束斷線不會清除戰績。";
            if (State == "Rejected") return "遊戲回報入場遭拒。請向控制人員重新取得自己的連線檔。";
            if (State == "Disconnected") return "遊戲回報連線中斷。可在遊戲內重新讀取控制人員更新的票券。";
            if (State == "Connected") return LogAvailable ? "遊戲已回報入場。請切換到遊戲視窗；可關閉此啟動器。" : "先前已回報入場，目前無法讀取連線記錄。請查看遊戲視窗。";
            return State == "Unconfirmed" ? "尚未收到入場確認。請核對伺服器IPv4、UDP埠與遊戲版本，並查看遊戲視窗。" : "遊戲已啟動，正在等待入場確認…";
        }
    }
}
