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
        check(page == {"sessionId": session, "streamId": info["header"]["streamId"], "throughFrame": boundary,
                       "afterFrame": 0, "scannedThroughFrame": boundary, "nextAfterFrame": None,
                       "playerId": None,
                       "frames": [{"frameSequence": boundary, "elapsedMilliseconds": combat_packet["elapsedMilliseconds"],
                                   "matchCount": sum(e["kind"] == "PlayerDamaged" for e in combat_packet["events"])}]},
              "Room and kind search returns the exact saved damage frame at an inclusive prefix limit")
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
            result = subprocess.run([*RECOVERY, "--recover-server", str(recovery_config), "--work", str(work)],
                                    cwd=directory, capture_output=True, encoding="utf-8", timeout=30)
            assert not any(key in result.stdout + result.stderr for key in tokens.values())
            return work, result

        old_session = request(shared_route.rsplit("/", 1)[0])
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
        print(f"All {count} world streaming checks passed. No Unity or headset execution.")
    finally:
        if demo is not None and demo.poll() is None:
            demo.terminate()
            demo.wait(timeout=10)
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        log.close()
