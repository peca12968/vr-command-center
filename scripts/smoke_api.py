"""Exercise the real HTTP API using an isolated process and temporary mission data."""

import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import secrets
import sys
import sqlite3
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
DLL = Path(os.environ.get("VR_COMMAND_API_DLL", ROOT / "src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll"))
if not DLL.exists():
    raise SystemExit("Build first: dotnet build VrCommand.slnx --configuration Release")

with socket.socket() as reservation:
    reservation.bind(("127.0.0.1", 0))
    port = reservation.getsockname()[1]
base_url = f"http://127.0.0.1:{port}"
checks = 0
tokens = {name: secrets.token_urlsafe(32) for name in ["Master", "GameServer", *[f"Room{i}" for i in range(1, 6)]]}


def request(method, path, body=None, expected=200, identity="Master", request_id=None):
    global checks
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if request_id is not None:
        headers["Idempotency-Key"] = request_id
    if identity is not None:
        headers["Authorization"] = "Bearer " + tokens.get(identity, identity)
    req = urllib.request.Request(
        base_url + path, data=data, method=method,
        headers=headers,
    )
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        payload = response.read()
        if response.status != expected:
            raise AssertionError(f"{method} {path}: expected {expected}, got {response.status}: {payload!r}")
    checks += 1
    return json.loads(payload) if payload else None


