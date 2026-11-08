"""Real WebSocket publisher, authenticated SSE observation and SQLite restart checks."""
import json
import os
from pathlib import Path
import secrets
import sqlite3
import socket
import subprocess
import tempfile
import time
from uuid import uuid4
import urllib.error
import urllib.request

from world_test_socket import WebSocket

ROOT = Path(__file__).resolve().parents[1]
API = os.environ.get("VR_COMMAND_API_DLL", str(ROOT / "src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll"))
RELAY = os.environ.get("VR_COMMAND_WORLD_RELAY_DLL", str(ROOT / "tools/VrCommand.WorldRelay/bin/Release/net10.0/VrCommand.WorldRelay.dll"))
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
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    environment = {key: value for key, value in os.environ.items() if not key.lower().startswith("operatorkeys__") and key.lower() not in ("operatorkeyfile", "playerticketsigningkey")}
    environment.update({"DataDirectory": str(directory / "missions"), "SessionDataDirectory": str(directory / "sessions"), "OperatorKeyFile": str(keys), "Logging__LogLevel__Default": "Warning"})
    log = open(directory / "api.log", "wb")
    process = None
    demo = None

    def request(route, role="Master", expected=200, method="GET", body=None):
        req = urllib.request.Request(base + route, method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + tokens.get(role, role), "Content-Type": "application/json"})
        try:
            response = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        if response.status != expected:
            raise AssertionError(f"{route}: {response.status}, expected {expected}")
        if expected != 200:
            response.close()
            return None
        if response.headers.get_content_type() == "text/event-stream":
            return response
        with response:
            return json.load(response)

    def start():
        process = subprocess.Popen(["dotnet", API, "--urls", base], cwd=ROOT, env=environment, stdout=log, stderr=log)
        for _ in range(150):
            try:
                with urllib.request.urlopen(base + "/health", timeout=.5):
                    return process
            except (OSError, urllib.error.URLError):
                if process.poll() is not None:
                    raise AssertionError("Isolated world API exited before health")
                time.sleep(.1)
        raise AssertionError("Isolated world API startup timed out")

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

    try:
        process = start()
        check(request("/api/world-recordings") == [], "No fabricated world recording appears at startup")
        request("/api/world-recordings", "invalid", 401)
        check(True, "World listing requires authentication")
        recording = directory / "world.ndjson"
        command = ["dotnet", RELAY, "--recording", str(recording), "--base-url", base, "--key-file", str(keys)]
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
        publisher = WebSocket(port, route + "/publish", tokens["GameServer"])
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
        publisher = WebSocket(port, route + "/publish", tokens["GameServer"])
        publisher.send(frames[0])
        check(publisher.send(frames[1])["info"]["acceptedSequence"] == 44, "Late exact frame retry confirms the original record after sealing")
        altered = json.loads(json.dumps(frames[1]))
        altered["payload"]["frame"]["players"][0]["health"] = 1
        check(publisher.send(altered)["type"] == "error", "Conflicting retry cannot overwrite an accepted frame")
        publisher.close()
        publisher = WebSocket(port, route + "/publish", tokens["GameServer"])
        check(publisher.send(frames[1])["type"] == "error", "Each new socket must establish its header before frames")
        publisher.close()
        request(route + "/watch?rate=999", expected=400)
        request(route + "/watch?fromMs=-1", expected=400)
        check(True, "Unbounded replay speed and invalid seeks are rejected")
        unsupported_header = json.loads(json.dumps(info["header"]))
        unsupported_header["environmentVersion"] = 2
        publisher = WebSocket(port, route + "/publish", tokens["GameServer"])
        check(publisher.send({"type": "header", "payload": unsupported_header})["type"] == "error", "Unknown environment versions cannot publish a world")
        publisher.close()
        unsupported_header["environmentVersion"] = 0
        publisher = WebSocket(port, route + "/publish", tokens["GameServer"])
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
        check(request(exact_route, "Room5") == exact, "The exact event frame and its statistics remain identical after restart")
        check(request(route)["header"]["environmentVersion"] == 0, "Pre-versioned stored headers remain explicitly legacy instead of acquiring invented effects")
        check(request(cameras) == [] and request(cameras, "Room5") == [room_camera]
              and request(camera_route, method="PUT", body=camera)["deleted"], "SQLite restart preserves saved camera positions and removal history without changing world metadata")
        recovery = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        check(recovery.returncode == 0 and json.loads(recovery.stdout)["complete"], "A second native process replays the full saved source idempotently")
        check(request(route) == info, "Whole-source retry changes no frame or archive metadata")
        check(request("/api/sessions/" + session)["players"][0]["name"] == "World Simulation", "Observer creates no extra player seat")
        shared = directory / "shared.worldlog"
        shared_command = ["dotnet", RELAY, "--world-journal", str(shared), "--base-url", base, "--key-file", str(keys)]
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
        intact = shared.read_bytes()
        shared.write_bytes(intact[:-1])
        native = subprocess.run(shared_command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        check(native.returncode != 0 and shared.read_bytes() == intact[:-1], "Torn shared source fails closed in the native recovery process without truncation")
        check(request(shared_route) == shared_info, "Rejected source recovery changes no persisted world state")
        print(f"All {count} world streaming checks passed. No Unity or headset execution.")
    finally:
        if demo is not None and demo.poll() is None:
            demo.terminate()
            demo.wait(timeout=10)
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        log.close()
