using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

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
    static async Task WaitFor(Func<bool> condition, string description)
    {
        var elapsed = Stopwatch.StartNew();
        while (!condition())
        {
            if (elapsed.ElapsedMilliseconds >= 3000) throw new TimeoutException(description);
            await Task.Delay(15);
        }
    }

    static bool PressEnter(Control control, bool repeated = false)
    {
        const int keyDown = 0x0100;
        var message = Message.Create(control.Handle, keyDown, (IntPtr)Keys.Enter, repeated ? (IntPtr)(1 << 30) : IntPtr.Zero);
        return control.PreProcessMessage(ref message);
    }

    static void CheckResponsiveCatalog(string delayedInstance)
    {
        var folder = Path.GetDirectoryName(delayedInstance);
        var mode = Path.Combine(folder, "mode");
        var entered = Path.Combine(folder, "entered");
        var release = Path.Combine(folder, "release");
        Exception failure = null;
        bool closedWithRequestHeld = false;
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        var previousContext = SynchronizationContext.Current;
        using (var window = new ServerLauncher.Window { ShowInTaskbar = false, Opacity = 0 })
        {
            var path = window.Controls.OfType<TextBox>().First();
            var address = window.Controls.OfType<TextBox>().Skip(1).First();
            var rooms = window.Controls.OfType<ComboBox>().Single();
            var refresh = window.Controls.OfType<Button>().Single(button => button.Text == "載入／更新");
            var start = window.Controls.OfType<Button>().Single(button => button.Text == "啟動伺服器");
            Action<string> arm = response =>
            {
                File.Delete(entered);
                File.Delete(release);
                File.WriteAllText(mode, response);
            };
            window.Shown += async delegate
            {
                try
                {
                    path.Text = delayedInstance;
                    arm("success");
                    PressEnter(address);
                    Check(refresh.Enabled && !rooms.Enabled && !start.Enabled, "Enter outside the path does not load or launch a session");
                    Check(PressEnter(path, repeated: true) && refresh.Enabled && !rooms.Enabled && !start.Enabled,
                        "held Enter on the path does not issue a repeat load");
                    Check(PressEnter(path), "Enter on the management path is handled by the actual WinForms key path");
                    await WaitFor(() => File.Exists(entered), "catalog request reaches the relay");
                    Check(!File.Exists(release) && !refresh.Enabled && !path.Enabled && !start.Enabled && !rooms.Enabled,
                        "the WinForms message loop runs while the catalog response is held and launch stays disabled");
                    File.WriteAllText(release, "");
                    await WaitFor(() => refresh.Enabled, "initial catalog load completes");
                    Check(path.Enabled && rooms.Enabled && rooms.Items.Count == 2 && rooms.SelectedIndex == -1 && !start.Enabled,
                        "first background load restores room controls and requires explicit selection");
                    rooms.SelectedIndex = 0;
                    var original = ((ServerLauncher.Choice)rooms.SelectedItem).Id;
                    Check(start.Enabled, "the first explicitly selected original room can start");

                    arm("success");
                    Check(PressEnter(path), "Enter refresh uses the existing catalog path after an explicit selection");
                    await WaitFor(() => File.Exists(entered), "refresh reaches the relay");
                    Check(!start.Enabled, "a refresh makes the previously selected room ineligible while the read is pending");
                    File.WriteAllText(release, "");
                    await WaitFor(() => refresh.Enabled, "refresh completes");
                    Check(start.Enabled && ((ServerLauncher.Choice)rooms.SelectedItem).Id == original,
                        "the same instance refresh restores the exact original selected room");

                    arm("failure");
                    refresh.PerformClick();
                    await WaitFor(() => File.Exists(entered), "failed request reaches the relay");
                    File.WriteAllText(release, "");
                    await WaitFor(() => refresh.Enabled, "failed refresh restores inputs");
                    Check(path.Enabled && !rooms.Enabled && !start.Enabled && rooms.Items.Count == 0 && rooms.SelectedItem == null,
                        "a rejected response clears old rooms and keeps launch disabled");

                    arm("success");
                    refresh.PerformClick();
                    await WaitFor(() => File.Exists(entered), "final held request reaches the relay");
                    window.Close();
                    closedWithRequestHeld = window.IsDisposed && !File.Exists(release);
                }
                catch (Exception error)
                {
                    failure = error;
                    window.Close();
                }
                finally { File.WriteAllText(release, ""); }
            };
            try { Application.Run(window); }
            finally { SynchronizationContext.SetSynchronizationContext(previousContext); }
        }
        if (failure != null) throw failure;
        Check(closedWithRequestHeld, "the owned form closes normally before the catalog response is released");
    }

    [STAThread]
    static int Main(string[] args)
    {
        var output = args[1];
        try
        {
            CheckUdpBindings();
            foreach (var code in new[] { 502, 503, 504 })
                Check(ServerLauncher.ManagementUnavailable.IsTemporary(code, WebExceptionStatus.ProtocolError), "Temporary management gateway status " + code);
            foreach (var code in new[] { 401, 403, 404, 500 })
                Check(!ServerLauncher.ManagementUnavailable.IsTemporary(code, WebExceptionStatus.ProtocolError), "Terminal management HTTP status " + code);
            Check(ServerLauncher.ManagementUnavailable.IsTemporary(0, WebExceptionStatus.ConnectFailure)
                && ServerLauncher.ManagementUnavailable.IsTemporary(0, WebExceptionStatus.Timeout), "A disconnected or timed-out management read permits bounded recovery");
            Check(!ServerLauncher.ManagementUnavailable.IsTemporary(0, WebExceptionStatus.RequestCanceled)
                && !ServerLauncher.ManagementUnavailable.IsTemporary(0, WebExceptionStatus.ServerProtocolViolation), "Cancellation and malformed HTTP are terminal");
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
            var mrChoices = ServerLauncher.Catalog.Parse(new object[] { running, bound, mr });
            Check(mrChoices.Count == 1 && mrChoices[0].Experience == "MR" && mrChoices[0].ToString().Contains(" · MR · "),
                "Preparing MR appears with its own experience label while running and bound sessions stay excluded");
            Check(!mrChoices[0].CanStart && mrChoices[0].MissingAlignmentRooms.Length == 1 && mrChoices[0].MissingAlignmentRooms[0] == 3
                && mrChoices[0].Detail().Contains("房間 3") && mrChoices[0].Detail().Contains("重新載入"), "unlocked Independent MR identifies the affected room and operator action");
            var linked = Row(1); linked["mode"] = "Linked"; linked["roomIds"] = new object[] { 5, 4, 3, 2, 1 }; var all = ServerLauncher.Catalog.Parse(new object[] { linked });
            Check(all.Count == 1 && all[0].Rooms[0] == 1 && all[0].Rooms[4] == 5 && all[0].CanStart && all[0].ToString().Contains("五房全連線"), "linked VR identity covers all five rooms without requiring MR pins");
            ServerLauncher.Child(linked, "environment")["mode"] = "MR";
            var hash = new String('a', 64);
            linked["roomAlignment"] = new Dictionary<string, object> { { "room1", hash }, { "room2", new String('A', 64) }, { "room3", null }, { "room4", hash }, { "room5", 5 } };
            var incomplete = ServerLauncher.Catalog.Parse(new object[] { linked })[0];
            Check(!incomplete.CanStart && String.Join(",", incomplete.MissingAlignmentRooms) == "2,3,5" && incomplete.ToString().Contains("待鎖定校正"), "Linked MR reports only missing or invalid pins in sorted room order");
            var pins = ServerLauncher.Child(linked, "roomAlignment");
            for (int room = 1; room <= 5; room++) pins["room" + room] = hash;
            var ready = ServerLauncher.Catalog.Parse(new object[] { linked })[0];
            Check(ready.CanStart && ready.MissingAlignmentRooms.Length == 0 && ready.Id == incomplete.Id && !ready.Detail().Contains("重新載入"), "all five locked pins enable the same Linked choice without advertising a digest");
            linked["roomAlignment"] = "malformed";
            Check(!ServerLauncher.Catalog.Parse(new object[] { linked })[0].CanStart, "malformed lock data fails closed without dropping the choice");
            Check(ServerLauncher.Choice.Label("甲\n乙\u202e丙") == "甲 乙丙", "display removes control / bidi formatting only");
            Check(!Char.IsHighSurrogate(ServerLauncher.Choice.Label(new String('甲', 31) + "\ud83d\ude80尾")[31]), "truncation preserves a surrogate boundary");
            var descriptor = ServerLauncher.Read(args[0], 8192); var instance = ServerLauncher.Text(descriptor, "instance");
            CheckResponsiveCatalog(ServerLauncher.Text(descriptor, "delayedInstance"));
            var profilePath = Path.Combine(Path.GetDirectoryName(args[0]), "profile-proof", "control-instance.json");
            Directory.CreateDirectory(Path.GetDirectoryName(profilePath));
            var profile = new Dictionary<string, object> { { "schemaVersion", 1 }, { "kind", "VrCommand-RemoteGameServer" },
                { "instanceId", Guid.NewGuid().ToString("D") }, { "managementApiUrl", "https://control.venue.example:8443" },
                { "gameServerKey", new String('g', 64) }, { "managementCertificateSha256", hash } };
            ServerLauncher.Save(profilePath, profile);
            var remote = ServerLauncher.Catalog.ReadTarget(profilePath);
            remote.Choices = parsed;
            var remoteState = new ServerLauncher.CatalogState { Draft = profilePath, Loaded = true, Current = remote };
            remoteState.Select(parsed[0].Id);
            var start = remoteState.StartSettings("127.0.0.1", "127.0.0.1", 7777);
            Check(start.Api == remote.Target.Api && start.CertificateSha256 == hash && start.Session == parsed[0].Id,
                "remote GUI selection passes its HTTPS origin and pin to the original session");
            profile["managementCertificateSha256"] = new String('b', 64);
            File.WriteAllText(profilePath, ServerLauncher.Json.Serialize(profile), new UTF8Encoding(false));
            bool changedPin = false;
            try { remoteState.StartSettings("127.0.0.1", "127.0.0.1", 7777); } catch (InvalidDataException) { changedPin = true; }
            Check(changedPin && !remoteState.CanStart && remoteState.Current == null && remoteState.Selected == null,
                "profile pin changed after preview requires reload and a new selection before GUI launch");
            var state = new ServerLauncher.CatalogState(); state.Edit(instance); state.Load().GetAwaiter().GetResult(); Check(state.Loaded && !state.CanStart && state.Selected == null && state.Current.Choices.Count > 0, "initial load requires an explicit selection");
            var original = state.Current.Choices[0].Id; state.Select(original); Check(state.CanStart && state.Selected.Id == original, "select maps the original id");
            state.Edit(instance); Check(!state.CanStart, "editing invalidates launch even for the same path"); state.Load().GetAwaiter().GetResult(); Check(state.CanStart && state.Selected.Id == original, "same identity refresh preserves only its original selection");
            var markerText = File.ReadAllText(instance, Encoding.UTF8); var marker = ServerLauncher.Read(instance, 4096);
            try { marker["instanceId"] = Guid.NewGuid().ToString("D"); File.WriteAllText(instance, ServerLauncher.Json.Serialize(marker), new UTF8Encoding(false)); state.Load().GetAwaiter().GetResult(); Check(state.Loaded && !state.CanStart && state.Selected == null, "changed instance identity requires a new selection"); }
            finally { File.WriteAllText(instance, markerText, new UTF8Encoding(false)); }
            state.Load().GetAwaiter().GetResult(); state.Select(original); var keysPath = Path.Combine(Path.GetDirectoryName(instance), "operator-keys.json"); var keysText = File.ReadAllText(keysPath, Encoding.UTF8); var keyFile = ServerLauncher.Read(keysPath, 8192);
            try { ServerLauncher.Child(keyFile, "OperatorKeys")["GameServer"] = ServerLauncher.Text(descriptor, "masterKey"); File.WriteAllText(keysPath, ServerLauncher.Json.Serialize(keyFile), new UTF8Encoding(false)); bool denied = false; try { state.Load().GetAwaiter().GetResult(); } catch (InvalidDataException) { denied = true; } Check(denied && !state.CanStart && state.Current == null && state.Selected == null, "changed credential with wrong role cannot restore old target"); }
            finally { File.WriteAllText(keysPath, keysText, new UTF8Encoding(false)); }
            state.Load().GetAwaiter().GetResult(); state.Select(original); state.Edit(Path.Combine(Path.GetDirectoryName(instance), "missing", "control-instance.json")); bool failed = false; try { state.Load().GetAwaiter().GetResult(); } catch (IOException) { failed = true; }
            Check(failed && state.Current == null && state.Selected == null && !state.CanStart, "failed reload cannot reuse old target or selection");
            state.Edit(instance); state.Load().GetAwaiter().GetResult(); Check(!state.CanStart && state.Selected == null, "recovery after failure does not silently restore a selection");
            state.Select(original); var api = state.Current.Target.Api; var request = (HttpWebRequest)WebRequest.Create(api + "/api/sessions/" + original + "/commands"); request.Method = "POST"; request.Proxy = null; request.Timeout = 5000; request.ContentType = "application/json"; request.Headers[HttpRequestHeader.Authorization] = "Bearer " + ServerLauncher.Text(descriptor, "masterKey");
            var body = Encoding.UTF8.GetBytes(ServerLauncher.Json.Serialize(new { commandId = Guid.NewGuid().ToString("D"), action = "End" })); request.ContentLength = body.Length; using (var stream = request.GetRequestStream()) stream.Write(body, 0, body.Length); using (var response = request.GetResponse()) { }
            state.Load().GetAwaiter().GetResult(); Check(state.Loaded && state.Current.Choices.Count > 0 && state.Selected == null && !state.CanStart, "removed original choice never selects another room on refresh");
            original = state.Current.Choices[0].Id;
            state.Select(original); state.Edit(""); failed = false; try { state.Load().GetAwaiter().GetResult(); } catch (InvalidDataException) { failed = true; }
            Check(failed && !state.CanStart && state.Current == null, "empty path fails closed");
            ServerLauncher.Save(output, new { complete = true, checks = checks, scope = "Actual Framework catalog state, in-process WinForms message loop with held management responses, and Windows UDP socket owner/address/port checks. No desktop input, game readiness or headset proof." }); return 0;
        }
        catch (Exception e) { ServerLauncher.Save(output, new { complete = false, checks = checks, error = ServerLauncher.Safe(e) }); return 1; }
    }
}