def require(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1
    print("PASS:", message)


temporary = tempfile.TemporaryDirectory(prefix="vr-command-http-")
test_directory = Path(temporary.name).resolve()
temp_root = Path(tempfile.gettempdir()).resolve()
# Validate the cleanup target before allowing recursive cleanup of the unique test directory.
if test_directory.parent != temp_root or not test_directory.name.startswith("vr-command-http-"):
    raise RuntimeError("Refusing cleanup outside the temporary test directory")

try:
    environment = {key: value for key, value in os.environ.items()
                   if not key.lower().startswith("operatorkeys__") and key.lower() not in ("operatorkeyfile", "playerticketsigningkey")}
    environment["DataDirectory"] = str(test_directory / "missions")
    environment["SessionDataDirectory"] = str(test_directory / "sessions")
    environment["ASPNETCORE_ENVIRONMENT"] = "Production"
    environment["Logging__LogLevel__Default"] = "Warning"
    for name, token in tokens.items():
        environment[f"OperatorKeys__{name}"] = token
    with (test_directory / "server.log").open("w", encoding="utf-8") as log:
        key_file = test_directory / "operator-keys.local.json"

        def launch(overrides=None, use_key_file=False):
            process_environment = environment.copy()
            args = ["dotnet", str(DLL), "--urls", base_url]
            if use_key_file:
                process_environment = {key: value for key, value in process_environment.items()
                                       if not key.lower().startswith("operatorkeys__")}
                key_file.write_text(json.dumps({"OperatorKeys": tokens}), encoding="utf-8")
                args += ["--OperatorKeyFile", str(key_file)]
            if overrides:
                process_environment.update(overrides)
            return subprocess.Popen(
                args, cwd=ROOT, env=process_environment,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

        def stop(process):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        def wait_ready(process):
            deadline = time.monotonic() + 30
            while True:
                try:
                    request("GET", "/health")
                    break
                except (urllib.error.URLError, TimeoutError):
                    if process.poll() is not None:
                        raise RuntimeError("API exited during startup; inspect test output")
                    if time.monotonic() >= deadline:
                        raise RuntimeError("API startup timed out")
                    time.sleep(0.1)

        for invalid in [
            {"OperatorKeys__Master": ""},
            {"OperatorKeys__Master": "short"},
            {"OperatorKeys__Room1": tokens["Master"]},
            {"OperatorKeys__Room9": secrets.token_urlsafe(32)},
        ]:
            invalid_process = launch(overrides=invalid)
            try:
                require(invalid_process.wait(timeout=10) != 0, "Missing, weak, duplicated or unknown credentials prevent API startup")
            finally:
                if invalid_process.poll() is None:
                    stop(invalid_process)

        process = launch()
        try:
            wait_ready(process)
            request("GET", "/health", identity=None)
            request("GET", "/api/rooms", expected=401, identity=None)
            request("GET", "/api/rooms", expected=401, identity="invalid-credential-with-no-configured-identity")
            require(request("GET", "/api/me")["role"] == "Master", "Master credential resolves to a server-assigned identity")
            for room in range(1, 6):
                own_rooms = request("GET", "/api/rooms", identity=f"Room{room}")
                require(len(own_rooms) == 1 and own_rooms[0]["id"] == room, f"Room {room} controller only lists its room")
            rooms = request("GET", "/api/rooms")
            require(len(rooms) == 5 and all(r["capacity"] == 5 for r in rooms), "Five rooms expose five slots each")
            draft = json.loads((ROOT / "examples/mission.json").read_text(encoding="utf-8"))
            mission = request("POST", "/api/missions", draft, 201)
            loaded = request("GET", f"/api/missions/{mission['id']}")
            require(loaded["definition"] == draft, "Mission round-trips through JSON persistence")
            require(len(request("GET", "/api/missions")) == 1, "Saved mission appears in list")
            request("POST", "/api/missions", draft, 403, identity="Room1")
            request("POST", "/api/missions", draft, 403, identity="GameServer")
            request("POST", "/api/missions", {**draft, "durationSeconds": 0}, 400)
            request("POST", "/api/missions", {**draft, "props": None}, 400)
            request("GET", f"/api/missions/{uuid.uuid4()}", expected=404)

            def start(mode, room_ids, expected=201, request_id=None):
                return request("POST", "/api/sessions", {
                    "missionId": mission["id"], "mode": mode, "roomIds": room_ids,
                }, expected, request_id=request_id)

            start("Linked", [1, 2, 3, 4, 4], 400)
            start("Linked", None, 400)
            request("POST", "/api/sessions", {"missionId": mission["id"], "mode": "Linked", "roomIds": [1,2,3,4,5]}, 403, identity="Room1")
            request("POST", "/api/sessions", {"missionId": mission["id"], "mode": "Independent", "roomIds": [2]}, 403, identity="Room1")
            request("POST", "/api/sessions", {"missionId": mission["id"], "mode": "Independent", "roomIds": [1]}, 403, identity="GameServer")
            create_key = str(uuid.uuid4())
            creation_body = {"missionId": mission["id"], "mode": "Independent", "roomIds": [1]}
            for malformed in ["", "not-a-uuid", str(uuid.UUID(int=0)), str(uuid.uuid4()) + "," + str(uuid.uuid4())]:
                request("POST", "/api/sessions", creation_body, 400, request_id=malformed)
            with ThreadPoolExecutor(max_workers=8) as pool:
                creations = list(pool.map(lambda _: start("Independent", [1], request_id=create_key), range(8)))
            require(len({value["id"] for value in creations}) == 1, "Concurrent keyed HTTP creations produce one session")
            independent = [creations[0], *[start("Independent", [room]) for room in range(2, 6)]]
            start("Independent", [2], 409, request_id=create_key)
            request("POST", "/api/sessions", creation_body, 409, identity="Room1", request_id=create_key)
            request("POST", "/api/sessions", creation_body, 403, identity="Room2", request_id=create_key)
            request("POST", "/api/sessions", creation_body, 403, identity="GameServer", request_id=create_key)
            require(len(request("GET", "/api/sessions", identity="Room1")) == 1, "Room controller session list excludes other independent rooms")
            request("GET", f"/api/sessions/{independent[1]['id']}", expected=403, identity="Room1")
            request("GET", f"/api/sessions/{independent[1]['id']}/events", expected=403, identity="Room1")
            request("GET", f"/api/sessions/{independent[1]['id']}/statistics", expected=403, identity="Room1")
            request("DELETE", f"/api/sessions/{independent[1]['id']}", expected=403, identity="Room1")
            start("Linked", [1, 2, 3, 4, 5], 409)
            first_player_id = str(uuid.uuid4())
            player = {"playerId": first_player_id, "name": "Alpha", "roomId": 1, "headset": "Quest3"}
            request("POST", f"/api/sessions/{independent[0]['id']}/players", player)
            room_player = {**player, "playerId": str(uuid.uuid4())}
            own_path = f"/api/sessions/{independent[0]['id']}"
            join_key = str(uuid.uuid4())
            with ThreadPoolExecutor(max_workers=8) as pool:
                joins = list(pool.map(lambda _: request("POST", own_path + "/players", room_player, identity="Room1", request_id=join_key), range(8)))
            require(all(len(value["players"]) == 2 and value["sequence"] == 3 for value in joins), "Concurrent HTTP join retries retain one roster entry and seat")
            request("POST", own_path + "/players", {**room_player, "name": "Changed"}, 409, identity="Room1", request_id=join_key)
            request("POST", own_path + "/players", room_player, 409, request_id=join_key)
            request("POST", own_path + "/players", room_player, 403, identity="Room2", request_id=join_key)
            request("POST", own_path + "/players", room_player, 409, identity="Room1", request_id=create_key)
            invitation = request("POST", own_path + "/players/" + room_player["playerId"] + "/join-ticket", identity="Room1")
            require(len(invitation["ticket"]) < 256, "Headset receives a compact player-only connection ticket")
            validate = {"sessionId": independent[0]["id"], "ticket": invitation["ticket"]}
            approved = request("POST", "/api/player-tickets/validate", validate, identity="GameServer")
            require(approved["playerId"] == room_player["playerId"] and approved["roomId"] == 1 and approved["seat"] == 1,
                    "Game server validates the assigned player, room and stable spawn seat")
            request("POST", "/api/player-tickets/validate", validate, 403, identity="Master")
            request("POST", "/api/player-tickets/validate", {**validate, "sessionId": independent[1]["id"]}, 403, identity="GameServer")
            request("POST", "/api/player-tickets/validate", {**validate, "ticket": invitation["ticket"][:-5] + "AAAAA"}, 403, identity="GameServer")
            request("POST", own_path + "/players/" + room_player["playerId"] + "/join-ticket", expected=403, identity="Room2")
            request("POST", own_path + "/players/" + room_player["playerId"] + "/join-ticket", expected=403, identity="GameServer")
            request("DELETE", own_path + "/players/" + room_player["playerId"], expected=403, identity="Room2")
            leave_key = str(uuid.uuid4())
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda _: request("DELETE", own_path + "/players/" + room_player["playerId"], expected=204, identity="Room1", request_id=leave_key), range(8)))
            require(len(request("GET", own_path)["players"]) == 1, "Concurrent HTTP leave retries remove the player once")
            request("DELETE", own_path + "/players/" + player["playerId"], expected=409, identity="Room1", request_id=leave_key)
            require(len(request("POST", own_path + "/players", room_player, identity="Room1", request_id=join_key)["players"]) == 1,
                    "Delayed HTTP join acknowledgment does not resurrect a departed player")
            request("POST", "/api/player-tickets/validate", validate, 403, identity="GameServer")
            command = {"commandId": str(uuid.uuid4()), "action": "SetEnvironment", "environment": draft["environment"]}
            request("POST", own_path + "/commands", command, identity="Room1")
            request("POST", own_path + "/commands", command, 409)  # another identity cannot claim this retry
            own_events = request("GET", own_path + "/events", identity="Room1")
            require(own_events[-1]["actor"]["id"] == "room-1" and own_events[-1]["schemaVersion"] == 5,
                    "Management events retain authenticated console identity")
            request("POST", f"/api/sessions/{independent[1]['id']}/players", {**player, "roomId": 2}, 409)
            request("POST", f"/api/sessions/{independent[0]['id']}/players", {**player, "playerId": str(uuid.uuid4()), "roomId": 2}, 400)
            for session in independent:
                request("DELETE", f"/api/sessions/{session['id']}", expected=204)

            session = start("Linked", [1, 2, 3, 4, 5])
            session_path = f"/api/sessions/{session['id']}"
            for room in range(1, 6):
                for index in range(5):
                    request("POST", session_path + "/players", {
                        "playerId": str(uuid.uuid4()), "name": f"P{room}-{index}", "roomId": room,
                        "headset": "Quest3" if index % 2 else "ViveXr",
                    })
            current = request("GET", session_path)
            require(len(current["players"]) == 25, "Linked session contains 25 mixed-device player records")
            require(current["state"] == "Preparing" and current["startedAtUtc"] is None,
                    "Creating a session does not start the mission")
            request("POST", session_path + "/players/" + player["playerId"] + "/join-ticket", expected=404)
            require(request("GET", session_path, identity="Room1")["id"] == session["id"],
                    "Room controllers may read the shared linked scene")
            request("POST", session_path + "/commands", {"commandId": str(uuid.uuid4()), "action": "Begin", "actor": {"id": "master", "role": "Master"}}, 403, identity="Room1")
            request("POST", session_path + "/commands", {"commandId": str(uuid.uuid4()), "action": "Begin"}, 403, identity="GameServer")
            request("DELETE", session_path, expected=403, identity="Room1")
            competing = launch()
            try:
                require(competing.wait(timeout=10) != 0, "Another API process cannot acquire the same event-store writer lease")
            finally:
                if competing.poll() is None:
                    stop(competing)
            require(request("GET", session_path) == current, "Rejected competing process leaves active state intact")
            request("POST", session_path + "/players", {**player, "playerId": str(uuid.uuid4())}, 409)
            require(all(r["playerCount"] == 5 for r in request("GET", "/api/rooms")), "Every room remains at capacity after overflow rejection")
            request("DELETE", session_path + "/players/" + current["players"][0]["id"], expected=403, identity="Room2")
            request("DELETE", session_path + "/players/" + current["players"][0]["id"], expected=204, identity="Room1")
            request("POST", session_path + "/players", {**player, "roomId": 2}, 403, identity="Room1")
            request("POST", session_path + "/players", player, identity="Room1")
            live_ticket = request("POST", session_path + "/players/" + player["playerId"] + "/join-ticket", identity="Room1")
            live_validation = {"sessionId": session["id"], "ticket": live_ticket["ticket"]}
            require(request("POST", "/api/player-tickets/validate", live_validation, identity="GameServer")["seat"] == 0,
                    "Replacement player receives the released stable spawn seat")

            def control(action, expected=200, **extra):
                body = {"commandId": str(uuid.uuid4()), "action": action, **extra}
                return request("POST", session_path + "/commands", body, expected)

            control("Resume", 409)
            control("SetEnvironment", 400)
            control("SetEnemies", 400, enemies={"count": -1, "behavior": "Hold", "autoAttack": True})
            request("POST", session_path + "/commands", {"commandId": str(uuid.uuid4())}, 400)
            request("POST", session_path + "/commands", {"commandId": str(uuid.uuid4()), "action": "Begin", "environment": draft["environment"]}, 400)
            current = request("GET", session_path)
            begin = {"commandId": str(uuid.uuid4()), "action": "Begin", "expectedSequence": current["sequence"]}
            fired = {"reportId": str(uuid.uuid4()), "kind": "ShotFired", "origin": "Simulation",
                     "playerId": player["playerId"], "shotId": str(uuid.uuid4())}
            request("POST", session_path + "/combat", fired, 409, identity="GameServer")
            receipt = request("POST", session_path + "/commands", begin)
            require(receipt["session"]["state"] == "Running" and receipt["session"]["startedAtUtc"] is not None,
                    "Begin moves a populated mission to Running")
            request("POST", session_path + "/players", {**player, "playerId": str(uuid.uuid4())}, 409)

            def report(body, expected=200, identity="GameServer"):
                return request("POST", session_path + "/combat", body, expected, identity)

            baseline = request("GET", session_path + "/statistics")
            require(baseline["origin"] is None and all(p["ammoUsed"] == 0 and p["health"] == 100 for p in baseline["players"]),
                    "Statistics start empty and include previously departed players")
            report(fired, 403, identity="Master")
            report({**fired, "actor": {"role": "GameServer"}}, 403, identity="Room1")
            accepted_shot = report(fired)
            require(report(fired)["duplicate"], "Repeated combat report returns an idempotent receipt")
            second_shot = {**fired, "reportId": str(uuid.uuid4()), "shotId": str(uuid.uuid4())}
            third_shot = {**fired, "reportId": str(uuid.uuid4()), "shotId": str(uuid.uuid4())}
            report(second_shot)
            report(third_shot)
            enemy = str(uuid.uuid4())
            hit = {**fired, "reportId": str(uuid.uuid4()), "kind": "ShotHit", "enemyId": enemy}
            report(hit)
            report({**hit, "reportId": str(uuid.uuid4()), "kind": "EnemyEliminated"})
            report({**second_shot, "reportId": str(uuid.uuid4()), "kind": "ShotHit", "enemyId": str(uuid.uuid4())})
            report({"reportId": str(uuid.uuid4()), "kind": "PlayerDamaged", "origin": "Simulation", "playerId": player["playerId"], "damage": 20})
            report({**fired, "reportId": str(uuid.uuid4())}, 409)
            report({**hit, "reportId": str(uuid.uuid4()), "shotId": str(uuid.uuid4())}, 409)
            report({**fired, "reportId": str(uuid.uuid4()), "shotId": str(uuid.uuid4()), "origin": "GameServer"}, 409)
            report({**fired, "origin": "Unspecified"}, 400)
            report({"reportId": str(uuid.uuid4()), "kind": "PlayerDamaged", "origin": "Simulation", "playerId": player["playerId"], "damage": 0}, 400)
            alpha = next(p for p in request("GET", session_path + "/statistics")["players"] if p["playerId"] == player["playerId"])
            require(alpha["ammoUsed"] == 3 and alpha["shotsHit"] == 2 and alpha["accuracyPercent"] == 66.67
                    and alpha["kills"] == 1 and alpha["hitsReceived"] == 1 and alpha["damageTaken"] == 20 and alpha["health"] == 80,
                    "HTTP combat events produce the six requested player metrics")
            control("Resume", 409)
            control("Pause", expectedSequence=1, expected=409)
            pause = {"commandId": str(uuid.uuid4()), "action": "Pause"}
            before_pause_sequence = request("GET", session_path)["sequence"]
            with ThreadPoolExecutor(max_workers=8) as pool:
                # request() counts are kept on the main thread below for deterministic reporting.
                def retry_pause(_):
                    req = urllib.request.Request(base_url + session_path + "/commands",
                        data=json.dumps(pause).encode(), method="POST", headers={"Content-Type": "application/json", "Authorization": "Bearer " + tokens["Master"]})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return json.load(response)
                retries = list(pool.map(retry_pause, range(12)))
            require(sum(not result["duplicate"] for result in retries) == 1,
                    "Concurrent HTTP retries apply one pause command")
            current = request("GET", session_path)
            require(current["state"] == "Paused" and current["sequence"] == before_pause_sequence + 1,
                    "Retrying does not append extra events")
            report({**fired, "reportId": str(uuid.uuid4()), "shotId": str(uuid.uuid4())}, 409)
            require(report(fired)["duplicate"], "Combat retry remains valid while paused without new events")
            request("POST", session_path + "/commands", {**pause, "action": "Resume"}, 409)
            environment_override = {"mode": "VR", "weather": "Clear", "timeOfDay": "Day", "lightning": False}
            control("SetEnvironment", environment=environment_override)
            control("SetEnemies", enemies={"count": 2, "behavior": "Advance", "autoAttack": False})
            control("Resume")
            current = request("GET", session_path)
            statistics = request("GET", session_path + "/statistics")
            require(current["environment"] == environment_override and current["mission"]["definition"] == draft,
                    "Runtime overrides preserve the saved template")
            events = request("GET", session_path + "/events?after=0&limit=500")
            combat_events = [event for event in events if event["kind"] == "CombatRecorded"]
            require(len(combat_events) == 7 and all(event["actor"]["id"] == "game-server" and event["schemaVersion"] == 5 for event in combat_events),
                    "Combat and management share a versioned, authenticated event stream")
            with closing(sqlite3.connect(test_directory / "sessions/events.db")) as database:
                stored = database.execute("SELECT COUNT(*) FROM session_events WHERE session_id=?", (session["id"],)).fetchone()[0]
            require(stored == current["sequence"], "SQLite stores exactly one row per accepted management or combat event")
            require(not any(token in json.dumps(events) for token in tokens.values()),
                    "Event history contains console identity without credential values")
            require(live_ticket["ticket"] not in json.dumps(events), "Player admission ticket is never written into event history")
            require(len(events) == current["sequence"] and [e["sequence"] for e in events] == list(range(1, len(events) + 1)),
                    "Ordered event stream covers accepted mutations without gaps")
            page = request("GET", session_path + "/events?after=1&limit=2")
            require([e["sequence"] for e in page] == [2, 3], "HTTP event cursor is exclusive")
            request("GET", session_path + "/events?after=-1", expected=400)
            request("GET", session_path + "/events?limit=501", expected=400)

            stop(process)
            process = launch(use_key_file=True)
            wait_ready(process)
            recovered = request("GET", session_path)
            require(recovered == current, "Process restart reconstructs active state, players and control settings")
            old_archive = request("GET", own_path)
            require(request("POST", "/api/sessions", creation_body, 201, request_id=create_key) == old_archive,
                    "HTTP creation retry after restart returns its archived session despite a new linked reservation")
            require(request("POST", own_path + "/players", room_player, identity="Room1", request_id=join_key) == old_archive,
                    "HTTP join key is recovered from SQLite and remains valid after archival")
            request("DELETE", own_path + "/players/" + room_player["playerId"], expected=204, identity="Room1", request_id=leave_key)
            require(request("GET", own_path) == old_archive, "Recovered HTTP leave acknowledgment adds no event")
            require(request("POST", "/api/player-tickets/validate", live_validation, identity="GameServer")["playerId"] == player["playerId"],
                    "Player ticket signing key survives API process restart")
            require(request("GET", session_path + "/statistics") == statistics, "Restart rebuilds identical combat statistics from SQLite")
            require(report(fired)["duplicate"] and report(fired)["appliedAtSequence"] == accepted_shot["appliedAtSequence"],
                    "Combat report deduplication survives API process restart")
            require(all(r["playerCount"] == 5 for r in request("GET", "/api/rooms")),
                    "Restart retains room capacity reservations")
            start("Independent", [1], 409)
            duplicate = request("POST", session_path + "/commands", begin)
            require(duplicate["duplicate"] and duplicate["appliedAtSequence"] == receipt["appliedAtSequence"],
                    "Command retry deduplicates after process restart")
            ended = control("End")
            require(ended["session"]["state"] == "Ended" and ended["session"]["endedAtUtc"] is not None,
                    "End archives the session and timestamps completion")
            request("DELETE", session_path, expected=409)
            require(request("GET", session_path)["state"] == "Ended", "Ended history remains readable")
            request("POST", "/api/player-tickets/validate", live_validation, 403, identity="GameServer")
            require(request("GET", session_path + "/statistics")["players"] == statistics["players"], "Ended session preserves combat statistics")
            require(report(fired)["duplicate"], "Combat report retry is available after session end")
            report({**fired, "reportId": str(uuid.uuid4()), "shotId": str(uuid.uuid4())}, 409)
            require(request("GET", "/api/sessions") == [], "Active list excludes archived sessions")
            require(len(request("GET", "/api/sessions?includeEnded=true")) == 6, "History list includes independent and linked sessions")
            require(all(r["sessionId"] is None and r["playerCount"] == 0 for r in request("GET", "/api/rooms")), "Ending releases all room reservations and player slots")
            require(len(request("GET", "/api/missions")) == 1, "Mission survives session cleanup")
            stop(process)
            old_master = tokens["Master"]
            tokens["Master"] = secrets.token_urlsafe(32)
            process = launch(use_key_file=True)
            wait_ready(process)
            request("GET", "/api/me", expected=401, identity=old_master)
            require(request("GET", "/api/me")["id"] == "master", "Restart rotation rejects the old key and retains the console identity")
            require(request("GET", session_path)["state"] == "Ended"
                    and all(r["sessionId"] is None for r in request("GET", "/api/rooms")),
                    "Second restart preserves archived state and released rooms")
            request("POST", session_path + "/commands", {"commandId": str(uuid.uuid4()), "action": "Pause"}, 409)
            require(request("GET", session_path + "/statistics")["players"] == statistics["players"], "Archived statistics also survive a second restart")
            demo = subprocess.run([sys.executable, str(ROOT / "scripts/demo_combat.py"), "--base-url", base_url,
                                   "--key-file", str(key_file), "--room", "1"], capture_output=True, text=True, encoding="utf-8", timeout=30)
            if demo.returncode != 0:
                raise AssertionError("Combat demo failed: " + demo.stderr)
            summary = json.loads(demo.stdout)
            require(summary["origin"] == "Simulation" and summary["players"][0]["ammoUsed"] == 3
                    and summary["players"][0]["accuracyPercent"] == 66.67 and summary["players"][0]["kills"] == 1
                    and summary["players"][0]["health"] == 80, "Standalone Quest3-record demo creates a simulated combat archive")
            require(all(room["sessionId"] is None for room in request("GET", "/api/rooms")), "Combat demo releases only its own session on completion")
            provision = subprocess.run([sys.executable, str(ROOT / "scripts/prepare-vr-session.py"), "--base-url", base_url,
                                       "--key-file", str(key_file), "--server-address", "127.0.0.1", "--output", str(test_directory / "connections")],
                                      capture_output=True, text=True, encoding="utf-8", timeout=30)
            if provision.returncode != 0:
                raise AssertionError("VR session provisioning failed: " + provision.stderr)
            plan = json.loads(provision.stdout)
            config_directory = Path(plan["directory"])
            server_config = json.loads((config_directory / "server.json").read_text())
            client_config = json.loads((config_directory / "player-1.json").read_text())
            require(server_config["gameServerKey"] == tokens["GameServer"] and "gameServerKey" not in client_config
                    and not any(key in json.dumps(client_config) for key in tokens.values()),
                    "Provisioning keeps control/server credentials out of headset connection files")
            require(request("POST", "/api/player-tickets/validate", {"sessionId": plan["sessionId"], "ticket": client_config["joinTicket"]},
                            identity="GameServer")["roomId"] == 1, "Provisioned Quest client ticket is accepted by the management API")
            request("DELETE", "/api/sessions/" + plan["sessionId"], expected=204)
            simulation_dll = Path(os.environ.get("VR_COMMAND_SIMULATION_DEMO_DLL", ROOT / "tools/VrCommand.SimulationDemo/bin/Release/net10.0/VrCommand.SimulationDemo.dll"))
            simulation_output = test_directory / "simulation-world.json"
            geometric_demo = subprocess.run(["dotnet", str(simulation_dll), "--base-url", base_url, "--key-file", str(key_file),
                                             "--room", "1", "--output", str(simulation_output)],
                                            capture_output=True, text=True, encoding="utf-8", timeout=30)
            if geometric_demo.returncode != 0:
                raise AssertionError("Geometric simulation demo failed: " + geometric_demo.stderr)
            geometric_result = json.loads(geometric_demo.stdout)
            geometric_archive = json.loads(simulation_output.read_text(encoding="utf-8"))
            require(geometric_result["origin"] == "Simulation" and geometric_result["blockedByCover"]
                    and geometric_result["player"]["ammoUsed"] == 3 and geometric_result["player"]["shotsHit"] == 2
                    and geometric_result["player"]["kills"] == 1 and geometric_result["player"]["health"] == 80,
                    "Shared simulation raycasts cover and enemies before emitting persisted combat statistics")
            require(geometric_archive["schemaVersion"] == 2 and geometric_archive["origin"] == "Simulation"
                    and any(frame["players"][0]["health"] == 80 for frame in geometric_archive["frames"])
                    and geometric_archive["frames"][-1]["phase"] == "Ended"
                    and geometric_archive["frames"][-1]["throughSequence"] == geometric_archive["events"][-1]["sequence"]
                    and sum(event["kind"] == "EnemyEliminated" for event in geometric_archive["events"]) == 1,
                    "Headless geometry demo saves world frames and actual AI damage without claiming a 3D replay")
            require(request("GET", "/api/sessions/" + geometric_result["sessionId"])["state"] == "Ended"
                    and all(room["sessionId"] is None for room in request("GET", "/api/rooms")),
                    "Geometric demo archives its own session and releases all its reservations")
            relay_dll = Path(os.environ.get("VR_COMMAND_TELEMETRY_RELAY_DLL", ROOT / "tools/VrCommand.TelemetryRelay/bin/Release/net10.0/VrCommand.TelemetryRelay.dll"))
            journal = test_directory / "outbox.journal"
            relay_args = ["dotnet", str(relay_dll), "--journal", str(journal), "--base-url", base_url, "--key-file", str(key_file)]
            demo = subprocess.run([*relay_args, "--demo-room", "1"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            if demo.returncode != 0:
                raise AssertionError("Outbox demo failed: " + demo.stderr)
            queued = json.loads(demo.stdout)
            stream_path = "/api/sessions/" + queued["sessionId"]
            require(queued["origin"] == "Simulation" and queued["queuedReports"] == 6 and queued["pendingTelemetry"],
                    "Real simulation persists six causal reports, ends the session and exits before delivering them")
            first = queued["firstReport"]
            request("POST", stream_path + "/combat-stream/reports", first, 403)
            request("POST", stream_path + "/combat-stream/reports", first, 403, identity="Room1")
            request("POST", stream_path + "/combat-stream/batch", [], 400, identity="GameServer")
            request("POST", stream_path + "/combat-stream/batch", [first] * 129, 400, identity="GameServer")
            request("POST", stream_path + "/combat-stream/reports", {**first, "streamSequence": 2}, 409, identity="GameServer")
            ended_sequence = request("GET", stream_path)["sequence"]
            request("POST", stream_path + "/combat-stream/reports", {**first, "observedSequence": ended_sequence}, 409, identity="GameServer")
            request("POST", stream_path + "/combat-stream/reports", {**first, "report": {**first["report"], "origin": "GameServer"}}, 409, identity="GameServer")
            accepted = request("POST", stream_path + "/combat-stream/reports", first, identity="GameServer")
            require(accepted["acceptedSequence"] == 1 and accepted["statistics"]["pendingTelemetry"], "Ended stream accepts only its known Running-context tail and stays visibly unsealed")
            require(request("POST", stream_path + "/combat-stream/reports", first, identity="GameServer")["duplicate"], "Lost response leaves a retryable accepted prefix without another shot")
            request("POST", stream_path + "/combat-stream/seal", {"streamId": first["streamId"], "finalSequence": 6}, 409, identity="GameServer")
            stop(process)
            process = launch(use_key_file=True)
            wait_ready(process)
            recovered = subprocess.run(relay_args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            if recovered.returncode != 0:
                raise AssertionError("Outbox recovery failed: " + recovered.stderr)
            delivered = json.loads(recovered.stdout)
            player_stats = delivered["statistics"]["players"][0]
            require(delivered["complete"] and delivered["sealedStream"] and delivered["acknowledged"] == 6 and not delivered["statistics"]["pendingTelemetry"],
                    "Separate recovery process drains the durable journal after API restart and seals its exact boundary")
            require((player_stats["ammoUsed"], player_stats["shotsHit"], player_stats["kills"], player_stats["hitsReceived"], player_stats["damageTaken"], player_stats["health"], player_stats["accuracyPercent"]) == (2, 2, 1, 1, 20, 80, 100),
                    "Recovered geometric combat preserves every requested statistic without double counting the lost-response prefix")
            history = request("GET", stream_path + "/events?limit=500")
            require(sum(event["kind"] == "StreamCombatRecorded" for event in history) == 6 and sum(event["kind"] == "CombatStreamSealed" for event in history) == 1,
                    "Six ordered reports and one seal remain in durable event history")
            retry = subprocess.run(relay_args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            require(retry.returncode == 0 and json.loads(retry.stdout)["statistics"] == delivered["statistics"], "Running recovery again returns unchanged sealed statistics")
        except BaseException:
            log.flush()
            diagnostic = (test_directory / "server.log").read_text(encoding="utf-8", errors="replace")
            for token in tokens.values():
                diagnostic = diagnostic.replace(token, "[redacted]")
            print(diagnostic)
            raise
        finally:
            if process.poll() is None:
                stop(process)
finally:
    temporary.cleanup()

print(f"All {checks} HTTP assertions passed; this is not a headset or gameplay load test.")
