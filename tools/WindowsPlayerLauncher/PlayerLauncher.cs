// Standalone Windows Forms entry point; no Unity, editor or management credentials.
// Built with the installed .NET Framework compiler by package-windows-player.py.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

internal static class PlayerLauncher
{
    private static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 4 * 1024 * 1024 };
    private static readonly string Root = AppDomain.CurrentDomain.BaseDirectory;
    private static string statusReport;
    private static string lastStatusReport;
    private static bool SamePath(string a, string b) { return a != null && b != null && String.Equals(a, b, StringComparison.OrdinalIgnoreCase); }
    private static Dictionary<string, object> Map(object value) { return value as Dictionary<string, object>; }
    private static string Text(Dictionary<string, object> value, string key)
    { object result; return value.TryGetValue(key, out result) ? result as string : null; }
    private static int Number(Dictionary<string, object> value, string key)
    { object result; return value.TryGetValue(key, out result) && result is int ? (int)result : -1; }
    private static long DebriefCounter(Dictionary<string, object> value, string key)
    {
        object result;
        if (!value.TryGetValue(key, out result)) return -1;
        if (result is int) return (int)result;
        return result is long ? (long)result : -1;
    }
    private static bool DebriefId(Dictionary<string, object> value, string key, out Guid id)
    { return Guid.TryParseExact(Text(value, key), "D", out id) && id != Guid.Empty; }
    internal static bool TryReadFinalDebrief(string body, out Guid session)
    {
        session = Guid.Empty;
        // The current final record is a flat object with 17 fields. None of its values contain a colon.
        // Count the original separators too, since the Framework JSON reader collapses repeated keys.
        if (body.Length > 4096 || !body.StartsWith("{", StringComparison.Ordinal)
            || !body.EndsWith("}", StringComparison.Ordinal) || body.Split(':').Length != 18) return false;
        Dictionary<string, object> value;
        try { value = Map(Json.DeserializeObject(body)); }
        catch (ArgumentException) { return false; }
        catch (InvalidOperationException) { return false; }
        if (value == null || value.Count != 17 || Number(value, "version") != 1) return false;
        var room = Number(value, "roomId"); var health = Number(value, "health");
        var origin = Text(value, "origin");
        Guid id;
        if (room < 1 || room > 5 || health < 0 || health > 100 || (origin != "Simulation" && origin != "GameServer")
            || !DebriefId(value, "sessionId", out session) || !DebriefId(value, "playerId", out id)
            || !DebriefId(value, "admissionId", out id) || !DebriefId(value, "streamId", out id)
            || DebriefCounter(value, "throughSequence") <= 0 || DebriefCounter(value, "worldSequence") <= 0
            || DebriefCounter(value, "finalStreamSequence") < 0 || DebriefCounter(value, "hitsReceived") < 0
            || DebriefCounter(value, "damageTaken") < 0) return false;
        var ammo = DebriefCounter(value, "ammoUsed"); var hits = DebriefCounter(value, "shotsHit"); var kills = DebriefCounter(value, "kills");
        object accuracy;
        if (kills < 0 || kills > hits || hits > ammo || !value.TryGetValue("accuracyPercent", out accuracy)
            || !(accuracy is int || accuracy is long || accuracy is decimal || accuracy is double)) return false;
        var percent = Convert.ToDouble(accuracy);
        return percent >= 0 && percent <= 100;
    }
    private static void Require(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }
    private static Dictionary<string, object> Read(string path, long max, string expectedHash = null, Action<string> recordHash = null)
    {
        using (var file = File.OpenRead(path))
            return Read(file, max, expectedHash, recordHash);
    }
    private static Dictionary<string, object> Read(Stream file, long max, string expectedHash = null, Action<string> recordHash = null)
    {
        Require(file.Length <= max, "檔案過大，請重新取得正確檔案。");
        if (expectedHash != null || recordHash != null)
        {
            var actualHash = Hash(file);
            Require(expectedHash == null || actualHash == expectedHash, "本機玩家包清單與場館發行報告不同。");
            if (recordHash != null) recordHash(actualHash);
            file.Position = 0;
        }
        using (var reader = new StreamReader(file, Encoding.UTF8, true, 1024, leaveOpen: true))
        {
            var value = Map(Json.DeserializeObject(reader.ReadToEnd()));
            Require(value != null, "檔案格式不正確。"); return value;
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
    internal sealed class ReleaseProof
    {
        internal readonly string ManifestHash, ReportHash;
        internal ReleaseProof(string manifestHash, string reportHash)
        {
            ManifestHash = manifestHash;
            ReportHash = reportHash;
        }
    }
    private static ReleaseProof ReadRelease(string path)
    {
        PlainPath(path);
        string reportHash = null;
        var release = Read(path, 8192, recordHash: digest => reportHash = digest);
        object verified, windows;
        Require(release.TryGetValue("verified", out verified) && verified is bool && (bool)verified
            && Text(release, "scope") == "offline-package-consistency", "請使用已核對的場館發行報告。");
        Require(release.TryGetValue("windows", out windows) && Map(windows) != null, "發行報告缺少 Windows 玩家套件資訊。");
        var hash = Text(Map(windows), "playerManifestSha256");
        Require(hash != null && Regex.IsMatch(hash, @"\A[a-f0-9]{64}\z"), "發行報告缺少有效的 Windows 玩家套件清單雜湊。");
        return new ReleaseProof(hash, reportHash);
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
        PlainPath(path);
        return Config(Read(path, 32768));
    }
    private static Dictionary<string, object> Config(Dictionary<string, object> value)
    {
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
    private static void Report(string path, object value, bool replaceExisting = true)
    {
        if (path == null) return;
        var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            File.WriteAllText(temporary, Json.Serialize(value), new UTF8Encoding(false));
            if (replaceExisting && File.Exists(path)) File.Replace(temporary, path, null);
            else File.Move(temporary, path);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }
    private static bool LocalFullPath(string path)
    {
        return path != null && Regex.IsMatch(path, @"\A[A-Za-z]:[\\/][^:\x00-\x1f]*\z");
    }
    private static string ConfigEndpoint(Dictionary<string, object> value)
    { return Text(value, "address") + ":" + Number(value, "port"); }

    private sealed class TicketRenewal
    {
        internal readonly string Status, FileHash;
        internal readonly TicketPreview Ticket;
        internal TicketRenewal(string status, string fileHash, TicketPreview ticket)
        { Status = status; FileHash = fileHash; Ticket = ticket; }
    }

    private static TicketRenewal RefreshTicket(string current, string renewal, TicketPreview activeSeat = null, string activeEndpoint = null)
    {
        Require(LocalFullPath(current) && LocalFullPath(renewal) && !SamePath(current, renewal)
            && !current.StartsWith(Root, StringComparison.OrdinalIgnoreCase), "Use separate local connection files outside the player package.");
        PlainPath(current); PlainPath(renewal);
        // Serialize concurrent refreshes of the same connection file. Unity can still read it.
        using (var guard = new FileStream(current + ".refresh.lock", FileMode.CreateNew, FileAccess.Write, FileShare.None, 1, FileOptions.DeleteOnClose))
        using (var original = new FileStream(current, FileMode.Open, FileAccess.Read, FileShare.Read | FileShare.Delete))
        using (var replacement = File.OpenRead(renewal))
        {
            string originalHash = null, replacementHash = null;
            var a = Config(Read(original, 32768, recordHash: hash => originalHash = hash));
            var b = Config(Read(replacement, 32768, recordHash: hash => replacementHash = hash));
            var oldTicket = Text(a, "joinTicket"); var newTicket = Text(b, "joinTicket");
            var oldSeat = TicketPreview.Read(oldTicket); var newSeat = TicketPreview.Read(newTicket);
            var endpoint = ConfigEndpoint(a);
            Require(oldSeat != null && oldSeat.SameAdmission(newSeat) && endpoint == ConfigEndpoint(b)
                && (activeSeat == null || activeSeat.SameAdmission(oldSeat) && activeEndpoint == endpoint),
                "The connection files must use the original admission, seat and endpoint.");
            Require(newSeat.ExpiresAtUtc > DateTimeOffset.UtcNow && newSeat.ExpiresAtUtc >= oldSeat.ExpiresAtUtc
                && (activeSeat == null || newSeat.ExpiresAtUtc >= activeSeat.ExpiresAtUtc),
                "The replacement ticket is expired or older than the current ticket.");
            if (oldTicket == newTicket)
            {
                Require(Hash(current) == originalHash, "The original file changed during renewal.");
                return new TicketRenewal("ticket-file-current", originalHash, oldSeat);
            }
            var temporary = current + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                replacement.Position = 0;
                using (var staged = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    replacement.CopyTo(staged);
                    staged.Flush(true);
                }
                Require(Hash(temporary) == replacementHash && Hash(current) == originalHash, "The connection file changed during renewal.");
                File.Replace(temporary, current, null);
                Require(Hash(current) == replacementHash, "The updated file could not be confirmed.");
                return new TicketRenewal("ticket-file-refreshed", replacementHash, newSeat);
            }
            finally { if (File.Exists(temporary)) File.Delete(temporary); }
        }
    }
    private static int RefreshTicketCommand(string[] args)
    {
        string report = null;
        try
        {
            Require(args.Length == 5 && args[3] == "--report" && LocalFullPath(args[1])
                && LocalFullPath(args[2]) && LocalFullPath(args[4]), "Use three absolute local paths.");
            var current = Path.GetFullPath(args[1]); var renewal = Path.GetFullPath(args[2]); var output = Path.GetFullPath(args[4]);
            Require(!SamePath(current, renewal) && !SamePath(current, output) && !SamePath(renewal, output)
                && !current.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !output.StartsWith(Root, StringComparison.OrdinalIgnoreCase)
                && !File.Exists(output) && !Directory.Exists(output), "Use separate files and a new report outside the player package.");
            PlainPath(Path.GetDirectoryName(output));
            report = output;
            var status = RefreshTicket(current, renewal).Status;
            Report(report, new { status, complete = true }, replaceExisting: false);
            return 0;
        }
        catch (Exception)
        {
            // Neither the connection files nor exceptions are safe to copy to diagnostics.
            if (report != null)
                try { Report(report, new { status = "ticket-refresh-unconfirmed", complete = false }, replaceExisting: false); } catch { }
            Console.Error.WriteLine("Ticket refresh not confirmed. Check the original seat, endpoint and file paths, then retry.");
            return 1;
        }
    }
    private static bool IsX64Dll(string path)
    {
        using (var reader = new BinaryReader(File.OpenRead(path)))
        {
            var file = reader.BaseStream;
            if (file.Length < 64 || reader.ReadUInt16() != 0x5A4D) return false;
            file.Position = 60;
            var header = reader.ReadInt32();
            if (header < 64 || header > file.Length - 26) return false;
            file.Position = header;
            if (reader.ReadUInt32() != 0x4550 || reader.ReadUInt16() != 0x8664) return false;
            file.Position = header + 20L;
            var optionalSize = reader.ReadUInt16();
            var flags = reader.ReadUInt16();
            return (flags & 0x2000) != 0 && optionalSize >= 112 && header + 24L + optionalSize <= file.Length
                && reader.ReadUInt16() == 0x20B;
        }
    }
    private static string InspectOpenXrRuntime(out string source)
    {
        object configured = Environment.GetEnvironmentVariable("XR_RUNTIME_JSON");
        source = "environment";
        if (String.IsNullOrEmpty(configured as string))
        {
            source = "registry64";
            try
            {
                using (var hive = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64))
                using (var key = hive.OpenSubKey(@"SOFTWARE\Khronos\OpenXR\1"))
                    configured = key == null ? null : key.GetValue("ActiveRuntime", null, RegistryValueOptions.DoNotExpandEnvironmentNames);
            }
            catch (System.Security.SecurityException) { return "registry-unreadable"; }
            catch (UnauthorizedAccessException) { return "registry-unreadable"; }
            catch (IOException) { return "registry-unreadable"; }
            if (configured == null || Object.Equals(configured, "")) return "runtime-not-configured";
        }
        var manifest = configured as string;
        if (!LocalFullPath(manifest)) return "manifest-path-invalid";
        Dictionary<string, object> doc;
        try
        {
            using (var reader = new BinaryReader(File.OpenRead(manifest)))
            {
                var size = reader.BaseStream.Length;
                if (size < 1 || size > 65536) return "manifest-invalid";
                var bytes = reader.ReadBytes((int)size);
                if (bytes.Length != size || reader.BaseStream.ReadByte() != -1) return "manifest-invalid";
                var json = new UTF8Encoding(false, true).GetString(bytes).TrimStart('\uFEFF');
                doc = Map(new JavaScriptSerializer { MaxJsonLength = 65536 }.DeserializeObject(json));
            }
        }
        catch (FileNotFoundException) { return "manifest-missing"; }
        catch (DirectoryNotFoundException) { return "manifest-missing"; }
        catch (IOException) { return "manifest-invalid"; }
        catch (UnauthorizedAccessException) { return "manifest-invalid"; }
        catch (ArgumentException) { return "manifest-invalid"; }
        catch (InvalidOperationException) { return "manifest-invalid"; }
        catch (NotSupportedException) { return "manifest-invalid"; }
        object runtime;
        if (doc == null || Text(doc, "file_format_version") != "1.0.0" || !doc.TryGetValue("runtime", out runtime)
            || Map(runtime) == null) return "manifest-invalid";
        var library = Text(Map(runtime), "library_path");
        if (library == null || !library.EndsWith(".dll", StringComparison.OrdinalIgnoreCase)) return "manifest-invalid";
        if (library.IndexOfAny(new[] { '\\', '/' }) < 0) return "library-search-required";
        try
        {
            if (!Path.IsPathRooted(library)) library = Path.Combine(Path.GetDirectoryName(manifest), library);
            if (!LocalFullPath(library)) return "library-path-invalid";
            return IsX64Dll(library) ? "x64-runtime-files-found" : "library-not-x64-dll";
        }
        catch (FileNotFoundException) { return "library-missing"; }
        catch (DirectoryNotFoundException) { return "library-missing"; }
        catch (ArgumentException) { return "library-path-invalid"; }
        catch (NotSupportedException) { return "library-path-invalid"; }
        catch (IOException) { return "library-unreadable"; }
        catch (UnauthorizedAccessException) { return "library-unreadable"; }
    }
    private static int CheckOpenXrCommand(string[] args)
    {
        if (args.Length != 3 || args[0] != "--check-openxr" || args[1] != "--report" || args[2].StartsWith("--", StringComparison.Ordinal))
            return 2;
        try
        {
            var report = Path.GetFullPath(args[2]);
            Require(LocalFullPath(report) && String.Equals(Path.GetExtension(report), ".json", StringComparison.OrdinalIgnoreCase)
                && !report.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !File.Exists(report) && !Directory.Exists(report),
                "請在玩家包外指定新的 JSON 報告路徑。");
            PlainPath(Path.GetDirectoryName(report));
            string source;
            var status = InspectOpenXrRuntime(out source);
            var complete = status == "x64-runtime-files-found";
            Report(report, new { version = 1, scope = "windows-openxr-runtime-files", complete, source, status }, replaceExisting: false);
            return complete ? 0 : 1;
        }
        catch (Exception) { return 2; }
    }
    private static void ProcessReport(string path, string status, ReleaseProof release, Process child = null,
        bool exited = false, string linkMetrics = null, string log = null, bool deferSharing = false)
    {
        if (path == null) return;
        var value = new Dictionary<string, object> { { "status", status } };
        if (child != null) value.Add("processId", child.Id);
        if (exited) value.Add("exitCode", child.ExitCode);
        if (exited && log != null && (linkMetrics != null || release != null))
        {
            var logHash = EvidenceHash(log, 16 * 1024 * 1024, deferSharing);
            if (release != null) value.Add("playerLogSha256", logHash);
            if (linkMetrics != null)
            {
                var metricsHash = EvidenceHash(linkMetrics, 64 * 1024, deferSharing);
                value.Add("linkMetrics", metricsHash != null && logHash != null
                    ? new { metricsSha256 = metricsHash, logSha256 = logHash } : null);
            }
        }
        if (release != null)
        {
            value.Add("playerManifestSha256", release.ManifestHash);
            value.Add("venueReleaseReportSha256", release.ReportHash);
        }
        Report(path, value);
    }
    private static bool WriteEvidenceZip(string path, string logPath, string reportPath, ReleaseProof release, int processId,
        string linkMetricsPath = null)
    {
        PlainPath(Path.GetDirectoryName(path)); PlainPath(logPath); PlainPath(reportPath);
        if (linkMetricsPath != null) PlainPath(linkMetricsPath);
        var temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            using (var log = File.OpenRead(logPath))
            using (var report = File.OpenRead(reportPath))
            using (var metrics = linkMetricsPath == null ? null : File.OpenRead(linkMetricsPath))
            {
                var result = Read(reportPath, 4096);
                Require(Text(result, "status") == "exited" && Number(result, "exitCode") == 0 && Number(result, "processId") == processId
                    && Text(result, "playerManifestSha256") == release.ManifestHash
                    && Text(result, "venueReleaseReportSha256") == release.ReportHash && log.Length <= 16 * 1024 * 1024,
                    "本次日誌與退出報告不符。");
                var terminal = new PlayerConnectionMonitor(logPath, verifyEvidence: true);
                using (var reader = new StreamReader(log, Encoding.UTF8, true, 4096, true))
                {
                    var buffer = new char[4096];
                    int count;
                    while ((count = reader.Read(buffer, 0, buffer.Length)) != 0)
                        terminal.Feed(new string(buffer, 0, count));
                }
                if (!terminal.CanArchiveEvidence) return false;
                log.Position = 0;
                var logHash = Hash(log);
                Require(Text(result, "playerLogSha256") == logHash, "本次日誌與退出報告不符。");
                log.Position = 0;
                if (metrics != null)
                {
                    object value;
                    var proof = result.TryGetValue("linkMetrics", out value) ? Map(value) : null;
                    Require(metrics.Length > 0 && metrics.Length <= 64 * 1024 && proof != null
                        && Text(proof, "logSha256") == logHash && Text(proof, "metricsSha256") == Hash(metrics),
                        "本次連線量測與退出報告不符。");
                    metrics.Position = 0;
                }
                using (var file = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                using (var zip = new ZipArchive(file, ZipArchiveMode.Create))
                {
                    using (var entry = zip.CreateEntry("player.log", CompressionLevel.Fastest).Open()) log.CopyTo(entry);
                    using (var entry = zip.CreateEntry("launch-report.json", CompressionLevel.Fastest).Open()) report.CopyTo(entry);
                    if (metrics != null)
                        using (var entry = zip.CreateEntry("link-metrics.json", CompressionLevel.Fastest).Open()) metrics.CopyTo(entry);
                }
            }
            File.Move(temporary, path);
            return true;
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
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
    private static bool IsSharingViolation(IOException error)
    {
        return error.HResult == unchecked((int)0x80070020) || error.HResult == unchecked((int)0x80070021);
    }
    private static string EvidenceHash(string path, long limit, bool deferSharing = false)
    {
        try
        {
            if (!File.Exists(path)) return null;
            PlainPath(path);
            using (var file = File.OpenRead(path))
                return file.Length > 0 && file.Length <= limit ? Hash(file) : null;
        }
        catch (IOException error) { if (deferSharing && IsSharingViolation(error)) throw; }
        catch (UnauthorizedAccessException) { }
        catch (InvalidDataException) { }
        return null;
    }
    private static Process Launch(string config, bool headless, string log, string reviewedHash = null, bool openXR = false,
        string linkMetrics = null, ReleaseProof release = null, string reportPath = null)
    {
        Verify(release == null ? null : release.ManifestHash); Config(config);
        Require(reviewedHash == null || Hash(config) == reviewedHash, "連線檔已變更，請重新載入後核對。");
        var args = "--vr-config " + Quote(config) + " -job-worker-count 2";
        if (headless) args += " -batchmode -nographics";
        if (openXR) args += " -force-d3d11 --vr-openxr";
        if (log != null) args += " -logFile " + Quote(log);
        if (linkMetrics != null) args += " --vr-link-metrics " + Quote(linkMetrics);
        var image = Path.Combine(Root, "VrCommand.exe");
        WindowsFirewallPreflight.Require(image);
        var child = Process.Start(new ProcessStartInfo(image, args)
        { UseShellExecute = false, WorkingDirectory = Root, CreateNoWindow = headless });
        Require(child != null, "無法啟動玩家程式。");
        try { ProcessReport(reportPath, "started", release, child); return child; }
        catch { if (!child.HasExited) { child.Kill(); child.WaitForExit(); } child.Dispose(); throw; }
    }
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length > 0 && args[0] == "--refresh-player-ticket") return RefreshTicketCommand(args);
        if (Array.IndexOf(args, "--check-openxr") >= 0) return CheckOpenXrCommand(args);
        string config = null, log = null, linkMetrics = null, releasePath = null, report = null, evidenceZip = null;
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
                else if (args[i] == "--link-metrics" || args[i] == "--release-report" || args[i] == "--evidence-zip")
                {
                    var option = args[i];
                    if (i + 1 == args.Length || args[i + 1].StartsWith("--", StringComparison.Ordinal)) invalidEvidenceOption = true;
                    else
                    {
                        var path = Path.GetFullPath(args[++i]);
                        if (option == "--link-metrics" && linkMetrics == null) linkMetrics = path;
                        else if (option == "--release-report" && releasePath == null) releasePath = path;
                        else if (option == "--evidence-zip" && evidenceZip == null) evidenceZip = path;
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
            Require(!invalidEvidenceOption, "連線量測、發行報告及驗收 ZIP 各只能指定一份檔案。");
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
            if (evidenceZip != null)
            {
                Require(launch && wait && !verify && releasePath != null && log != null && report != null
                    && String.Equals(Path.GetExtension(evidenceZip), ".zip", StringComparison.OrdinalIgnoreCase)
                    && !evidenceZip.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !File.Exists(evidenceZip) && !Directory.Exists(evidenceZip),
                    "驗收 ZIP 須搭配等待啟動、原日誌、退出報告及發行報告，並使用玩家包外的新 ZIP 路徑。");
                foreach (var path in new[] { config, log, report, statusReport, linkMetrics, releasePath })
                    Require(!SamePath(evidenceZip, path), "驗收 ZIP 須使用獨立路徑。");
                PlainPath(Path.GetDirectoryName(evidenceZip));
            }
            var release = releasePath == null ? null : ReadRelease(releasePath);
            if (verify) { Verify(release == null ? null : release.ManifestHash); ProcessReport(report, "verified", release); return 0; }
            if (launch)
            {
                using (var child = Launch(config, headless, log, openXR: openXR, linkMetrics: linkMetrics,
                    release: release, reportPath: report))
                {
                    if (!wait) return 0;
                    if (statusReport == null) child.WaitForExit();
                    else
                    {
                        var monitor = new PlayerConnectionMonitor(log);
                        while (!child.WaitForExit(200)) { monitor.Poll(); StatusReport(monitor, child.Id, false); }
                        monitor.Poll(exited: true); StatusReport(monitor, child.Id, true);
                    }
                    ProcessReport(report, "exited", release, child, exited: true, linkMetrics: linkMetrics, log: log);
                    if (evidenceZip != null && child.ExitCode == 0)
                        Require(WriteEvidenceZip(evidenceZip, log, report, release, child.Id, linkMetrics),
                            "驗收 ZIP 需要同一次遊戲的完整最終戰績及結束斷線。");
                    return child.ExitCode;
                }
            }
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new PlayerForm(config, log, report)); return 0;
        }
        catch (Exception error)
        {
            // Serializer / IO exception text can contain input. Do not echo secrets or file contents.
            var firewall = error as WindowsFirewallPreflight;
            if (report != null && !File.Exists(report) && !report.StartsWith(Root, StringComparison.OrdinalIgnoreCase) && !SamePath(report, config)
                && !SamePath(report, log) && !SamePath(report, linkMetrics) && !SamePath(report, releasePath) && !SamePath(report, evidenceZip))
                try { Report(report, new { status = "rejected", reason = firewall == null ? "Package, connection file or launch options are invalid." : firewall.Message }); } catch { }
            if (report == null) Console.Error.WriteLine(firewall == null ? "Unable to start. Check the extracted player package and the downloaded player connection file." : firewall.Message);
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
        internal bool CanRenew { get { return LocalFullPath(FilePath) && !FilePath.StartsWith(Root, StringComparison.OrdinalIgnoreCase)
            && Ticket != null && Ticket.HasAdmission; } }
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
                Endpoint = ConfigEndpoint(value);
                Ticket = TicketPreview.Read(Text(value, "joinTicket"));
            }
        }
        internal string Renew(string file)
        {
            Require(CanRenew && LocalFullPath(file), "The active ticket and replacement must be local files.");
            var result = RefreshTicket(FilePath, Path.GetFullPath(file), Ticket, Endpoint);
            ContentHash = result.FileHash;
            Ticket = result.Ticket;
            return result.Status;
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

    internal sealed class ReleaseReview
    {
        private string file;
        private ReleaseProof proof;
        public bool Loaded { get { return proof != null; } }
        public void Clear() { file = null; proof = null; }
        public void Load(string path)
        {
            Clear();
            Require(!String.IsNullOrWhiteSpace(path) && Path.IsPathRooted(path) && Path.GetPathRoot(path).Length > 2,
                "請輸入發行報告完整路徑。");
            var full = Path.GetFullPath(path); PlainPath(full);
            var expected = ReadRelease(full);
            Require(Hash(PackagePath("player-package.json")) == expected.ManifestHash, "本機玩家包清單與場館發行報告不同。");
            file = full; proof = expected;
        }
        public ReleaseProof RequireCurrent()
        {
            if (Loaded && EvidenceHash(file, 8192) == proof.ReportHash) return proof;
            Clear(); throw new InvalidDataException("發行報告已變更，請重新載入後核對。");
        }
    }
    internal sealed class TicketPreview
    {
        private Guid session, player, admission;
        public int Room { get; private set; }
        public int Seat { get; private set; }
        public DateTimeOffset ExpiresAtUtc { get; private set; }
        internal bool HasAdmission { get { return session != Guid.Empty && player != Guid.Empty && admission != Guid.Empty; } }

        public static TicketPreview Read(string ticket)
        {
            // The v2 fields support local review. Signature validation stays with the game server.
            if (ticket == null || ticket.Length != 147 ||
                !Regex.IsMatch(ticket, @"\Av2\.[A-Za-z0-9_-]{100}\.[A-Za-z0-9_-]{43}\z")) return null;
            var payload = Convert.FromBase64String(ticket.Substring(3, 100).Replace('-', '+').Replace('_', '/'));
            if (payload[0] != 2 || payload[49] < 1 || payload[49] > 5 || payload[50] > 4) return null;
            long seconds = 0;
            for (var offset = 51; offset < 59; offset++) seconds = (seconds << 8) | payload[offset];
            if (seconds <= 0 || seconds > 253402300799L) return null;
            return new TicketPreview { session = TicketId(payload, 1), player = TicketId(payload, 17), admission = TicketId(payload, 33),
                Room = payload[49], Seat = payload[50] + 1,
                ExpiresAtUtc = DateTimeOffset.FromUnixTimeSeconds(seconds) };
        }

        private static Guid TicketId(byte[] payload, int offset)
        {
            var bytes = new byte[16];
            Buffer.BlockCopy(payload, offset, bytes, 0, bytes.Length);
            return new Guid(bytes);
        }

        internal bool SameAdmission(TicketPreview other)
        {
            return other != null && HasAdmission
                && session == other.session && player == other.player && admission == other.admission
                && Room == other.Room && Seat == other.Seat;
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

    internal sealed class LinkMeasurement
    {
        private ulong connection;
        private bool complete;
        private int replies, timeouts, interrupted;

        public static LinkMeasurement ReadReport(string path, int processId)
        {
            PlainPath(path);
            var value = Read(path, 64 * 1024);
            object rawConnection, rawComplete, rawSamples;
            ulong id = 0;
            Require(Number(value, "version") == 1 && Number(value, "processId") == processId
                && value.TryGetValue("connection", out rawConnection) && (rawConnection is int || rawConnection is long || rawConnection is decimal)
                && UInt64.TryParse(Convert.ToString(rawConnection, System.Globalization.CultureInfo.InvariantCulture), out id)
                && value.TryGetValue("complete", out rawComplete) && rawComplete is bool
                && value.TryGetValue("samples", out rawSamples) && rawSamples is object[], "本次連線量測格式或程序不符。");
            var samples = (object[])value["samples"];
            var reason = Text(value, "reason");
            var result = new LinkMeasurement { connection = id, complete = (bool)value["complete"] };
            Require(samples.Length <= 30 && result.complete == (reason == "Limit") && (!result.complete || samples.Length == 30)
                && (reason == "Limit" || reason == "Ended" || reason == "Disconnected" || reason == "Deadline" || reason == "Shutdown"),
                "本次連線量測結案狀態不符。");
            for (var index = 0; index < samples.Length; index++)
            {
                var sample = Map(samples[index]);
                Require(sample != null && Number(sample, "sequence") == index + 1, "本次連線量測樣本序號不符。");
                switch (Text(sample, "result"))
                {
                    case "Reply": result.replies++; break;
                    case "Timeout": result.timeouts++; break;
                    case "Interrupted": result.interrupted++; break;
                    default: throw new InvalidDataException("本次連線量測樣本結果不符。");
                }
            }
            return result;
        }

        public string Describe(ulong? lastConnection, bool reconnected)
        {
            if (reconnected) return "遊戲已重新入場，已保存的量測未涵蓋目前連線。";
            if (!lastConnection.HasValue) return "已保存連線量測，等待核對本次入場記錄。";
            if (lastConnection.Value != connection) return "已保存的量測與目前連線不符。";
            return (complete ? "連線量測已完成" : "連線量測已停止") + "（" + (replies + timeouts + interrupted)
                + "／30）　回覆 " + replies + "、逾時 " + timeouts + "、中斷 " + interrupted + "。";
        }
    }

    private sealed class PlayerForm : Form
    {
        private readonly Label selected = new Label { AutoSize = false, Dock = DockStyle.Top, Height = 75, UseMnemonic = false };
        private readonly Label ticketInfo = new Label { AutoSize = false, Dock = DockStyle.Top, Height = 58, UseMnemonic = false };
        private readonly Label status = new Label { AutoSize = false, Dock = DockStyle.Top, Height = 65 };
        private readonly Label linkStatus = new Label { Dock = DockStyle.Top, Height = 35, UseMnemonic = false, Visible = false };
        private readonly Label renewalStatus = new Label { Dock = DockStyle.Top, Height = 55, Visible = false, UseMnemonic = false };
        private readonly Button play = new Button { Text = "開始遊戲(&S)", AccessibleName = "開始遊戲", AutoSize = true, Enabled = false };
        private readonly Button refreshTicket = new Button { Text = "更新重連票券(&T)", AccessibleName = "更新重連票券", AutoSize = true, Enabled = false, Visible = false };
        private readonly RadioButton openXR = new RadioButton { Text = "Windows OpenXR(&O)", AutoSize = true };
        private readonly Button checkOpenXR = new Button { Text = "檢查 OpenXR(&X)", AccessibleName = "檢查 OpenXR", AutoSize = true };
        private readonly Label openXRStatus = new Label { Dock = DockStyle.Top, Height = 46, UseMnemonic = false, Visible = false };
        private readonly CheckBox measureLink = new CheckBox { Text = "記錄本次連線量測(&M)", AccessibleName = "記錄本次連線量測", AutoSize = true, Enabled = false };
        private readonly TextBox path = new TextBox { Dock = DockStyle.Top, AccessibleName = "玩家連線檔完整路徑" };
        private readonly TextBox releasePath = new TextBox { Dock = DockStyle.Top, AccessibleName = "場館發行報告完整路徑" };
        private readonly Label releaseInfo = new Label { Dock = DockStyle.Top, Height = 33, UseMnemonic = false };
        private readonly LinkLabel records = new LinkLabel { Text = "開啟本次紀錄資料夾", Dock = DockStyle.Top, Height = 30, Visible = false };
        private readonly ConfigReview review = new ConfigReview();
        private readonly ReleaseReview release = new ReleaseReview();
        private bool settingPath;
        private Process child; private PlayerConnectionMonitor monitor;
        private bool HasReleasePath { get { return !String.IsNullOrWhiteSpace(releasePath.Text); } }
        public PlayerForm(string initial, string diagnosticLog, string diagnosticReport)
        {
            Text = "VR Command 玩家"; ClientSize = new Size(660, 643); MinimumSize = new Size(676, 682); AutoScroll = true;
            Font = new Font("Microsoft JhengHei UI", 11); Padding = new Padding(20); StartPosition = FormStartPosition.CenterScreen;
            var title = new Label { Text = "選擇控制台下載的玩家連線檔", Dock = DockStyle.Top, Height = 40 };
            var buttons = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 45 };
            var choose = new Button { Text = "選擇連線檔…", AutoSize = true };
            var load = new Button { Text = "載入／更新", AutoSize = true };
            buttons.Controls.Add(choose); buttons.Controls.Add(load); buttons.Controls.Add(play); buttons.Controls.Add(refreshTicket);
            var modes = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 40, AccessibleName = "遊戲模式" };
            modes.Controls.Add(new RadioButton { Text = "桌面模式(&D)", AutoSize = true, Checked = true });
            modes.Controls.Add(openXR);
            modes.Controls.Add(measureLink);
            modes.Controls.Add(checkOpenXR);
            var pathHint = new Label { Text = "可選檔或貼上完整路徑，再按 Enter 載入。", Dock = DockStyle.Top, Height = 35 };
            var hint = new Label { Text = "票券過期或入場被拒絕時，請向控制人員重新取得連線檔。", Dock = DockStyle.Top, Height = 50 };
            var releaseButtons = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 40 };
            var chooseRelease = new Button { Text = "選擇發行報告…", AutoSize = true };
            var loadRelease = new Button { Text = "核對發行報告(&R)", AccessibleName = "核對發行報告", AutoSize = true };
            releaseButtons.Controls.Add(chooseRelease); releaseButtons.Controls.Add(loadRelease);
            Controls.Add(hint); Controls.Add(records); Controls.Add(linkStatus); Controls.Add(status); Controls.Add(renewalStatus); Controls.Add(buttons);
            Controls.Add(openXRStatus); Controls.Add(modes);
            Controls.Add(releaseInfo); Controls.Add(releaseButtons); Controls.Add(releasePath);
            Controls.Add(ticketInfo); Controls.Add(selected); Controls.Add(pathHint); Controls.Add(path); Controls.Add(title);
            checkOpenXR.Click += async delegate
            {
                checkOpenXR.Enabled = false;
                openXRStatus.Text = "正在檢查 Windows OpenXR 檔案…";
                openXRStatus.Visible = true;
                string result;
                try
                {
                    result = await Task.Run(() =>
                    {
                        string source;
                        return InspectOpenXrRuntime(out source);
                    });
                }
                catch (Exception) { result = null; }
                if (IsDisposed) return;
                openXRStatus.Text = DescribeOpenXrFiles(result);
                checkOpenXR.Enabled = true;
            };
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
            refreshTicket.Click += delegate
            {
                if (!CanRenewPlayerTicket()) return;
                using (var dialog = new OpenFileDialog { Title = "選擇控制人員發出的新票券", Filter = "玩家連線檔 (*.json)|*.json",
                    CheckFileExists = true, Multiselect = false })
                    if (dialog.ShowDialog(this) == DialogResult.OK) RefreshCurrentPlayerTicket(dialog.FileName);
            };
            releasePath.TextChanged += delegate
            {
                release.Clear();
                releaseInfo.Text = HasReleasePath ? "請按 Enter 或「核對發行報告」。" : "場館發行報告（選用，連線量測時須核對）";
                UpdatePlay();
            };
            loadRelease.Click += delegate { SelectRelease(); };
            chooseRelease.Click += delegate
            {
                using (var dialog = new OpenFileDialog { Filter = "發行報告 (*.json)|*.json", CheckFileExists = true, Multiselect = false })
                    if (dialog.ShowDialog(this) == DialogResult.OK) { releasePath.Text = dialog.FileName; SelectRelease(); }
            };
            ReleaseProof activeRelease = null;
            string activeLog = null, activeReport = null, activeMetrics = null, resultFolder = null;
            LinkMeasurement measurement = null;
            Stopwatch terminalWait = null;
            records.LinkClicked += delegate
            {
                try { using (Process.Start(new ProcessStartInfo(resultFolder) { UseShellExecute = true })) { } }
                catch { status.Text = "無法開啟本次紀錄資料夾。"; }
            };
            play.Click += delegate
            {
                play.Enabled = false; status.Text = "正在核對玩家包…"; Refresh();
                try
                {
                    review.RequireCurrent();
                    var reviewedRelease = HasReleasePath ? release.RequireCurrent() : null;
                    var ownLog = diagnosticLog; var ownReport = diagnosticReport;
                    Require((ownLog == null || (!File.Exists(ownLog) && !Directory.Exists(ownLog)))
                        && (ownReport == null || (!File.Exists(ownReport) && !Directory.Exists(ownReport))),
                        "診斷記錄與報告須使用新路徑。");
                    if (ownLog == null || (reviewedRelease != null && ownReport == null))
                    {
                        var directory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VrCommand", "PlayerRuns", Guid.NewGuid().ToString("N"));
                        Directory.CreateDirectory(directory);
                        if (ownLog == null) ownLog = Path.Combine(directory, "player.log");
                        if (ownReport == null && reviewedRelease != null) ownReport = Path.Combine(directory, "launch-report.json");
                    }
                    var ownMetrics = measureLink.Checked ? Path.Combine(Path.GetDirectoryName(ownReport), "link-metrics.json") : null;
                    if (ownMetrics != null)
                    {
                        PlainPath(Path.GetDirectoryName(ownMetrics));
                        Require(!SamePath(ownMetrics, ownLog) && !SamePath(ownMetrics, ownReport) && !SamePath(ownMetrics, review.FilePath)
                            && !File.Exists(ownMetrics) && !Directory.Exists(ownMetrics), "連線量測須使用獨立的新檔案。");
                    }
                    child = Launch(review.FilePath, false, ownLog, review.ContentHash, openXR: openXR.Checked,
                        linkMetrics: ownMetrics, release: reviewedRelease, reportPath: ownReport);
                    diagnosticLog = null; diagnosticReport = null;
                    activeRelease = reviewedRelease; activeLog = ownLog; activeReport = ownReport; activeMetrics = ownMetrics;
                    measurement = null;
                    terminalWait = null;
                    linkStatus.Text = ownMetrics == null ? "" : "正在等候本次連線量測的 30 筆樣本結案。";
                    linkStatus.Visible = ownMetrics != null;
                    records.Visible = false; resultFolder = null;
                    monitor = new PlayerConnectionMonitor(ownLog);
                    choose.Enabled = false; load.Enabled = false; path.Enabled = false; modes.Enabled = false;
                    releasePath.Enabled = false; chooseRelease.Enabled = false; loadRelease.Enabled = false;
                    status.Text = monitor.Message;
                    renewalStatus.Text = "取得原席位的新連線檔後，可在此更新原遊戲的重連票券。";
                    UpdateTicketRenewal();
                    RenderTicket();
                }
                catch (WindowsFirewallPreflight error)
                {
                    status.Text = error.Message; UpdatePlay();
                }
                catch
                {
                    if (HasReleasePath && !release.Loaded) releaseInfo.Text = "發行報告已變更或遺失，請重新核對。";
                    review.Clear(); RenderTicket(); selected.Text = "請重新載入並核對連線檔。";
                    status.Text = "無法啟動或檔案已變更。請確認玩家包完整，再重新載入正確的連線檔。"; UpdatePlay();
                }
            };
            var timer = new Timer { Interval = 500 };
            timer.Tick += delegate
            {
                if (child == null) { RenderTicket(); return; }
                var exited = child.HasExited;
                monitor.Poll(exited); status.Text = monitor.Message;
                UpdateTicketRenewal();
                if (activeMetrics != null)
                {
                    if (measurement == null && File.Exists(activeMetrics))
                    {
                        try { measurement = LinkMeasurement.ReadReport(activeMetrics, child.Id); }
                        catch (Exception error)
                        {
                            if (!(error is IOException || error is InvalidDataException || error is UnauthorizedAccessException
                                || error is ArgumentException || error is InvalidOperationException)) throw;
                            linkStatus.Text = "無法核對本次連線量測檔。";
                        }
                    }
                    if (measurement != null) linkStatus.Text = measurement.Describe(monitor.LogAvailable ? monitor.LastConnection : null, monitor.Reconnected);
                    else if (exited && !File.Exists(activeMetrics)) linkStatus.Text = "未取得本次連線量測檔。";
                }
                if (exited)
                {
                    var saved = true; var zipStatus = "";
                    if (activeRelease != null)
                    {
                        if (terminalWait == null) terminalWait = Stopwatch.StartNew();
                        var canWait = terminalWait.Elapsed < TimeSpan.FromSeconds(3);
                        try
                        {
                            ProcessReport(activeReport, "exited", activeRelease, child, exited: true, linkMetrics: activeMetrics,
                                log: activeLog, deferSharing: canWait);
                            resultFolder = Path.GetDirectoryName(activeReport);
                            if (child.ExitCode == 0)
                            {
                                try
                                {
                                    var archived = WriteEvidenceZip(Path.Combine(resultFolder, "player-evidence.zip"), activeLog, activeReport,
                                        activeRelease, child.Id, activeMetrics);
                                    zipStatus = archived ? (activeMetrics == null ? " 本次驗收 ZIP 已建立。" : " 本次驗收 ZIP 已附連線量測。")
                                        : " 本次記錄未通過驗收 ZIP 核對，可查看原檔。";
                                }
                                catch (Exception error)
                                {
                                    var io = error as IOException;
                                    if (io != null && canWait && IsSharingViolation(io)) throw;
                                    zipStatus = " 本次驗收 ZIP 未能建立，可在紀錄資料夾查看原檔。";
                                }
                            }
                            records.Visible = true;
                        }
                        catch (Exception error)
                        {
                            var io = error as IOException;
                            if (io != null && canWait && IsSharingViolation(io))
                            {
                                status.Text = "遊戲已關閉，正在等候本次紀錄檔解除占用。";
                                return;
                            }
                            saved = false;
                        }
                    }
                    var final = monitor.State == "Final"; child.Dispose(); child = null;
                    measureLink.Checked = false;
                    choose.Enabled = true; load.Enabled = true; path.Enabled = true; modes.Enabled = true;
                    releasePath.Enabled = true; chooseRelease.Enabled = true; loadRelease.Enabled = true; UpdatePlay();
                    RenderTicket();
                    status.Text = final ? "遊戲已關閉；本次已收到最終戰績。" : "遊戲已關閉。" + monitor.Message;
                    if (!saved) status.Text += " 本次程序報告儲存失敗。";
                    status.Text += zipStatus;
                }
            };
            FormClosing += delegate(object sender, FormClosingEventArgs args)
            {
                if (args.CloseReason != CloseReason.UserClosing || child == null || activeRelease == null) return;
                args.Cancel = true; status.Text = "請先關閉遊戲，等本次程序報告儲存完成。";
            };
            timer.Start(); FormClosed += delegate { timer.Dispose(); if (child != null) child.Dispose(); };
            selected.Text = "尚未選擇連線檔";
            releaseInfo.Text = "場館發行報告（選用，連線量測時須核對）";
            if (initial != null) SelectConfig(initial);
        }
        protected override bool ProcessCmdKey(ref Message message, Keys keyData)
        {
            if (keyData == Keys.Enter)
            {
                var repeated = (message.LParam.ToInt64() & (1L << 30)) != 0;
                if (path.IsHandleCreated && message.HWnd == path.Handle)
                { if (path.Enabled && !repeated) SelectConfig(path.Text); return true; }
                if (releasePath.IsHandleCreated && message.HWnd == releasePath.Handle)
                { if (releasePath.Enabled && !repeated) SelectRelease(); return true; }
            }
            return base.ProcessCmdKey(ref message, keyData);
        }
        private void UpdatePlay()
        {
            if (!release.Loaded) measureLink.Checked = false;
            measureLink.Enabled = child == null && release.Loaded;
            play.Enabled = child == null && review.Loaded && (!HasReleasePath || release.Loaded);
        }
        private bool CanRenewPlayerTicket()
        { return child != null && !child.HasExited && monitor != null && monitor.State != "Final" && review.CanRenew; }

        private void UpdateTicketRenewal()
        {
            var available = CanRenewPlayerTicket();
            refreshTicket.Enabled = refreshTicket.Visible = renewalStatus.Visible = available;
        }

        private void RefreshCurrentPlayerTicket(string file)
        {
            if (!CanRenewPlayerTicket()) { UpdateTicketRenewal(); return; }
            try
            {
                var result = review.Renew(file);
                renewalStatus.Text = (result == "ticket-file-current" ? "原連線檔已是此票券。" : "原連線檔的票券已更新。")
                    + "請回到原遊戲操作重連。";
                RenderTicket();
            }
            catch (Exception)
            { renewalStatus.Text = "未能確認更新。請核對原席位、端點及所選連線檔，再試一次。"; }
        }
        private void SelectRelease()
        {
            release.Clear();
            if (HasReleasePath)
            {
                try { release.Load(releasePath.Text); releaseInfo.Text = "發行清單相符，啟動時會逐檔核對。"; }
                catch { releaseInfo.Text = "發行報告或套件不符。請核對主控交付的原始檔案。"; }
            }
            else releaseInfo.Text = "場館發行報告（選用，連線量測時須核對）";
            UpdatePlay();
        }
        private static string DescribeOpenXrFiles(string status)
        {
            switch (status)
            {
                case "x64-runtime-files-found": return "已找到 OpenXR 清單與 x64 DLL。請連接頭盔後用 Windows OpenXR 模式確認追蹤。";
                case "runtime-not-configured": return "Windows 尚未設定使用中的 OpenXR 執行環境。請在頭盔軟體中設定。";
                case "registry-unreadable": return "無法讀取 Windows OpenXR 登錄設定。";
                case "manifest-path-invalid": return "OpenXR 清單路徑無效。請確認頭盔軟體的執行環境設定。";
                case "manifest-missing": return "找不到 OpenXR 清單。請確認頭盔軟體的執行環境設定。";
                case "manifest-invalid": return "無法讀取 OpenXR 清單，或清單格式不正確。";
                case "library-search-required": return "OpenXR 清單只提供 DLL 檔名。請用 Windows OpenXR 模式確認載入。";
                case "library-path-invalid": return "OpenXR DLL 路徑無效。請確認頭盔軟體的執行環境設定。";
                case "library-missing": return "找不到 OpenXR 清單指定的 DLL。請確認頭盔軟體安裝。";
                case "library-unreadable": return "無法讀取 OpenXR 清單指定的 DLL。";
                case "library-not-x64-dll": return "OpenXR 清單指定的 DLL 標頭與 x64 Windows 不相符。";
                default: return "無法完成 OpenXR 檔案檢查。";
            }
        }
        private void SelectConfig(string file)
        {
            try
            {
                review.Load(file); settingPath = true;
                try { path.Text = review.FilePath; } finally { settingPath = false; }
                selected.Text = Path.GetFileName(review.FilePath) + "\n伺服器 " + review.Endpoint;
                RenderTicket();
                UpdatePlay(); status.Text = "核對目的地與席位，選擇遊戲模式，再按「開始遊戲」。";
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
    private const string ConnectedPrefix = "VR_CLIENT_CONNECTED ";
    private const string PendingPrefix = "VR_CLIENT_DEBRIEF_PENDING ";
    private const string FinalPrefix = "VR_CLIENT_DEBRIEF_FINAL ";
    private readonly string path;
    private readonly Stopwatch clock = Stopwatch.StartNew();
    private readonly Decoder decoder = Encoding.UTF8.GetDecoder();
    private readonly StringBuilder line = new StringBuilder();
    private readonly HashSet<string> evidenceConnections;
    private Guid pendingSession;
    private long offset;
    private bool discardLine;
    private bool invalidLog;
    private bool invalidEvidence;
    private bool sawFinal;
    private bool finalDisconnected;
    public string State { get; private set; }
    public bool LogAvailable { get; private set; }
    public ulong? LastConnection { get; private set; }
    public bool Reconnected { get; private set; }
    public bool CanArchiveEvidence { get { return evidenceConnections != null && finalDisconnected && !invalidEvidence && !invalidLog; } }
    public bool Truncated { get; private set; }
    public readonly List<string> Transitions = new List<string>();
    public PlayerConnectionMonitor(string log, bool verifyEvidence = false)
    {
        path = log;
        if (verifyEvidence) evidenceConnections = new HashSet<string>(StringComparer.Ordinal);
        Change("Waiting");
    }
    private void Change(string state)
    {
        if (State == state) return;
        State = state;
        if (Transitions.Count < 64) Transitions.Add(state); else Truncated = true;
    }
    internal void Observe(string value)
    {
        // Never serialize or display arbitrary log text or IDs.
        if (value.StartsWith(ConnectedPrefix, StringComparison.Ordinal))
        {
            var connection = Regex.Match(value, @"\AVR_CLIENT_CONNECTED id=(0|[1-9][0-9]{0,19})\z");
            if (!connection.Success) { invalidEvidence = true; return; }
            ulong id;
            Reconnected |= LastConnection.HasValue;
            LastConnection = UInt64.TryParse(connection.Groups[1].Value, out id) ? (ulong?)id : null;
            if (evidenceConnections != null && (!evidenceConnections.Add(value) || sawFinal || State == "Connected" || State == "ResultPending"))
                invalidEvidence = true;
            pendingSession = Guid.Empty;
            finalDisconnected = false;
            Change("Connected");
        }
        else if (value.StartsWith(FinalPrefix, StringComparison.Ordinal))
        {
            Guid session;
            if (State != "ResultPending" || !PlayerLauncher.TryReadFinalDebrief(value.Substring(FinalPrefix.Length), out session)
                || session != pendingSession)
            { invalidEvidence = true; return; }
            if (sawFinal) invalidEvidence = true;
            sawFinal = true;
            Change("Final");
        }
        else if (State == "Final")
        {
            if (value == "VR_CLIENT_DISCONNECTED") finalDisconnected = true;
        }
        else if ((value == "VR_OPENXR_STARTUP status=rejected" || value == "VR_OPENXR_STARTUP status=unavailable")
                 && (State == "Waiting" || State == "Unconfirmed")) Change("OpenXRUnavailable");
        else if (value == "VR_CLIENT_ADMISSION_REJECTED") Change("Rejected");
        else if (value == "VR_CLIENT_DISCONNECTED")
        {
            if (State == "ResultPending") Change("ResultInterrupted");
            else if (State != "ResultInterrupted") Change("Disconnected");
        }
        else if ((State == "Connected" || State == "ResultPending") && value.StartsWith(PendingPrefix, StringComparison.Ordinal))
        {
            Guid session;
            if (value.Length != PendingPrefix.Length + 36
                || !Guid.TryParseExact(value.Substring(PendingPrefix.Length), "D", out session) || session == Guid.Empty) return;
            if (State == "ResultPending" && session != pendingSession) { invalidEvidence = true; return; }
            pendingSession = session;
            Change("ResultPending");
        }
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
                else
                {
                    var prefix = line.ToString(0, FinalPrefix.Length);
                    if (prefix == FinalPrefix || prefix.StartsWith(ConnectedPrefix, StringComparison.Ordinal)) invalidEvidence = true;
                    line.Clear(); discardLine = true;
                }
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
