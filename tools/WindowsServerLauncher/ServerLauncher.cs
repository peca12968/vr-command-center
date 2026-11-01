// Framework 4.8 companion for the existing Unity Windows build. No Master key is passed to Unity.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal static class ServerLauncher
{
    internal static readonly string Root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar);
    internal static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 4 * 1024 * 1024 };
    internal static void Need(bool ok, string message) { if (!ok) throw new InvalidDataException(message); }
    internal static string Safe(Exception error) { return error is InvalidDataException || error is IOException ? error.Message : error.GetType().Name; }
    internal static Dictionary<string, object> Map(object value) { return value as Dictionary<string, object>; }
    internal static string Text(Dictionary<string, object> map, string key) { object value; return map != null && map.TryGetValue(key, out value) ? value as string : null; }
    internal static long Num(Dictionary<string, object> map, string key) { object value; return map != null && map.TryGetValue(key, out value) && (value is int || value is long) ? Convert.ToInt64(value) : -1; }
    internal static bool Yes(Dictionary<string, object> map, string key) { object value; return map != null && map.TryGetValue(key, out value) && value is bool && (bool)value; }
    internal static Dictionary<string, object> Child(Dictionary<string, object> map, string key) { object value; return map != null && map.TryGetValue(key, out value) ? Map(value) : null; }
    internal static string Full(string path) { return Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar); }
    internal static bool Inside(string path, string parent) { return String.Equals(Full(path), Full(parent), StringComparison.OrdinalIgnoreCase) || Full(path).StartsWith(Full(parent) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase); }
    internal static void Plain(string path) { for (var p = Path.GetFullPath(path); !String.IsNullOrEmpty(p); p = Path.GetDirectoryName(p)) if (File.Exists(p) || Directory.Exists(p)) Need((File.GetAttributes(p) & FileAttributes.ReparsePoint) == 0, "請使用實際路徑，不要使用連結。"); }
    internal static Dictionary<string, object> Read(string path, int max) { Plain(path); Need(new FileInfo(path).Length <= max, "設定檔過大。"); var value = Map(Json.DeserializeObject(File.ReadAllText(path, Encoding.UTF8))); Need(value != null, "設定格式錯誤。"); return value; }
    internal static string Hash(string path) { using (var s = SHA256.Create()) using (var f = File.OpenRead(path)) return Hex(s.ComputeHash(f)); }
    internal static string Hex(byte[] data) { return BitConverter.ToString(data).Replace("-", "").ToLowerInvariant(); }
    internal static void Save(string path, object value)
    {
        var temp = Full(path) + "." + Guid.NewGuid().ToString("N") + ".tmp"; Plain(temp);
        using (var f = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None)) using (var w = new StreamWriter(f, new UTF8Encoding(false))) { w.WriteLine(Json.Serialize(value)); w.Flush(); f.Flush(true); }
        File.Move(temp, path);
    }
    internal static void Output(string path, string work)
    {
        Need(!String.IsNullOrEmpty(path), "需要新的結果路徑。"); Plain(path);
        Need(!File.Exists(path) && !Directory.Exists(path) && Directory.Exists(Path.GetDirectoryName(Full(path))) && !Inside(path, Root) && (work == null || !Inside(path, work)), "結果路徑已存在或與程式／資料重疊。");
    }
    internal static void Verify()
    {
        var manifest = Read(Path.Combine(Root, "server-package.json"), 4 * 1024 * 1024); object rows;
        Need(Num(manifest, "schemaVersion") == 1 && Text(manifest, "target") == "win-x64" && manifest.TryGetValue("files", out rows) && rows is object[], "伺服器包版本不正確。");
        rows = manifest["files"]; var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var item in (object[])rows)
        {
            var row = Map(item); var name = Text(row, "path"); Need(!String.IsNullOrEmpty(name) && !Path.IsPathRooted(name) && name.IndexOf('\\') < 0 && name.IndexOf(':') < 0 && seen.Add(name), "伺服器包路徑錯誤。");
            foreach (var part in name.Split('/')) Need(part.Length > 0 && part != "." && part != "..", "伺服器包路徑錯誤。");
            var path = Path.Combine(Root, name.Replace('/', Path.DirectorySeparatorChar)); Plain(path);
            Need(File.Exists(path) && new FileInfo(path).Length == Num(row, "bytes") && Hash(path) == Text(row, "sha256"), "伺服器包不完整，請完整解壓。");
        }
        foreach (var name in new[] { "Launch-Server.exe", "Runtime/VrCommand.exe", "Runtime/UnityPlayer.dll", "Runtime/VrCommand_Data/globalgamemanagers", "Runtime/build-receipt.json" }) Need(seen.Contains(name), "伺服器包缺少必要檔案。");
        var actual = new HashSet<string>(StringComparer.OrdinalIgnoreCase); var folders = new Stack<string>(); folders.Push(Root);
        while (folders.Count > 0) { var folder = folders.Pop(); Plain(folder); foreach (var file in Directory.GetFiles(folder)) { Plain(file); Need(actual.Add(file.Substring(Root.Length + 1).Replace('\\', '/')), "伺服器包路徑重複。"); } foreach (var child in Directory.GetDirectories(folder)) { Plain(child); folders.Push(child); } }
        var expected = new HashSet<string>(seen, StringComparer.OrdinalIgnoreCase); expected.Add("server-package.json"); Need(actual.SetEquals(expected), "程式包有額外檔案；私人設定與結果須放在包外。");
    }
    internal static string IPv4(string value, bool wildcard)
    {
        Need(value != null, "需要IPv4地址。"); var parts = value.Split('.'); Need(parts.Length == 4, "IPv4格式錯誤。");
        foreach (var part in parts) { byte n; Need(Byte.TryParse(part, out n) && n.ToString(System.Globalization.CultureInfo.InvariantCulture) == part, "IPv4格式錯誤。"); }
        Need(wildcard && value == "0.0.0.0" || Int32.Parse(parts[0]) > 0 && Int32.Parse(parts[0]) < 224, "需要單播IPv4地址。"); return value;
    }
    internal static void LocalBind(string value)
    {
        IPv4(value, true); if (value == "0.0.0.0" || value == "127.0.0.1") return;
        foreach (var n in NetworkInterface.GetAllNetworkInterfaces()) foreach (var a in n.GetIPProperties().UnicastAddresses) if (a.Address.AddressFamily == AddressFamily.InterNetwork && a.Address.ToString() == value) return;
        throw new InvalidDataException("綁定地址必須已配置在本機。");
    }
    internal sealed class Settings
    {
        internal string Api, Key, Session, Address, Bind; internal int Port;
        internal static Settings From(Dictionary<string, object> value)
        {
            Need(value.Count == 7 && Num(value, "port") >= 1024 && Num(value, "port") <= 65535, "請使用七欄伺服器連線檔與有效UDP埠。"); var result = new Settings { Api = Text(value, "managementApiUrl"), Key = Text(value, "gameServerKey"), Session = Text(value, "sessionId"), Address = Text(value, "address"), Bind = Text(value, "listenAddress"), Port = (int)Num(value, "port") };
            Need(Text(value, "role") == "Server", "這是獨立伺服器啟動器。"); result.Validate(); return result;
        }
        internal void Validate()
        {
            Guid id; Need(Guid.TryParseExact(Session, "D", out id) && id != Guid.Empty && id.ToString("D") == Session, "場次ID格式錯誤。");
            ValidateTarget();
            IPv4(Address, false); LocalBind(Bind); Need(Bind == "0.0.0.0" || Bind == Address, "明確綁定地址須與公告地址相同。"); Need(Port >= 1024 && Port <= 65535, "UDP埠須為1024至65535。");
        }
        internal void ValidateTarget()
        {
            Uri uri; Need(Uri.TryCreate(Api, UriKind.Absolute, out uri) && uri.Scheme == "http" && uri.AbsolutePath == "/" && uri.Query == "" && uri.Fragment == "" && uri.UserInfo == "" && uri.Port >= 1024 && uri.Port <= 65535, "管理地址須為http://IPv4:埠。");
            IPv4(uri.Host, false); Need(Api == "http://" + uri.Host + ":" + uri.Port, "管理地址須為http://IPv4:埠，不含結尾斜線。");
            Need(Key != null && Key.Length >= 32 && Key.Length <= 512, "GameServer金鑰格式錯誤。"); foreach (var c in Key) Need(c > 32 && c < 127, "GameServer金鑰格式錯誤。");
        }
        internal object Config(string telemetry) { return new { role = "Server", address = Address, listenAddress = Bind, port = Port, sessionId = Session, managementApiUrl = Api, gameServerKey = Key, telemetryOrigin = "Simulation", telemetryDirectory = telemetry }; }
        internal Dictionary<string, object> Request(string path, object body = null, bool missing = false)
        {
            var request = (HttpWebRequest)WebRequest.Create(Api + path); request.Proxy = null; request.AllowAutoRedirect = false; request.Timeout = 5000; request.ReadWriteTimeout = 5000;
            request.Headers[HttpRequestHeader.Authorization] = "Bearer " + Key;
            if (body != null) { request.Method = "PUT"; request.ContentType = "application/json"; var bytes = Encoding.UTF8.GetBytes(Json.Serialize(body)); request.ContentLength = bytes.Length; using (var stream = request.GetRequestStream()) stream.Write(bytes, 0, bytes.Length); }
            try { using (var response = (HttpWebResponse)request.GetResponse()) using (var reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8)) { Need(response.StatusCode == HttpStatusCode.OK, "管理服務回應不正確。"); var bytes = new char[256 * 1024 + 1]; var count = 0; int read; while ((read = reader.Read(bytes, count, bytes.Length - count)) > 0 && count < bytes.Length) count += read; Need(count <= 256 * 1024, "管理回應過大。"); var result = Map(Json.DeserializeObject(new string(bytes, 0, count))); Need(result != null, "管理回應格式錯誤。"); return result; } }
            catch (WebException error) { var response = error.Response as HttpWebResponse; var code = response == null ? 0 : (int)response.StatusCode; if (response != null) response.Dispose(); if (missing && code == 404) return null; throw new IOException("管理服務請求失敗，HTTP " + code + "。"); }
        }
        internal void Identity() { ValidateTarget(); Need(Text(Request("/"), "version") == "0.31.0", "需要管理服務0.31.0。"); Need(Text(Request("/api/me"), "role") == "GameServer", "請使用GameServer角色金鑰。"); }
        internal object[] Sessions()
        {
            var request = (HttpWebRequest)WebRequest.Create(Api + "/api/sessions"); request.Proxy = null; request.AllowAutoRedirect = false; request.Timeout = 5000; request.ReadWriteTimeout = 5000; request.Headers[HttpRequestHeader.Authorization] = "Bearer " + Key;
            using (var response = (HttpWebResponse)request.GetResponse()) using (var reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8))
            {
                Need(response.StatusCode == HttpStatusCode.OK, "場次列表回應不正確。"); var chars = new char[256 * 1024 + 1]; var count = 0; int n;
                while ((n = reader.Read(chars, count, chars.Length - count)) > 0 && count < chars.Length) count += n;
                Need(count <= 256 * 1024, "場次回應過大。"); var rows = Json.DeserializeObject(new string(chars, 0, count)) as object[]; Need(rows != null && rows.Length <= 5, "場次列表格式或數量錯誤。"); return rows;
            }
        }
    }
    internal sealed class Choice
    {
        internal string Id, MissionId, MissionName, Mode; internal int[] Rooms;
        internal static string GuidValue(string value) { Guid id; Need(Guid.TryParseExact(value, "D", out id) && id != Guid.Empty && id.ToString("D") == value, "場次或任務識別格式錯誤。"); return value; }
        internal static Choice Parse(Dictionary<string, object> value)
        {
            Need(value != null, "場次列表內容錯誤。"); var mission = Child(value, "mission"); var name = Text(Child(mission, "definition"), "name");
            Need(!String.IsNullOrWhiteSpace(name) && name.Length <= 100, "任務名稱格式錯誤。"); object raw; Need(value.TryGetValue("roomIds", out raw) && raw is object[], "場次房間缺失。"); var rows = (object[])raw;
            var mode = Text(value, "mode"); Need(mode == "Independent" && rows.Length == 1 || mode == "Linked" && rows.Length == 5, "場次房間或連線模式錯誤。");
            var seen = new HashSet<int>(); var rooms = new List<int>(); foreach (var row in rows) { Need(row is int && (int)row >= 1 && (int)row <= 5 && seen.Add((int)row), "場次房間重複或越界。"); rooms.Add((int)row); } rooms.Sort();
            return new Choice { Id = GuidValue(Text(value, "id")), MissionId = GuidValue(Text(mission, "id")), MissionName = name, Mode = mode, Rooms = rooms.ToArray() };
        }
        internal static string Label(string value)
        {
            var text = new StringBuilder(); foreach (var c in value) { if (Char.GetUnicodeCategory(c) == System.Globalization.UnicodeCategory.Format) continue; text.Append(Char.IsControl(c) || Char.IsWhiteSpace(c) ? ' ' : c); }
            var result = text.ToString().Trim(); if (result.Length > 32) { var length = Char.IsHighSurrogate(result[31]) ? 31 : 32; result = result.Substring(0, length) + "…"; } return result;
        }
        public override string ToString() { var rooms = Array.ConvertAll(Rooms, room => room.ToString(System.Globalization.CultureInfo.InvariantCulture)); return "房間 " + String.Join("、", rooms) + " · " + (Mode == "Linked" ? "五房全連線" : "單房獨立") + " · " + Label(MissionName) + " · " + Id.Substring(0, 8); }
        internal object Public() { return new { id = Id, missionId = MissionId, missionName = MissionName, mode = Mode, roomIds = Rooms, display = ToString() }; }
    }
    internal sealed class Catalog
    {
        internal Settings Target; internal string PathName, InstanceId; internal List<Choice> Choices;
        internal static Catalog Load(string path)
        {
            Need(!String.IsNullOrWhiteSpace(path), "請輸入control-instance.json完整路徑。");
            path = Full(path.Trim()); Need(String.Equals(Path.GetFileName(path), "control-instance.json", StringComparison.OrdinalIgnoreCase) && !Inside(path, Root), "請選取包外的control-instance.json。");
            var marker = Read(path, 4096); Need(Num(marker, "schemaVersion") == 1 && Text(marker, "kind") == "VrCommand-ControlServer" && Num(marker, "port") >= 1024 && Num(marker, "port") <= 65535, "管理實例格式不符。");
            var id = Choice.GuidValue(Text(marker, "instanceId")); var keys = Child(Read(System.IO.Path.Combine(System.IO.Path.GetDirectoryName(path), "operator-keys.json"), 8192), "OperatorKeys");
            var target = new Settings { Api = "http://" + IPv4(Text(marker, "bindAddress"), false) + ":" + Num(marker, "port"), Key = Text(keys, "GameServer") }; target.Identity();
            return new Catalog { Target = target, PathName = path, InstanceId = id, Choices = Parse(target.Sessions()) };
        }
        internal static List<Choice> Parse(object[] rows)
        {
            Need(rows != null && rows.Length <= 5, "場次列表超界。"); var choices = new List<Choice>(); var ids = new HashSet<string>(); var occupied = new HashSet<int>();
            foreach (var item in rows)
            {
                var value = Map(item); Need(value != null, "場次列表內容錯誤。");
                object bound; Need(value.TryGetValue("combatStream", out bound) && (bound == null || Map(bound) != null), "場次來源格式錯誤。");
                var phase = Text(value, "state"); var experience = Text(Child(value, "environment"), "mode"); Need(phase == "Preparing" || phase == "Running" || phase == "Paused" || phase == "Ended", "場次階段格式錯誤。"); Need(experience == "VR" || experience == "MR", "場次環境格式錯誤。");
                if (phase != "Preparing" || bound != null || experience != "VR") continue;
                var choice = Choice.Parse(value); Need(ids.Add(choice.Id), "場次識別重複。"); foreach (var room in choice.Rooms) Need(occupied.Add(room), "待開場次房間重疊。"); choices.Add(choice);
            }
            choices.Sort((a, b) => a.Rooms[0] != b.Rooms[0] ? a.Rooms[0].CompareTo(b.Rooms[0]) : String.CompareOrdinal(a.Id, b.Id)); return choices;
        }
        internal bool Same(Catalog other) { return other != null && String.Equals(PathName, other.PathName, StringComparison.OrdinalIgnoreCase) && InstanceId == other.InstanceId && Target.Api == other.Target.Api && Target.Key == other.Target.Key; }
        internal object Public() { return new { schemaVersion = 1, status = "catalogued", complete = true, instanceId = InstanceId, sessions = Choices.ConvertAll(choice => choice.Public()), scope = "Read-only Preparing VR choices; not reservation, server readiness or gameplay completion. No key in report." }; }
    }
    internal sealed class CatalogState
    {
        internal string Draft = ""; internal Catalog Current; internal Choice Selected; internal bool Loaded;
        internal bool CanStart { get { return Loaded && Current != null && Selected != null && String.Equals(Full(Draft.Trim()), Current.PathName, StringComparison.OrdinalIgnoreCase); } }
        internal void Edit(string path) { Draft = path; Loaded = false; }
        internal void Load()
        {
            var old = Current; var selectedId = Selected == null ? null : Selected.Id; Loaded = false; Current = null; Selected = null;
            var loaded = Catalog.Load(Draft); Current = loaded; Loaded = true;
            if (loaded.Same(old) && selectedId != null) Selected = loaded.Choices.Find(choice => choice.Id == selectedId);
        }
        internal void Select(string id) { Need(Loaded && Current != null, "請先載入管理實例。"); Selected = id == null ? null : Current.Choices.Find(choice => choice.Id == id); }
    }
    // Kill-on-close job, assigned before native execution. No CPU, priority or memory limits.
    internal sealed class Native : IDisposable
    {
        [StructLayout(LayoutKind.Sequential)] struct Basic { public long a, b; public uint flags; public UIntPtr c, d; public uint e; public UIntPtr f; public uint g, h; }
        [StructLayout(LayoutKind.Sequential)] struct IO { public ulong a, b, c, d, e, f; }
        [StructLayout(LayoutKind.Sequential)] struct Limits { public Basic basic; public IO io; public UIntPtr a, b, c, d; }
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] struct Startup { public int size; public string reserved, desktop, title; public int x, y, width, height, xc, yc, fill, flags; public short show, reservedSize; public IntPtr reservedBytes, input, output, error; }
        [StructLayout(LayoutKind.Sequential)] struct Info { public IntPtr process, thread; public int pid, tid; }
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] static extern IntPtr CreateJobObject(IntPtr security, string name);
        [DllImport("kernel32.dll", SetLastError = true)] static extern bool SetInformationJobObject(IntPtr job, int type, ref Limits value, int size);
        [DllImport("kernel32.dll", SetLastError = true)] static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] static extern bool CreateProcess(string app, StringBuilder command, IntPtr ps, IntPtr ts, bool inherit, uint flags, IntPtr environment, string directory, ref Startup startup, out Info info);
        [DllImport("kernel32.dll", SetLastError = true)] static extern uint ResumeThread(IntPtr thread);
        [DllImport("kernel32.dll", SetLastError = true)] static extern bool TerminateProcess(IntPtr process, uint code);
        [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
        [DllImport("kernel32.dll")] static extern bool GetExitCodeProcess(IntPtr process, out uint code);
        [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
        IntPtr job, process; internal int Pid; internal bool Exited { get { return process != IntPtr.Zero && WaitForSingleObject(process, 0) == 0; } }
        internal uint ExitCode { get { uint code; Need(Exited && GetExitCodeProcess(process, out code), "無法確認原始遊戲程序已停止。"); GetExitCodeProcess(process, out code); return code; } }
        internal Native(string config, string log)
        {
            var exe = Path.Combine(Root, "Runtime/VrCommand.exe"); job = CreateJobObject(IntPtr.Zero, null); Need(job != IntPtr.Zero, "無法建立程序群組。");
            var limits = new Limits(); limits.basic.flags = 0x2000; if (!SetInformationJobObject(job, 9, ref limits, Marshal.SizeOf(limits))) { Dispose(); throw new IOException("無法設定程序群組。"); }
            var startup = new Startup(); startup.size = Marshal.SizeOf(startup); Info info;
            var command = new StringBuilder(Quote(exe) + " -batchmode -nographics -job-worker-count 2 -logFile " + Quote(log) + " --vr-config " + Quote(config));
            if (!CreateProcess(exe, command, IntPtr.Zero, IntPtr.Zero, false, 0x08000004, IntPtr.Zero, Path.GetDirectoryName(config), ref startup, out info)) { Dispose(); throw new IOException("無法啟動遊戲程序。"); }
            process = info.process; Pid = info.pid;
            try { Need(AssignProcessToJobObject(job, process), "無法接管新遊戲程序。"); Need(ResumeThread(info.thread) != UInt32.MaxValue, "無法執行新遊戲程序。"); }
            catch { TerminateProcess(process, 1); Dispose(); throw; }
            finally { CloseHandle(info.thread); }
        }
        internal static string Quote(string text) { Need(text.IndexOf('"') < 0 && !text.EndsWith("\\", StringComparison.Ordinal), "路徑不正確。"); return "\"" + text + "\""; }
        internal void Stop() { if (!Exited) Need(TerminateProcess(process, 0), "無法停止自己的遊戲程序。"); Need(WaitForSingleObject(process, 15000) == 0, "遊戲程序尚未停止。"); }
        public void Dispose() { if (job != IntPtr.Zero) { CloseHandle(job); job = IntPtr.Zero; } if (process != IntPtr.Zero) { Need(WaitForSingleObject(process, 15000) == 0, "遊戲程序清理未完成。"); CloseHandle(process); process = IntPtr.Zero; } }
    }
    internal sealed class Run : IDisposable
    {
        internal Settings Config; internal string Work, Stream; internal Native Process; internal volatile string Status = "準備中"; internal bool Complete, Cleanup; internal uint? Code; internal Dictionary<string, object> FinalWorld, FinalStream; Mutex lease; bool ownsLease;
        internal Run(Settings config, string work)
        {
            Config = config; Work = Full(work); Plain(Work); Need(!Inside(Work, Root) && !Inside(Root, Work) && !Directory.Exists(Work) && !File.Exists(Work), "請使用程式包之外的新資料夾。");
        }
        internal void Start(Func<bool> cancelled = null)
        {
            Config.Validate(); Verify(); Config.Identity(); var state = Config.Request("/api/sessions/" + Config.Session);
            Need(Text(state, "id") == Config.Session && Text(state, "state") == "Preparing" && Child(state, "combatStream") == null && Text(Child(state, "environment"), "mode") == "VR", "只接受沒有綁定來源的Preparing VR場次；不重啟既有戰場。");
            string name; using (var sha = SHA256.Create()) name = Hex(sha.ComputeHash(Encoding.UTF8.GetBytes(Config.Api + "/" + Config.Session)));
            bool created; lease = new Mutex(true, "Local\\VRCommand.Server." + name, out created); ownsLease = created; Need(created, "此場次已有本機啟動器。");
            using (var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp)) { socket.ExclusiveAddressUse = true; socket.Bind(new IPEndPoint(IPAddress.Parse(Config.Bind), Config.Port)); }
            Directory.CreateDirectory(Work); Save(Path.Combine(Work, "server-config.json"), Config.Config(Path.Combine(Work, "telemetry")));
            Process = new Native(Path.Combine(Work, "server-config.json"), Path.Combine(Work, "server.log"));
            var timer = Stopwatch.StartNew(); Status = "等待遊戲來源與UDP啟動";
            while (timer.Elapsed.TotalSeconds < 90)
            {
                Need(cancelled == null || !cancelled(), "已中止啟動；此輪未完成。");
                Need(!Process.Exited, "遊戲程序在就緒前結束。");
                // This private log line is emitted only AFTER Unity verifies its own immutable combat-stream receipt.
                // New work/log + actual owned process + canonical bootstrap order bind the API stream to this child.
                if (NetworkStarted())
                {
                    state = Config.Request("/api/sessions/" + Config.Session); var stream = Child(state, "combatStream"); Guid id;
                    Stream = Text(stream, "streamId");
                    Need(Guid.TryParseExact(Stream, "D", out id) && id != Guid.Empty && Text(stream, "origin") == "Simulation" && Text(Child(stream, "owner"), "id") == "game-server", "遊戲來源身分不符。");
                    var world = Config.Request("/api/sessions/" + Config.Session + "/world", missing: true);
                    if (world != null)
                    {
                        Need(Text(Child(world, "header"), "sessionId") == Config.Session && Text(Child(world, "header"), "streamId") == Stream && Text(Child(world, "header"), "origin") == "Simulation", "世界來源身分不符。");
                        Need(Text(state, "state") == "Preparing", "公告前場次已離開Preparing。");
                        var endpoint = Config.Request("/api/sessions/" + Config.Session + "/connection-endpoint", new { version = 1, streamId = Stream, address = Config.Address, port = Config.Port });
                        Need(Text(endpoint, "sessionId") == Config.Session && Text(endpoint, "streamId") == Stream && Text(endpoint, "address") == Config.Address && Num(endpoint, "port") == Config.Port && !Yes(endpoint, "sessionEnded"), "公告回條不符。"); Status = "伺服器就緒，請在控制台開始任務"; return;
                    }
                }
                Thread.Sleep(250);
            }
            throw new IOException("遊戲來源90秒內未就緒。");
        }
        bool NetworkStarted()
        {
            var path = Path.Combine(Work, "server.log"); if (!File.Exists(path)) return false;
            using (var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)) using (var reader = new StreamReader(file, Encoding.UTF8))
            {
                Need(file.Length <= 4 * 1024 * 1024, "就緒log超界。"); var text = reader.ReadToEnd(); return text.Contains("VR_NETWORK_STARTED role=Server started=True background=True port=" + Config.Port + "\n") || text.Contains("VR_NETWORK_STARTED role=Server started=True background=True port=" + Config.Port + "\r\n");
            }
        }
        internal void Wait(int seconds, Func<bool> cancel)
        {
            var deadline = Stopwatch.StartNew(); Stopwatch ended = null, retention = null;
            while (deadline.Elapsed.TotalSeconds < seconds && !cancel())
            {
                Need(!Process.Exited, "遊戲程序意外結束，保留journal供檢查。"); var state = Config.Request("/api/sessions/" + Config.Session); var stream = Child(state, "combatStream");
                Need(Text(stream, "streamId") == Stream && Text(stream, "origin") == "Simulation", "場次來源已改變。");
                if (Text(state, "state") == "Ended")
                {
                    if (ended == null) ended = Stopwatch.StartNew(); var world = Config.Request("/api/sessions/" + Config.Session + "/world");
                    Need(Text(Child(world, "header"), "sessionId") == Config.Session && Text(Child(world, "header"), "streamId") == Stream, "封存來源不符。");
                    if (Yes(stream, "sealed") && Yes(world, "complete"))
                    {
                        if (retention == null) { retention = Stopwatch.StartNew(); FinalWorld = world; FinalStream = stream; }
                        Status = "任務已封存，保留戰績傳送 " + Math.Max(0, 36 - (int)retention.Elapsed.TotalSeconds) + " 秒";
                        if (retention.Elapsed.TotalSeconds >= 36) { Complete = true; Status = "任務已封存，停止伺服器"; return; }
                    }
                    else { Need(ended.Elapsed.TotalSeconds < 30, "結束後30秒仍未完成雙封存。"); Status = "等待戰鬥與世界封存"; }
                }
                else Status = "伺服器運行中：" + Text(state, "state");
                Thread.Sleep(250);
            }
            throw new IOException("已中止或超過保留期限；此輪不算正常封存完成。");
        }
        internal object Report(string status, string error) { return new { schemaVersion = 1, status = status, complete = Complete && Cleanup, sessionId = Config.Session, streamId = Stream, childPid = Process == null ? (int?)null : Process.Pid, childExited = Process == null ? (bool?)null : Cleanup, cleanupCompleted = Cleanup, exitCode = Code, workDirectory = Work, finalWorld = FinalWorld, finalCombatStream = FinalStream, playerResultsAcknowledged = (bool?)null, error = error, scope = "Owned server lifecycle and API dual seals; 36s retention, intentional OS process termination after seals, no graceful Unity shutdown / client delivery / gameplay / LAN capacity claim." }; }
        public void Dispose()
        {
            try { if (Process != null) { Process.Stop(); Code = Process.ExitCode; Process.Dispose(); } Cleanup = true; }
            finally { if (lease != null) { if (ownsLease) lease.ReleaseMutex(); lease.Dispose(); lease = null; ownsLease = false; } }
        }
    }
    internal sealed class Window : Form
    {
        readonly TextBox selected = new TextBox(), address = new TextBox { Text = "127.0.0.1" }, bind = new TextBox { Text = "127.0.0.1" };
        readonly NumericUpDown port = new NumericUpDown { Minimum = 1024, Maximum = 65535, Value = 7777 }; readonly ComboBox session = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Enabled = false };
        readonly Button open = new Button { Text = "選擇檔案" }, refresh = new Button { Text = "載入／更新" }, start = new Button { Text = "啟動伺服器", Enabled = false }, abort = new Button { Text = "中止伺服器", Enabled = false };
        readonly Label state = new Label { Text = "先啟動管理服務，再載入其管理實例。", AutoSize = false }, detail = new Label { Text = "請先載入，再明確選擇要啟動的房間與任務。", AutoEllipsis = true };
        readonly CatalogState catalog = new CatalogState(); Run active; volatile bool cancel; Thread worker;
        internal Window()
        {
            Text = "VR Command 遊戲伺服器"; ClientSize = new Size(920, 510); Font = new Font("Microsoft JhengHei UI", 11); FormBorderStyle = FormBorderStyle.FixedDialog; MaximizeBox = false;
            Add(new Label { Text = "每個獨立房間一個伺服器；五房合併場次只需一個。", AutoSize = true }, 24, 24, 860, 30);
            Add(new Label { Text = "管理實例檔案完整路徑", AutoSize = true }, 24, 56, 600, 28); Add(selected, 24, 86, 594, 32); Add(open, 630, 84, 120, 36); Add(refresh, 766, 84, 124, 36);
            Add(new Label { Text = "可選檔，也可直接貼上control-instance.json路徑，再按載入／更新。", AutoSize = true }, 24, 127, 866, 30);
            Add(new Label { Text = "尚未綁定來源的VR場次", AutoSize = true }, 24, 164, 400, 28); Add(session, 24, 194, 866, 34); Add(detail, 24, 240, 866, 48);
            Add(new Label { Text = "公告IPv4", AutoSize = true }, 24, 299, 210, 28); Add(address, 24, 330, 230, 32); Add(new Label { Text = "本機綁定IPv4", AutoSize = true }, 284, 299, 230, 28); Add(bind, 284, 330, 230, 32); Add(new Label { Text = "UDP埠", AutoSize = true }, 544, 299, 130, 28); Add(port, 544, 330, 130, 32);
            Add(start, 24, 382, 260, 40); Add(abort, 310, 382, 260, 40); Add(state, 24, 440, 866, 64);
            selected.TextChanged += delegate { catalog.Edit(selected.Text); start.Enabled = session.Enabled = false; detail.Text = "路徑已變更，請重新載入；未沿用舊場次。"; };
            open.Click += delegate { using (var dialog = new OpenFileDialog { Filter = "管理實例|control-instance.json", CheckFileExists = true }) if (dialog.ShowDialog(this) == DialogResult.OK) { selected.Text = dialog.FileName; Guard(LoadInstance); } };
            refresh.Click += delegate { Guard(LoadInstance); };
            session.SelectedIndexChanged += delegate { if (catalog.Loaded) { var choice = session.SelectedItem as Choice; catalog.Select(choice == null ? null : choice.Id); start.Enabled = catalog.CanStart; detail.Text = choice == null ? "請明確選擇要啟動的房間與任務。" : "場次ID：" + choice.Id + "\r\n任務版本ID：" + choice.MissionId; } };
            start.Click += delegate { Guard(Begin); }; abort.Click += delegate { cancel = true; abort.Enabled = false; state.Text = "中止中；此輪不算正常封存完成。"; };
            FormClosing += delegate(object sender, FormClosingEventArgs e) { if (worker != null && worker.IsAlive) { e.Cancel = true; state.Text = "伺服器仍在執行；請由控制台結束任務，或按中止。"; } };
            var timer = new System.Windows.Forms.Timer { Interval = 500 }; timer.Tick += delegate { if (active != null && !cancel) state.Text = active.Status; }; timer.Start();
        }
        void Add(Control control, int x, int y, int w, int h) { control.SetBounds(x, y, w, h); Controls.Add(control); }
        void Guard(Action action) { try { action(); } catch (Exception e) { state.Text = "未完成：" + Safe(e); } }
        void LoadInstance()
        {
            start.Enabled = session.Enabled = false; detail.Text = "正在重新讀取管理服務；不保留未確認的啟動選取。";
            try { catalog.Load(); }
            catch { session.Items.Clear(); detail.Text = "載入未完成，已清除舊場次。請確認管理服務與路徑後重新載入。"; throw; }
            var retained = catalog.Selected; session.Items.Clear(); foreach (var choice in catalog.Current.Choices) session.Items.Add(choice);
            session.Enabled = true; if (retained != null) session.SelectedItem = retained;
            start.Enabled = catalog.CanStart; detail.Text = retained == null ? "請明確選擇要啟動的房間與任務。" : "場次ID：" + retained.Id + "\r\n任務版本ID：" + retained.MissionId;
            state.Text = session.Items.Count > 0 ? "清單已更新；只保留同一管理實例中仍可啟動的原選取。" : "沒有可啟動的Preparing VR場次，請先在控制台建立。";
        }
        void Begin()
        {
            Need(catalog.CanStart, "請先載入實例並明確選擇待開場次。"); var target = catalog.Current.Target;
            var config = new Settings { Api = target.Api, Key = target.Key, Session = catalog.Selected.Id, Address = address.Text, Bind = bind.Text, Port = (int)port.Value }; config.Validate();
            var work = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VrCommand", "GameServers", DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N"));
            var reports = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VrCommand", "GameServerReports"); Directory.CreateDirectory(reports); var report = Path.Combine(reports, Guid.NewGuid().ToString("N") + ".json");
            active = new Run(config, work); cancel = false; open.Enabled = refresh.Enabled = start.Enabled = selected.Enabled = address.Enabled = bind.Enabled = port.Enabled = session.Enabled = false; abort.Enabled = true;
            worker = new Thread(delegate() { string error = null; try { active.Start(() => cancel); active.Wait(86400, () => cancel); } catch (Exception e) { error = Safe(e); } finally { try { active.Dispose(); } catch (Exception e) { error = Safe(e); } }
                try { Save(report, active.Report(active.Complete && active.Cleanup ? "sealed-stopped" : "incomplete", error)); } catch (Exception e) { error = Safe(e); }
                var final = error == null && active.Complete && active.Cleanup ? "任務已封存並停止。" : "未完成：" + (error ?? "封存未確認。"); BeginInvoke((Action)delegate { active = null; catalog.Edit(selected.Text); session.Enabled = false; detail.Text = "此輪已收尾；再次啟動前請重新載入場次。"; state.Text = final + " 結果：" + report; open.Enabled = refresh.Enabled = selected.Enabled = address.Enabled = bind.Enabled = port.Enabled = true; abort.Enabled = false; }); }); worker.IsBackground = false; worker.Start();
        }
    }
    [STAThread] static int Main(string[] args)
    {
        if (args.Length == 0) { Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false); Application.Run(new Window()); return 0; }
        string report = null; Run run = null; bool outputValid = false; string error = null;
        try
        {
            var options = new Dictionary<string, string>(); for (var i = 0; i < args.Length; i += 2) { Need(i + 1 < args.Length && !options.ContainsKey(args[i]), "參數格式錯誤。"); options.Add(args[i], args[i + 1]); }
            Need(options.ContainsKey("--report"), "需要結果路徑。"); report = options["--report"]; Output(report, options.ContainsKey("--catalog") ? Path.GetDirectoryName(Full(options["--catalog"])) : options.ContainsKey("--work") ? options["--work"] : null); outputValid = true;
            if (options.Count == 2 && options.ContainsKey("--verify")) { Need(options["--verify"] == "package", "驗證參數錯誤。"); Verify(); Save(report, new { schemaVersion = 1, complete = true, status = "verified" }); return 0; }
            if (options.Count == 2 && options.ContainsKey("--catalog")) { Verify(); Save(report, Catalog.Load(options["--catalog"]).Public()); return 0; }
            Need(options.Count == 5 && options.ContainsKey("--run") && options.ContainsKey("--work") && options.ContainsKey("--seconds") && options.ContainsKey("--ready-report"), "需要run/work/seconds/ready-report/report五個參數。");
            int seconds; Need(Int32.TryParse(options["--seconds"], out seconds) && seconds >= 60 && seconds <= 86400, "執行期限須為60至86400秒。");
            var configPath = Full(options["--run"]); var work = Full(options["--work"]); Need(!Inside(configPath, Root) && !Inside(configPath, work) && !Inside(work, configPath), "設定必須在程式包與新資料夾之外。");
            Output(report, work); Output(options["--ready-report"], work); Need(!String.Equals(Full(report), Full(options["--ready-report"]), StringComparison.OrdinalIgnoreCase), "結果路徑不能重複。");
            run = new Run(Settings.From(Read(configPath, 8192)), work); run.Start(); Save(options["--ready-report"], new { schemaVersion = 1, status = "ready", sessionId = run.Config.Session, streamId = run.Stream, childPid = run.Process.Pid, address = run.Config.Address, port = run.Config.Port, workDirectory = run.Work }); run.Wait(seconds, () => false);
        }
        catch (Exception e) { error = Safe(e); }
        finally { if (run != null) try { run.Dispose(); } catch (Exception e) { error = Safe(e); } }
        try { if (outputValid) Save(report, run == null ? (object)new { schemaVersion = 1, complete = false, status = "rejected", error = error } : run.Report(run.Complete && run.Cleanup ? "sealed-stopped" : "incomplete", error)); } catch { return 1; }
        return error == null && run != null && run.Complete && run.Cleanup ? 0 : 1;
    }
}
