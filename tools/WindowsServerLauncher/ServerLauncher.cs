// Framework 4.8 companion for the existing Unity Windows build. No Master key is passed to Unity.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Net.Security;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal static class ServerLauncher
{
    internal static readonly string Root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar);
    [ThreadStatic] static JavaScriptSerializer serializer;
    internal static JavaScriptSerializer Json { get { return serializer ?? (serializer = new JavaScriptSerializer { MaxJsonLength = 4 * 1024 * 1024 }); } }
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
    internal sealed class UdpBinding
    {
        const uint InsufficientBuffer = 122;
        const uint Ipv4 = 2;
        const int OwnerPid = 1;
        // The table starts with a DWORD count. Each IPv4 row has three DWORDs.
        const int HeaderBytes = 4, RowBytes = 12, MaximumBytes = 4 * 1024 * 1024;
        [DllImport("iphlpapi.dll", ExactSpelling = true)]
        static extern uint GetExtendedUdpTable(IntPtr table, ref int size, [MarshalAs(UnmanagedType.Bool)] bool ordered, uint family, int tableClass, uint reserved);

        readonly int processId, port;
        readonly string address;
        readonly DateTimeOffset observedAt;
        UdpBinding(int processId, string address, int port)
        {
            this.processId = processId; this.address = address; this.port = port; observedAt = DateTimeOffset.UtcNow;
        }
        internal object Public() { return new { processId = processId, address = address, port = port, observedAtUtc = observedAt.ToString("O") }; }

        internal static UdpBinding Find(int processId, string address, int port)
        {
            var expectedAddress = BitConverter.ToInt32(IPAddress.Parse(address).GetAddressBytes(), 0);
            var expectedPort = (ushort)IPAddress.HostToNetworkOrder((short)port);
            int size = 0;
            var result = GetExtendedUdpTable(IntPtr.Zero, ref size, false, Ipv4, OwnerPid, 0);
            if (result != InsufficientBuffer) throw new IOException("無法讀取 Windows UDP 端點，錯誤 " + result + "。");
            for (var attempt = 0; attempt < 3; attempt++)
            {
                Need(size >= HeaderBytes && size <= MaximumBytes, "Windows UDP 端點表大小超界。");
                var capacity = size;
                var table = Marshal.AllocHGlobal(capacity);
                try
                {
                    result = GetExtendedUdpTable(table, ref size, false, Ipv4, OwnerPid, 0);
                    if (result == InsufficientBuffer) continue;
                    if (result != 0) throw new IOException("無法讀取 Windows UDP 端點，錯誤 " + result + "。");
                    var count = Marshal.ReadInt32(table);
                    Need(count >= 0 && count <= (capacity - HeaderBytes) / RowBytes, "Windows UDP 端點表內容超界。");
                    for (var index = 0; index < count; index++)
                    {
                        var row = IntPtr.Add(table, HeaderBytes + index * RowBytes);
                        if (Marshal.ReadInt32(row, 8) == processId && Marshal.ReadInt32(row, 0) == expectedAddress
                            && (Marshal.ReadInt32(row, 4) & 0xffff) == expectedPort)
                            return new UdpBinding(processId, address, port);
                    }
                    return null;
                }
                finally { Marshal.FreeHGlobal(table); }
            }
            throw new IOException("Windows UDP 端點表持續變動，無法核對本次綁定。");
        }
    }
    internal sealed class ManagementUnavailable : IOException
    {
        internal ManagementUnavailable(int code) : base("管理服務請求失敗，HTTP " + code + "。") { }
        internal static bool IsTemporary(int code, WebExceptionStatus status)
        {
            if (code != 0) return code == 502 || code == 503 || code == 504;
            return status == WebExceptionStatus.ConnectFailure || status == WebExceptionStatus.ConnectionClosed
                || status == WebExceptionStatus.KeepAliveFailure || status == WebExceptionStatus.ReceiveFailure
                || status == WebExceptionStatus.SendFailure || status == WebExceptionStatus.Timeout;
        }
    }
    internal sealed class Settings
    {
        internal string Api, Key, Session, Address, Bind, CertificateSha256; internal int Port;
        internal static Settings From(Dictionary<string, object> value)
        {
            var pin = Text(value, "managementCertificateSha256");
            Need(value.Count == (value.ContainsKey("managementCertificateSha256") ? 8 : 7)
                && (!value.ContainsKey("managementCertificateSha256") || !String.IsNullOrEmpty(pin))
                && Num(value, "port") >= 1024 && Num(value, "port") <= 65535, "請使用伺服器連線檔與有效UDP埠。");
            var result = new Settings { Api = Text(value, "managementApiUrl"), Key = Text(value, "gameServerKey"), Session = Text(value, "sessionId"), Address = Text(value, "address"), Bind = Text(value, "listenAddress"), Port = (int)Num(value, "port"), CertificateSha256 = pin };
            Need(Text(value, "role") == "Server", "這是獨立伺服器啟動器。"); result.Validate(); return result;
        }
        internal void Validate()
        {
            Guid id; Need(Guid.TryParseExact(Session, "D", out id) && id != Guid.Empty && id.ToString("D") == Session, "場次ID格式錯誤。");
            ValidateTarget();
            IPv4(Address, false); LocalBind(Bind); Need(Bind == "0.0.0.0" || Bind == Address, "明確綁定地址須與公告地址相同。"); Need(Port >= 1024 && Port <= 65535, "UDP埠須為1024至65535。");
        }
        internal Settings ForSession(string session, string address, string bind, int port)
        {
            var settings = new Settings { Api = Api, Key = Key, CertificateSha256 = CertificateSha256,
                Session = session, Address = address, Bind = bind, Port = port };
            settings.Validate();
            return settings;
        }
        internal void ValidateTarget()
        {
            Uri uri;
            Need(Uri.TryCreate(Api, UriKind.Absolute, out uri) && (uri.Scheme == "http" || uri.Scheme == "https")
                && uri.AbsolutePath == "/" && uri.Query == "" && uri.Fragment == "" && uri.UserInfo == "", "請使用管理服務的HTTP或HTTPS原點。");
            var authority = uri.Scheme + "://" + uri.Host;
            if (uri.Scheme == "http")
            {
                IPv4(uri.Host, false);
                Need(uri.Port >= 1024 && Api == authority + ":" + uri.Port && CertificateSha256 == null,
                    "HTTP使用IPv4與埠號；憑證指紋須搭配HTTPS。");
            }
            else
            {
                if (uri.HostNameType == UriHostNameType.IPv4) IPv4(uri.Host, false);
                else Need(uri.HostNameType == UriHostNameType.Dns && System.Text.RegularExpressions.Regex.IsMatch(uri.Host,
                    @"\A[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*\z"), "HTTPS管理名稱不正確。");
                Need((uri.Port == 443 || uri.Port >= 1024) && (Api == authority + ":" + uri.Port || uri.Port == 443 && Api == authority), "HTTPS管理原點格式不正確。");
                Need(CertificateSha256 != null && System.Text.RegularExpressions.Regex.IsMatch(CertificateSha256, @"\A[0-9a-f]{64}\z"), "HTTPS需要管理員提供的憑證SHA-256。");
            }
            Need(Key != null && Key.Length >= 32 && Key.Length <= 512, "GameServer金鑰格式錯誤。"); foreach (var c in Key) Need(c > 32 && c < 127, "GameServer金鑰格式錯誤。");
        }
        internal object Config(string telemetry, string origin) { return new { role = "Server", address = Address, listenAddress = Bind, port = Port, sessionId = Session, managementApiUrl = Api, managementCertificateSha256 = CertificateSha256, gameServerKey = Key, telemetryOrigin = origin, telemetryDirectory = telemetry }; }

        private bool CheckCertificate(X509Certificate certificate, SslPolicyErrors errors)
        {
            if (certificate == null || (errors & ~SslPolicyErrors.RemoteCertificateChainErrors) != SslPolicyErrors.None) return false;
            using (var hash = SHA256.Create())
            using (var leaf = new X509Certificate2(certificate))
            {
                var now = DateTime.UtcNow;
                return leaf.NotBefore.ToUniversalTime() <= now && now < leaf.NotAfter.ToUniversalTime()
                    && BitConverter.ToString(hash.ComputeHash(leaf.RawData)).Replace("-", "").ToLowerInvariant() == CertificateSha256;
            }
        }
        private HttpWebRequest ManagementRequest(string path)
        {
            var request = (HttpWebRequest)WebRequest.Create(Api + path); request.Proxy = null; request.AllowAutoRedirect = false; request.Timeout = 5000; request.ReadWriteTimeout = 5000;
            if (CertificateSha256 != null)
            {
                request.ConnectionGroupName = CertificateSha256;
                request.ServerCertificateValidationCallback = (sender, certificate, chain, errors) => CheckCertificate(certificate, errors);
            }
            request.Headers[HttpRequestHeader.Authorization] = "Bearer " + Key;
            return request;
        }
        internal Dictionary<string, object> Request(string path, object body = null, bool missing = false)
        {
            var request = ManagementRequest(path);
            if (body != null) { request.Method = "PUT"; request.ContentType = "application/json"; var bytes = Encoding.UTF8.GetBytes(Json.Serialize(body)); request.ContentLength = bytes.Length; using (var stream = request.GetRequestStream()) stream.Write(bytes, 0, bytes.Length); }
            try { using (var response = (HttpWebResponse)request.GetResponse()) using (var reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8)) { Need(response.StatusCode == HttpStatusCode.OK, "管理服務回應不正確。"); var bytes = new char[256 * 1024 + 1]; var count = 0; int read; while ((read = reader.Read(bytes, count, bytes.Length - count)) > 0 && count < bytes.Length) count += read; Need(count <= 256 * 1024, "管理回應過大。"); var result = Map(Json.DeserializeObject(new string(bytes, 0, count))); Need(result != null, "管理回應格式錯誤。"); return result; } }
            catch (WebException error)
            {
                var response = error.Response as HttpWebResponse; var code = response == null ? 0 : (int)response.StatusCode;
                if (response != null) response.Dispose();
                if (missing && code == 404) return null;
                if (body == null && ManagementUnavailable.IsTemporary(code, error.Status)) throw new ManagementUnavailable(code);
                throw new IOException("管理服務請求失敗，HTTP " + code + "。");
            }
            catch (IOException error)
            {
                if (body == null && error.InnerException is SocketException) throw new ManagementUnavailable(0);
                throw;
            }
        }
        internal void Identity() { ValidateTarget(); Need(Text(Request("/"), "version") == "0.31.0", "需要管理服務0.31.0。"); Need(Text(Request("/api/me"), "role") == "GameServer", "請使用GameServer角色金鑰。"); }
        internal void CheckPort()
        {
            using (var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp))
            {
                socket.ExclusiveAddressUse = true;
                socket.Bind(new IPEndPoint(IPAddress.Parse(Bind), Port));
            }
        }
        internal object[] Sessions()
        {
            var request = ManagementRequest("/api/sessions");
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
        internal string Id, MissionId, MissionName, Mode, Experience; internal int[] Rooms, MissingAlignmentRooms;
        internal long Sequence;
        internal bool CanStart { get { return MissingAlignmentRooms.Length == 0; } }
        internal static string GuidValue(string value) { Guid id; Need(Guid.TryParseExact(value, "D", out id) && id != Guid.Empty && id.ToString("D") == value, "場次或任務識別格式錯誤。"); return value; }
        internal static int[] ReadRooms(Dictionary<string, object> value, string mode)
        {
            object raw; Need(value.TryGetValue("roomIds", out raw) && raw is object[], "場次房間缺失。"); var rows = (object[])raw;
            Need(mode == "Independent" && rows.Length == 1 || mode == "Linked" && rows.Length == 5, "場次房間或連線模式錯誤。");
            var seen = new HashSet<int>(); var rooms = new List<int>(); foreach (var row in rows) { Need(row is int && (int)row >= 1 && (int)row <= 5 && seen.Add((int)row), "場次房間重複或越界。"); rooms.Add((int)row); } rooms.Sort();
            return rooms.ToArray();
        }
        internal static int[] MissingAlignment(Dictionary<string, object> session, int[] rooms)
        {
            var pins = Child(session, "roomAlignment");
            return Array.FindAll(rooms, room => !ValidPin(Text(pins, "room" + room.ToString(System.Globalization.CultureInfo.InvariantCulture))));
        }
        static bool ValidPin(string value)
        {
            if (value == null || value.Length != 64) return false;
            foreach (var c in value) if (!(c >= '0' && c <= '9' || c >= 'a' && c <= 'f')) return false;
            return true;
        }
        static string RoomLabels(int[] rooms) { return String.Join("、", Array.ConvertAll(rooms, room => room.ToString(System.Globalization.CultureInfo.InvariantCulture))); }
        internal static string AlignmentPrompt(int[] rooms) { return "MR 房間 " + RoomLabels(rooms) + " 尚無有效的校正鎖定。請由主控鎖定後重新載入。"; }
        internal static Choice Parse(Dictionary<string, object> value)
        {
            Need(value != null, "場次列表內容錯誤。"); var mission = Child(value, "mission"); var name = Text(Child(mission, "definition"), "name");
            Need(!String.IsNullOrWhiteSpace(name) && name.Length <= 100, "任務名稱格式錯誤。");
            var mode = Text(value, "mode"); var rooms = ReadRooms(value, mode); var experience = Text(Child(value, "environment"), "mode");
            return new Choice { Id = GuidValue(Text(value, "id")), MissionId = GuidValue(Text(mission, "id")), MissionName = name,
                Sequence = Num(value, "sequence"), Mode = mode, Experience = experience, Rooms = rooms,
                MissingAlignmentRooms = experience == "MR" ? MissingAlignment(value, rooms) : new int[0] };
        }
        internal static string Label(string value)
        {
            var text = new StringBuilder(); foreach (var c in value) { if (Char.GetUnicodeCategory(c) == System.Globalization.UnicodeCategory.Format) continue; text.Append(Char.IsControl(c) || Char.IsWhiteSpace(c) ? ' ' : c); }
            var result = text.ToString().Trim(); if (result.Length > 32) { var length = Char.IsHighSurrogate(result[31]) ? 31 : 32; result = result.Substring(0, length) + "…"; } return result;
        }
        public override string ToString() { return "房間 " + RoomLabels(Rooms) + " · " + (Mode == "Linked" ? "五房全連線" : "單房獨立") + " · " + Experience + " · " + (CanStart ? "" : "待鎖定校正 · ") + Label(MissionName) + " · " + Id.Substring(0, 8); }
        internal string Detail() { return "場次ID：" + Id + "\r\n任務版本ID：" + MissionId + (CanStart ? "" : "\r\n" + AlignmentPrompt(MissingAlignmentRooms)); }
        internal object Public() { return new { id = Id, missionId = MissionId, missionName = MissionName, mode = Mode, experienceMode = Experience, roomIds = Rooms, canStart = CanStart, missingAlignmentRoomIds = MissingAlignmentRooms, display = ToString() }; }
    }
    internal sealed class Catalog
    {
        internal Settings Target; internal string PathName, InstanceId; internal List<Choice> Choices;
        internal static Catalog Load(string path)
        {
            var catalog = ReadTarget(path);
            catalog.Target.Identity();
            catalog.Choices = Parse(catalog.Target.Sessions());
            return catalog;
        }
        internal static Catalog ReadTarget(string path)
        {
            Need(!String.IsNullOrWhiteSpace(path), "請輸入control-instance.json完整路徑。");
            path = Full(path.Trim()); Need(String.Equals(Path.GetFileName(path), "control-instance.json", StringComparison.OrdinalIgnoreCase) && !Inside(path, Root), "請選取包外的control-instance.json。");
            var marker = Read(path, 4096);
            var kind = Text(marker, "kind");
            Need(Num(marker, "schemaVersion") == 1, "管理實例格式不符。");
            var id = Choice.GuidValue(Text(marker, "instanceId"));
            Settings target;
            if (kind == "VrCommand-RemoteGameServer")
            {
                target = new Settings { Api = Text(marker, "managementApiUrl"), Key = Text(marker, "gameServerKey"),
                    CertificateSha256 = Text(marker, "managementCertificateSha256") };
                Need(marker.Count == 6 && target.Api != null && target.Api.StartsWith("https://", StringComparison.Ordinal), "遠端管理設定須使用 HTTPS 與憑證指紋。");
            }
            else
            {
                Need(kind == "VrCommand-ControlServer" && Num(marker, "port") >= 1024 && Num(marker, "port") <= 65535, "管理實例格式不符。");
                var keys = Child(Read(Path.Combine(Path.GetDirectoryName(path), "operator-keys.json"), 8192), "OperatorKeys");
                target = new Settings { Api = "http://" + IPv4(Text(marker, "bindAddress"), false) + ":" + Num(marker, "port"), Key = Text(keys, "GameServer") };
            }
            target.ValidateTarget();
            return new Catalog { Target = target, PathName = path, InstanceId = id };
        }
        internal static List<Choice> Parse(object[] rows)
        {
            Need(rows != null && rows.Length <= 5, "場次列表超界。"); var choices = new List<Choice>(); var ids = new HashSet<string>(); var occupied = new HashSet<int>();
            foreach (var item in rows)
            {
                var value = Map(item); Need(value != null, "場次列表內容錯誤。");
                object bound; Need(value.TryGetValue("combatStream", out bound) && (bound == null || Map(bound) != null), "場次來源格式錯誤。");
                var phase = Text(value, "state"); var experience = Text(Child(value, "environment"), "mode"); Need(phase == "Preparing" || phase == "Running" || phase == "Paused" || phase == "Ended", "場次階段格式錯誤。"); Need(experience == "VR" || experience == "MR", "場次環境格式錯誤。");
                if (phase != "Preparing" || bound != null) continue;
                var choice = Choice.Parse(value); Need(ids.Add(choice.Id), "場次識別重複。"); foreach (var room in choice.Rooms) Need(occupied.Add(room), "待開場次房間重疊。"); choices.Add(choice);
            }
            choices.Sort((a, b) => a.Rooms[0] != b.Rooms[0] ? a.Rooms[0].CompareTo(b.Rooms[0]) : String.CompareOrdinal(a.Id, b.Id)); return choices;
        }
        internal bool Same(Catalog other) { return other != null && String.Equals(PathName, other.PathName, StringComparison.OrdinalIgnoreCase) && InstanceId == other.InstanceId && Target.Api == other.Target.Api && Target.Key == other.Target.Key && Target.CertificateSha256 == other.Target.CertificateSha256; }
        internal object Public() { return new { schemaVersion = 1, status = "catalogued", complete = true, instanceId = InstanceId, sessions = Choices.ConvertAll(choice => choice.Public()), scope = "Read-only Preparing VR and MR choices. No key in report." }; }
    }
    internal sealed class CatalogState
    {
        internal string Draft = ""; internal Catalog Current; internal Choice Selected; internal bool Loaded;
        internal bool CanStart { get { return Loaded && Current != null && Selected != null && Selected.CanStart && String.Equals(Full(Draft.Trim()), Current.PathName, StringComparison.OrdinalIgnoreCase); } }
        internal void Edit(string path) { Draft = path; Loaded = false; }
        internal void Load()
        {
            var old = Current; var selectedId = Selected == null ? null : Selected.Id; Loaded = false; Current = null; Selected = null;
            var loaded = Catalog.Load(Draft); Current = loaded; Loaded = true;
            if (loaded.Same(old) && selectedId != null) Selected = loaded.Choices.Find(choice => choice.Id == selectedId);
        }
        internal void Select(string id) { Need(Loaded && Current != null, "請先載入管理實例。"); Selected = id == null ? null : Current.Choices.Find(choice => choice.Id == id); }
        internal Settings StartSettings(string address, string bind, int port)
        {
            Need(CanStart, "請先載入實例並明確選擇待開場次。");
            try { Need(Current.Same(Catalog.ReadTarget(Draft)), "管理設定已變更；請重新載入及選擇場次。"); }
            catch { Loaded = false; Current = null; Selected = null; throw; }
            return Current.Target.ForSession(Selected.Id, address, bind, port);
        }
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
        internal Native(string config, string log, bool peerDiagnostics)
        {
            var exe = Path.Combine(Root, "Runtime/VrCommand.exe"); job = CreateJobObject(IntPtr.Zero, null); Need(job != IntPtr.Zero, "無法建立程序群組。");
            var limits = new Limits(); limits.basic.flags = 0x2000; if (!SetInformationJobObject(job, 9, ref limits, Marshal.SizeOf(limits))) { Dispose(); throw new IOException("無法設定程序群組。"); }
            var startup = new Startup(); startup.size = Marshal.SizeOf(startup); Info info;
            var command = new StringBuilder(Quote(exe) + " -batchmode -nographics -job-worker-count 2 -logFile " + Quote(log) + " --vr-config " + Quote(config));
            if (peerDiagnostics) command.Append(" --vr-peer-diagnostics");
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
        internal UdpBinding VerifiedUdp;
        internal bool PeerDiagnosticsEnabled { get; private set; }
        private string Origin;
        const int ManagementRecoverySeconds = 15;
        int managementOutages, managementRecoveries;
        long longestManagementOutageMilliseconds;
        internal Run(Settings config, string work)
        {
            Config = config; Work = Full(work); Plain(Work); Need(!Inside(Work, Root) && !Inside(Root, Work) && !Directory.Exists(Work) && !File.Exists(Work), "請使用程式包之外的新資料夾。");
        }
        internal void Start(Func<bool> cancelled = null, bool peerDiagnostics = false, bool packageVerified = false,
            Action beforeNative = null, bool deferPublication = false)
        {
            Config.Validate(); if (!packageVerified) Verify(); Config.Identity(); var state = Config.Request("/api/sessions/" + Config.Session);
            var experience = Text(Child(state, "environment"), "mode");
            object streamValue;
            Need(Text(state, "id") == Config.Session && Text(state, "state") == "Preparing" && state.TryGetValue("combatStream", out streamValue) && streamValue == null
                && (experience == "VR" || experience == "MR"), "只接受尚未綁定來源的 Preparing VR 或 MR 場次。");
            if (experience == "MR")
            {
                var missing = Choice.MissingAlignment(state, Choice.ReadRooms(state, Text(state, "mode")));
                if (missing.Length > 0) throw new InvalidDataException(Choice.AlignmentPrompt(missing));
            }
            Origin = experience == "MR" ? "GameServer" : "Simulation";
            string name; using (var sha = SHA256.Create()) name = Hex(sha.ComputeHash(Encoding.UTF8.GetBytes(Config.Api + "/" + Config.Session)));
            bool created; lease = new Mutex(true, "Local\\VRCommand.Server." + name, out created); ownsLease = created; Need(created, "此場次已有本機啟動器。");
            Config.CheckPort();
            if (beforeNative != null) beforeNative();
            Need(cancelled == null || !cancelled(), "已中止啟動；此輪未完成。");
            Directory.CreateDirectory(Work); Save(Path.Combine(Work, "server-config.json"), Config.Config(Path.Combine(Work, "telemetry"), Origin));
            Process = new Native(Path.Combine(Work, "server-config.json"), Path.Combine(Work, "server.log"), peerDiagnostics);
            PeerDiagnosticsEnabled = peerDiagnostics;
            var timer = Stopwatch.StartNew(); Status = "等待遊戲來源與UDP啟動";
            var awaitingUdp = false;
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
                    Need(Guid.TryParseExact(Stream, "D", out id) && id != Guid.Empty && Text(stream, "origin") == Origin && Text(Child(stream, "owner"), "id") == "game-server", "遊戲來源身分不符。");
                    var world = Config.Request("/api/sessions/" + Config.Session + "/world", missing: true);
                    if (world != null)
                    {
                        Need(Text(Child(world, "header"), "sessionId") == Config.Session && Text(Child(world, "header"), "streamId") == Stream && Text(Child(world, "header"), "origin") == Origin, "世界來源身分不符。");
                        Need(Text(state, "state") == "Preparing", "公告前場次已離開Preparing。");
                        var binding = UdpBinding.Find(Process.Pid, Config.Bind, Config.Port);
                        if (binding == null)
                        {
                            awaitingUdp = true; Status = "等待 Windows 確認原遊戲程序的 UDP 綁定";
                            Thread.Sleep(250);
                            continue;
                        }
                        Need(cancelled == null || !cancelled(), "已中止啟動；此輪未完成。");
                        Need(!Process.Exited, "遊戲程序在公告前結束。");
                        VerifiedUdp = binding;
                        if (deferPublication) Status = "已確認 UDP，等候全館公告";
                        else ConfirmEndpoint(Config.Request("/api/sessions/" + Config.Session + "/connection-endpoint", EndpointDraft()));
                        return;
                    }
                }
                Thread.Sleep(250);
            }
            throw new IOException(awaitingUdp ? "90 秒內未確認原遊戲程序的 UDP 綁定。" : "遊戲來源90秒內未就緒。");
        }
        internal object EndpointDraft() { return new { version = 1, streamId = Stream, address = Config.Address, port = Config.Port }; }
        internal void ConfirmEndpoint(Dictionary<string, object> endpoint)
        {
            Need(Num(endpoint, "version") == 1 && Text(endpoint, "sessionId") == Config.Session && Text(endpoint, "streamId") == Stream
                && Text(endpoint, "address") == Config.Address && Num(endpoint, "port") == Config.Port
                && endpoint.ContainsKey("sessionEnded") && endpoint["sessionEnded"] is bool && !Yes(endpoint, "sessionEnded"), "公告回條不符。");
            Status = "伺服器就緒，請在控制台開始任務";
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
            TimeSpan? unavailableSince = null;
            long lastSequence = 0, lastCombatSequence = 0;
            while (deadline.Elapsed.TotalSeconds < seconds && !cancel())
            {
                Need(!Process.Exited, "遊戲程序意外結束，保留journal供檢查。");
                var pollStarted = deadline.Elapsed;
                if (unavailableSince.HasValue) CheckRecoveryTime(pollStarted - unavailableSince.Value);
                Dictionary<string, object> stream, world = null;
                string phase;
                try
                {
                    var state = Config.Request("/api/sessions/" + Config.Session);
                    stream = Child(state, "combatStream"); phase = Text(state, "state");
                    Need(Text(state, "id") == Config.Session && Text(stream, "streamId") == Stream && Text(stream, "origin") == Origin
                        && Text(Child(stream, "owner"), "id") == "game-server", "場次來源已改變。");
                    var sequence = Num(state, "sequence"); var combatSequence = Num(stream, "acceptedSequence");
                    Need(sequence > 0 && sequence >= lastSequence && combatSequence >= lastCombatSequence
                        && (phase == "Ended" || (ended == null && (phase == "Preparing" || phase == "Running" || phase == "Paused"))),
                        "場次階段或接受序號不符。");
                    lastSequence = sequence; lastCombatSequence = combatSequence;
                    if (phase == "Ended")
                    {
                        if (ended == null) ended = Stopwatch.StartNew();
                        world = Config.Request("/api/sessions/" + Config.Session + "/world");
                        var header = Child(world, "header");
                        Need(Text(header, "sessionId") == Config.Session && Text(header, "streamId") == Stream && Text(header, "origin") == Origin,
                            "封存來源不符。");
                    }
                }
                catch (ManagementUnavailable)
                {
                    if (!unavailableSince.HasValue) { unavailableSince = pollStarted; managementOutages++; }
                    var elapsed = deadline.Elapsed - unavailableSince.Value;
                    CheckRecoveryTime(elapsed);
                    Need(ended == null || retention != null || ended.Elapsed.TotalSeconds < 30, "結束後30秒仍未完成雙封存。");
                    Status = "管理服務暫時無法連線，等待原服務恢復 " + (ManagementRecoverySeconds - (int)elapsed.TotalSeconds) + " 秒";
                    Thread.Sleep(250);
                    continue;
                }
                if (unavailableSince.HasValue)
                {
                    CheckRecoveryTime(deadline.Elapsed - unavailableSince.Value);
                    managementRecoveries++;
                    unavailableSince = null;
                }
                if (deadline.Elapsed.TotalSeconds >= seconds || cancel()) break;
                Need(!Process.Exited, "遊戲程序意外結束，保留journal供檢查。");
                if (phase == "Ended")
                {
                    if (retention != null)
                        Need(Yes(stream, "sealed") && Yes(world, "complete") && Num(stream, "acceptedSequence") == Num(FinalStream, "acceptedSequence")
                            && Num(world, "acceptedSequence") == Num(FinalWorld, "acceptedSequence"), "已確認的封存界線不符。");
                    if (Yes(stream, "sealed") && Yes(world, "complete"))
                    {
                        if (retention == null) { retention = Stopwatch.StartNew(); FinalWorld = world; FinalStream = stream; }
                        Status = "任務已封存，保留戰績傳送 " + Math.Max(0, 36 - (int)retention.Elapsed.TotalSeconds) + " 秒";
                        if (retention.Elapsed.TotalSeconds >= 36) { Complete = true; Status = "任務已封存，停止伺服器"; return; }
                    }
                    else { Need(ended.Elapsed.TotalSeconds < 30, "結束後30秒仍未完成雙封存。"); Status = "等待戰鬥與世界封存"; }
                }
                else Status = "伺服器運行中 " + phase + " · 啟動時已核對 UDP " + Config.Bind + ":" + Config.Port;
                Thread.Sleep(250);
            }
            throw new IOException("已中止或超過保留期限；此輪不算正常封存完成。");
        }
        void CheckRecoveryTime(TimeSpan elapsed)
        {
            longestManagementOutageMilliseconds = Math.Max(longestManagementOutageMilliseconds, (long)elapsed.TotalMilliseconds);
            Need(elapsed.TotalSeconds < ManagementRecoverySeconds, "管理服務等待恢復逾時，保留journal供檢查。");
        }
        internal object Report(string status, string error) { return new { schemaVersion = 1, status = status, complete = Complete && Cleanup, sessionId = Config.Session, streamId = Stream, childPid = Process == null ? (int?)null : Process.Pid, childExited = Process == null ? (bool?)null : Cleanup, cleanupCompleted = Cleanup, exitCode = Code, workDirectory = Work, udpBinding = VerifiedUdp == null ? null : VerifiedUdp.Public(), peerDiagnosticsEnabled = PeerDiagnosticsEnabled, finalWorld = FinalWorld, finalCombatStream = FinalStream, playerResultsAcknowledged = (bool?)null, managementRecovery = new { outages = managementOutages, recoveries = managementRecoveries, longestMilliseconds = longestManagementOutageMilliseconds }, error = error, scope = "Owned server lifecycle and API dual seals; 36s retention, intentional OS process termination after seals, no graceful Unity shutdown / client delivery / gameplay / LAN capacity claim." }; }
        internal object Ready() { return new { schemaVersion = 1, status = "ready", sessionId = Config.Session, streamId = Stream, childPid = Process.Pid, address = Config.Address, port = Config.Port, workDirectory = Work, udpBinding = VerifiedUdp.Public(), peerDiagnosticsEnabled = PeerDiagnosticsEnabled }; }
        public void Dispose()
        {
            try
            {
                if (Process != null) try { Process.Stop(); Code = Process.ExitCode; }
                finally { Process.Dispose(); }
                Cleanup = true;
            }
            finally { if (lease != null) { if (ownsLease) lease.ReleaseMutex(); lease.Dispose(); lease = null; ownsLease = false; } }
        }
    }

    sealed class VenueServer
    {
        internal Choice Choice;
        internal Settings Config;
        internal Run Run;
        internal bool Ready;
        internal string Error;
    }

    sealed class VenueGate
    {
        internal volatile bool Abort;
    }

    sealed class VenuePlan
    {
        internal long Version;
        internal Catalog Catalog;
        internal string Topology;
        internal List<VenueServer> Servers;
        internal object Public()
        {
            return new { schemaVersion = 1, status = "venue-checked", complete = true, topology = Topology, instanceId = Catalog.InstanceId,
                servers = Servers.ConvertAll(server =>
                {
                    var choice = server.Choice;
                    var row = new Dictionary<string, object> { { "roomIds", choice.Rooms }, { "sessionId", choice.Id },
                        { "missionId", choice.MissionId }, { "missionName", choice.MissionName }, { "experienceMode", choice.Experience },
                        { "address", server.Config.Address }, { "listenAddress", server.Config.Bind }, { "port", server.Config.Port } };
                    if (Version == 2) row.Add("sessionSequence", choice.Sequence);
                    return row;
                }) };
        }
        internal bool Same(VenuePlan other)
        {
            return Version == other.Version && Catalog.Same(other.Catalog) && Json.Serialize(Public()) == Json.Serialize(other.Public());
        }
    }

    const string VenueEndpointsRoute = "/api/venue/connection-endpoints";

    static int RunVenue(Dictionary<string, string> options, ref bool outputValid)
    {
        outputValid = false;
        string diagnostics; var peerDiagnostics = options.TryGetValue("--peer-diagnostics", out diagnostics);
        Need(!peerDiagnostics || diagnostics == "on", "來源診斷只接受 on。");
        Need(options.Count == (peerDiagnostics ? 6 : 5) && options.ContainsKey("--work")
            && options.ContainsKey("--seconds") && options.ContainsKey("--ready-report"), "需要venue-run/work/seconds/ready-report/report五個參數。");
        int seconds; Need(Int32.TryParse(options["--seconds"], out seconds) && seconds >= 60 && seconds <= 86400, "執行期限須為60至86400秒。");
        var planPath = Full(options["--venue-run"]); var work = Full(options["--work"]);
        Need(!Inside(planPath, Root) && !Inside(planPath, work) && !Inside(work, Root) && !Inside(Root, work)
            && !Directory.Exists(work) && !File.Exists(work) && Directory.Exists(Path.GetDirectoryName(work)), "請使用包外的設定檔及全新工作目錄。");
        Plain(work);
        var plan = Read(planPath, 8192);
        var instancePath = VenueInstancePath(plan);
        var instanceDirectory = Path.GetDirectoryName(instancePath);
        Need(!Inside(work, instanceDirectory) && !Inside(instanceDirectory, work), "工作目錄必須與管理實例分開。");
        var report = options["--report"]; var ready = options["--ready-report"];
        Output(report, instanceDirectory); Output(ready, instanceDirectory);
        Output(report, work); Output(ready, work);
        Need(!String.Equals(Full(report), Full(ready), StringComparison.OrdinalIgnoreCase), "結果路徑不能重複。");
        outputValid = true;
        return ExecuteVenue(LoadVenuePlan(plan, instancePath), work, seconds, ready, report, peerDiagnostics, () => false);
    }

    static string VenueInstancePath(Dictionary<string, object> plan)
    {
        var instancePath = Text(plan, "controlInstance");
        Need(!String.IsNullOrWhiteSpace(instancePath) && Path.IsPathRooted(instancePath), "需要管理實例的完整路徑。");
        return Full(instancePath);
    }

    static VenuePlan ReadVenuePlan(string path, Action<string> checkInstance = null)
    {
        Need(!String.IsNullOrWhiteSpace(path) && Path.IsPathRooted(path), "需要場館計畫的完整路徑。");
        path = Full(path);
        Need(!Inside(path, Root), "場館計畫必須在程式包之外。");
        var plan = Read(path, 8192); var instance = VenueInstancePath(plan);
        if (checkInstance != null) checkInstance(Path.GetDirectoryName(instance));
        return LoadVenuePlan(plan, instance);
    }

    static VenuePlan LoadVenuePlan(Dictionary<string, object> plan, string instancePath)
    {
        var version = Num(plan, "version"); var topology = Text(plan, "topology"); object raw;
        Need((version == 1 || version == 2) && plan.Count == 6 && (topology == "Linked" || topology == "Independent")
            && plan.TryGetValue("servers", out raw) && raw is object[]
            && ((object[])raw).Length == (topology == "Linked" ? 1 : 5), "請提供完整的獨立或合併場館設定。");
        Verify();
        var catalog = Catalog.Load(instancePath);
        Need(Num(catalog.Target.Request(VenueEndpointsRoute, missing: true), "version") == 1,
            "管理服務尚未支援全館端點公告，請搭配 0.31.100 或以上版本。");
        var rooms = new HashSet<int>(); var ports = new HashSet<int>();
        var servers = new List<VenueServer>();
        foreach (var item in (object[])plan["servers"])
        {
            var row = Map(item);
            Need(row != null && row.Count == (version == 2 ? 5 : 3) && Num(row, "port") >= 1024 && Num(row, "port") <= 65535,
                "請提供有效場次、房號及 UDP 埠。");
            var choice = catalog.Choices.Find(candidate => candidate.Id == Text(row, "sessionId"));
            var assigned = Choice.ReadRooms(row, topology);
            Need(choice != null && choice.Mode == topology && String.Join(",", choice.Rooms) == String.Join(",", assigned),
                "原場次與房間不符或已無法啟動。");
            if (version == 2)
                CheckVenueRevision(choice, Num(row, "sessionSequence"), Choice.GuidValue(Text(row, "missionId")), assigned);
            Need(choice.CanStart, Choice.AlignmentPrompt(choice.MissingAlignmentRooms));
            foreach (var room in assigned) Need(rooms.Add(room), "場館房間重複。");
            var config = catalog.Target.ForSession(choice.Id, Text(plan, "address"), Text(plan, "listenAddress"), (int)Num(row, "port"));
            Need(ports.Add(config.Port), "獨立場次須使用不同的 UDP 埠。");
            servers.Add(new VenueServer { Choice = choice, Config = config });
        }
        servers.Sort((a, b) => a.Choice.Rooms[0].CompareTo(b.Choice.Rooms[0]));
        foreach (var server in servers)
            try { server.Config.CheckPort(); }
            catch (SocketException) { throw new InvalidDataException("無法使用房間 " + String.Join("、", server.Choice.Rooms) + " 的 UDP 埠 " + server.Config.Port + "。"); }
        return new VenuePlan { Version = version, Catalog = catalog, Topology = topology, Servers = servers };
    }

    static void CheckVenueRevision(Choice current, long sequence, string missionId, int[] rooms)
    {
        Need(sequence > 0 && current != null && current.Sequence == sequence && current.MissionId == missionId,
            "房間 " + String.Join("、", rooms) + " 的場次序號或任務版本已變更；請在主控台重新讀取並下載計畫。");
    }

    static int ExecuteVenue(VenuePlan plan, string work, int seconds, string ready, string report, bool peerDiagnostics, Func<bool> cancel)
    {
        Need(!cancel(), "已中止啟動；此輪未完成。");
        var servers = plan.Servers;
        foreach (var server in servers)
        {
            var name = plan.Topology == "Linked" ? "linked" : "room-" + server.Choice.Rooms[0].ToString("00", System.Globalization.CultureInfo.InvariantCulture);
            server.Run = new Run(server.Config, Path.Combine(work, name));
        }
        var staging = Path.Combine(Path.GetDirectoryName(work), ".vr-venue-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        try { Directory.Move(staging, work); }
        finally { if (Directory.Exists(staging)) Directory.Delete(staging); }

        var gate = new VenueGate();
        var workers = new List<Thread>();
        var published = false;
        var endpointPublication = "not-attempted";
        string publicationError = null;
        using (var reserved = new CountdownEvent(servers.Count))
        using (var launch = new ManualResetEventSlim())
        using (var started = new CountdownEvent(servers.Count))
        using (var proceed = new ManualResetEventSlim())
        {
            try
            {
                foreach (var entry in servers)
                {
                    var server = entry;
                    var worker = new Thread(delegate()
                    {
                        var reservedSlot = false;
                        try
                        {
                            try
                            {
                                server.Run.Start(() => gate.Abort || cancel(), peerDiagnostics, packageVerified: true, beforeNative: delegate
                                {
                                    reservedSlot = true;
                                    reserved.Signal();
                                    launch.Wait();
                                }, deferPublication: true);
                                server.Ready = true;
                            }
                            catch (Exception error) { server.Error = Safe(error); gate.Abort = true; }
                            finally { if (!reservedSlot) reserved.Signal(); started.Signal(); }
                            proceed.Wait();
                            if (!gate.Abort) server.Run.Wait(seconds, cancel);
                        }
                        catch (Exception error) { server.Error = Safe(error); }
                        finally { try { server.Run.Dispose(); } catch (Exception error) { server.Error = Safe(error); } }
                    });
                    worker.Start();
                    workers.Add(worker);
                }
                reserved.Wait();
                if (plan.Version == 2 && !gate.Abort && !cancel())
                {
                    var current = Catalog.Parse(plan.Catalog.Target.Sessions());
                    foreach (var server in servers)
                    {
                        var expected = server.Choice;
                        CheckVenueRevision(current.Find(choice => choice.Id == expected.Id), expected.Sequence, expected.MissionId, expected.Rooms);
                    }
                }
                launch.Set();
                started.Wait();
                if (!gate.Abort && !cancel() && servers.TrueForAll(server => server.Ready && !server.Run.Process.Exited))
                {
                    try
                    {
                        foreach (var server in servers)
                            Need(!server.Run.Process.Exited && UdpBinding.Find(server.Run.Process.Pid, server.Config.Bind, server.Config.Port) != null,
                                "房間 " + String.Join("、", server.Choice.Rooms) + " 的原遊戲程序或 UDP 綁定已失效。");
                        Need(!cancel(), "已中止啟動；此輪未完成。");
                        endpointPublication = "unconfirmed";
                        var receipt = plan.Catalog.Target.Request(VenueEndpointsRoute, new { version = 1, topology = plan.Topology,
                            servers = servers.ConvertAll(server => new { sessionId = server.Choice.Id, endpoint = server.Run.EndpointDraft() }) });
                        object raw;
                        Need(Num(receipt, "version") == 1 && Text(receipt, "topology") == plan.Topology
                            && receipt.TryGetValue("servers", out raw) && raw is object[] && ((object[])raw).Length == servers.Count, "全館公告回條不符。");
                        var endpoints = (object[])receipt["servers"];
                        for (var index = 0; index < servers.Count; index++) servers[index].Run.ConfirmEndpoint(Map(endpoints[index]));
                        endpointPublication = "confirmed";
                        Need(!cancel(), "已中止啟動；此輪未完成。");
                        Save(ready, new { schemaVersion = 1, status = "venue-ready", topology = plan.Topology, instanceId = plan.Catalog.InstanceId,
                            servers = servers.ConvertAll(server => new { roomIds = server.Choice.Rooms, ready = server.Run.Ready() }) });
                        published = true;
                    }
                    catch (Exception error) { publicationError = Safe(error); }
                }
            }
            finally
            {
                gate.Abort = !published;
                launch.Set();
                proceed.Set();
                foreach (var worker in workers) worker.Join();
            }
        }
        var complete = published && !cancel() && servers.TrueForAll(server => server.Error == null && server.Run.Complete && server.Run.Cleanup);
        Save(report, new { schemaVersion = 1, status = complete ? "venue-sealed-stopped" : "venue-incomplete",
            complete = complete, topology = plan.Topology, instanceId = plan.Catalog.InstanceId, readyPublished = published,
            endpointPublication = endpointPublication, publicationError = publicationError,
            servers = servers.ConvertAll(server => new { roomIds = server.Choice.Rooms,
                result = server.Run.Report(server.Run.Complete && server.Run.Cleanup ? "sealed-stopped" : "incomplete", server.Error) }) });
        return complete ? 0 : 1;
    }

    sealed class VenueWindow : Form
    {
        readonly TextBox path = new TextBox(), status = new TextBox { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical };
        readonly Button browse = new Button { Text = "選擇計畫" }, check = new Button { Text = "核對計畫" },
            start = new Button { Text = "啟動全館", Enabled = false }, abort = new Button { Text = "中止全館", Enabled = false };
        readonly CheckBox peers = new CheckBox { Text = "記錄本次玩家連線來源（場館驗收）", AutoSize = true };
        readonly Label summary = new Label { AutoEllipsis = true };
        readonly ListView rooms = new ListView { View = View.Details, FullRowSelect = true, ShowItemToolTips = true, AccessibleName = "五房計畫明細" };
        VenuePlan preview;
        bool busy, readyShown;
        volatile bool cancel;
        string readyPath;

        internal VenueWindow(string initialPath = "")
        {
            Text = "VR Command 五房批次啟動";
            ClientSize = new Size(1000, 494); Font = new Font("Microsoft JhengHei UI", 11);
            FormBorderStyle = FormBorderStyle.FixedDialog; MaximizeBox = false;
            Add(new Label { Text = "場館計畫 JSON 完整路徑", AutoSize = true }, 22, 20, 500, 26);
            Add(path, 22, 50, 680, 32); Add(browse, 715, 48, 118, 36); Add(check, 846, 48, 132, 36);
            Add(summary, 22, 92, 956, 30);
            rooms.Columns.Add("房間", 140); rooms.Columns.Add("任務", 225); rooms.Columns.Add("場次 ID", 340); rooms.Columns.Add("公告位址與 UDP", 230);
            Add(rooms, 22, 126, 956, 195);
            Add(peers, 22, 329, 600, 29); Add(start, 22, 368, 165, 36); Add(abort, 200, 368, 165, 36);
            Add(status, 22, 416, 956, 56);
            path.AccessibleName = "場館計畫 JSON 完整路徑";
            status.AccessibleName = "批次啟動狀態";
            path.TextChanged += delegate { ClearPreview(); };
            browse.Click += delegate
            {
                using (var dialog = new OpenFileDialog { Filter = "場館計畫 (*.json)|*.json", CheckFileExists = true })
                    if (dialog.ShowDialog(this) == DialogResult.OK) path.Text = dialog.FileName;
            };
            check.Click += delegate { CheckPlan(); };
            start.Click += delegate { StartVenue(); };
            abort.Click += delegate { cancel = true; abort.Enabled = false; status.Text = "中止中；此輪不算正常封存完成。"; };
            FormClosing += delegate(object sender, FormClosingEventArgs e)
            {
                if (!busy) return;
                e.Cancel = true;
                status.Text = readyPath == null ? "請等候計畫核對完成。" : "全館仍在執行；請由控制台結束任務，或按中止全館。";
            };
            var timer = new System.Windows.Forms.Timer { Interval = 400 };
            timer.Tick += delegate
            {
                if (readyPath == null || readyShown || cancel || !File.Exists(readyPath)) return;
                readyShown = true;
                status.Text = "全館就緒。請由控制台配票、開始及結束任務。\r\n就緒紀錄：" + readyPath;
            };
            FormClosed += delegate { timer.Dispose(); };
            timer.Start();
            ClearPreview();
            path.Text = initialPath;
        }

        void Add(Control control, int x, int y, int width, int height)
        {
            control.SetBounds(x, y, width, height);
            Controls.Add(control);
        }

        void ClearPreview()
        {
            preview = null; rooms.Items.Clear(); start.Enabled = false;
            summary.Text = "請載入並核對控制台下載的五房場館計畫。";
            status.Text = "核對計畫後會列出房間、任務及連線端點。";
        }

        void Background(Action work, Action<Exception> complete)
        {
            busy = true; path.Enabled = browse.Enabled = check.Enabled = start.Enabled = peers.Enabled = false;
            new Thread(delegate()
            {
                Exception failure = null;
                try { work(); } catch (Exception error) { failure = error; }
                BeginInvoke((Action)delegate
                {
                    busy = false; path.Enabled = browse.Enabled = check.Enabled = peers.Enabled = true;
                    abort.Enabled = false; readyPath = null;
                    complete(failure);
                    start.Enabled = preview != null;
                });
            }).Start();
        }

        void CheckPlan()
        {
            var selectedPath = path.Text.Trim();
            ClearPreview();
            status.Text = "正在核對場次、校正鎖定與 UDP 埠。";
            VenuePlan result = null;
            Background(() => result = ReadVenuePlan(selectedPath), failure =>
            {
                if (failure != null) { status.Text = "核對未完成：" + Safe(failure); return; }
                preview = result;
                foreach (var server in result.Servers)
                {
                    var room = String.Join("、", server.Choice.Rooms);
                    var endpoint = server.Config.Address + ":" + server.Config.Port;
                    var item = new ListViewItem(new[] { room, Choice.Label(server.Choice.MissionName) + " · " + server.Choice.Experience,
                        server.Choice.Id, endpoint });
                    item.ToolTipText = server.Choice.Detail() + "\r\n本機綁定：" + server.Config.Bind + ":" + server.Config.Port;
                    if (result.Version == 2) item.ToolTipText += "\r\n場次序號：" + server.Choice.Sequence;
                    rooms.Items.Add(item);
                }
                summary.Text = (result.Topology == "Linked" ? "五房合併" : "五房獨立") + " · " + result.Servers.Count + " 個遊戲伺服器";
                status.Text = "計畫已核對。確認房間與端點後按啟動全館。";
            });
        }

        void StartVenue()
        {
            var reviewed = preview;
            if (reviewed == null || busy) return;
            var selectedPath = path.Text.Trim();
            var capturePeers = peers.Checked;
            cancel = false; readyShown = false; abort.Enabled = true;
            status.Text = "正在重新核對計畫，然後啟動全館。";
            var local = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VrCommand");
            var runs = Path.Combine(local, "GameServers");
            var reports = Path.Combine(local, "GameServerReports");
            var id = "venue-" + Guid.NewGuid().ToString("N");
            var work = Path.Combine(runs, id);
            var ready = Path.Combine(reports, id + "-ready.json");
            var report = Path.Combine(reports, id + "-final.json");
            readyPath = ready;
            var result = 1;
            Background(delegate
            {
                var current = ReadVenuePlan(selectedPath);
                Need(reviewed.Same(current), "計畫或管理實例已變更；請重新核對。");
                var instance = Path.GetDirectoryName(current.Catalog.PathName);
                Need(!Inside(work, instance) && !Inside(instance, work) && !Inside(reports, instance), "工作及結果目錄必須與管理實例分開。");
                Need(!cancel, "已中止啟動；此輪未完成。");
                Plain(runs); Plain(reports);
                Directory.CreateDirectory(runs); Directory.CreateDirectory(reports);
                Output(ready, work); Output(report, work);
                result = ExecuteVenue(current, work, 86400, ready, report, capturePeers, () => cancel);
            }, failure =>
            {
                preview = null; peers.Checked = false;
                status.Text = result == 0 ? "全館任務已封存並停止。"
                    : "未完成：" + (failure != null ? Safe(failure) : "請核對各房結果。");
                if (File.Exists(report)) status.AppendText("\r\n結果：" + report);
                summary.Text = "再次啟動前請重新核對場館計畫。";
            });
        }
    }

    internal sealed class Window : Form
    {
        readonly TextBox selected = new TextBox(), address = new TextBox { Text = "127.0.0.1" }, bind = new TextBox { Text = "127.0.0.1" };
        readonly NumericUpDown port = new NumericUpDown { Minimum = 1024, Maximum = 65535, Value = 7777 }; readonly ComboBox session = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Enabled = false };
        readonly Button open = new Button { Text = "選擇檔案" }, refresh = new Button { Text = "載入／更新" }, start = new Button { Text = "啟動伺服器", Enabled = false }, abort = new Button { Text = "中止伺服器", Enabled = false },
            venue = new Button { Text = "五房批次啟動" };
        readonly CheckBox peerDiagnostics = new CheckBox { Text = "記錄本次玩家連線來源（場館驗收）" };
        readonly Label state = new Label { Text = "先啟動管理服務，再載入其管理實例。", AutoSize = false }, detail = new Label { Text = "請先載入，再明確選擇要啟動的房間與任務。", AutoEllipsis = true };
        readonly CatalogState catalog = new CatalogState(); Run active; volatile bool cancel; Thread worker;
        internal Window()
        {
            Text = "VR Command 遊戲伺服器"; ClientSize = new Size(920, 580); Font = new Font("Microsoft JhengHei UI", 11); FormBorderStyle = FormBorderStyle.FixedDialog; MaximizeBox = false;
            Add(new Label { Text = "每個獨立房間一個伺服器；五房合併場次只需一個。", AutoSize = true }, 24, 24, 860, 30);
            Add(new Label { Text = "管理實例檔案完整路徑", AutoSize = true }, 24, 56, 600, 28); Add(selected, 24, 86, 594, 32); Add(open, 630, 84, 120, 36); Add(refresh, 766, 84, 124, 36);
            Add(new Label { Text = "可選檔，也可直接貼上control-instance.json路徑，再按載入／更新。", AutoSize = true }, 24, 127, 866, 30);
            Add(new Label { Text = "尚未綁定來源的 VR 或 MR 場次", AutoSize = true }, 24, 164, 400, 28); Add(session, 24, 194, 866, 34); Add(detail, 24, 240, 866, 76);
            Add(new Label { Text = "公告IPv4", AutoSize = true }, 24, 327, 210, 28); Add(address, 24, 358, 230, 32); Add(new Label { Text = "本機綁定IPv4", AutoSize = true }, 284, 327, 230, 28); Add(bind, 284, 358, 230, 32); Add(new Label { Text = "UDP埠", AutoSize = true }, 544, 327, 130, 28); Add(port, 544, 358, 130, 32);
            Add(peerDiagnostics, 24, 400, 430, 30);
            Add(new Label { Text = "開啟後，來源 IP 與埠會寫入本機私有 server.log。", AutoSize = true }, 463, 404, 427, 28);
            Add(start, 24, 452, 260, 40); Add(abort, 310, 452, 260, 40); Add(venue, 630, 452, 260, 40); Add(state, 24, 510, 866, 64);
            selected.TextChanged += delegate { catalog.Edit(selected.Text); start.Enabled = session.Enabled = false; detail.Text = "路徑已變更，請重新載入；未沿用舊場次。"; };
            open.Click += delegate { using (var dialog = new OpenFileDialog { Filter = "管理實例|control-instance.json", CheckFileExists = true }) if (dialog.ShowDialog(this) == DialogResult.OK) { selected.Text = dialog.FileName; Guard(LoadInstance); } };
            refresh.Click += delegate { Guard(LoadInstance); };
            venue.Click += delegate { using (var window = new VenueWindow()) window.ShowDialog(this); };
            session.SelectedIndexChanged += delegate { if (catalog.Loaded) { var choice = session.SelectedItem as Choice; catalog.Select(choice == null ? null : choice.Id); ShowSelection(); } };
            start.Click += delegate { Guard(Begin); }; abort.Click += delegate { cancel = true; abort.Enabled = false; state.Text = "中止中；此輪不算正常封存完成。"; };
            FormClosing += delegate(object sender, FormClosingEventArgs e) { if (worker != null && worker.IsAlive) { e.Cancel = true; state.Text = "伺服器仍在執行；請由控制台結束任務，或按中止。"; } };
            var timer = new System.Windows.Forms.Timer { Interval = 500 }; timer.Tick += delegate { if (active != null && !cancel) state.Text = active.Status; }; timer.Start();
        }
        void Add(Control control, int x, int y, int w, int h) { control.SetBounds(x, y, w, h); Controls.Add(control); }
        void Guard(Action action) { try { action(); } catch (Exception e) { state.Text = "未完成：" + Safe(e); } }
        void ShowSelection() { start.Enabled = catalog.CanStart; detail.Text = catalog.Selected == null ? "請明確選擇要啟動的房間與任務。" : catalog.Selected.Detail(); }
        void LoadInstance()
        {
            start.Enabled = session.Enabled = false; detail.Text = "正在重新讀取管理服務；不保留未確認的啟動選取。";
            try { catalog.Load(); }
            catch { session.Items.Clear(); detail.Text = "載入未完成，已清除舊場次。請確認管理服務與路徑後重新載入。"; throw; }
            var retained = catalog.Selected; session.Items.Clear(); foreach (var choice in catalog.Current.Choices) session.Items.Add(choice);
            session.Enabled = true; if (retained != null) session.SelectedItem = retained;
            ShowSelection();
            state.Text = session.Items.Count > 0 ? "清單已更新；只保留同一管理實例中仍在清單內的原選取。" : "沒有待開的 VR 或 MR 場次，請先在控制台建立。";
        }
        void Begin()
        {
            Settings config;
            try { config = catalog.StartSettings(address.Text, bind.Text, (int)port.Value); }
            finally { if (!catalog.Loaded) { session.Items.Clear(); session.Enabled = false; ShowSelection(); } }
            var work = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VrCommand", "GameServers", DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N"));
            var reports = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VrCommand", "GameServerReports"); Directory.CreateDirectory(reports); var report = Path.Combine(reports, Guid.NewGuid().ToString("N") + ".json");
            var capturePeers = peerDiagnostics.Checked;
            active = new Run(config, work); cancel = false; open.Enabled = refresh.Enabled = start.Enabled = selected.Enabled = address.Enabled = bind.Enabled = port.Enabled = session.Enabled = peerDiagnostics.Enabled = venue.Enabled = false; abort.Enabled = true;
            worker = new Thread(delegate() { string error = null; try { active.Start(() => cancel, capturePeers); active.Wait(86400, () => cancel); } catch (Exception e) { error = Safe(e); } finally { try { active.Dispose(); } catch (Exception e) { error = Safe(e); } }
                try { Save(report, active.Report(active.Complete && active.Cleanup ? "sealed-stopped" : "incomplete", error)); } catch (Exception e) { error = Safe(e); }
                var final = error == null && active.Complete && active.Cleanup ? "任務已封存並停止。" : "未完成：" + (error ?? "封存未確認。"); BeginInvoke((Action)delegate { active = null; catalog.Edit(selected.Text); session.Enabled = false; detail.Text = "此輪已收尾；再次啟動前請重新載入場次。"; state.Text = final + " 結果：" + report; peerDiagnostics.Checked = false; open.Enabled = refresh.Enabled = selected.Enabled = address.Enabled = bind.Enabled = port.Enabled = peerDiagnostics.Enabled = venue.Enabled = true; abort.Enabled = false; }); }); worker.IsBackground = false; worker.Start();
        }
    }
    [STAThread] static int Main(string[] args)
    {
        if (args.Length == 0 || args.Length == 2 && args[0] == "--venue-window")
        {
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            using (Form window = args.Length == 0 ? (Form)new Window() : new VenueWindow(args[1])) Application.Run(window);
            return 0;
        }
        string report = null; Run run = null; bool outputValid = false; string error = null;
        try
        {
            var options = new Dictionary<string, string>(); for (var i = 0; i < args.Length; i += 2) { Need(i + 1 < args.Length && !options.ContainsKey(args[i]), "參數格式錯誤。"); options.Add(args[i], args[i + 1]); }
            Need(options.ContainsKey("--report"), "需要結果路徑。"); report = options["--report"]; Output(report, options.ContainsKey("--catalog") ? Path.GetDirectoryName(Full(options["--catalog"])) : options.ContainsKey("--work") ? options["--work"] : null); outputValid = true;
            if (options.Count == 2 && options.ContainsKey("--verify")) { Need(options["--verify"] == "package", "驗證參數錯誤。"); Verify(); Save(report, new { schemaVersion = 1, complete = true, status = "verified" }); return 0; }
            if (options.Count == 2 && options.ContainsKey("--catalog")) { Verify(); Save(report, Catalog.Load(options["--catalog"]).Public()); return 0; }
            if (options.Count == 2 && options.ContainsKey("--venue-check"))
            {
                outputValid = false;
                var preview = ReadVenuePlan(options["--venue-check"], instance => { Output(report, instance); outputValid = true; });
                Save(report, preview.Public()); return 0;
            }
            if (options.ContainsKey("--venue-run")) return RunVenue(options, ref outputValid);
            string diagnostics;
            var peerDiagnostics = options.TryGetValue("--peer-diagnostics", out diagnostics);
            Need(!peerDiagnostics || diagnostics == "on", "來源診斷只接受 on。");
            Need(options.Count == (peerDiagnostics ? 6 : 5) && options.ContainsKey("--run") && options.ContainsKey("--work") && options.ContainsKey("--seconds") && options.ContainsKey("--ready-report"), "需要run/work/seconds/ready-report/report五個參數。");
            int seconds; Need(Int32.TryParse(options["--seconds"], out seconds) && seconds >= 60 && seconds <= 86400, "執行期限須為60至86400秒。");
            var configPath = Full(options["--run"]); var work = Full(options["--work"]); Need(!Inside(configPath, Root) && !Inside(configPath, work) && !Inside(work, configPath), "設定必須在程式包與新資料夾之外。");
            Output(report, work); Output(options["--ready-report"], work); Need(!String.Equals(Full(report), Full(options["--ready-report"]), StringComparison.OrdinalIgnoreCase), "結果路徑不能重複。");
            run = new Run(Settings.From(Read(configPath, 8192)), work); run.Start(peerDiagnostics: peerDiagnostics); Save(options["--ready-report"], run.Ready()); run.Wait(seconds, () => false);
        }
        catch (Exception e) { error = Safe(e); }
        finally { if (run != null) try { run.Dispose(); } catch (Exception e) { error = Safe(e); } }
        try { if (outputValid) Save(report, run == null ? (object)new { schemaVersion = 1, complete = false, status = "rejected", error = error } : run.Report(run.Complete && run.Cleanup ? "sealed-stopped" : "incomplete", error)); } catch { return 1; }
        return error == null && run != null && run.Complete && run.Cleanup ? 0 : 1;
    }
}
