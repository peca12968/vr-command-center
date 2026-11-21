"""Real WebSocket publisher, authenticated SSE observation and SQLite restart checks."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import csv
from decimal import Decimal
import io
import json
import os
from pathlib import Path
import secrets
import sqlite3
import socket
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from uuid import uuid4
import urllib.error
import urllib.request

from world_test_socket import WebSocket
from local_api import api_command as resolve_api_command, checked_api_command
from windows_firewall import WindowsFirewallLaunchError, require_silent_windows_launch, start_checked_windows_process

ROOT = Path(__file__).resolve().parents[1]
api_exe = os.environ.get("VR_COMMAND_API_EXE")
use_ipc = os.name == "nt" and os.environ.get(
    "VR_COMMAND_WORLD_TEST_WINDOWS_IPC", os.environ.get("VR_COMMAND_UNATTENDED")
) == "1"
try:
    if not use_ipc:
        require_silent_windows_launch(sys.executable)
    resolve_api = resolve_api_command if use_ipc else checked_api_command
    api_command, api_cwd, _ = resolve_api(SimpleNamespace(api_exe=Path(api_exe) if api_exe else None))
except WindowsFirewallLaunchError as error:
    raise SystemExit(str(error)) from None
RELAY = os.environ.get("VR_COMMAND_WORLD_RELAY_DLL", str(ROOT / "tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll"))
RECOVERY = [os.environ["VR_COMMAND_RECOVERY_EXE"]] if "VR_COMMAND_RECOVERY_EXE" in os.environ else ["dotnet", RELAY]
count = 0


def check(condition, message):
    global count
    if not condition:
        raise AssertionError(message)
    count += 1
    print(f"PASS {count}: {message}")


with tempfile.TemporaryDirectory(prefix="vr-world-") as directory:
    directory = Path(directory)
    tokens = {role: secrets.token_hex(32) for role in ("Master", "Room1", "Room5", "GameServer")}
    keys = directory / "keys.json"
    keys.write_text(json.dumps({"OperatorKeys": tokens}), encoding="utf-8")
    if use_ipc:
        from windows_ipc_api import has_no_ip_endpoints, unix_address, unix_http_opener

        ipc_endpoint = directory / "api.sock"
        port = 18000
        open_http = unix_http_opener(lambda _port: ipc_endpoint).open
        relay_transport = ["--local-socket", str(ipc_endpoint)]
    else:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        open_http = urllib.request.urlopen
        relay_transport = []
    base = f"http://127.0.0.1:{port}"
    environment = {key: value for key, value in os.environ.items()
                   if not key.lower().startswith(("operatorkeys__", "kestrel__", "vr_command_managed_tls_"))
                   and key.lower() not in ("operatorkeyfile", "playerticketsigningkey")}
    environment.update({"DataDirectory": str(directory / "missions"), "SessionDataDirectory": str(directory / "sessions"), "OperatorKeyFile": str(keys), "Logging__LogLevel__Default": "Warning"})
    log = open(directory / "api.log", "wb")
    process = None
    demo = None

    def request(route, role="Master", expected=200, method="GET", body=None):
        req = urllib.request.Request(base + route, method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + tokens.get(role, role), "Content-Type": "application/json"})
        try:
            response = open_http(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        if response.status != expected:
            raise AssertionError(f"{route}: {response.status}, expected {expected}")
        if expected not in (200, 201):
            response.close()
            return None
        if response.headers.get_content_type() == "text/event-stream":
            return response
        with response:
            if response.headers.get_content_type() == "text/csv":
                return response.headers, response.read()
            return json.load(response)

    def start():
        launch = [*api_command, "--urls", base]
        if use_ipc:
            ipc_endpoint.unlink(missing_ok=True)
            launch = [*api_command, "--urls", "http://unix:/" + str(ipc_endpoint), "--preferHostingUrls", "true"]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        start_api = subprocess.Popen if use_ipc else start_checked_windows_process
        child = start_api(launch, cwd=api_cwd, env=environment, stdout=log, stderr=log, creationflags=flags)
        try:
            for _ in range(150):
                try:
                    with open_http(base + "/health", timeout=.5):
                        break
                except OSError:
                    if child.poll() is not None:
                        raise AssertionError("Isolated world API exited before health")
                    time.sleep(.1)
            else:
                raise AssertionError("Isolated world API startup timed out")
            if use_ipc and not has_no_ip_endpoints([child.pid]):
                raise AssertionError("The isolated IPC API must have zero TCP listeners and zero UDP endpoints")
            return child
        except BaseException:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
            raise

    def event(response):
        kind, data = "", ""
        for _ in range(10):
            line = response.readline().decode().strip()
            if line.startswith("event: "):
                kind = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
            elif not line and data:
                return kind, json.loads(data)
        raise AssertionError("Missing SSE event")

    def world_socket(route, token):
        return WebSocket(None if use_ipc else port, route, token,
                         ipc_address=unix_address(ipc_endpoint) if use_ipc else None)

    def next_live_event(response):
        for _ in range(5):
            item = event(response)
            if item[0] != "status":
                return item
        raise AssertionError("Only heartbeats arrived while waiting for the next live event")

    try:
        process = start()
        check(request("/api/world-recordings") == [], "No fabricated world recording appears at startup")
        request("/api/world-recordings", "invalid", 401)
        check(True, "World listing requires authentication")
        recording = directory / "world.ndjson"
        command = ["dotnet", RELAY, "--recording", str(recording), "--base-url", base, "--key-file", str(keys), *relay_transport]
        demo = subprocess.Popen(command + ["--demo-room", "5", "--seconds", "2"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        for _ in range(100):
            entries = request("/api/world-recordings")
            if entries and entries[0]["acceptedSequence"] > 1:
                break
            if demo.poll() is not None:
                raise AssertionError("World demo failed: " + demo.communicate()[1][-2000:])
            time.sleep(.05)
        info = entries[0]
        session = info["header"]["sessionId"]
        route = "/api/sessions/" + session + "/world"
        check(info["header"]["origin"] == "Simulation" and not info["complete"], "Live source explicitly identifies synthetic, incomplete data")
        live_clip = route + "/clips/" + str(uuid4())
        live_draft = {"streamId": info["header"]["streamId"], "name": "Live review", "startFrame": 1, "endFrame": 2}
        request(live_clip, method="PUT", body=live_draft)
        request(live_clip + "/player-replay.json", expected=409)
        request(live_clip, expected=204, method="DELETE")
        check(True, "An existing live clip cannot be exported before sealing")
        with request(route + "/watch", "Room5") as stream:
            kind, metadata = event(stream)
            kind2, live = event(stream)
            check(kind == "header" and kind2 == "frame" and live["packet"]["sequence"] > 1, "Scoped SSE observer receives an active world without a player admission")
        request(route, "Room1", 403)
        request(route + "/watch", "Room1", 403)
        request(route + "/publish", "Master", 403)
        request(route + "/publish", "Room5", 403)
        check(True, "Foreign room reads and operator world publication are rejected")
        check(request("/api/world-recordings", "Room1") == [], "World listing preserves room scope")
        publisher = world_socket(route + "/publish", tokens["GameServer"])
        check(publisher.send({"type": "header", "payload": info["header"]})["type"] == "ack", "Publisher may reconnect to the immutable header")
        check(publisher.send({"type": "seal", "finalSequence": info["acceptedSequence"]})["type"] == "error", "Running or undrained world cannot seal")
        publisher.close()
        stdout, stderr = demo.communicate(timeout=30)
        check(demo.returncode == 0, "Native WebSocket simulation completes: " + stderr[-500:])
        result = json.loads(stdout)
        frames = [json.loads(line) for line in recording.read_text(encoding="utf-8").splitlines()]
        info = request(route)
        check(info["header"]["environmentVersion"] == 1, "New world source explicitly versions its deterministic environment presentation")
        check(info["complete"] and info["acceptedSequence"] == result["frames"] == 44, "All ordered source frames durably seal after combat confirmation")
        session_route = "/api/sessions/" + session
        terminal = request(session_route)
        statistics_before_receipts = request(session_route + "/statistics")
        receipt_route = session_route + "/debrief-receipts"
        receipts_world = route + "?includeDebriefReceipts=true"
        unconfirmed = request(receipts_world)["debriefReceipts"]
        receipt_rows = unconfirmed["players"]
        check(receipt_rows and not any(row["acknowledged"] for row in receipt_rows)
              and "debriefReceipts" not in info, "A sealed recording without receipts keeps every terminal admission unconfirmed")
        batch = {key: unconfirmed[key] for key in ("streamId", "throughSequence", "finalStreamSequence", "worldSequence")}
        batch["players"] = [{key: receipt_rows[0][key] for key in ("playerId", "admissionId", "roomId")}]
        request(receipt_route, "Master", 403, "POST", batch)
        request(receipt_route, "Room5", 403, "POST", batch)
        request(receipts_world, "Room1", 403)
        request(receipts_world, "GameServer", 403)
        check(True, "Debrief receipt writes require the game-server identity and reads preserve room authorization")
        for key in ("throughSequence", "finalStreamSequence", "worldSequence"):
            request(receipt_route, "GameServer", 409, "POST", {**batch, key: batch[key] + 1})
        request(receipt_route, "GameServer", 409, "POST", {**batch, "streamId": str(uuid4())})
        request(receipt_route, "GameServer", 400, "POST", {**batch, "players": batch["players"] * 2})
        request(receipt_route, "GameServer", 409, "POST", {**batch, "players": [
            *batch["players"], {**batch["players"][0], "admissionId": str(uuid4())}]})
        check(request(receipts_world)["debriefReceipts"] == unconfirmed,
              "Wrong sealed boundaries and mixed invalid admission batches cannot record partial receipts")
        request(receipt_route, "GameServer", 204, "POST", batch)
        confirmed = request(receipts_world, "Room5")["debriefReceipts"]
        request(receipt_route, "GameServer", 204, "POST", batch)
        check(confirmed["players"] == [{**row, "acknowledged": index == 0} for index, row in enumerate(receipt_rows)]
              and request(receipts_world)["debriefReceipts"] == confirmed and request(route) == info
              and request(session_route) == terminal and request(session_route + "/statistics") == statistics_before_receipts,
              "Original admission receipt and idempotent retry preserve exact archive, session and statistics boundaries")
        endpoint_route = "/api/sessions/" + session + "/connection-endpoint"
        endpoint_draft = {"version": 1, "streamId": info["header"]["streamId"], "address": "127.0.0.1", "port": 17777}
        request(endpoint_route, "Room1", 403)
        request(endpoint_route, "GameServer", 403)
        request(endpoint_route, "Room5", 404)
        request(endpoint_route, "Master", 403, "PUT", endpoint_draft)
        check(True, "Endpoint metadata requires the correct reader scope and a source publisher")
        endpoint = request(endpoint_route, "GameServer", method="PUT", body=endpoint_draft)
        check(endpoint["version"] == 1 and endpoint["address"] == "127.0.0.1" and endpoint["port"] == 17777 and endpoint["sessionEnded"], "Owning source may preserve its declared endpoint as ended metadata without reopening gameplay")
        check(request(endpoint_route, "Room5") == endpoint and request(endpoint_route, "GameServer", method="PUT", body=endpoint_draft) == endpoint, "Endpoint reads and exact retries retain the source identity and original creation time")
        rooms_after_end = request("/api/rooms/readiness", "Room5")["rooms"]
        check(len(rooms_after_end) == 1 and rooms_after_end[0]["roomId"] == 5 and rooms_after_end[0]["sessionId"] is None
              and "endpoint" not in rooms_after_end[0], "A historical endpoint never returns to the scoped room overview")
        request(endpoint_route, "GameServer", 409, "PUT", {**endpoint_draft, "port": 17778})
        request(endpoint_route, "GameServer", 400, "PUT", {**endpoint_draft, "address": "0.0.0.0"})
        check(request(endpoint_route, "Room5") == endpoint, "Conflicting redirect and invalid wildcard leave the accepted endpoint unchanged")
        check(len(info["header"]["props"]) == 2, "World archive uses actual canonical mission geometry")
        check(any(player["rig"]["kind"] == "Simulated" for row in frames if row["type"] == "frame" for player in row["payload"]["frame"]["players"]), "Head and both hands retain explicit synthetic rig provenance")
        packets = [row["payload"] for row in frames if row["type"] == "frame"]
        combat_packet = next(packet for packet in packets if any(entry["kind"] == "PlayerDamaged" for entry in packet["events"]))
        exact_route = route + f"/frames/{combat_packet['sequence']}"
        exact = request(exact_route, "Room5")
        check(exact["packet"] == combat_packet and exact["statistics"][0]["health"] == 80,
              "Exact saved frame returns original events and statistics at the same boundary")
        request(exact_route, "Room1", 403)
        request(exact_route, "invalid", 401)
        request(route + "/frames/0", expected=400)
        request(route + f"/frames/{info['acceptedSequence'] + 1}", expected=404)
        check(True, "Exact frame reads retain authorization and reject invalid or missing frames")
        kill_packet, kill = next((packet, entry) for packet in packets for entry in packet["events"]
                                 if entry["kind"] == "EnemyEliminated")
        tail = info["acceptedSequence"]
        trace_route = route + "/shot-trace"
        trace_query = f"{trace_route}?fromFrame={kill_packet['sequence']}&throughFrame={tail}&eventId={kill['eventId']}"
        expected_trace = {"sessionId": info["header"]["sessionId"], "streamId": info["header"]["streamId"],
                          "fromFrame": kill_packet["sequence"], "throughFrame": tail, "eventId": kill["eventId"],
                          "shotId": kill["shotId"], "playerId": kill["playerId"], "roomId": 5,
                          "events": [{"eventId": entry["eventId"], "kind": entry["kind"], "frameSequence": packet["sequence"],
                                      "elapsedMilliseconds": packet["elapsedMilliseconds"], "roomId": 5}
                                     for packet in packets for entry in packet["events"] if entry["shotId"] == kill["shotId"]]}
        check(len(expected_trace["events"]) == 3 and request(trace_query, "Room5") == expected_trace,
              "A room controller's shot trace matches all original saved fire, hit and elimination records")
        request(trace_query + "&roomId=4", "Room5", 403)
        request(trace_query, "GameServer", 403)
        request(trace_query, "invalid", 401)
        request(trace_query.replace(kill["eventId"], str(uuid4())), expected=404)
        request(trace_query.replace(f"throughFrame={tail}", f"throughFrame={tail + 1}"), expected=404)
        request(trace_query.replace(f"throughFrame={tail}", "throughFrame=0"), expected=400)
        check(True, "Shot trace rejects foreign scopes, unauthorized readers, missing events and invalid saved boundaries")
        clip_route = route + "/clip-statistics"
        clip = f"{clip_route}?fromFrame={combat_packet['sequence']}&throughFrame={combat_packet['sequence']}"
        statistics = request(clip, "Room5")
        damaged = exact["statistics"][0]["playerId"]
        player_events = [event for event in combat_packet["events"] if event["playerId"] == damaged]
        fired = {event["shotId"] for event in player_events if event["kind"] == "ShotFired"}
        hits = [event["shotId"] for event in player_events if event["kind"] == "ShotHit"]
        damage = [event["damage"] for event in player_events if event["kind"] == "PlayerDamaged"]
        matched = len(fired.intersection(hits))
        check(statistics["roomId"] == 5 and statistics["streamId"] == info["header"]["streamId"]
              and request(clip + f"&playerId={damaged}", "Room5")["players"] == [{"playerId": damaged,
                  "name": exact["statistics"][0]["name"], "roomId": 5, "ammoUsed": len(fired), "shotsHit": len(hits),
                  "kills": sum(event["kind"] == "EnemyEliminated" for event in player_events),
                  "hitsReceived": len(damage), "damageTaken": sum(damage), "matchedShots": matched,
                  "accuracyPercent": round(100 * matched / len(fired), 2) if fired else None}]
              and request(f"{clip_route}?fromFrame=1&throughFrame=1")["players"] == [],
              "Clip statistics count exact original events at the inclusive boundaries and retain an empty clip")
        request(clip + "&roomId=4", "Room5", 403)
        request(clip, "GameServer", 403)
        request(clip, "invalid", 401)
        request(f"{clip_route}?fromFrame=2&throughFrame=1", expected=400)
        request(f"{clip_route}?fromFrame=1&throughFrame=301", expected=400)
        request(f"{clip_route}?fromFrame=1&throughFrame={info['acceptedSequence'] + 1}", expected=404)
        check(True, "Clip statistics enforce room authorization, ordered bounds and the saved archive tail")
        clip_csv = clip.replace("/clip-statistics?", "/clip-statistics.csv?") + f"&streamId={info['header']['streamId']}&playerId={damaged}"
        headers, raw = request(clip_csv, "Room5")
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
        row, = rows
        stat, = request(clip + f"&playerId={damaged}", "Room5")["players"]
        filename = (f"vr-command-clip-statistics-v1-{session}-{combat_packet['sequence']}-{combat_packet['sequence']}"
                    f"-room-05-player-{damaged}.csv")
        check(raw.startswith(b"\xef\xbb\xbf") and raw.endswith(b"\r\n") and headers["Cache-Control"] == "no-store"
              and headers["Content-Type"] == "text/csv; charset=utf-8" and filename in headers["Content-Disposition"]
              and (row["rowType"], row["sessionId"], row["streamId"], row["reportRoomId"], row["reportPlayerId"], row["playerId"])
                  == ("Player", session, info["header"]["streamId"], "5", damaged, damaged)
              and all(int(row[key]) == stat[key] for key in ("ammoUsed", "shotsHit", "matchedShots", "kills", "hitsReceived", "damageTaken"))
              and (None if row["accuracyPercent"] == "" else Decimal(row["accuracyPercent"]))
                  == (None if stat["accuracyPercent"] is None else Decimal(str(stat["accuracyPercent"])))
              and request(clip_csv, "Room5")[1] == raw and request(session_route) == terminal,
              "Clip CSV preserves exact read-only scope, counters and undefined accuracy from the saved prefix")
        _, complete_clip = request(f"{clip_route}.csv?fromFrame=1&throughFrame={tail}&streamId={info['header']['streamId']}")
        whole, = list(csv.DictReader(io.StringIO(complete_clip.decode("utf-8-sig"), newline="")))
        original = statistics_before_receipts["players"][0]
        check(whole["reportRoomId"] == "" and whole["reportPlayerId"] == "" and int(whole["ammoUsed"]) == original["ammoUsed"]
              and int(whole["shotsHit"]) == int(whole["matchedShots"]) == original["shotsHit"]
              and Decimal(whole["accuracyPercent"]) == Decimal(str(original["accuracyPercent"])),
              "Full saved clip CSV preserves the original hit numerator and percentage")
        _, empty_clip = request(f"{clip_route}.csv?fromFrame=1&throughFrame=1&streamId={info['header']['streamId']}")
        empty, = list(csv.DictReader(io.StringIO(empty_clip.decode("utf-8-sig"), newline="")))
        check(empty["rowType"] == "Clip" and empty["sessionId"] == session and empty["playerId"] == empty["ammoUsed"] == "",
              "An empty clip CSV preserves its original scope without an invented player or metric")
        request(clip_csv + "&roomId=4", "Room5", 403)
        request(clip_csv, "GameServer", 403)
        request(clip_csv, "invalid", 401)
        request(clip_csv.replace(info["header"]["streamId"], str(uuid4())), "Room5", 409)
        request(clip_csv.replace(f"&streamId={info['header']['streamId']}", ""), "Room5", 400)
        request(f"{clip_route}.csv?fromFrame=1&throughFrame=301&streamId={info['header']['streamId']}", expected=400)
        check(True, "Clip CSV rejects foreign scopes, unauthorized readers, wrong streams and invalid bounds")
        context_route = route + "/frame-context"
        center = combat_packet["sequence"]
        mark = lambda packet: {"sequence": packet["sequence"], "elapsedMilliseconds": packet["elapsedMilliseconds"]}
        eligible = [packet for packet in packets if abs(packet["elapsedMilliseconds"] - combat_packet["elapsedMilliseconds"]) <= 5000]
        expected_context = {"sessionId": session, "streamId": info["header"]["streamId"], "throughFrame": info["acceptedSequence"],
                            "center": mark(combat_packet), "start": mark(eligible[0]), "end": mark(eligible[-1])}
        check(request(f"{context_route}?centerFrame={center}&throughFrame={info['acceptedSequence']}", "Room5") == expected_context,
              "Frame context returns the original center and time bounds within the authorized recording")
        check(request(f"{context_route}?centerFrame={center}&throughFrame={center}") ==
              dict(expected_context, throughFrame=center, end=mark(combat_packet)) and
              request(f"{context_route}?centerFrame=1&throughFrame=1")["end"] == mark(packets[0]),
              "Frame context stays within a fixed saved prefix, including a one-frame prefix")
        request(f"{context_route}?centerFrame=0&throughFrame={center}", expected=400)
        request(f"{context_route}?centerFrame={center + 1}&throughFrame={center}", expected=400)
        request(f"{context_route}?centerFrame={center}&throughFrame={info['acceptedSequence'] + 1}", expected=404)
        request(f"{context_route}?centerFrame={center}&throughFrame={center}", "Room1", 403)
        request(f"{context_route}?centerFrame={center}&throughFrame={center}", "GameServer", 403)
        request(f"{context_route}?centerFrame={center}&throughFrame={center}", "invalid", 401)
        check(True, "Frame context rejects invalid ranges, missing frames and unauthorized roles")
        policy_route = route + "/policy-frames"
        tail = info["acceptedSequence"]
        policy = request(f"{policy_route}?throughFrame={tail}", "Room5")
        check(policy["sessionId"] == session and policy["streamId"] == info["header"]["streamId"]
              and policy["scannedThroughFrame"] == tail and policy["nextAfterFrame"] is None
              and policy["frames"][0]["changes"] == ["initial"] and policy["frames"][0]["frameSequence"] == 1
              and any(row["changes"] == ["environment"] and row["policy"]["weather"] == "Storm"
                      and row["policy"]["night"] and row["policy"]["lightning"] for row in policy["frames"])
              and policy["frames"][-1]["changes"] == ["phase"] and policy["frames"][-1]["policy"]["phase"] == "Ended",
              "Policy timeline indexes the original first and final states in the saved prefix")
        prefix = request(f"{policy_route}?throughFrame={tail - 1}")
        suffix = request(f"{policy_route}?throughFrame={tail}&afterFrame={tail - 1}")
        check(prefix["frames"] + suffix["frames"] == policy["frames"]
              and request(f"{policy_route}?throughFrame={tail}&afterFrame={tail}")["frames"] == [],
              "Policy cursor compares its first candidate with the previous saved frame and respects the fixed tail")
        environment_rows = [row for row in policy["frames"] if "environment" in row["changes"]]
        filtered = request(f"{policy_route}?throughFrame={tail}&change=environment", "Room5")
        change_frame = environment_rows[0]["frameSequence"]
        empty = request(f"{policy_route}?throughFrame={change_frame - 1}&change=environment", "Room5")
        at_change = request(f"{policy_route}?throughFrame={change_frame}&afterFrame={change_frame - 1}&change=environment", "Room5")
        check(filtered == dict(policy, change="environment", frames=environment_rows)
              and not empty["frames"] and empty["scannedThroughFrame"] == change_frame - 1
              and at_change["frames"] == environment_rows[:1],
              "Environment-only pages retain the exact saved transition and compare a cursor with its predecessor")
        request(f"{policy_route}?throughFrame={tail}&change=invalid", expected=400)
        request(f"{policy_route}?throughFrame={tail}&change=enemy-roster", expected=400)
        request(f"{policy_route}?throughFrame={tail}&change=environment", "Room1", 403)
        check(True, "Policy kind lookup rejects invalid filters and retains recording permissions")
        policy_neighbor = route + "/policy-neighbor"
        seek = f"{policy_neighbor}?throughFrame={tail}&change=environment"
        prev = request(seek + f"&direction=previous&fromFrame={tail}", "Room5")
        following = request(seek + f"&direction=next&fromFrame={change_frame - 1}", "Room5")
        no_repeat = request(seek + f"&direction=previous&fromFrame={change_frame}", "Room5")
        check(prev["frame"] == following["frame"] == environment_rows[0]
              and prev["scannedToFrame"] == following["scannedToFrame"] == change_frame
              and prev["nextFromFrame"] is None and no_repeat["frame"] is None and no_repeat["scannedToFrame"] == 1,
              "Policy neighbors match the original adjacent transition in either direction and exclude the current frame")
        inclusive = request(f"{policy_neighbor}?throughFrame={change_frame}&change=environment"
                            f"&direction=previous&includeFrom=true&fromFrame={change_frame}", "Room5")
        first = request(f"{policy_neighbor}?throughFrame=1&direction=previous&includeFrom=true&fromFrame=1&change=initial", "Room5")
        check(inclusive["includeFrom"] is True and inclusive["frame"] == environment_rows[0]
              and inclusive["scannedToFrame"] == change_frame and inclusive["nextFromFrame"] is None
              and first["frame"] == policy["frames"][0] and first["nextFromFrame"] is None
              and "includeFrom" not in prev,
              "Inclusive previous lookup can match the fixed tail or first saved frame without changing the adjacent query")
        request(seek + "&direction=sideways&fromFrame=1", expected=400)
        request(seek + "&direction=next&fromFrame=1&includeFrom=true", expected=400)
        request(seek + f"&direction=next&fromFrame={tail + 1}", expected=400)
        request(seek + "&direction=next&fromFrame=1", "Room1", 403)
        request(f"{policy_neighbor}?throughFrame={tail + 1}&direction=next&fromFrame=1", expected=404)
        check(True, "Policy neighbors reject invalid cursors and retain recording authorization")
        request(f"{policy_route}?throughFrame={tail}&afterFrame=-1", expected=400)
        request(f"{policy_route}?throughFrame={tail + 1}", expected=404)
        request(f"{policy_route}?throughFrame={tail}", "Room1", 403)
        request(f"{policy_route}?throughFrame={tail}", "invalid", 401)
        check(True, "Policy lookup rejects invalid bounds and retains archive authorization")
        roster_route = f"{policy_route}?throughFrame={tail}&includeEnemyRoster=true"
        scoped = request(roster_route + "&roomId=5", "Room5")
        unscoped = request(roster_route)
        check("includeEnemyRoster" not in policy and "roomId" not in policy
              and all("enemyRoster" not in row for row in policy["frames"])
              and scoped["includeEnemyRoster"] and scoped["roomId"] == 5
              and unscoped["includeEnemyRoster"] and "roomId" not in unscoped and scoped["frames"] == unscoped["frames"],
              "Roster projection is opt-in and the single recorded room matches the all-room projection")
        for row in scoped["frames"]:
            index = row["frameSequence"] - 1
            enemies = packets[index]["frame"]["enemies"]
            ids = {enemy["id"] for enemy in enemies}
            previous = {enemy["id"] for enemy in packets[index - 1]["frame"]["enemies"]} if index else ids
            assert row["enemyRoster"] == {"enemyIds": sorted(ids), "alive": sum(enemy["health"] > 0 for enemy in enemies),
                                          "added": len(ids - previous), "removed": len(previous - ids)}
        check(True, "Roster rows report original saved identities and living count")
        request(roster_route + "&roomId=1", expected=400)
        request(roster_route + "&roomId=5", "Room1", 403)
        request(f"{policy_route}?throughFrame={tail}&roomId=5", expected=400)
        request(f"{policy_route}?throughFrame={tail}&includeEnemyRoster=invalid", expected=400)
        check(True, "Roster lookup rejects out-of-recording rooms and retains authorization")
        search = route + "/event-frames"
        boundary = combat_packet["sequence"]
        page = request(f"{search}?throughFrame={boundary}&roomId=5&kind=PlayerDamaged", "Room5")
        damage_ids = [event["eventId"] for event in combat_packet["events"] if event["kind"] == "PlayerDamaged"]
        check(page == {"sessionId": session, "streamId": info["header"]["streamId"], "throughFrame": boundary,
                       "afterFrame": 0, "scannedThroughFrame": boundary, "nextAfterFrame": None,
                       "playerId": None, "roomId": 5, "kind": "PlayerDamaged",
                       "frames": [{"frameSequence": boundary, "elapsedMilliseconds": combat_packet["elapsedMilliseconds"],
                                   "matchCount": len(damage_ids), "eventIds": damage_ids}]},
              "Room and kind search returns the exact saved damage frame and event IDs at an inclusive prefix limit")
        earlier = request(f"{search}?throughFrame={boundary - 1}&kind=PlayerDamaged")
        exhausted = request(f"{search}?throughFrame={boundary}&afterFrame={boundary}")
        check(not earlier["frames"] and earlier["scannedThroughFrame"] == boundary - 1 and not exhausted["frames"]
              and exhausted["scannedThroughFrame"] == boundary and exhausted["nextAfterFrame"] is None,
              "An earlier fixed prefix cannot see later saved damage and an exhausted cursor stays at the tail")
        for suffix, status in [("", 400), ("&roomId=1", 400), ("&kind=0", 400), ("&afterFrame=-1", 400),
                               (f"&afterFrame={boundary + 1}", 400), (f"&afterFrame={boundary}&kind=", 400)]:
            request(search + (f"?throughFrame={boundary}{suffix}" if suffix else ""), expected=status)
        request(f"{search}?throughFrame={info['acceptedSequence'] + 1}", expected=404)
        request(f"{search}?throughFrame={boundary}", "Room1", 403)
        request(f"{search}?throughFrame={boundary}", "invalid", 401)
        check(True, "Event search rejects invalid filters, missing frames and unauthorized readers")
        player_id = exact["statistics"][0]["playerId"]
        player_search = f"{search}?throughFrame={boundary}&roomId=5&kind=PlayerDamaged&playerId="
        check(request(player_search + player_id, "Room5") == dict(page, playerId=player_id)
              and request(player_search + str(uuid4()), "Room5")["frames"] == [],
              "Player search intersects room and kind by stable saved player ID")
        request(player_search + "00000000-0000-0000-0000-000000000000", "Room5", 400)
        request(player_search + "not-an-id", "Room5", 400)
        request(player_search + player_id, "Room1", 403)
        check(True, "Player search rejects malformed IDs and retains original recording permissions")
        neighbor = route + "/event-neighbor"
        filters = f"&roomId=5&kind=PlayerDamaged&playerId={player_id}"
        tail = info['acceptedSequence']
        previous = request(f"{neighbor}?throughFrame={tail}&fromFrame={tail}&direction=previous{filters}", "Room5")
        following = request(f"{neighbor}?throughFrame={tail}&fromFrame=1&direction=next{filters}", "Room5")
        check(previous["frame"] == following["frame"] == page["frames"][0]
              and previous["scannedToFrame"] == following["scannedToFrame"] == boundary
              and all(value["nextFromFrame"] is None and value["playerId"] == player_id and value["roomId"] == 5
                      and value["streamId"] == info["header"]["streamId"] for value in (previous, following)),
              "Directional navigation finds the exact same saved frame in either direction")
        missing = request(f"{neighbor}?throughFrame={boundary}&fromFrame={boundary}&direction=previous{filters}")
        capped = request(f"{neighbor}?throughFrame={boundary - 1}&fromFrame=1&direction=next{filters}")
        check(missing["frame"] is None and missing["scannedToFrame"] == 1 and missing["nextFromFrame"] is None
              and capped["frame"] is None and capped["scannedToFrame"] == boundary - 1 and capped["nextFromFrame"] is None,
              "Directional navigation excludes the current frame and respects a fixed saved prefix")
        for params in (f"fromFrame=0&throughFrame={tail}&direction=previous", f"fromFrame=1&throughFrame={tail}&direction=back",
                       f"fromFrame={tail}&throughFrame=1&direction=next", f"fromFrame=1&throughFrame={tail}&direction=next&roomId=1"):
            request(f"{neighbor}?{params}", expected=400)
        request(f"{neighbor}?fromFrame=1&throughFrame={tail + 1}&direction=next", expected=404)
        request(f"{neighbor}?fromFrame=1&throughFrame={tail}&direction=next", "Room1", 403)
        check(True, "Directional navigation rejects invalid bounds, direction and foreign recording access")
        with request(route + f"/watch?mode=replay&fromFrame={combat_packet['sequence']}&rate=4", "Room5") as stream:
            check(event(stream)[0] == "header" and event(stream) == ("frame", exact),
                  "Resuming by frame starts on the same exact packet as a single-frame read")
            check(event(stream)[1]["packet"]["sequence"] == combat_packet["sequence"] + 1,
                  "Exact replay continues in stored sequence order")
        request(route + "/watch?mode=replay&fromFrame=1&fromMs=0", expected=400)
        request(route + "/watch?mode=live&fromFrame=1", expected=400)
        request(route + "/watch?mode=replay&fromFrame=0", expected=400)
        request(route + f"/watch?mode=replay&fromFrame={info['acceptedSequence'] + 1}", expected=404)
        check(True, "Exact replay refuses invalid or ambiguous seek parameters")
        limit = combat_packet["sequence"]
        with request(route + f"/watch?mode=replay&throughFrame={limit}&rate=4", "Room5") as stream:
            check(event(stream)[0] == "header" and event(stream)[1]["packet"] == packets[0],
                  "Saved replay without a seek starts from sequence one")
        with request(route + f"/watch?mode=replay&fromMs=86400000&throughFrame={limit}&rate=4", "Room5") as stream:
            kind, prefix = event(stream)
            check(kind == "header" and not prefix["complete"] and prefix["acceptedSequence"] == limit
                  and prefix["durationMilliseconds"] == combat_packet["elapsedMilliseconds"],
                  "Saved replay caps sequence and time even when a later sealed archive exists")
            check(event(stream) == ("frame", exact) and event(stream) == ("saved-end", prefix) and stream.read() == b"",
                  "A seek beyond the saved range stops on the exact saved tail and closes without a seal event")
        with request(route + f"/watch?mode=replay&fromFrame={info['acceptedSequence']}&throughFrame=latest", "Room5") as stream:
            check(event(stream) == ("header", info) and event(stream)[1]["packet"]["sequence"] == info["acceptedSequence"]
                  and event(stream) == ("saved-end", info), "A saved range covering a sealed archive retains its actual seal")
        request(route + "/watch?mode=live&throughFrame=latest", expected=400)
        request(route + "/watch?mode=replay&throughFrame=0", expected=400)
        request(route + f"/watch?mode=replay&throughFrame={info['acceptedSequence'] + 1}", expected=404)
        request(route + f"/watch?mode=replay&throughFrame={limit}&fromFrame={limit + 1}", expected=404)
        request(route + "/watch?mode=replay&throughFrame=latest", "Room1", 403)
        check(True, "Saved replay rejects invalid bounds, unsupported modes and foreign-room access")
        seek_ms = packets[5]["elapsedMilliseconds"]
        expected_seek = [packet for packet in packets if packet["elapsedMilliseconds"] <= seek_ms][-1]
        with request(route + f"/watch?mode=replay&fromMs={seek_ms}&rate=4") as stream:
            check(event(stream)[0] == "header", "Persisted replay starts with versioned metadata")
            replay = []
            while True:
                kind, data = event(stream)
                if kind == "frame":
                    replay.append(data)
                if kind == "complete":
                    break
            evidence = {"requestedMilliseconds": seek_ms, "expectedSequence": expected_seek["sequence"],
                        "actualSequence": replay[0]["packet"]["sequence"], "actualMilliseconds": replay[0]["packet"]["elapsedMilliseconds"],
                        "storedTimestamps": [{"sequence": p["sequence"], "milliseconds": p["elapsedMilliseconds"]} for p in packets]}
            (ROOT / "artifacts").mkdir(exist_ok=True)
            (ROOT / "artifacts/world-smoke-seek.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            check(replay[0]["packet"]["elapsedMilliseconds"] <= seek_ms and replay[0]["packet"]["sequence"] == expected_seek["sequence"] > 1, "Indexed replay seeks to the exact preceding stored frame")
            final = replay[-1]
            stats = final["statistics"][0]
            check(final["packet"]["frame"]["phase"] == "Ended" and final["packet"]["weather"] == "Storm" and final["packet"]["frame"]["night"], "Replay retains pause, environment changes and the final world")
            check(stats["ammoUsed"] == 2 and stats["kills"] == 1 and stats["health"] == 80, "Frame statistics agree with actual recorded combat")
        publisher = world_socket(route + "/publish", tokens["GameServer"])
        publisher.send(frames[0])
        check(publisher.send(frames[1])["info"]["acceptedSequence"] == 44, "Late exact frame retry confirms the original record after sealing")
        altered = json.loads(json.dumps(frames[1]))
        altered["payload"]["frame"]["players"][0]["health"] = 1
        check(publisher.send(altered)["type"] == "error", "Conflicting retry cannot overwrite an accepted frame")
        publisher.close()
        publisher = world_socket(route + "/publish", tokens["GameServer"])
        check(publisher.send(frames[1])["type"] == "error", "Each new socket must establish its header before frames")
        publisher.close()
        request(route + "/watch?rate=999", expected=400)
        request(route + "/watch?fromMs=-1", expected=400)
        check(True, "Unbounded replay speed and invalid seeks are rejected")
        unsupported_header = json.loads(json.dumps(info["header"]))
        unsupported_header["environmentVersion"] = 2
        publisher = world_socket(route + "/publish", tokens["GameServer"])
        check(publisher.send({"type": "header", "payload": unsupported_header})["type"] == "error", "Unknown environment versions cannot publish a world")
        publisher.close()
        unsupported_header["environmentVersion"] = 0
        publisher = world_socket(route + "/publish", tokens["GameServer"])
        check(publisher.send({"type": "header", "payload": unsupported_header})["type"] == "error", "Existing versioned world cannot be relabeled as a legacy presentation")
        publisher.close()
        cameras = route + "/cameras"
        camera_id = str(uuid4())
        camera_route = cameras + "/" + camera_id
        camera = {"name": "East <sandbags>", "view": {"target": [28, .8, 0], "theta": .6, "phi": .9, "radius": 15}}
        request(cameras, "invalid", 401)
        request(cameras, "Room1", 403)
        request(camera_route, "Room1", 403, "PUT", camera)
        request(camera_route, "Room1", 403, "DELETE")
        request(cameras, "GameServer", 403)
        request(camera_route, "GameServer", 403, "PUT", camera)
        check(True, "Camera HTTP reads and mutations enforce authentication, room scope and operator role")
        saved_camera = request(camera_route, method="PUT", body=camera)
        check(request(camera_route, method="PUT", body=camera) == saved_camera and request(cameras) == [saved_camera], "Camera HTTP retry preserves the exact saved view and creation time")
        request(camera_route, expected=409, method="PUT", body={**camera, "name": "changed"})
        request(camera_route + "bad", expected=404, method="PUT", body=camera)
        invalid_view = {**camera, "view": {**camera["view"], "target": [999, 0, 0]}}
        request(cameras + "/" + str(uuid4()), expected=400, method="PUT", body=invalid_view)
        check(True, "Camera HTTP rejects conflicting identity, invalid IDs and unbounded targets")
        check(request(cameras, "Room5") == [], "Camera positions are private to the current authenticated operator identity")
        request(camera_route, "Room5", 404, "DELETE")
        room_camera = request(camera_route, "Room5", method="PUT", body={**camera, "name": "Room view"})
        check(request(cameras) == [saved_camera] and request(cameras, "Room5") == [room_camera], "Same camera ID cannot overwrite another operator's position")
        request(camera_route, expected=204, method="DELETE")
        request(camera_route, expected=204, method="DELETE")
        check(request(camera_route, method="PUT", body=camera)["deleted"] and request(cameras) == [], "Late camera save and remove retries do not resurrect a removed position")
        clips = route + "/clips"
        clip_id = str(uuid4())
        clip_route = clips + "/" + clip_id
        player_replay_route = clip_route + "/player-replay.json"
        clip = {"streamId": info["header"]["streamId"], "name": "Cover review", "startFrame": 2, "endFrame": 6}
        request(clips, "invalid", 401)
        request(clips, "Room1", 403)
        request(clips, "GameServer", 403)
        request(clip_route, "Room5", 403, "PUT", clip)
        request(clip_route, "Room5", 403, "DELETE")
        request(clip_route, "GameServer", 403, "PUT", clip)
        check(True, "Shared replay clips require recording scope to read and Master authority to change")
        request(clip_route, expected=409, method="PUT", body={**clip, "streamId": str(uuid4())})
        request(clip_route, expected=400, method="PUT", body={**clip, "startFrame": 6})
        request(clip_route, expected=400, method="PUT", body={**clip, "endFrame": info["acceptedSequence"] + 1})
        request(clip_route, expected=400, method="PUT", body={**clip, "name": " bad "})
        check(True, "Shared clips reject another source, reversed or unsaved bounds and invalid names")
        saved_clip = request(clip_route, method="PUT", body=clip)
        clip_list = {"sessionId": session, "streamId": clip["streamId"], "clips": [saved_clip]}
        check(saved_clip["id"] == clip_id and not saved_clip["deleted"]
              and saved_clip["startMilliseconds"] == packets[1]["elapsedMilliseconds"]
              and saved_clip["endMilliseconds"] == packets[5]["elapsedMilliseconds"]
              and request(clip_route, method="PUT", body=clip) == saved_clip
              and request(clips) == request(clips, "Room5") == clip_list,
              "Both operators read the same stored interval with exact frame times and idempotent identity")
        for role, status in (("invalid", 401), ("Room5", 403), ("Room1", 403), ("GameServer", 403)):
            request(player_replay_route, role, status)
        player_replay = request(player_replay_route)
        check(set(player_replay) == {"playerReplayVersion", "header", "missionName", "clipName", "startFrame", "endFrame", "packets"}
              and player_replay["playerReplayVersion"] == 1 and player_replay["header"] == info["header"]
              and player_replay["clipName"] == clip["name"] and player_replay["missionName"] == info["missionName"]
              and [player_replay["startFrame"], player_replay["endFrame"]] == [2, 6]
              and player_replay["packets"] == [request(f"{route}/frames/{sequence}")["packet"] for sequence in range(2, 7)],
              "Master exports exact original inclusive frames without the private statistics")
        scoped_route = player_replay_route + "?roomId=5"
        scoped = request(scoped_route)
        check(scoped["playerReplayVersion"] == 2 and scoped["roomId"] == 5 and scoped["header"] == player_replay["header"]
              and [row["sequence"] for row in scoped["packets"]] == [2, 3, 4, 5, 6]
              and [row["elapsedMilliseconds"] for row in scoped["packets"]] ==
              [row["elapsedMilliseconds"] for row in player_replay["packets"]]
              and all("observedSequence" not in row and "throughCombatSequence" not in row
                      and "throughSequence" not in row["frame"] and all("sequence" not in event for event in row["events"])
                      for row in scoped["packets"]),
              "Room export preserves the inclusive saved frames and time without global counters")
        request(scoped_route, "Room5", 403)
        request(player_replay_route + "?roomId=1", expected=400)
        request(player_replay_route + "?roomId=0", expected=400)
        check(request(player_replay_route) == player_replay and request(route)["header"] == info["header"],
              "Room export leaves the original recording and full player file unchanged")
        request(clips + "/" + str(uuid4()) + "/player-replay.json", expected=404)
        request(clip_route, expected=409, method="PUT", body={**clip, "endFrame": 7})
        other_clips = [clips + "/" + str(uuid4()) for _ in range(23)]
        for other in other_clips:
            request(other, method="PUT", body=clip)
        request(clips + "/" + str(uuid4()), expected=409, method="PUT", body=clip)
        check(len(request(clips)["clips"]) == 24 and request(clip_route, method="PUT", body=clip) == saved_clip,
              "The 24-clip limit still permits exact retries")
        for other in other_clips:
            request(other, expected=204, method="DELETE")
        request(other_clips[0] + "/player-replay.json", expected=404)
        request(other_clips[0], expected=204, method="DELETE")
        check(request(other_clips[0], method="PUT", body=clip)["deleted"] and request(clips) == clip_list,
              "Removing clips leaves the original frames readable and late retries cannot recreate a removed clip")

        # Publish a separate controlled round without session-specific props.
        damage_mission = request("/api/missions", expected=201, method="POST",
                                 body=dict(terminal["mission"]["definition"], props=[]))
        room_ids = [1, 2, 3, 4, 5]
        overkill = request("/api/sessions", expected=201, method="POST", body={"missionId": damage_mission["id"],
                           "mode": "Linked", "roomIds": room_ids})
        overkill_id = overkill["id"]
        overkill_session = f"/api/sessions/{overkill_id}"
        overkill_world = overkill_session + "/world"
        damage_stream = str(uuid4())
        damage_player = str(uuid4())
        other_player = str(uuid4())
        spreadsheet_name = ' =HYPERLINK("test","fixture")\r\nline two'
        request(overkill_session + "/players", method="POST", body={"playerId": damage_player,
                "name": spreadsheet_name, "roomId": 5, "headset": "Quest3"})
        request(overkill_session + "/players", method="POST", body={"playerId": other_player,
                "name": "Other room fixture", "roomId": 1, "headset": "Quest3"})
        request(overkill_session + "/combat-stream", "GameServer", method="POST",
                body={"streamId": damage_stream, "origin": "Simulation"})
        damage_header = dict(info["header"], sessionId=overkill_id, streamId=damage_stream, roomIds=room_ids, props=[])
        damage_template = next(entry for entry in combat_packet["events"] if entry["kind"] == "PlayerDamaged")

        def damage_frame(number, combat_sequence, phase, observed, health, events=()):
            packet = deepcopy(packets[0])
            packet.update(sequence=number, elapsedMilliseconds=(number - 1) * 50, observedSequence=observed,
                          throughCombatSequence=combat_sequence, events=list(events))
            packet["frame"].update(tick=number - 1, phase=phase, throughSequence=combat_sequence)
            packet["frame"]["players"][0].update(id=damage_player, health=health)
            other_body = deepcopy(packets[0]["frame"]["players"][0])
            other_body.update(id=other_player, roomId=1)
            for point in ("head", "muzzle"):
                other_body[point]["x"] -= 56
            packet["frame"]["players"].append(other_body)
            return packet

        damage_publisher = world_socket(overkill_world + "/publish", tokens["GameServer"])
        try:
            reply = damage_publisher.send({"type": "header", "payload": damage_header})
            assert reply["type"] == "ack", reply
            initial_damage_frame = damage_frame(1, 0, "Preparing", request(overkill_session)["sequence"], 100)
            reply = damage_publisher.send({"type": "frame", "payload": initial_damage_frame})
            assert reply["type"] == "ack", reply
            begin = request(overkill_session + "/commands", method="POST",
                            body={"commandId": str(uuid4()), "action": "Begin"})["session"]["sequence"]
            for position, (raw, health) in enumerate([(50, 50), (90, 0)], 1):
                event_id = str(uuid4())
                request(overkill_session + "/combat-stream/batch", "GameServer", method="POST", body=[{
                    "streamId": damage_stream, "streamSequence": position, "observedSequence": begin,
                    "report": {"reportId": event_id, "kind": "PlayerDamaged", "origin": "Simulation",
                               "playerId": damage_player, "damage": raw}}])
                entry = dict(damage_template, sequence=position, tick=position, eventId=event_id,
                             playerId=damage_player, damage=raw)
                if position == 1:
                    entry["targetId"] = other_player  # Source retains this event; the Room 5 projection omits it.
                packet = damage_frame(position + 1, position, "Running", begin, health, [entry])
                reply = damage_publisher.send({"type": "frame", "payload": packet})
                assert reply["type"] == "ack", reply
            request(overkill_world + "/watch?mode=live&observerRoomId=5", "Room1", 403)
            with request(overkill_world + "/watch?mode=live&observerRoomId=1", "Room1") as live_room:
                kind, scoped_header = event(live_room)
                next_kind, scoped_frame = event(live_room)
                check(kind == "header" and scoped_header.get("observerRoomId") == 1
                      and next_kind == "frame" and scoped_frame.get("observerRoomId") == 1 and scoped_frame["packet"]["sequence"] == 3
                      and [body["id"] for body in scoped_frame["packet"]["frame"]["players"]] == [other_player]
                      and scoped_frame["packet"]["frame"]["enemies"] == [] and scoped_frame["packet"]["events"] == []
                      and [row["playerId"] for row in scoped_frame["statistics"]] == [other_player],
                      "Linked live room access omits foreign bodies, enemies, events and statistics")
                end = request(overkill_session + "/commands", method="POST",
                              body={"commandId": str(uuid4()), "action": "End"})["session"]["sequence"]
                request(overkill_session + "/combat-stream/seal", "GameServer", method="POST",
                        body={"streamId": damage_stream, "finalSequence": 2})
                terminal_damage_frame = damage_frame(4, 2, "Ended", end, 0)
                reply = damage_publisher.send({"type": "frame", "payload": terminal_damage_frame})
                assert reply["type"] == "ack", reply
                terminal_frame = request(overkill_world + "/frames/4?observerRoomId=1", "Room1")
                check(next_live_event(live_room) == ("frame", terminal_frame) and not reply["info"]["complete"],
                      "A scoped live viewer receives the Ended frame while the recording awaits sealing")
                sealed = damage_publisher.send({"type": "seal", "finalSequence": 4})
                assert sealed["type"] == "ack", sealed
                check(sealed["info"]["complete"],
                      "A recorded overkill seals through the original WebSocket publisher after combat seal")
                scoped_seal = request(overkill_world + "?observerRoomId=1", "Room1")
                check(next_live_event(live_room) == ("complete", scoped_seal) and live_room.readline() == b"",
                      "An active scoped live stream sends its original seal and closes without duplicating the last frame")
        finally:
            damage_publisher.close()
        with request(overkill_world + "/watch") as sealed_live:
            check(event(sealed_live) == ("header", sealed["info"])
                  and event(sealed_live) == ("frame", request(overkill_world + "/frames/4"))
                  and event(sealed_live) == ("complete", sealed["info"]) and sealed_live.readline() == b"",
                  "Opening a sealed full observation returns exactly its final frame and its seal, then closes")
        damage_stats = request(overkill_session + "/statistics")["players"]
        damage_stats = [row for row in damage_stats if row["playerId"] == damage_player]
        damage_view = request(overkill_world + "/frames/3?observerRoomId=5", "Room5")
        damage_clip = request(overkill_world + "/clip-statistics?fromFrame=3&throughFrame=3", "Room5")["players"]
        check(damage_view["packet"]["events"][0]["damage"] == 90 and damage_view["statistics"] == damage_stats
              and damage_stats[0]["damageTaken"] == 100 and damage_stats[0]["health"] == 0
              and damage_clip[0]["damageTaken"] == 50 and damage_clip[0]["hitsReceived"] == 1,
              "The scoped replay retains the original hit but reports the same actual health loss as final statistics")
        _, safe_clip = request(overkill_world + f"/clip-statistics.csv?fromFrame=3&throughFrame=3&streamId={damage_stream}", "Room5")
        safe, = list(csv.DictReader(io.StringIO(safe_clip.decode("utf-8-sig"), newline="")))
        check(safe["playerName"] == "'" + spreadsheet_name and damage_clip[0]["name"] == spreadsheet_name
              and safe["reportRoomId"] == safe["playerRoomId"] == "5" and safe["damageTaken"] == "50" and safe["accuracyPercent"] == "",
              "Scoped clip CSV protects formula text and preserves actual loss, quotes and line breaks")
        master_frame = request(overkill_world + "/frames/3")
        other_frame = request(overkill_world + "/frames/3?observerRoomId=1", "Room1")
        listed = next(record for record in request("/api/world-recordings", "Room5") if record["header"]["sessionId"] == overkill_id)
        scope_info = request(overkill_world + "?observerRoomId=5", "Room5")
        request(overkill_world + "/frames/3?observerRoomId=5", "Room1", 403)
        check({body["id"] for body in master_frame["packet"]["frame"]["players"]} == {damage_player, other_player}
              and request(overkill_world + "/frames/3", "Room1") == master_frame
              and damage_view["packet"]["events"] == master_frame["packet"]["events"]
              and [body["id"] for body in damage_view["packet"]["frame"]["players"]] == [damage_player]
              and other_frame == scoped_frame and listed == request(overkill_world, "Room5")
              and scope_info["observerRoomId"] == 5 and scope_info["header"]["roomIds"] == room_ids,
              "Explicit exact reads are room scoped while the shared observation still returns the full Linked frame")
        with request(overkill_world + "/watch?mode=replay&fromFrame=3&throughFrame=3&observerRoomId=5", "Room5") as replay_room:
            kind, replay_info = event(replay_room)
            check(kind == "header" and replay_info["observerRoomId"] == 5 and event(replay_room) == ("frame", damage_view)
                  and event(replay_room)[0] == "saved-end", "Room replay uses the same projection through the original saved boundary")
        event_path = overkill_world + "/event-frames?throughFrame=4&kind=PlayerDamaged"
        legacy_search = request(event_path + "&roomId=5", "Room5")
        scoped_search = request(event_path + "&observerRoomId=5", "Room5")
        check([row["frameSequence"] for row in legacy_search["frames"]] == [2, 3]
              and request(overkill_world + "/frames/2?observerRoomId=5", "Room5")["packet"]["events"] == []
              and scoped_search["frames"] == legacy_search["frames"][1:] and scoped_search.get("observerRoomId") == 5
              and scoped_search["roomId"] == 5 and scoped_search["kind"] == "PlayerDamaged"
              and scoped_search["frames"][0]["eventIds"] == [entry["eventId"] for entry in damage_view["packet"]["events"]
                                                             if entry["kind"] == "PlayerDamaged"]
              and request(event_path + "&observerRoomId=1", "Room1")["frames"] == [],
              "Projected event search omits an event that belongs to the room player but is absent from the projected frame")
        neighbor_path = overkill_world + "/event-neighbor?throughFrame=4&kind=PlayerDamaged"
        for direction, start_frame in [("next", 1), ("previous", 4)]:
            found = request(neighbor_path + f"&fromFrame={start_frame}&direction={direction}&observerRoomId=5", "Room5")
            check(found["observerRoomId"] == found["roomId"] == 5 and found["frame"] == scoped_search["frames"][0],
                  f"Projected {direction} navigation matches the exact scoped search and skips the omitted event")
        for url in [event_path, neighbor_path + "&fromFrame=1&direction=next"]:
            request(url + "&observerRoomId=5", "Room1", 403)
            request(url + "&observerRoomId=5&roomId=1", "Room5", 400)
        check(True, "Projected event lookup rejects a foreign observation room and conflicting room filters")
        policy_roster = overkill_world + "/policy-frames?throughFrame=4&includeEnemyRoster=true"
        local_roster = request(policy_roster + "&roomId=1", "Room1")
        check(local_roster["roomId"] == 1 and all(not row["enemyRoster"]["enemyIds"] for row in local_roster["frames"])
              and any(row["enemyRoster"]["enemyIds"] for row in request(policy_roster)["frames"]),
              "The room-selected policy timeline returns the local enemy roster while the shared one retains all rooms")
        process.terminate()
        process.wait(timeout=10)
        # A pre-v0.16 fixture: same known frames and source, header stored before the new optional field existed.
        legacy_header = {key: value for key, value in info["header"].items() if key != "environmentVersion"}
        legacy_db = sqlite3.connect(directory / "sessions/worlds.db")
        try:
            with legacy_db:
                legacy_db.execute("UPDATE recordings SET header=? WHERE session=?", (json.dumps(legacy_header, separators=(",", ":")), session))
        finally:
            legacy_db.close()
        frames[0]["payload"] = legacy_header
        recording.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in frames), encoding="utf-8")
        info["header"]["environmentVersion"] = 0
        process = start()
        check(request(route) == info, "SQLite restart restores recording identity, cursor, time and completion")
        check(request(receipts_world)["debriefReceipts"] == confirmed, "SQLite restart retains the original debrief receipt")
        check(request(exact_route, "Room5") == exact, "The exact event frame and its statistics remain identical after restart")
        check(request(trace_query, "Room5") == expected_trace, "Restart reconstructs shot report links from the existing persisted session")
        check(request(f"{search}?throughFrame={boundary}&roomId=5&kind=PlayerDamaged", "Room5") == page,
              "Search reconstructs the same result after restart using the existing archive")
        check(request(route)["header"]["environmentVersion"] == 0, "Pre-versioned stored headers remain explicitly legacy instead of acquiring invented effects")
        check(request(cameras) == [] and request(cameras, "Room5") == [room_camera]
              and request(camera_route, method="PUT", body=camera)["deleted"], "SQLite restart preserves saved camera positions and removal history without changing world metadata")
        check(request(clips, "Room5") == clip_list and request(other_clips[0], method="PUT", body=clip)["deleted"],
              "SQLite restart preserves the shared clip and its deleted neighbors")
        recovery = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        check(recovery.returncode == 0 and json.loads(recovery.stdout)["complete"], "A second native process replays the full saved source idempotently")
        check(request(route) == info, "Whole-source retry changes no frame or archive metadata")
        check(request("/api/sessions/" + session)["players"][0]["name"] == "World Simulation", "Observer creates no extra player seat")
        shared = directory / "shared.worldlog"
        shared_command = ["dotnet", RELAY, "--world-journal", str(shared), "--base-url", base, "--key-file", str(keys), *relay_transport]
        native = subprocess.run(shared_command + ["--demo-room", "5", "--seconds", "1"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        check(native.returncode == 0, "Shared netstandard publisher completes through a real authenticated WebSocket: " + native.stderr[-400:])
        shared_result = json.loads(native.stdout)
        shared_route = "/api/sessions/" + shared_result["sessionId"] + "/world"
        shared_info = request(shared_route)
        check(shared.read_bytes()[:8] == b"VRWORLD1", "Shared source uses a versioned binary checksummed journal")
        check(shared_info["complete"] and shared_info["acceptedSequence"] == 24, "Shared publisher seals every world frame after combat confirmation")
        check(bool(shared_info["header"]["captureStartedAtUtc"]) and bool(shared_info["capturedAtUtc"]), "Shared archive retains source capture time independently of upload time")
        native = subprocess.run(shared_command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        check(native.returncode == 0 and json.loads(native.stdout)["acknowledged"] == 24 and json.loads(native.stdout)["complete"], "Independent process recovers shared durable acknowledgments and final seal")
        check(request(shared_route) == shared_info, "Shared source recovery preserves the exact accepted world archive")
        recovery_input = directory / "closed-server"
        recovery_input.mkdir()
        recovery_config = recovery_input / "server-config.json"
        original_world = recovery_input / (shared_result["sessionId"] + ".worldlog")
        original_combat = recovery_input / (shared_result["sessionId"] + ".journal")
        sealed_world = shared.read_bytes()
        sealed_combat = Path(str(shared) + ".combat").read_bytes()
        # Simulate loss of only the final durable receipts, leaving both original completion records.
        assert sealed_world[-45:-40] == b"\x09\x00\x00\x00\x04" and sealed_combat[-37:-32] == b"\x01\x00\x00\x00\x05"
        original_world.write_bytes(sealed_world[:-45])
        original_combat.write_bytes(sealed_combat[:-37])
        recovery_draft = {"role": "Server", "sessionId": shared_result["sessionId"], "managementApiUrl": base,
                          "gameServerKey": tokens["GameServer"], "telemetryOrigin": "Simulation", "telemetryDirectory": str(recovery_input)}

        def recover(label, config):
            recovery_config.write_text(json.dumps(config), encoding="utf-8-sig")
            work = directory / label
            result = subprocess.run([*RECOVERY, "--recover-server", str(recovery_config), "--work", str(work), *relay_transport],
                                    cwd=directory, capture_output=True, encoding="utf-8", timeout=30)
            assert not any(key in result.stdout + result.stderr for key in tokens.values())
            return work, result

        old_session = request(shared_route.rsplit("/", 1)[0])
        if use_ipc:
            for label, origin, pin in (
                ("remote-http", "http://venue.invalid", ""),
                ("pinned-https", base.replace("http:", "https:", 1), "a" * 64),
            ):
                work, denied = recover(label, {**recovery_draft, "managementApiUrl": origin, "managementCertificateSha256": pin})
                check(denied.returncode == 1 and json.loads(denied.stderr)["reason"] == "local-recovery-requires-loopback-http-origin"
                      and not work.exists(), "Local recovery rejects " + label + " before staging journals")
        for label, config in (
            ("http-with-pin", {**recovery_draft, "managementCertificateSha256": "a" * 64}),
            ("https-without-pin", {**recovery_draft, "managementApiUrl": base.replace("http:", "https:", 1)}),
            ("https-invalid-pin", {**recovery_draft, "managementApiUrl": base.replace("http:", "https:", 1),
                                   "managementCertificateSha256": "A" * 64}),
        ):
            work, bad_pin = recover(label, config)
            check(bad_pin.returncode == 1 and json.loads(bad_pin.stderr)["reason"] == "invalid-management-certificate-pin"
                  and not work.exists(), "Operational recovery rejects " + label + " before staging journals")
        work, denied = recover("wrong-role", {**recovery_draft, "gameServerKey": tokens["Master"]})
        check(denied.returncode == 1 and json.loads(denied.stderr)["reason"] == "require-original-game-server-role"
              and not (work / "recovery.json").exists() and request(shared_route.rsplit("/", 1)[0]) == old_session,
              "The operational recovery path rejects a valid credential of the wrong role before writing to management")
        work, mismatch = recover("wrong-origin", {**recovery_draft, "telemetryOrigin": "GameServer"})
        check(mismatch.returncode == 1 and json.loads(mismatch.stderr)["reason"] == "journal-identity-or-completion-mismatch"
              and not (work / "recovery.json").exists() and request(shared_route) == shared_info,
              "The operational recovery path rejects a mismatched source and preserves the existing archive")
        work, restored = recover("restored-recording", recovery_draft)
        proof = json.loads((work / "recovery.json").read_bytes()) if restored.returncode == 0 else {}
        check(restored.returncode == 0 and proof == json.loads(restored.stdout)
              and proof["recoverySucceeded"] and proof["worldBefore"] == proof["worldAcknowledged"] == 24
              and proof["combatBefore"] == proof["combatAcknowledged"] == old_session["combatStream"]["acceptedSequence"]
              and proof["worldSealed"] and proof["combatSealed"] and not proof["gameplayRestarted"]
              and (work / "world.worldlog").read_bytes() == sealed_world and (work / "combat.journal").read_bytes() == sealed_combat,
              "The operational recovery path restores only the original acknowledged seal receipts into its working copies")
        check(original_world.read_bytes() == sealed_world[:-45] and original_combat.read_bytes() == sealed_combat[:-37]
              and request(shared_route) == shared_info and request(shared_route.rsplit("/", 1)[0]) == old_session,
              "Operational recovery leaves both originals and the already accepted management state byte-consistent")
        original_world.write_bytes(sealed_world[:-1])
        work, damaged = recover("damaged-recording", recovery_draft)
        check(damaged.returncode == 1 and not (work / "recovery.json").exists()
              and original_world.read_bytes() == sealed_world[:-1] and request(shared_route) == shared_info,
              "Operational recovery rejects a torn original without truncating it or claiming a completed transfer")
        intact = shared.read_bytes()
        shared.write_bytes(intact[:-1])
        native = subprocess.run(shared_command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        check(native.returncode != 0 and shared.read_bytes() == intact[:-1], "Torn shared source fails closed in the native recovery process without truncation")
        check(request(shared_route) == shared_info, "Rejected source recovery changes no persisted world state")

        list_path = "/api/world-recordings"
        page_path = list_path + "/page"
        initial = {row["header"]["sessionId"]: row for row in request(list_path)}
        older_active = request("/api/sessions", expected=201, method="POST", body={"missionId": damage_mission["id"],
            "mode": "Independent", "roomIds": [3]})["id"]
        older_route = f"/api/sessions/{older_active}"
        older_stream = str(uuid4())
        request(older_route + "/combat-stream", "GameServer", method="POST",
                body={"streamId": older_stream, "origin": "Simulation"})
        publisher = world_socket(older_route + "/world/publish", tokens["GameServer"])
        try:
            reply = publisher.send({"type": "header", "payload": dict(damage_header, sessionId=older_active,
                streamId=older_stream, roomIds=[3])})
            assert reply["type"] == "ack", reply
            initial[older_active] = reply["info"]
        finally:
            publisher.close()
        source_free = None
        for index in range(288):
            room = 1 if index % 2 == 0 else 5
            historical = request("/api/sessions", expected=201, method="POST", body={"missionId": damage_mission["id"],
                "mode": "Independent", "roomIds": [room]})
            historical_id = historical["id"]
            if index == 0:
                source_free = historical_id
            historical_session = f"/api/sessions/{historical_id}"
            if index % 12:
                stream = str(uuid4())
                request(historical_session + "/combat-stream", "GameServer", method="POST",
                        body={"streamId": stream, "origin": "Simulation"})
                publisher = world_socket(historical_session + "/world/publish", tokens["GameServer"])
                try:
                    reply = publisher.send({"type": "header", "payload": dict(damage_header, sessionId=historical_id,
                        streamId=stream, roomIds=[room])})
                    assert reply["type"] == "ack", reply
                    initial[historical_id] = reply["info"]
                finally:
                    publisher.close()
            request(historical_session + "/commands", method="POST", body={"commandId": str(uuid4()), "action": "End"})

        expected_lists = {}
        for role in ("Master", "Room1", "Room5"):
            ordered = request("/api/sessions?includeEnded=true", role)
            expected_lists[role] = [initial[row["id"]] for row in ordered if row["id"] in initial]
            check(request(list_path, role) == expected_lists[role],
                  f"Large recording list keeps exact management order, metadata and authorized rooms for {role}")
        check(len(expected_lists["Master"]) > 256 and len(expected_lists["Room5"]) > 128,
              "Large recording fixture spans multiple archive reads and includes incomplete and sealed sources")

        for role, expected in expected_lists.items():
            collected, cursor = [], None
            while len(collected) < len(expected):
                query = f"?before={cursor}" if cursor else ""
                page = request(page_path + query, role)
                chunk = expected[len(collected):len(collected) + 30]
                assert page["recordings"] == chunk
                assert page["pinned"] == ([initial[older_active]] if not cursor and role == "Master" else [])
                collected.extend(page["recordings"])
                next_cursor = chunk[-1]["header"]["sessionId"] if len(collected) < len(expected) else None
                assert page["nextBefore"] == next_cursor and (not next_cursor or next_cursor != cursor)
                cursor = next_cursor
            check(collected == expected, f"Paginated catalog reproduces every scoped row in the same order for {role}")

        room_one = next(row for row in reversed(expected_lists["Room1"]) if row["header"]["roomIds"] == [1])
        room_five = next(row for row in reversed(expected_lists["Room5"]) if row["header"]["roomIds"] == [5])
        one_id, five_id = (row["header"]["sessionId"] for row in (room_one, room_five))
        newest_id = expected_lists["Room5"][0]["header"]["sessionId"]
        included = request(f"{page_path}?limit=1&include={one_id}&include={five_id}&include={five_id}&include={newest_id}", "Room5")
        check(included["recordings"] == expected_lists["Room5"][:1] and included["pinned"] == [room_five]
              and included["nextBefore"] == newest_id,
              "Explicit pins include each older authorized recording once and suppress both foreign and already listed IDs")
        limited = request(f"{page_path}?limit=50", "Master")
        check(limited["recordings"] == expected_lists["Master"][:50]
              and limited["nextBefore"] == limited["recordings"][-1]["header"]["sessionId"],
              "The maximum page size bounds the response and returns an exclusive cursor")
        request(f"{page_path}?before={one_id}", "Room5", 404)
        request(f"{page_path}?before={source_free}", "Master", 404)
        request(f"{page_path}?before={uuid4()}", "Master", 404)
        check(True, "Foreign, source-free, and nonexistent cursor IDs have the same not-found response")
        empty = "00000000-0000-0000-0000-000000000000"
        for query in ("limit=0", "limit=51", "before=invalid", f"before={empty}", f"include={empty}",
                      "&".join(f"include={uuid4()}" for _ in range(7))):
            request(page_path + "?" + query, "Master", 400)
        request(page_path, "invalid", 401)
        check(True, "Recording pagination validates query bounds and requires authentication")
        request(older_route + "/commands", method="POST", body={"commandId": str(uuid4()), "action": "End"})
        check(request(page_path)["pinned"] == [], "The previously pinned source drops out of the live pins after End")

        demo = subprocess.Popen([*shared_command[:2], "--world-journal", str(directory / "list-live.worldlog"),
            "--base-url", base, "--key-file", str(keys), "--demo-room", "5", "--seconds", "3", *relay_transport],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        for _ in range(100):
            if any(row["header"]["sessionId"] not in initial and 0 < row["acceptedSequence"] and not row["complete"]
                   for row in request(list_path)):
                break
            if demo.poll() is not None:
                raise AssertionError("Publisher exited before concurrent list observations")
            time.sleep(.03)
        else:
            raise AssertionError("No advancing publisher available for list observations")

        def list_during_publication(role):
            observations = set()
            times = []
            for _ in range(24):
                started = time.perf_counter()
                entries = request(list_path, role)
                times.append((time.perf_counter() - started) * 1000)
                assert [row for row in entries if row["header"]["sessionId"] in initial] == expected_lists[role]
                fresh = [row for row in entries if row["header"]["sessionId"] not in initial]
                assert len(fresh) <= 1 and all(row["header"]["roomIds"] == [5] for row in fresh)
                observations.update(row["acceptedSequence"] for row in fresh if not row["complete"] and row["acceptedSequence"] > 0)
                time.sleep(.07)
            return observations, times

        with ThreadPoolExecutor(max_workers=3) as pool:
            listing = list(pool.map(list_during_publication, ("Master", "Room1", "Room5")))
        output, errors = demo.communicate(timeout=15)
        check(demo.returncode == 0, "Native .NET publisher completes while archive readers are active: " + errors[-400:])
        live_info = request("/api/sessions/" + json.loads(output)["sessionId"] + "/world")
        check(live_info["complete"] and live_info["acceptedSequence"] == 64
              and len(listing[0][0]) >= 2 and not listing[1][0] and len(listing[2][0]) >= 2,
              "Concurrent archive reads observe advancing publication within the original room scope and the source seals")
        print("ARCHIVE_LIST_PROBE " + json.dumps({
            role: {"historyRows": len(expected_lists[role]), "liveSequences": sorted(observed),
                   "medianMilliseconds": round(sorted(times)[len(times) // 2], 2)}
            for role, (observed, times) in zip(("Master", "Room1", "Room5"), listing, strict=True)
        }))

        sparse_mission = request("/api/missions", expected=201, method="POST",
                                 body=dict(damage_mission["definition"], enemies={"count": 0, "behavior": "Hold", "autoAttack": False}))
        sparse = request("/api/sessions", expected=201, method="POST", body={"missionId": sparse_mission["id"],
                         "mode": "Independent", "roomIds": [3]})
        sparse_session = f"/api/sessions/{sparse['id']}"
        sparse_stream = str(uuid4())
        request(sparse_session + "/combat-stream", "GameServer", method="POST", body={"streamId": sparse_stream, "origin": "Simulation"})
        publisher = world_socket(sparse_session + "/world/publish", tokens["GameServer"])
        try:
            reply = publisher.send({"type": "header", "payload": dict(damage_header, sessionId=sparse["id"], streamId=sparse_stream, roomIds=[3])})
            assert reply["type"] == "ack", reply
            packet = deepcopy(packets[0])
            packet.update(observedSequence=request(sparse_session)["sequence"], throughCombatSequence=0, events=[])
            packet["frame"].update(players=[], enemies=[], phase="Preparing", autoAttack=False, tick=0, throughSequence=0)
            for number in range(1, 1101):
                reply = publisher.send({"type": "frame", "payload": dict(packet, sequence=number, elapsedMilliseconds=(number - 1) * 50)})
                assert reply["type"] == "ack", reply
            ended = request(sparse_session + "/commands", method="POST", body={"commandId": str(uuid4()), "action": "End"})
            packet["frame"]["phase"] = "Ended"
            reply = publisher.send({"type": "frame", "payload": dict(packet, sequence=1101, elapsedMilliseconds=55000,
                observedSequence=ended["session"]["sequence"])})
            assert reply["type"] == "ack", reply
        finally:
            publisher.close()
        sparse_route = sparse_session + "/world/policy-neighbor?throughFrame=1101"
        earlier = request(sparse_route + "&change=initial&direction=previous&fromFrame=1101")
        later = request(sparse_route + "&change=phase&direction=next&fromFrame=1")
        check(earlier["frame"] is None and earlier["nextFromFrame"] == 77
              and later["frame"] is None and later["nextFromFrame"] == 1025
              and request(sparse_route + "&change=initial&direction=previous&fromFrame=77")["frame"]["frameSequence"] == 1
              and request(sparse_route + "&change=phase&direction=next&fromFrame=1025")["frame"]["frameSequence"] == 1101,
              "Both policy neighbor directions continue across an empty bounded page and retain the original predecessor")
        inclusive = request(sparse_route + "&change=initial&direction=previous&fromFrame=1101&includeFrom=true")
        resumed = request(sparse_route + f"&change=initial&direction=previous&fromFrame={inclusive['nextFromFrame']}")
        check(inclusive["includeFrom"] and inclusive["frame"] is None and inclusive["scannedToFrame"] == inclusive["nextFromFrame"] == 78
              and "includeFrom" not in resumed and resumed["frame"]["frameSequence"] == 1,
              "Live policy lookup includes its anchor once and resumes before the empty page boundary")
        if use_ipc:
            check(has_no_ip_endpoints([os.getpid(), process.pid]), "The owned world fixture and API have zero TCP listeners and UDP endpoints")
        print(f"All {count} world streaming checks passed. No Unity or headset execution.")
    finally:
        if demo is not None and demo.poll() is None:
            demo.terminate()
            demo.wait(timeout=10)
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        log.close()
