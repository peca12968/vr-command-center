using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

internal static class ServerCatalogProof
{
    static int checks;
    static void Check(bool value, string name) { if (!value) throw new InvalidDataException(name); checks++; }
    static Dictionary<string, object> Row(int room, string name = "軍事任務")
    {
        return ServerLauncher.Map(ServerLauncher.Json.DeserializeObject(ServerLauncher.Json.Serialize(new { id = Guid.NewGuid().ToString("D"), mode = "Independent", roomIds = new[] { room }, state = "Preparing", combatStream = (object)null, environment = new { mode = "VR" }, mission = new { id = Guid.NewGuid().ToString("D"), definition = new { name = name } } })));
    }
    static void Reject(object[] rows, string name) { bool rejected = false; try { ServerLauncher.Catalog.Parse(rows); } catch (InvalidDataException) { rejected = true; } Check(rejected, name); }
    static void CheckUdpBindings()
    {
        int pid, port;
        using (var process = Process.GetCurrentProcess()) pid = process.Id;
        using (var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp))
        {
            socket.ExclusiveAddressUse = true;
            socket.Bind(new IPEndPoint(IPAddress.Loopback, 0));
            port = ((IPEndPoint)socket.LocalEndPoint).Port;
            Check(ServerLauncher.UdpBinding.Find(pid, "127.0.0.1", port) != null, "OS table returns an actual bound UDP endpoint owned by this process");
            Check(ServerLauncher.UdpBinding.Find(pid + 1, "127.0.0.1", port) == null, "Another PID cannot satisfy the same address and port");
            Check(ServerLauncher.UdpBinding.Find(pid, "0.0.0.0", port) == null, "Loopback cannot satisfy a wildcard request");
            Check(ServerLauncher.UdpBinding.Find(pid, "127.0.0.1", port == 65535 ? port - 1 : port + 1) == null, "A different port cannot satisfy the same owner and address");
        }
        Check(SpinWait.SpinUntil(() => ServerLauncher.UdpBinding.Find(pid, "127.0.0.1", port) == null, 1000), "The closed socket no longer satisfies an endpoint query");
        using (var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp))
        {
            socket.ExclusiveAddressUse = true;
            socket.Bind(new IPEndPoint(IPAddress.Any, 0));
            port = ((IPEndPoint)socket.LocalEndPoint).Port;
            Check(ServerLauncher.UdpBinding.Find(pid, "0.0.0.0", port) != null, "An actual wildcard socket satisfies only its exact bind address");
            Check(ServerLauncher.UdpBinding.Find(pid, "127.0.0.1", port) == null, "Wildcard cannot satisfy an explicit loopback request");
        }
    }
    static int Main(string[] args)
    {
        var output = args[1];
        try
        {
            CheckUdpBindings();
            var first = Row(1); var second = Row(2); var parsed = ServerLauncher.Catalog.Parse(new object[] { second, first });
            Check(parsed.Count == 2 && parsed[0].Id == (string)first["id"] && parsed[0].ToString().Contains("房間 1") && parsed[0].ToString().Contains("軍事任務"), "room/name display sorts without replacing original id");
            Check(parsed[0].MissionId != parsed[1].MissionId && parsed[0].MissionName == parsed[1].MissionName && parsed[0].Id != parsed[1].Id, "duplicate names retain distinct session / version identities");
            Reject(new object[] { first, first }, "duplicate session id"); Reject(new object[] { first, Row(1) }, "overlapping room");
            var bad = Row(1); bad["mode"] = "Linked"; Reject(new object[] { bad }, "incomplete linked rooms");
            bad = Row(1); bad["roomIds"] = new object[] { 6 }; Reject(new object[] { bad }, "outside room");
            bad = Row(1); bad["roomIds"] = new object[] { true }; Reject(new object[] { bad }, "boolean room");
            bad = Row(1); bad["id"] = Guid.Empty.ToString("D"); Reject(new object[] { bad }, "empty id");
            bad = Row(1); bad["id"] = "not-a-guid"; Reject(new object[] { bad }, "invalid id");
            bad = Row(1); bad["combatStream"] = "invalid"; Reject(new object[] { bad }, "malformed source");
            bad = Row(1); bad.Remove("combatStream"); Reject(new object[] { bad }, "missing source field");
            bad = Row(1); bad["state"] = "future-state"; Reject(new object[] { bad }, "unknown state");
            var running = Row(1); running["state"] = "Running"; var bound = Row(2); bound["combatStream"] = new Dictionary<string, object>(); var mr = Row(3); ServerLauncher.Child(mr, "environment")["mode"] = "MR";
            Check(ServerLauncher.Catalog.Parse(new object[] { running, bound, mr }).Count == 0, "running / bound / MR are not available choices");
            var linked = Row(1); linked["mode"] = "Linked"; linked["roomIds"] = new object[] { 5, 4, 3, 2, 1 }; var all = ServerLauncher.Catalog.Parse(new object[] { linked });
            Check(all.Count == 1 && all[0].Rooms[0] == 1 && all[0].Rooms[4] == 5 && all[0].ToString().Contains("五房全連線"), "linked identity covers all five rooms");
            Check(ServerLauncher.Choice.Label("甲\n乙\u202e丙") == "甲 乙丙", "display removes control / bidi formatting only");
            Check(!Char.IsHighSurrogate(ServerLauncher.Choice.Label(new String('甲', 31) + "\ud83d\ude80尾")[31]), "truncation preserves a surrogate boundary");
            var descriptor = ServerLauncher.Read(args[0], 8192); var instance = ServerLauncher.Text(descriptor, "instance");
            var state = new ServerLauncher.CatalogState(); state.Edit(instance); state.Load(); Check(state.Loaded && !state.CanStart && state.Selected == null && state.Current.Choices.Count > 0, "initial load requires an explicit selection");
            var original = state.Current.Choices[0].Id; state.Select(original); Check(state.CanStart && state.Selected.Id == original, "select maps the original id");
            state.Edit(instance); Check(!state.CanStart, "editing invalidates launch even for the same path"); state.Load(); Check(state.CanStart && state.Selected.Id == original, "same identity refresh preserves only its original selection");
            var markerText = File.ReadAllText(instance, Encoding.UTF8); var marker = ServerLauncher.Read(instance, 4096);
            try { marker["instanceId"] = Guid.NewGuid().ToString("D"); File.WriteAllText(instance, ServerLauncher.Json.Serialize(marker), new UTF8Encoding(false)); state.Load(); Check(state.Loaded && !state.CanStart && state.Selected == null, "changed instance identity requires a new selection"); }
            finally { File.WriteAllText(instance, markerText, new UTF8Encoding(false)); }
            state.Load(); state.Select(original); var keysPath = Path.Combine(Path.GetDirectoryName(instance), "operator-keys.json"); var keysText = File.ReadAllText(keysPath, Encoding.UTF8); var keyFile = ServerLauncher.Read(keysPath, 8192);
            try { ServerLauncher.Child(keyFile, "OperatorKeys")["GameServer"] = ServerLauncher.Text(descriptor, "masterKey"); File.WriteAllText(keysPath, ServerLauncher.Json.Serialize(keyFile), new UTF8Encoding(false)); bool denied = false; try { state.Load(); } catch (InvalidDataException) { denied = true; } Check(denied && !state.CanStart && state.Current == null && state.Selected == null, "changed credential with wrong role cannot restore old target"); }
            finally { File.WriteAllText(keysPath, keysText, new UTF8Encoding(false)); }
            state.Load(); state.Select(original); state.Edit(Path.Combine(Path.GetDirectoryName(instance), "missing", "control-instance.json")); bool failed = false; try { state.Load(); } catch (IOException) { failed = true; }
            Check(failed && state.Current == null && state.Selected == null && !state.CanStart, "failed reload cannot reuse old target or selection");
            state.Edit(instance); state.Load(); Check(!state.CanStart && state.Selected == null, "recovery after failure does not silently restore a selection");
            state.Select(original); var api = state.Current.Target.Api; var request = (HttpWebRequest)WebRequest.Create(api + "/api/sessions/" + original + "/commands"); request.Method = "POST"; request.Proxy = null; request.Timeout = 5000; request.ContentType = "application/json"; request.Headers[HttpRequestHeader.Authorization] = "Bearer " + ServerLauncher.Text(descriptor, "masterKey");
            var body = Encoding.UTF8.GetBytes(ServerLauncher.Json.Serialize(new { commandId = Guid.NewGuid().ToString("D"), action = "End" })); request.ContentLength = body.Length; using (var stream = request.GetRequestStream()) stream.Write(body, 0, body.Length); using (var response = request.GetResponse()) { }
            state.Load(); Check(state.Loaded && state.Current.Choices.Count > 0 && state.Selected == null && !state.CanStart, "removed original choice never selects another room on refresh");
            original = state.Current.Choices[0].Id;
            state.Select(original); state.Edit(""); failed = false; try { state.Load(); } catch (InvalidDataException) { failed = true; }
            Check(failed && !state.CanStart && state.Current == null, "empty path fails closed");
            ServerLauncher.Save(output, new { complete = true, checks = checks, scope = "Actual Framework catalog/state methods and Windows UDP socket owner/address/port checks. No WinForms UI automation, game readiness or headset proof." }); return 0;
        }
        catch (Exception e) { ServerLauncher.Save(output, new { complete = false, checks = checks, error = ServerLauncher.Safe(e) }); return 1; }
    }
}
