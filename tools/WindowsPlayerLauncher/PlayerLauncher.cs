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
    private static Dictionary<string, object> Read(string path, long max, string expectedHash = null)
    {
        using (var file = File.OpenRead(path))
        {
            Require(file.Length <= max, "檔案過大，請重新取得正確檔案。");
            if (expectedHash != null)
            {
                Require(Hash(file) == expectedHash, "本機玩家包清單與場館發行報告不同。");
                file.Position = 0;
            }
            using (var reader = new StreamReader(file, Encoding.UTF8))
            {
                var value = Map(Json.DeserializeObject(reader.ReadToEnd()));
                Require(value != null, "檔案格式不正確。"); return value;
            }
        }
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
    { using (var file = File.OpenRead(path)) return Hash(file); }
    private static string Hash(Stream stream)
    { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
    private static string ReadReleaseManifestHash(string path)
    {
        PlainPath(path);
        var release = Read(path, 8192);
        object verified, windows;
        Require(release.TryGetValue("verified", out verified) && verified is bool && (bool)verified
            && Text(release, "scope") == "offline-package-consistency", "請使用已核對的場館發行報告。");
        Require(release.TryGetValue("windows", out windows) && Map(windows) != null, "發行報告缺少 Windows 玩家套件資訊。");
        var hash = Text(Map(windows), "playerManifestSha256");
        Require(hash != null && Regex.IsMatch(hash, @"\A[a-f0-9]{64}\z"), "發行報告缺少有效的 Windows 玩家套件清單雜湊。");
        return hash;
    }
    private static void Verify(string releaseManifestHash = null)
    {
        var manifestPath = Path.Combine(Root, "player-package.json");
        PlainPath(manifestPath);
        var manifest = Read(manifestPath, 4 * 1024 * 1024, releaseManifestHash);
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
        if (releaseManifestHash != null)
        {
            seen.Add("player-package.json");
            var directories = new Stack<string>();
            directories.Push(Root);
            while (directories.Count != 0)
            {
                foreach (var entry in Directory.EnumerateFileSystemEntries(directories.Pop()))
                {
                    var attributes = File.GetAttributes(entry);
                    Require((attributes & FileAttributes.ReparsePoint) == 0, "發行包不能包含檔案或目錄連結。");
                    if ((attributes & FileAttributes.Directory) != 0) directories.Push(entry);
                    else Require(seen.Remove(entry.Substring(Root.Length).Replace('\\', '/')), "本機玩家包含有發行清單外的檔案。");
                }
            }
            Require(seen.Count == 0, "本機玩家包缺少發行清單中的檔案。");
        }
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
        return value; // The server decides ticket validity, expiry and admission.
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
    private static void ProcessReport(string status, string releaseManifestHash, Process child = null,
        bool exited = false, string linkMetrics = null, string log = null)
    {
        var value = new Dictionary<string, object> { { "status", status } };
        if (child != null) value.Add("processId", child.Id);
        if (exited) value.Add("exitCode", child.ExitCode);
        if (linkMetrics != null) value.Add("linkMetrics", LinkEvidence(linkMetrics, log));
        if (releaseManifestHash != null) value.Add("playerManifestSha256", releaseManifestHash);
        Report(value);
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
    private static string EvidenceHash(string path, long limit)
    {
        if (!File.Exists(path)) return null;
        PlainPath(path);
        using (var file = File.OpenRead(path))
            return file.Length > 0 && file.Length <= limit ? Hash(file) : null;
    }
    private static object LinkEvidence(string metrics, string log)
    {
        try
        {
            var metricsHash = EvidenceHash(metrics, 64 * 1024);
            var logHash = EvidenceHash(log, 16 * 1024 * 1024);
            if (metricsHash != null && logHash != null) return new { metricsSha256 = metricsHash, logSha256 = logHash };
        }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
        catch (InvalidDataException) { }
        return null;
    }
    private static Process Launch(string config, bool headless, string log, string reviewedHash = null, bool openXR = false,
        string linkMetrics = null, string releaseManifestHash = null)
    {
        Verify(releaseManifestHash); Config(config);
        Require(reviewedHash == null || Hash(config) == reviewedHash, "連線檔已變更，請重新載入後核對。");
        var args = "--vr-config " + Quote(config) + " -job-worker-count 2";
        if (headless) args += " -batchmode -nographics";
        if (openXR) args += " -force-d3d11 --vr-openxr";
        if (log != null) args += " -logFile " + Quote(log);
        if (linkMetrics != null) args += " --vr-link-metrics " + Quote(linkMetrics);
        var child = Process.Start(new ProcessStartInfo(Path.Combine(Root, "VrCommand.exe"), args)
        { UseShellExecute = false, WorkingDirectory = Root, CreateNoWindow = headless });
        Require(child != null, "無法啟動玩家程式。");
        try { ProcessReport("started", releaseManifestHash, child); return child; }
        catch { if (!child.HasExited) { child.Kill(); child.WaitForExit(); } child.Dispose(); throw; }
    }
    [STAThread]
    private static int Main(string[] args)
    {
        string config = null, log = null, linkMetrics = null, releasePath = null;
        bool launch = false, wait = false, headless = false, verify = false, openXR = false, invalidEvidenceOption = false;
        try
        {
            for (var i = 0; i < args.Length; i++)
            {
                if (args[i] == "--launch") launch = true;
                else if (args[i] == "--wait") wait = true;
                else if (args[i] == "--headless") headless = true;
                else if (args[i] == "--openxr") openXR = true;
                else if (args[i] == "--verify") verify = true;
                else if (args[i] == "--link-metrics" || args[i] == "--release-report")
                {
                    var option = args[i];
                    if (i + 1 == args.Length || args[i + 1].StartsWith("--", StringComparison.Ordinal)) invalidEvidenceOption = true;
                    else
                    {
                        var path = Path.GetFullPath(args[++i]);
                        if (option == "--link-metrics" && linkMetrics == null) linkMetrics = path;
                        else if (option == "--release-report" && releasePath == null) releasePath = path;
                        else invalidEvidenceOption = true;
                    }
                }
                else if ((args[i] == "--config" || args[i] == "--log" || args[i] == "--report" || args[i] == "--status-report") && i + 1 < args.Length)
                {
                    var option = args[i++]; var path = Path.GetFullPath(args[i]);
                    if (option == "--config") config = path; else if (option == "--log") log = path; else if (option == "--report") report = path; else statusReport = path;
                }
                else throw new InvalidDataException("啟動選項不正確。");
            }
            Require(report == null || (!File.Exists(report) && !report.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !SamePath(report, config) && !SamePath(report, log) && !SamePath(report, linkMetrics)),
                "診斷報告須使用玩家包外的新路徑。");
            Require(log == null || (!File.Exists(log) && !log.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !SamePath(log, config)),
                "診斷記錄須使用玩家包外的新路徑。");
            Require(statusReport == null || (!verify && launch && wait && log != null && !File.Exists(statusReport) && !statusReport.StartsWith(Root, StringComparison.OrdinalIgnoreCase)
                && !SamePath(statusReport, config) && !SamePath(statusReport, log) && !SamePath(statusReport, report)), "連線狀態報告須搭配等待啟動及獨立的新記錄路徑。");
            Require((!headless && !wait || launch) && (!launch || config != null), "請提供玩家連線檔。");
            Require(!openXR || (launch && !headless && !verify), "OpenXR 需要直接啟動有圖形的玩家端。");
            Require(!invalidEvidenceOption, "連線量測與發行報告各只能指定一份檔案。");
            if (linkMetrics != null)
            {
                Require(launch && wait && !verify && log != null && report != null && String.Equals(Path.GetExtension(linkMetrics), ".json", StringComparison.OrdinalIgnoreCase)
                    && !linkMetrics.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !File.Exists(linkMetrics) && !Directory.Exists(linkMetrics)
                    && !SamePath(linkMetrics, config) && !SamePath(linkMetrics, log) && !SamePath(linkMetrics, statusReport),
                    "連線量測須搭配等待啟動，並使用玩家包外獨立的新 JSON 路徑及原日誌、程序報告。");
                foreach (var path in new[] { linkMetrics, log, report, statusReport })
                    if (path != null) PlainPath(Path.GetDirectoryName(path));
            }
            Require(releasePath == null || ((verify != launch) && !SamePath(releasePath, config) && !SamePath(releasePath, log)
                && !SamePath(releasePath, statusReport) && !SamePath(releasePath, linkMetrics) && !SamePath(releasePath, report)),
                "發行報告須搭配核對或直接啟動，並使用獨立路徑。");
            var releaseManifestHash = releasePath == null ? null : ReadReleaseManifestHash(releasePath);
            if (verify) { Verify(releaseManifestHash); ProcessReport("verified", releaseManifestHash); return 0; }
            if (launch)
            {
                using (var child = Launch(config, headless, log, openXR: openXR, linkMetrics: linkMetrics, releaseManifestHash: releaseManifestHash))
                {
                    if (!wait) return 0;
                    if (statusReport == null) child.WaitForExit();
                    else
                    {
                        var monitor = new PlayerConnectionMonitor(log);
                        while (!child.WaitForExit(200)) { monitor.Poll(); StatusReport(monitor, child.Id, false); }
                        monitor.Poll(exited: true); StatusReport(monitor, child.Id, true);
                    }
                    ProcessReport("exited", releaseManifestHash, child, exited: true, linkMetrics: linkMetrics, log: log);
                    return child.ExitCode;
                }
            }
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new PlayerForm(config, log)); return 0;
        }
        catch
        {
            // Serializer / IO exception text can contain input. Do not echo secrets or file contents.
            if (report != null && !File.Exists(report) && !report.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !SamePath(report, config)
                && !SamePath(report, log) && !SamePath(report, linkMetrics) && !SamePath(report, releasePath))
                try { Report(new { status = "rejected", reason = "Package, connection file or launch options are invalid." }); } catch { }
            if (report == null) MessageBox.Show("無法啟動。請確認玩家包已完整解壓，並重新選擇控制台下載的玩家連線檔。", "VR Command 玩家", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return 1;
        }
    }
    // A review is a local preflight, not a ticket validation or an atomic handoff
    // to Unity. Reconnect still reads the original path using the original rules.
    internal sealed class ConfigReview
    {
        public string FilePath { get; private set; }
        public string ContentHash { get; private set; }
        public string Endpoint { get; private set; }
        public TicketPreview Ticket { get; private set; }
        public bool Loaded { get { return FilePath != null; } }
        public void Clear() { FilePath = null; ContentHash = null; Endpoint = null; Ticket = null; }
        public void Load(string file)
        {
            Clear();
            Require(!String.IsNullOrWhiteSpace(file) && Path.IsPathRooted(file) && Path.GetPathRoot(file).Length > 2, "請輸入連線檔完整路徑。");
            var full = Path.GetFullPath(file); PlainPath(full);
            // Prevent a writer changing the bytes between parsing and hashing.
            using (var lease = new FileStream(full, FileMode.Open, FileAccess.Read, FileShare.Read))
            {
                var value = Config(full); var hash = Hash(full);
                FilePath = full; ContentHash = hash;
                Endpoint = Text(value, "address") + ":" + Number(value, "port");
                Ticket = TicketPreview.Read(Text(value, "joinTicket"));
            }
        }
        public void RequireCurrent()
        {
            try
            {
                Require(Loaded, "請先載入連線檔。");
                PlainPath(FilePath);
                using (var lease = new FileStream(FilePath, FileMode.Open, FileAccess.Read, FileShare.Read))
                    Require(Hash(FilePath) == ContentHash, "連線檔已變更，請重新載入後核對。");
            }
            catch { Clear(); throw; }
        }
    }
    internal sealed class TicketPreview
    {
        public int Room { get; private set; }
        public int Seat { get; private set; }
        public DateTimeOffset ExpiresAtUtc { get; private set; }

        public static TicketPreview Read(string ticket)
        {
            // Only read the public display fields of the current v2 layout. Unknown shapes
            // still reach the original game path, which checks the signature and admission.
            if (ticket == null || ticket.Length != 147 ||
                !Regex.IsMatch(ticket, @"\Av2\.[A-Za-z0-9_-]{100}\.[A-Za-z0-9_-]{43}\z")) return null;
            var payload = Convert.FromBase64String(ticket.Substring(3, 100).Replace('-', '+').Replace('_', '/'));
            if (payload[0] != 2 || payload[49] < 1 || payload[49] > 5 || payload[50] > 4) return null;
            long seconds = 0;
            for (var offset = 51; offset < 59; offset++) seconds = (seconds << 8) | payload[offset];
            if (seconds <= 0 || seconds > 253402300799L) return null;
            return new TicketPreview { Room = payload[49], Seat = payload[50] + 1,
                ExpiresAtUtc = DateTimeOffset.FromUnixTimeSeconds(seconds) };
        }

        public string SeatLabel { get { return "連線檔標示　房間 " + Room + "／席位 " + Seat; } }
        public string Describe(DateTimeOffset now)
        {
            var remaining = ExpiresAtUtc - now;
            var localExpiry = ExpiresAtUtc.ToLocalTime().ToString("HH:mm:ss", System.Globalization.CultureInfo.InvariantCulture);
            var detail = remaining <= TimeSpan.Zero ? "依本機時間已過期，請向控制人員重取連線檔。"
                : remaining > TimeSpan.FromMinutes(5) ? "票券時間與本機可能不同，請核對電腦時鐘。"
                : "依本機時間尚餘 " + TimeSpan.FromSeconds(Math.Ceiling(remaining.TotalSeconds)).ToString(@"mm\:ss") + "。";
            return SeatLabel + "　到期 " + localExpiry + "\n" + detail;
        }
    }
    private sealed class PlayerForm : Form
    {
        private readonly Label selected = new Label { AutoSize = false, Dock = DockStyle.Top, Height = 75, UseMnemonic = false };
        private readonly Label ticketInfo = new Label { AutoSize = false, Dock = DockStyle.Top, Height = 58, UseMnemonic = false };
        private readonly Label status = new Label { AutoSize = false, Dock = DockStyle.Top, Height = 65 };
        private readonly Button play = new Button { Text = "開始遊戲", AutoSize = true, Enabled = false };
        private readonly TextBox path = new TextBox { Dock = DockStyle.Top, AccessibleName = "玩家連線檔完整路徑" };
        private readonly ConfigReview review = new ConfigReview();
        private bool settingPath;
        private Process child; private PlayerConnectionMonitor monitor;
        public PlayerForm(string initial, string diagnosticLog)
        {
            Text = "VR Command 玩家"; ClientSize = new Size(660, 438); MinimumSize = new Size(676, 477);
            Font = new Font("Microsoft JhengHei UI", 11); Padding = new Padding(20); StartPosition = FormStartPosition.CenterScreen;
            var title = new Label { Text = "選擇控制台下載的玩家連線檔", Dock = DockStyle.Top, Height = 40 };
            var buttons = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 45 };
            var choose = new Button { Text = "選擇連線檔…", AutoSize = true };
            var load = new Button { Text = "載入／更新", AutoSize = true };
            buttons.Controls.Add(choose); buttons.Controls.Add(load); buttons.Controls.Add(play);
            var pathHint = new Label { Text = "可選檔或貼上完整路徑，再按「載入／更新」。", Dock = DockStyle.Top, Height = 35 };
            var hint = new Label { Text = "票券過期或入場被拒絕時，請向控制人員重新取得連線檔。", Dock = DockStyle.Top, Height = 50 };
            Controls.Add(hint); Controls.Add(status); Controls.Add(buttons); Controls.Add(ticketInfo); Controls.Add(selected); Controls.Add(pathHint); Controls.Add(path); Controls.Add(title);
            path.TextChanged += delegate
            {
                if (settingPath) return;
                review.Clear(); play.Enabled = false; selected.Text = "路徑已變更，請重新載入。";
                RenderTicket();
                status.Text = "未沿用先前選取的連線檔。";
            };
            load.Click += delegate { SelectConfig(path.Text); };
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
                    review.RequireCurrent();
                    var ownLog = diagnosticLog;
                    if (ownLog == null)
                    {
                        var directory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VrCommand", "PlayerRuns", Guid.NewGuid().ToString("N"));
                        Directory.CreateDirectory(directory); ownLog = Path.Combine(directory, "player.log");
                    }
                    child = Launch(review.FilePath, false, ownLog, review.ContentHash); monitor = new PlayerConnectionMonitor(ownLog);
                    choose.Enabled = false; load.Enabled = false; path.Enabled = false; status.Text = monitor.Message;
                    RenderTicket();
                }
                catch { review.Clear(); RenderTicket(); selected.Text = "請重新載入並核對連線檔。"; status.Text = "無法啟動或檔案已變更。請確認玩家包完整，再重新載入正確的連線檔。"; play.Enabled = false; }
            };
            var timer = new Timer { Interval = 500 };
            timer.Tick += delegate
            {
                if (child == null) { RenderTicket(); return; }
                var exited = child.HasExited;
                monitor.Poll(exited); status.Text = monitor.Message;
                if (exited)
                {
                    var final = monitor.State == "Final"; child.Dispose(); child = null; choose.Enabled = true; load.Enabled = true; path.Enabled = true; play.Enabled = review.Loaded;
                    RenderTicket();
                    status.Text = final ? "遊戲已關閉；本次已收到最終戰績。" : "遊戲已關閉。" + monitor.Message;
                }
            };
            timer.Start(); FormClosed += delegate { timer.Dispose(); if (child != null) child.Dispose(); };
            selected.Text = "尚未選擇連線檔";
            if (initial != null) SelectConfig(initial);
        }
        private void SelectConfig(string file)
        {
            try
            {
                review.Load(file); settingPath = true;
                try { path.Text = review.FilePath; } finally { settingPath = false; }
                selected.Text = Path.GetFileName(review.FilePath) + "\n伺服器 " + review.Endpoint;
                RenderTicket();
                play.Enabled = true; status.Text = "連線檔已載入。核對目的地與席位後按「開始遊戲」。";
            }
            catch { review.Clear(); RenderTicket(); play.Enabled = false; selected.Text = "未接受此連線檔"; status.Text = "請使用控制台下載的玩家連線檔完整路徑。"; }
        }
        private void RenderTicket()
        {
            var ticket = review.Ticket;
            var text = ticket != null ? (child == null ? ticket.Describe(DateTimeOffset.UtcNow) : ticket.SeatLabel)
                : review.Loaded ? "無法預覽房間、席位與效期。入場由遊戲伺服器確認。" : "";
            if (ticketInfo.Text != text) ticketInfo.Text = text;
        }
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
        else if ((value == "VR_OPENXR_STARTUP status=rejected" || value == "VR_OPENXR_STARTUP status=unavailable")
                 && (State == "Waiting" || State == "Unconfirmed")) Change("OpenXRUnavailable");
        else if (value == "VR_CLIENT_ADMISSION_REJECTED") Change("Rejected");
        else if (value == "VR_CLIENT_DISCONNECTED")
        {
            if (State == "ResultPending") Change("ResultInterrupted");
            else if (State != "ResultInterrupted") Change("Disconnected");
        }
        else if (State == "Connected" && IsPendingMarker(value)) Change("ResultPending");
        else if ((State == "Connected" || State == "ResultPending") && value.StartsWith("VR_CLIENT_DEBRIEF_FINAL {", StringComparison.Ordinal)) Change("Final");
    }
    private static bool IsPendingMarker(string value)
    {
        const string prefix = "VR_CLIENT_DEBRIEF_PENDING ";
        Guid session;
        return value.Length == prefix.Length + 36 && value.StartsWith(prefix, StringComparison.Ordinal)
            && Guid.TryParseExact(value.Substring(prefix.Length), "D", out session) && session != Guid.Empty;
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
    public void Poll(bool exited = false)
    {
        WaitingSeconds(clock.Elapsed.TotalSeconds);
        if (!invalidLog) ReadAvailable(exited);
        if (exited && State == "ResultPending") Change("ResultInterrupted");
    }
    private void ReadAvailable(bool drain)
    {
        try
        {
            using (var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            {
                var remaining = file.Length - offset;
                if (remaining < 0 || remaining > 2 * 1024 * 1024)
                { LogAvailable = false; Truncated = true; invalidLog = true; return; }
                file.Position = offset; var bytes = new byte[65536]; var chars = new char[65536];
                while (remaining > 0)
                {
                    var length = file.Read(bytes, 0, (int)Math.Min(remaining, bytes.Length));
                    if (length == 0) break;
                    offset += length;
                    Feed(new string(chars, 0, decoder.GetChars(bytes, 0, length, chars, 0, false)));
                    if (!drain) break;
                    remaining -= length;
                }
                LogAvailable = true;
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
            if (State == "ResultPending") return LogAvailable ? "正在等待最終戰績。請保留遊戲視窗，等候結果。"
                : "先前正在等待最終戰績，目前無法讀取記錄。請查看遊戲視窗。";
            if (State == "ResultInterrupted") return "等待戰績期間已中斷，未確認收到最終戰績。請向控制人員核對。";
            if (State == "OpenXRUnavailable") return "OpenXR 未能啟動。請確認頭盔與 Windows OpenXR 執行環境。";
            if (State == "Rejected") return "遊戲回報入場遭拒。請向控制人員重新取得自己的連線檔。";
            if (State == "Disconnected") return "遊戲回報連線中斷。可在遊戲內重新讀取控制人員更新的票券。";
            if (State == "Connected") return LogAvailable ? "遊戲已回報入場。請切換到遊戲視窗；可關閉此啟動器。" : "先前已回報入場，目前無法讀取連線記錄。請查看遊戲視窗。";
            return State == "Unconfirmed" ? "尚未收到入場確認。請核對伺服器IPv4、UDP埠與遊戲版本，並查看遊戲視窗。" : "遊戲已啟動，正在等待入場確認…";
        }
    }
}
