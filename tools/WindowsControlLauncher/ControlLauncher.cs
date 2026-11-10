// Standalone management launcher; compiled with the installed Framework 4.8 compiler.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.NetworkInformation;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal static class ControlLauncher
{
    internal static readonly string Root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);
    internal static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 4 * 1024 * 1024 };
    internal static readonly string[] Roles = { "Master", "Room1", "Room2", "Room3", "Room4", "Room5", "GameServer" };
    internal static void Require(bool value, string message) { if (!value) throw new InvalidDataException(message); }
    internal static Dictionary<string, object> Map(object value) { return value as Dictionary<string, object>; }
    internal static string Text(Dictionary<string, object> value, string key) { object x; return value.TryGetValue(key, out x) ? x as string : null; }
    internal static int Number(Dictionary<string, object> value, string key) { object x; return value.TryGetValue(key, out x) && x is int ? (int)x : -1; }
    internal static string Full(string path) { var value = Path.GetFullPath(path); return value.Length == Path.GetPathRoot(value).Length ? value : value.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar); }
    internal static bool Inside(string path, string folder) { return String.Equals(Full(path), Full(folder), StringComparison.OrdinalIgnoreCase) || Full(path).StartsWith(Full(folder) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase); }
    internal static void Plain(string path)
    {
        for (var current = Full(path); !String.IsNullOrEmpty(current); current = Path.GetDirectoryName(current))
            if (File.Exists(current) || Directory.Exists(current)) Require((File.GetAttributes(current) & FileAttributes.ReparsePoint) == 0, "請使用實際路徑，不要使用連結。");
    }
    internal static Dictionary<string, object> Read(string path, int maximum)
    {
        Plain(path); Require(new FileInfo(path).Length <= maximum, "設定檔過大。");
        var value = Map(Json.DeserializeObject(File.ReadAllText(path, Encoding.UTF8))); Require(value != null, "設定格式錯誤。"); return value;
    }
    internal static string Hash(string path) { using (var sha = SHA256.Create()) using (var f = File.OpenRead(path)) return BitConverter.ToString(sha.ComputeHash(f)).Replace("-", "").ToLowerInvariant(); }
    internal static void SaveNew(string path, object value)
    {
        var temporary = Full(path) + "." + Guid.NewGuid().ToString("N") + ".tmp"; Plain(temporary);
        using (var f = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        using (var w = new StreamWriter(f, new UTF8Encoding(false))) { w.WriteLine(Json.Serialize(value)); w.Flush(); f.Flush(true); }
        File.Move(temporary, path); // New destination only; never replace an existing report or key file.
    }
    internal static string Token() { var bytes = new byte[32]; using (var random = RandomNumberGenerator.Create()) random.GetBytes(bytes); return BitConverter.ToString(bytes).Replace("-", "").ToLowerInvariant(); }
    internal static Dictionary<string, object> Verify()
    {
        var manifest = Read(Path.Combine(Root, "control-package.json"), 4 * 1024 * 1024);
        Require(Number(manifest, "schemaVersion") == 1 && Text(manifest, "target") == "win-x64" && Text(manifest, "apiVersion") == "0.31.0", "管理包版本不正確。");
        object raw; Require(manifest.TryGetValue("files", out raw) && raw is object[], "管理包清單缺失。");
        var entries = (object[])raw; Require(entries.Length > 10 && entries.Length <= 4096, "管理包清單超界。");
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var item in entries)
        {
            var row = Map(item); Require(row != null, "管理包清單錯誤。"); var name = Text(row, "path");
            Require(!String.IsNullOrEmpty(name) && !Path.IsPathRooted(name) && name.IndexOf('\\') < 0 && name.IndexOf(':') < 0 && seen.Add(name), "管理包路徑錯誤。");
            foreach (var part in name.Split('/')) Require(part.Length > 0 && part != "." && part != "..", "管理包路徑錯誤。");
            var path = Path.Combine(Root, name.Replace('/', Path.DirectorySeparatorChar)); Plain(path);
            Require(File.Exists(path) && Hash(path) == Text(row, "sha256"), "管理包不完整，請重新完整解壓。");
        }
        foreach (var name in new[] { "Start-Control.exe", "Runtime/VrCommand.Api.exe", "Runtime/coreclr.dll", "Runtime/hostfxr.dll", "Runtime/hostpolicy.dll", "Runtime/wwwroot/console/index.html" }) Require(seen.Contains(name), "管理包必要檔案缺失。");
        return manifest;
    }
    internal static string Bind(string value)
    {
        var parts = value.Split('.'); Require(parts.Length == 4, "請選擇本機IPv4。");
        foreach (var part in parts) { byte n; Require(Byte.TryParse(part, out n) && n.ToString(System.Globalization.CultureInfo.InvariantCulture) == part, "IPv4格式不正確。"); }
        Require(parts[0] != "0" && Int32.Parse(parts[0]) < 224, "不能使用萬用或多播地址。");
        if (value == "127.0.0.1") return value;
        foreach (var network in NetworkInterface.GetAllNetworkInterfaces()) foreach (var address in network.GetIPProperties().UnicastAddresses)
            if (address.Address.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork && address.Address.ToString() == value) return value;
        throw new InvalidDataException("請選擇本機已配置的IPv4。");
    }
    internal static Dictionary<string, object> Instance(string root)
    {
        Plain(root); Require(!Inside(root, Root) && !Inside(Root, root), "資料必須與管理包分開。");
        var data = Read(Path.Combine(root, "control-instance.json"), 4096); Guid id;
        Require(Number(data, "schemaVersion") == 1 && Text(data, "kind") == "VrCommand-ControlServer" && Guid.TryParse(Text(data, "instanceId"), out id), "不是支援的資料實例。");
        Bind(Text(data, "bindAddress") ?? ""); var port = Number(data, "port"); Require(port >= 1024 && port <= 65535, "埠號須為1024至65535。"); Keys(root); return data;
    }
    internal static Dictionary<string, object> Keys(string root)
    {
        var config = Read(Path.Combine(root, "operator-keys.json"), 8192); object raw;
        Require(config.TryGetValue("OperatorKeys", out raw) && Map(raw) != null, "角色金鑰缺失。"); var keys = Map(raw);
        Require(keys.Count == Roles.Length, "角色金鑰數量不符。"); var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var role in Roles) { var value = Text(keys, role); Require(value != null && value.Length == 64 && seen.Add(value), "角色金鑰格式錯誤。"); foreach (var c in value) Require(c >= '0' && c <= '9' || c >= 'a' && c <= 'f', "角色金鑰格式錯誤。"); }
        return keys;
    }
    internal static void Initialize(string root, string bind, int port)
    {
        root = Full(root); Plain(root); Require(!Inside(root, Root) && !Inside(Root, root), "資料必須與管理包分開。"); Bind(bind);
        Require(port >= 1024 && port <= 65535, "埠號須為1024至65535。");
        Require(!File.Exists(root) && (!Directory.Exists(root) || Directory.GetFileSystemEntries(root).Length == 0), "新增實例必須使用全新或空的資料夾。");
        Directory.CreateDirectory(root); var keys = new Dictionary<string, object>(); foreach (var role in Roles) keys.Add(role, Token());
        SaveNew(Path.Combine(root, "operator-keys.json"), new { OperatorKeys = keys });
        SaveNew(Path.Combine(root, "control-instance.json"), new { schemaVersion = 1, kind = "VrCommand-ControlServer", instanceId = Guid.NewGuid().ToString(), bindAddress = bind, port = port, createdAtUtc = DateTime.UtcNow.ToString("O") });
    }
    internal static void OutputPath(string path, string data)
    {
        Require(!String.IsNullOrEmpty(path), "請指定新的結果路徑。"); Plain(path);
        Require(!Inside(path, Root) && (data == null || !Inside(path, data)) && !File.Exists(path) && !Directory.Exists(path), "結果路徑已存在或與管理包／資料重疊。");
        Require(Directory.Exists(Path.GetDirectoryName(Full(path))), "結果路徑的資料夾不存在。");
    }
    private sealed class HttpsSettings
    {
        internal const string PasswordVariable = "VR_COMMAND_CONTROL_PFX_PASSWORD";
        internal const string Prefix = "VR_COMMAND_MANAGED_TLS_";
        internal string Address;
        internal int Port;
        internal string Password;

        internal static HttpsSettings Load(string root, Dictionary<string, object> instance)
        {
            var path = Path.Combine(root, "control-https.json");
            try { File.GetAttributes(path); }
            catch (FileNotFoundException) { return null; }

            Require(Text(instance, "bindAddress") == "127.0.0.1", "啟用HTTPS時，原管理HTTP必須使用127.0.0.1。");
            var config = Read(path, 4096);
            var address = Bind(Text(config, "bindAddress") ?? "");
            var port = Number(config, "port");
            Require(config.Count == 3 && Number(config, "schemaVersion") == 1 && (port == 443 || port >= 1024 && port <= 65535)
                && port != Number(instance, "port"), "HTTPS設定版本或埠號錯誤。");

            var certificate = Path.Combine(root, "control-https.pfx");
            Plain(certificate);
            Require(File.Exists(certificate) && new FileInfo(certificate).Length <= 1024 * 1024, "請提供管理HTTPS PFX檔。");
            var password = Environment.GetEnvironmentVariable(PasswordVariable);
            Require(!String.IsNullOrEmpty(password), "請在啟動程序提供管理HTTPS PFX密碼。");
            return new HttpsSettings { Address = address, Port = port, Password = password };
        }
    }
    internal sealed class Service : IDisposable
    {
        internal Process Child; internal string Uri; internal string HttpsBinding; internal string RuntimeModule; internal bool Graceful; internal volatile bool Ready;
        internal int ChildId; internal int ExitCode = -1; private FileStream lease; private string nonce; private Dictionary<string, object> keys; private readonly object gate = new object(); private string tail = "";
        private string certificatePassword;
        internal string LogTail { get { lock (gate) return tail; } }
        private void Line(string value)
        {
            if (value == null) return;
            if (value == "VR_CONTROL_READY " + nonce) { Ready = true; return; }
            value = value.Replace(nonce, "[redacted]"); foreach (var role in Roles) value = value.Replace(Text(keys, role), "[redacted]");
            if (certificatePassword != null) value = value.Replace(certificatePassword, "[redacted]");
            lock (gate) { tail += value + "\n"; if (tail.Length > 4096) tail = tail.Substring(tail.Length - 4096); }
        }
        internal void Start(string root)
        {
            Verify(); var instance = Instance(root); keys = Keys(root); nonce = Token();
            var lockPath = Path.Combine(root, ".control-server.lock"); Plain(lockPath); lease = new FileStream(lockPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
            var https = HttpsSettings.Load(root, instance);
            Uri = "http://" + Text(instance, "bindAddress") + ":" + Number(instance, "port");
            var info = new ProcessStartInfo(Path.Combine(Root, "Runtime", "VrCommand.Api.exe"), "--urls " + Uri) { WorkingDirectory = Full(root), UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true };
            var remove = new List<string>(); foreach (string name in info.EnvironmentVariables.Keys) if (name.StartsWith("OperatorKeys__", StringComparison.OrdinalIgnoreCase) || String.Equals(name, "OperatorKeyFile", StringComparison.OrdinalIgnoreCase) || String.Equals(name, "PlayerTicketSigningKey", StringComparison.OrdinalIgnoreCase) || String.Equals(name, "ControlPipeToken", StringComparison.OrdinalIgnoreCase) || name.StartsWith(HttpsSettings.Prefix, StringComparison.OrdinalIgnoreCase) || String.Equals(name, HttpsSettings.PasswordVariable, StringComparison.OrdinalIgnoreCase)) remove.Add(name);
            foreach (var name in remove) info.EnvironmentVariables.Remove(name);
            info.EnvironmentVariables["OperatorKeyFile"] = Path.Combine(Full(root), "operator-keys.json"); info.EnvironmentVariables["DataDirectory"] = Path.Combine(Full(root), "missions"); info.EnvironmentVariables["SessionDataDirectory"] = Path.Combine(Full(root), "sessions");
            info.EnvironmentVariables["ControlPipeToken"] = nonce; info.EnvironmentVariables["ASPNETCORE_ENVIRONMENT"] = "Production"; info.EnvironmentVariables["Logging__LogLevel__Default"] = "Warning";
            if (https != null)
            {
                HttpsBinding = "https://" + https.Address + ":" + https.Port;
                certificatePassword = https.Password;
                info.EnvironmentVariables[HttpsSettings.Prefix + "ADDRESS"] = https.Address;
                info.EnvironmentVariables[HttpsSettings.Prefix + "PORT"] = https.Port.ToString();
                info.EnvironmentVariables[HttpsSettings.Prefix + "LOCAL_PORT"] = Number(instance, "port").ToString();
                info.EnvironmentVariables[HttpsSettings.PasswordVariable] = https.Password;
            }
            Child = new Process { StartInfo = info }; Child.OutputDataReceived += (s, e) => Line(e.Data); Child.ErrorDataReceived += (s, e) => Line(e.Data);
            Require(Child.Start(), "管理服務未啟動。"); ChildId = Child.Id; Child.BeginOutputReadLine(); Child.BeginErrorReadLine();
            info.EnvironmentVariables.Remove(HttpsSettings.PasswordVariable);
            var until = Stopwatch.StartNew();
            while (until.Elapsed.TotalSeconds < 30 && !Child.HasExited)
            {
                if (Ready)
                {
                    foreach (ProcessModule module in Child.Modules) if (String.Equals(module.ModuleName, "coreclr.dll", StringComparison.OrdinalIgnoreCase)) RuntimeModule = module.FileName;
                    Require(RuntimeModule != null && String.Equals(Full(RuntimeModule), Full(Path.Combine(Root, "Runtime/coreclr.dll")), StringComparison.OrdinalIgnoreCase), "未使用管理包的執行環境。");
                    var request = (HttpWebRequest)WebRequest.Create(Uri + "/api/me"); request.Timeout = 5000; request.Proxy = null; request.Headers[HttpRequestHeader.Authorization] = "Bearer " + Text(keys, "Master");
                    using (var response = (HttpWebResponse)request.GetResponse()) using (var reader = new StreamReader(response.GetResponseStream())) { var identity = Map(Json.DeserializeObject(reader.ReadToEnd())); Require(response.StatusCode == HttpStatusCode.OK && Text(identity, "role") == "Master", "管理身分尚未就緒。"); }
                    Require(!Child.HasExited, "管理服務在確認期間結束。"); return;
                }
                Thread.Sleep(50);
            }
            throw new InvalidOperationException("管理服務未在30秒內回報自己的就緒事件。");
        }
        internal bool Running { get { return Child != null && ChildId != 0 && !Child.HasExited; } }
        internal void Stop()
        {
            if (Child == null || ChildId == 0) { if (lease != null) { lease.Dispose(); lease = null; } return; }
            if (!Child.HasExited)
            {
                try { Child.StandardInput.WriteLine("STOP " + nonce); Child.StandardInput.Flush(); Child.StandardInput.Close(); } catch (IOException) { }
                Graceful = Child.WaitForExit(40000);
                if (!Graceful) { Child.Kill(); Require(Child.WaitForExit(5000), "管理服務停止尚未確認。"); }
            }
            Child.WaitForExit(); ExitCode = Child.ExitCode; if (ExitCode != 0) Graceful = false;
            if (lease != null) { lease.Dispose(); lease = null; }
        }
        public void Dispose() { Stop(); if (Child != null) { Child.Dispose(); Child = null; } if (lease != null) { lease.Dispose(); lease = null; } }
    }
    [STAThread] private static int Main(string[] args)
    {
        if (args.Length == 0) { Application.EnableVisualStyles(); Application.Run(new ServerForm()); return 0; }
        string report = null; Service service = null; int result = 1;
        try
        {
            var options = new Dictionary<string, string>(StringComparer.Ordinal); var flags = new HashSet<string> { "--verify" };
            for (var i = 0; i < args.Length; i++) { var name = args[i]; Require(!options.ContainsKey(name), "重複的參數。"); if (flags.Contains(name)) options.Add(name, "true"); else { Require(i + 1 < args.Length && new HashSet<string> { "--init", "--bind", "--port", "--run", "--seconds", "--stop-file", "--ready-report", "--report" }.Contains(name), "未知參數。"); options.Add(name, args[++i]); } }
            Require(options.ContainsKey("--report"), "請指定結果路徑。"); var candidateReport = options["--report"]; OutputPath(candidateReport, options.ContainsKey("--run") ? options["--run"] : options.ContainsKey("--init") ? options["--init"] : null); report = candidateReport; Verify();
            var modes = (options.ContainsKey("--verify") ? 1 : 0) + (options.ContainsKey("--init") ? 1 : 0) + (options.ContainsKey("--run") ? 1 : 0); Require(modes == 1, "一次只能選擇一種操作。");
            if (options.ContainsKey("--verify")) { Require(options.Count == 2, "核對模式不接受其他設定。"); SaveNew(report, new { status = "verified", started = false }); return 0; }
            if (options.ContainsKey("--init"))
            {
                foreach (var name in options.Keys) Require(name == "--init" || name == "--report" || name == "--bind" || name == "--port", "新增模式參數錯誤。");
                int port = 5081; if (options.ContainsKey("--port")) Require(Int32.TryParse(options["--port"], out port), "埠號格式錯誤。");
                Initialize(options["--init"], options.ContainsKey("--bind") ? options["--bind"] : "127.0.0.1", port); SaveNew(report, new { status = "initialized", started = false }); return 0;
            }
            foreach (var name in options.Keys) Require(name == "--run" || name == "--report" || name == "--seconds" || name == "--stop-file" || name == "--ready-report", "啟動模式參數錯誤。");
            int seconds; Require(options.ContainsKey("--seconds") && Int32.TryParse(options["--seconds"], out seconds) && seconds >= 1 && seconds <= 3600, "請指定1至3600秒的檢查上限。"); seconds = Int32.Parse(options["--seconds"]);
            Require(options.ContainsKey("--ready-report"), "請指定新的就緒報告。"); var ready = options["--ready-report"]; OutputPath(ready, options["--run"]); Require(!String.Equals(Full(ready), Full(report), StringComparison.OrdinalIgnoreCase), "報告路徑重疊。");
            string stop = null; if (options.ContainsKey("--stop-file")) { stop = options["--stop-file"]; OutputPath(stop, options["--run"]); Require(!String.Equals(Full(stop), Full(ready), StringComparison.OrdinalIgnoreCase) && !String.Equals(Full(stop), Full(report), StringComparison.OrdinalIgnoreCase), "停止路徑重疊。"); }
            service = new Service(); service.Start(options["--run"]); SaveNew(ready, new { status = "ready", childPid = service.ChildId, uri = service.Uri, httpsBinding = service.HttpsBinding, runtimeCoreClr = service.RuntimeModule, utc = DateTime.UtcNow.ToString("O") });
            var elapsed = Stopwatch.StartNew(); while (elapsed.Elapsed.TotalSeconds < seconds && service.Running && (stop == null || !File.Exists(stop))) Thread.Sleep(50);
            var requested = service.Running; service.Stop(); result = requested && service.Graceful ? 0 : 1;
            SaveNew(report, new { status = result == 0 ? "stopped" : "failed", complete = result == 0, childPid = service.ChildId, childExited = !service.Running, exitCode = service.ExitCode, graceful = service.Graceful, logTail = service.LogTail, utc = DateTime.UtcNow.ToString("O") }); return result;
        }
        catch (Exception error)
        {
            if (service != null) { try { service.Stop(); } catch { } }
            if (report != null && !File.Exists(report)) { try { SaveNew(report, new { status = "rejected", complete = false, errorType = error.GetType().Name, childPid = service == null ? 0 : service.ChildId, childExited = service == null || !service.Running }); } catch { } }
            return 1;
        }
        finally { if (service != null) service.Dispose(); }
    }

    private sealed class ServerForm : Form
    {
        private readonly TextBox folder = new TextBox { ReadOnly = true, Width = 610 };
        private readonly ComboBox bind = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 180 };
        private readonly NumericUpDown port = new NumericUpDown { Minimum = 1024, Maximum = 65535, Value = 5081, Width = 100 };
        private readonly ComboBox role = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 150 };
        private readonly Label status = new Label { Text = "選擇資料實例，或建立新的實例。", AutoSize = false, Width = 610, Height = 52 };
        private readonly Button create = new Button { Text = "新增資料實例", Width = 135 }, select = new Button { Text = "選取資料實例", Width = 135 }, start = new Button { Text = "啟動管理服務", Width = 135 }, stop = new Button { Text = "停止管理服務", Width = 135 }, open = new Button { Text = "開啟控制台", Width = 135 }, copy = new Button { Text = "複製登入金鑰", Width = 135 };
        private Service service; private bool busy; private string selectedBind; private int selectedPort;
        internal ServerForm()
        {
            Text = "VR Command 管理服務"; ClientSize = new Size(670, 370); Font = new Font("Microsoft JhengHei UI", 10); FormBorderStyle = FormBorderStyle.FixedDialog; MaximizeBox = false;
            var panel = new FlowLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(20), FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoScroll = true }; Controls.Add(panel);
            panel.Controls.Add(new Label { Text = "VR COMMAND / 控制台服務", AutoSize = true }); panel.Controls.Add(folder);
            var settings = new FlowLayoutPanel { Width = 620, Height = 42 }; settings.Controls.Add(new Label { Text = "新實例IPv4", AutoSize = true }); settings.Controls.Add(bind); settings.Controls.Add(new Label { Text = "埠號", AutoSize = true }); settings.Controls.Add(port); panel.Controls.Add(settings);
            bind.Items.Add("127.0.0.1"); foreach (var n in NetworkInterface.GetAllNetworkInterfaces()) foreach (var a in n.GetIPProperties().UnicastAddresses) if (a.Address.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork && !bind.Items.Contains(a.Address.ToString())) bind.Items.Add(a.Address.ToString()); bind.SelectedIndex = 0;
            var row = new FlowLayoutPanel { Width = 620, Height = 44 }; foreach (var button in new[] { create, select, start, stop }) row.Controls.Add(button); panel.Controls.Add(row);
            var credentials = new FlowLayoutPanel { Width = 620, Height = 44 }; role.Items.AddRange(Roles); role.SelectedIndex = 0; credentials.Controls.Add(role); credentials.Controls.Add(copy); credentials.Controls.Add(open); panel.Controls.Add(credentials); panel.Controls.Add(status);
            create.Click += (s, e) => Try(() => { var path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VrCommand", "ControlServers", DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N")); Verify(); Initialize(path, bind.Text, (int)port.Value); LoadInstance(path); });
            select.Click += (s, e) => { using (var dialog = new OpenFileDialog { Title = "選取資料實例的control-instance.json", Filter = "VR Command資料實例|control-instance.json", FileName = "control-instance.json", CheckFileExists = true, Multiselect = false, AutoUpgradeEnabled = true, InitialDirectory = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData) }) if (dialog.ShowDialog(this) == DialogResult.OK) Try(() => LoadInstance(Path.GetDirectoryName(dialog.FileName))); };
            start.Click += (s, e) => { var selectedRoot = folder.Text; busy = true; UpdateButtons(); status.Text = "正在啟動並核對管理服務…"; ThreadPool.QueueUserWorkItem(x => { try { var next = new Service(); service = next; next.Start(selectedRoot); BeginInvoke((Action)(() => { busy = false; status.Text = "服務已就緒：" + next.Uri + (next.HttpsBinding == null ? "" : "\r\n房控HTTPS監聽：" + next.HttpsBinding); UpdateButtons(); })); } catch { if (service != null) { try { service.Dispose(); service = null; } catch { } } BeginInvoke((Action)(() => { busy = false; status.Text = service == null ? "啟動失敗，請確認資料、地址、埠號與HTTPS設定。" : "啟動未完成，服務停止尚未確認。請保留此視窗。"; UpdateButtons(); })); } }); };
            stop.Click += (s, e) => Stop(false); open.Click += (s, e) => Try(() => Process.Start(new ProcessStartInfo(service.Uri + "/console/") { UseShellExecute = true })); copy.Click += (s, e) => Try(() => { Clipboard.SetText(ControlLauncher.Text(Keys(folder.Text), role.Text)); status.Text = "已複製所選角色的登入金鑰。"; });
            bind.SelectedIndexChanged += (s, e) => UpdateButtons(); port.ValueChanged += (s, e) => UpdateButtons();
            var monitor = new System.Windows.Forms.Timer { Interval = 1000 }; monitor.Tick += (s, e) => { if (!busy && service != null && !service.Running) { status.Text = "管理服務已中斷；確認停止後可重開原資料實例。"; UpdateButtons(); } }; monitor.Start();
            FormClosed += (s, e) => monitor.Dispose(); FormClosing += (s, e) => { if (busy) { e.Cancel = true; return; } if (service != null) { e.Cancel = true; Stop(true); } }; UpdateButtons();
        }
        private void Try(Action action) { try { action(); UpdateButtons(); } catch { status.Text = "操作未完成，請確認管理包與資料實例。"; } }
        private void LoadInstance(string path) { var data = Instance(path); folder.Text = Full(path); selectedBind = ControlLauncher.Text(data, "bindAddress"); selectedPort = Number(data, "port"); bind.SelectedItem = selectedBind; port.Value = selectedPort; status.Text = "已選取實例：" + selectedBind + ":" + selectedPort + "；可以啟動服務。"; }
        private void UpdateButtons()
        {
            create.Enabled = select.Enabled = !busy && service == null; var same = bind.Text == selectedBind && port.Value == selectedPort;
            start.Enabled = !busy && service == null && folder.Text.Length > 0 && same; stop.Enabled = !busy && service != null; open.Enabled = !busy && service != null && service.Running; copy.Enabled = !busy && folder.Text.Length > 0; bind.Enabled = port.Enabled = !busy && service == null;
            if (!busy && service == null && folder.Text.Length > 0 && !same) status.Text = "新地址／埠號只用於新增實例。要啟動原實例，請還原設定或重新選取。";
        }
        private void Stop(bool close)
        {
            busy = true; UpdateButtons(); status.Text = "正在等待管理服務關閉…";
            ThreadPool.QueueUserWorkItem(x => { var graceful = false; try { service.Stop(); graceful = service.Graceful; service.Dispose(); service = null; } catch { } BeginInvoke((Action)(() => { busy = false; status.Text = graceful ? "服務已正常停止；資料保留於所選實例。" : service == null ? "服務已停止，但上次執行未正常完成；資料已保留。" : "服務停止尚未完整確認，請保留此視窗與資料。"; UpdateButtons(); if (close && service == null) Close(); })); });
        }
    }
}
