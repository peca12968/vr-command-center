"""Exercise the real HTTP API using an isolated process and temporary mission data."""

import base64
import copy
import hashlib
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
import csv
import io
import zipfile
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
api_exe = os.environ.get("VR_COMMAND_API_EXE")
api_path = Path(api_exe or os.environ.get("VR_COMMAND_API_DLL", ROOT / "src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll")).resolve()
if not api_path.is_file():
    raise SystemExit("Build Release or point VR_COMMAND_API_EXE to an extracted management service binary.")
api_command = [str(api_path)] if api_exe else ["dotnet", str(api_path)]

with socket.socket() as reservation:
    reservation.bind(("127.0.0.1", 0))
    port = reservation.getsockname()[1]
base_url = f"http://127.0.0.1:{port}"
checks = 0
tokens = {name: secrets.token_urlsafe(32) for name in ["Master", "GameServer", *[f"Room{i}" for i in range(1, 6)]]}


def request(method, path, body=None, expected=200, identity="Master", request_id=None, admission_id=None, raw=False):
    global checks
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if admission_id is not None:
        headers["If-Match-Admission"] = admission_id
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
        if response.status not in (expected if isinstance(expected, tuple) else (expected,)):
            raise AssertionError(f"{method} {path}: expected {expected}, got {response.status}: {payload!r}")
    checks += 1
    if raw:
        return payload, response.headers
    return json.loads(payload) if payload else None


def require(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1
    print("PASS:", message)


def check_venue_deployment(mission_id):
    rooms = list(range(1, 6))
    route = "/api/mr-deployment/venue-check"
    session = request("POST", "/api/sessions", {"missionId": mission_id, "mode": "Linked", "roomIds": rooms}, 201)
    session_path = "/api/sessions/" + session["id"]
    markers = [{"room": {"x": x, "z": z}, "tracking": {"x": x + 1, "z": z}} for x, z in [(-2,-2),(2,-2),(-2,2)]]
    plans = {room: json.dumps(request("POST", "/api/room-alignment", {"roomId": room, "markers": markers})).encode() for room in rooms}
    pins = {f"room{room}": hashlib.sha256(plan).hexdigest() for room, plan in plans.items()}
    pin = {"commandId": str(uuid.uuid4()), "action": "SetRoomAlignment", "roomAlignment": pins}
    encode = lambda data: base64.b64encode(data).decode()
    bundle = {"topology": "Linked", "rooms": [{"roomId": room, "sessionId": session["id"],
        "alignmentFile": encode(plans[room]), "connectionFiles": [encode(b"{}")]*5} for room in rooms]}
    for actor, code in [(None,401),("Room1",403),("GameServer",403)]:
        request("POST", route, bundle, code, identity=actor)
    request("POST", route, {**bundle, "rooms": bundle["rooms"][:-1]}, 400)
    request("POST", route, {**bundle, "rooms": [*bundle["rooms"][:-1], bundle["rooms"][0]]}, 400)
    request("POST", route, {**bundle, "topology": "Independent"}, 400)
    oversized = copy.deepcopy(bundle)
    oversized["rooms"][0]["connectionFiles"][0] = encode(b"x" * 2049)
    request("POST", route, oversized, 400)
    oversized["rooms"][0]["alignmentFile"] = encode(b"x" * (180 * 1024))
    request("POST", route, oversized, 400)
    require({seat["status"] for seat in request("POST", route, bundle)["seats"]} == {"alignment-not-locked"},
            "Master-only venue check bounds its inputs and identifies the unlocked rooms")
    for room in rooms:
        for seat in range(5):
            session = request("POST", session_path+"/players", {"roomId": room, "playerId": str(uuid.uuid4()),
                "name": f"Venue {room}/{seat+1}", "headset": "Quest3"}, identity=f"Room{room}")
    session = request("POST", session_path+"/commands", pin)["session"]
    for item in bundle["rooms"]:
        room = item["roomId"]
        players = [p for p in session["players"] if p["roomId"] == room]
        zipped, _ = request("POST", session_path+f"/rooms/{room}/join-ticket-bundle", {"address": "192.0.2.10", "port": 7777,
            "players": [{"playerId": p["id"], "admissionId": p["admissionId"]} for p in players]}, raw=True, identity=f"Room{room}")
        with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
            item["connectionFiles"] = [encode(archive.read(f"room-{room:02}-seat-{seat:02}.json")) for seat in range(1,6)]
    raw, headers = request("POST", route, {**bundle, "rooms": bundle["rooms"][::-1]}, raw=True)
    result = json.loads(raw)
    require(headers["Cache-Control"] == "no-store" and result["allMatched"] and result["topology"] == "Linked"
            and [(s["roomId"], s["seat"]) for s in result["seats"]] == [(room, seat) for room in rooms for seat in range(5)]
            and all(s["status"] == "matched" and s["expiresAtUtc"] and set(s) == {"status","roomId","seat","expiresAtUtc"} for s in result["seats"])
            and request("GET", session_path) == session,
            "A real 25-seat venue verifies current signed files, returns only scoped statuses, and writes no session event")
    invalid = copy.deepcopy(bundle)
    invalid["rooms"][0]["alignmentFile"] = encode(plans[1]+b"\n")
    config = json.loads(base64.b64decode(invalid["rooms"][1]["connectionFiles"][1]))
    original = config["joinTicket"].split(".")
    original[2] = ("B" if original[2][0] == "A" else "A") + original[2][1:]
    config["joinTicket"] = ".".join(original)
    invalid["rooms"][1]["connectionFiles"][1] = encode(json.dumps(config).encode())
    player = next(p for p in session["players"] if p["roomId"] == 3 and p["seat"] == 2)
    request("DELETE", session_path+"/players/"+player["id"], expected=204, admission_id=player["admissionId"])
    missing = request("POST", route, invalid)
    require(not missing["allMatched"] and missing["seats"][12]["status"] == "seat-unavailable", "A vacant current roster seat cannot pass using a previously signed connection file")
    current = request("POST", session_path+"/players", {"roomId": 3, "playerId": player["id"], "name": "Renewed", "headset": "Quest3"})
    rejected = request("POST", route, invalid)
    require(not rejected["allMatched"] and rejected["seats"][6]["status"] == "ticket-invalid"
            and rejected["seats"][12]["status"] == "admission-changed"
            and all(s["status"] == "alignment-hash-mismatch" for s in rejected["seats"][:5])
            and request("GET", session_path) == current,
            "One venue check diagnoses forged signatures, changed admissions and changed original alignment bytes together")
    request("POST", session_path+"/commands", {"commandId": str(uuid.uuid4()), "action": "End"})
    require({s["status"] for s in request("POST", route, bundle)["seats"]} == {"session-unavailable"}, "Ended venues fail verification even with formerly valid signed files")


def check_independent_set(mission_id, other_mission_id, invalid_mission_id):
    path = "/api/sessions/independent-set"
    body = {"missionId": mission_id}
    request("POST", path, body, 400)
    request("POST", path, body, 403, identity="Room1", request_id=str(uuid.uuid4()))
    request("POST", path, body, 403, identity="GameServer", request_id=str(uuid.uuid4()))
    assert request("GET", "/api/sessions") == []
    keys = [str(uuid.uuid4()), str(uuid.uuid4())]
    with ThreadPoolExecutor(max_workers=2) as tasks:
        results = list(tasks.map(lambda key: request("POST", path, body, (201,409), request_id=key), keys))
    success = next(index for index, value in enumerate(results) if "sessions" in value)
    original = results[success]["sessions"]
    ids = [session["id"] for session in original]
    require(len(ids) == len(set(ids)) == 5 and [s["roomIds"] for s in original] == [[room] for room in range(1,6)]
            and all(s["state"] == "Preparing" and s["mode"] == "Independent" and s["mission"]["id"] == mission_id
                    and s["environment"]["mode"] == "MR" for s in original)
            and results[1-success]["code"] == "independent-rooms-occupied" and results[1-success]["roomIds"] == list(range(1,6)),
            "Two distinct requests reserve at most one complete five-room set using the saved MR mission")
    retry_key = keys[success]
    request("POST", path, {"missionId":other_mission_id}, 409, request_id=retry_key)
    request("POST", "/api/sessions", {"missionId":mission_id,"mode":"Independent","roomIds":[1]}, 409, request_id=retry_key)
    room_events, _ = request("GET", f"/api/sessions/{ids[0]}/events", identity="Room1", raw=True)
    require(all(other.encode() not in room_events for other in ids[1:]), "A room's creation event carries no other room's session ID")
    def end(sid):
        request("POST", f"/api/sessions/{sid}/commands", {"commandId":str(uuid.uuid4()),"action":"End"})
    end(ids[0])
    replacement = request("POST", "/api/sessions", {"missionId":other_mission_id,"mode":"Independent","roomIds":[1]}, 201)
    retry = request("POST", path, body, request_id=retry_key)
    require(retry["duplicate"] and [s["id"] for s in retry["sessions"]] == ids and retry["sessions"][0]["state"] == "Ended"
            and request("GET", "/api/rooms")[0]["sessionId"] == replacement["id"],
            "An archived set receipt returns all original IDs while a replacement room stays reserved")
    for sid in [replacement["id"], *ids[1:]]:
        end(sid)
    assignments = [{"roomId": room, "missionId": mission_id if room % 2 else other_mission_id} for room in range(1, 6)]
    distinct = {"rooms": assignments}
    mixed_key = str(uuid.uuid4())
    for invalid in [{"rooms": assignments[:-1]}, {"rooms": [*assignments[:-1], assignments[0]]},
                    {"rooms": [None, *assignments[1:]]}, {"missionId": mission_id, **distinct}]:
        request("POST", path, invalid, 400, request_id=mixed_key)
    request("POST", path, {"rooms": [*assignments[:-1], {"roomId": 5, "missionId": str(uuid.uuid4())}]}, 404, request_id=mixed_key)
    request("POST", path, distinct, 403, identity="Room1", request_id=mixed_key)
    invalid_room = [*assignments[:3], {"roomId": 4, "missionId": invalid_mission_id}, assignments[4]]
    refusal = request("POST", path, {"rooms": invalid_room}, 400, request_id=mixed_key)
    require(refusal["roomId"] == 4 and refusal["layout"]["canStart"] is False,
            "Server-side layout refusal identifies the exact invalid assigned room")
    require(request("GET", "/api/sessions") == [], "Invalid and unauthorized room assignments reserve no rooms")
    mixed = request("POST", path, {"rooms": list(reversed(assignments))}, 201, request_id=mixed_key)
    require([s["roomIds"] for s in mixed["sessions"]] == [[room] for room in range(1, 6)]
            and [s["mission"]["id"] for s in mixed["sessions"]] == [a["missionId"] for a in assignments]
            and [s["environment"]["mode"] for s in mixed["sessions"]] == ["MR", "VR", "MR", "VR", "MR"],
            "Explicit room assignments pin different VR and MR mission versions in canonical room order")
    repeat = request("POST", path, distinct, request_id=mixed_key)
    require(repeat["duplicate"] and repeat["sessions"] == mixed["sessions"], "Reordering explicit assignment rows returns the same five sessions")
    changed = {"rooms": [*assignments[:-1], {"roomId": 5, "missionId": other_mission_id}]}
    request("POST", path, changed, 409, request_id=mixed_key)
    require(request("POST", path, distinct, request_id=mixed_key) == repeat, "A conflicting retry leaves the original room assignments intact")
    for session in mixed["sessions"]:
        end(session["id"])


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
    launch_review_instance = str(uuid.uuid4())
    environment["ControlInstanceId"] = launch_review_instance
    environment["ASPNETCORE_ENVIRONMENT"] = "Production"
    environment["Logging__LogLevel__Default"] = "Warning"
    for name, token in tokens.items():
        environment[f"OperatorKeys__{name}"] = token
    with (test_directory / "server.log").open("w", encoding="utf-8") as log:
        key_file = test_directory / "operator-keys.local.json"

        def launch(overrides=None, use_key_file=False, output=log, url=base_url):
            process_environment = environment.copy()
            args = [*api_command, "--urls", url]
            if use_key_file:
                process_environment = {key: value for key, value in process_environment.items()
                                       if not key.lower().startswith("operatorkeys__")}
                key_file.write_text(json.dumps({"OperatorKeys": tokens}), encoding="utf-8")
                args += ["--OperatorKeyFile", str(key_file)]
            if overrides:
                process_environment.update(overrides)
            return subprocess.Popen(
                args, cwd=ROOT, env=process_environment,
                stdout=output, stderr=subprocess.STDOUT,
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

        def rejected_startup(label, overrides, diagnostic, untouched=None, extra_secrets=()):
            rejection_log = test_directory / f"startup-{label}.log"
            expected = diagnostic.encode("ascii")
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                rejected_port = probe.getsockname()[1]
            with rejection_log.open("wb") as output:
                rejected = launch(overrides=overrides, output=output, url=f"http://127.0.0.1:{rejected_port}")
                try:
                    exit_code = rejected.wait(timeout=10)
                except subprocess.TimeoutExpired as error:
                    raise AssertionError(f"Startup case {label} did not exit in 10 seconds. "
                                         f"Expected diagnostic present: {expected in rejection_log.read_bytes()}.") from error
                finally:
                    if rejected.poll() is None:
                        stop(rejected)
            message = rejection_log.read_bytes()
            with socket.socket() as probe:
                probe.settimeout(1)
                port_closed = probe.connect_ex(("127.0.0.1", rejected_port)) != 0
            require(exit_code == 1 and expected in message and b"Unhandled exception" not in message and port_closed
                    and not any(key and key.encode("ascii") in message for key in [*tokens.values(), *extra_secrets])
                    and (untouched is None or not untouched.exists()),
                    f"Startup case {label} exits with a safe diagnostic and leaves its endpoint closed")

        for label, invalid, diagnostic in [
            ("missing-credential", {"OperatorKeys__Master": ""}, "OperatorKeys:Master must be a unique credential"),
            ("weak-credential", {"OperatorKeys__Master": "short"}, "OperatorKeys:Master must be a unique credential"),
            ("duplicate-credential", {"OperatorKeys__Room1": tokens["Master"]}, "Operator credentials must be distinct across consoles."),
            ("unknown-credential", {"OperatorKeys__Room9": secrets.token_urlsafe(32)}, "Unknown OperatorKeys configuration name."),
        ]:
            invalid_data = test_directory / label
            rejected_startup(label, {**invalid, "DataDirectory": str(invalid_data / "missions"),
                                     "SessionDataDirectory": str(invalid_data / "sessions")},
                             diagnostic, untouched=invalid_data, extra_secrets=invalid.values())

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
            layout_body = {"experienceMode": "VR", "mode": "Independent", "enemyCount": 8, "props": []}
            request("POST", "/api/mission-layout", layout_body, 401, identity=None)
            request("POST", "/api/mission-layout", layout_body, 403, identity="Room1")
            request("POST", "/api/mission-layout", layout_body, 403, identity="GameServer")
            layout = request("POST", "/api/mission-layout", layout_body)
            wall = [{"assetId": "sandbag", "position": {"x": x, "y": 0, "z": -1}, "yawDegrees": 0}
                    for x in range(-5, 6, 2)]
            separated = request("POST", "/api/mission-layout", {**layout_body, "props": wall})
            require(separated["canStart"] and separated["routePreview"] == {"step": 0.5, "targetZ": 0,
                    "seats": [{"seat": seat, "path": []} for seat in range(5)]},
                    "Layout HTTP reports five isolated sampled routes while allowing an intentional barricade")
            opening = request("POST", "/api/mission-layout", {**layout_body, "mode": "Linked",
                              "props": [prop for prop in wall if prop["position"]["x"] != 1]})
            require(opening["canStart"] and all(row["path"][-1]["z"] == 0 for row in opening["routePreview"]["seats"]),
                    "Removing one bag produces a sampled route from each seat to the midfield")
            narrow = [{"assetId": "barrel" if x == -1.4 else "sandbag", "position": {"x": x, "y": 0, "z": -1}, "yawDegrees": 0}
                      for x in (-4.75, -2.75, -1.4, .75, 2.75, 4.75)]
            refined = request("POST", "/api/mission-layout", {**layout_body, "props": narrow})
            linked_refined = request("POST", "/api/mission-layout", {**layout_body, "props": narrow, "mode": "Linked"})
            require(refined["canStart"] and linked_refined["canStart"]
                    and refined["routePreview"] == linked_refined["routePreview"]
                    and refined["routePreview"]["step"] == .5
                    and all(row["sampleStep"] == .125 and row["path"][-1]["z"] == 0
                            for row in refined["routePreview"]["seats"]),
                    "Fine offset routes retain the base preview step and use the same room geometry in both topologies")
            require(layout["version"] == 1 and layout["canStart"] and layout["enemyCapacityPerRoom"] == 117 and len(layout["spawns"]) == 5,
                    "Authenticated draft preflight uses actual room and admission geometry")
            blocked_prop = {"assetId": "barrel", "position": {"x": -3, "y": 0, "z": -3}, "yawDegrees": 0}
            blocked = request("POST", "/api/mission-layout", {**layout_body, "props": [blocked_prop]})
            require(not blocked["canStart"] and any(issue["code"] == "SpawnBlocked" and issue["seat"] == 0 for issue in blocked["issues"]),
                    "Draft report identifies the exact blocked admission seat without persisting a mission")
            unknown = request("POST", "/api/mission-layout", {**layout_body, "props": [{**blocked_prop, "assetId": "unknown"}]})
            require(unknown["issues"][0]["code"] == "UnsupportedAsset", "Unsupported VR content is reported rather than launched")
            mr_layout = request("POST", "/api/mission-layout", {**layout_body, "experienceMode": "MR", "props": [blocked_prop]})
            require(mr_layout["applies"] and mr_layout["profile"] == "mr-room-v1" and not mr_layout["canStart"]
                    and any(issue["code"] == "SpawnBlocked" for issue in mr_layout["issues"]),
                    "MR preflight checks virtual spawn space without using device calibration")
            request("POST", "/api/mission-layout", {**layout_body, "props": [blocked_prop] * 501}, 400)
            require(request("GET", "/api/missions") == [], "Draft validation creates no library rows")
            draft = json.loads((ROOT / "examples/mission.json").read_text(encoding="utf-8"))
            mission_key = str(uuid.uuid4())
            mission = request("POST", "/api/missions", draft, 201, request_id=mission_key)
            loaded = request("GET", f"/api/missions/{mission['id']}")
            require(loaded["definition"] == draft, "Mission round-trips through JSON persistence")
            for role in ["Master", "Room1", "GameServer"]:
                require(request("GET", f"/api/missions/{mission['id']}/layout?mode=Linked", identity=role)["canStart"],
                        "Saved shared-template layout follows the existing read policy for " + role)
            request("GET", f"/api/missions/{mission['id']}/layout?mode=999", expected=400)
            require(len(request("GET", "/api/missions")) == 1, "Saved mission appears in list")
            request("POST", "/api/missions", draft, 403, identity="Room1")
            request("POST", "/api/missions", draft, 403, identity="GameServer")
            request("POST", "/api/missions", {**draft, "durationSeconds": 0}, 400)
            require(request("POST", "/api/missions", draft, 201, request_id=mission_key) == mission, "Mission creation response can be retried with its original durable key")
            request("POST", "/api/missions", {**draft, "name": "Changed request"}, 409, request_id=mission_key)
            revisions_path = f"/api/missions/{mission['id']}/revisions"
            revision_draft = {**draft, "name": "Second version", "durationSeconds": 1200,
                "environment": {**draft["environment"], "weather": "Storm", "timeOfDay": "Night", "lightning": True}}
            revision_key = str(uuid.uuid4())
            request("POST", revisions_path, revision_draft, 403, identity="Room1", request_id=revision_key)
            request("POST", revisions_path, revision_draft, 403, identity="GameServer", request_id=revision_key)
            request("POST", revisions_path, revision_draft, 401, identity=None, request_id=revision_key)
            request("POST", revisions_path, revision_draft, 400)
            request("POST", revisions_path, revision_draft, 400, request_id="bad-key")
            revision = request("POST", revisions_path, revision_draft, 201, request_id=revision_key)
            require(request("GET", f"/api/missions/{mission['id']}") == mission and revision["definition"] == revision_draft,
                    "Revision HTTP saves new conditions without changing the original mission")
            history = request("GET", f"/api/missions/{mission['id']}/history")
            require(history["headId"] == revision["id"] and [row["number"] for row in history["versions"]] == [2, 1], "Mission history exposes a single ordered immutable lineage")
            revision_info = request("GET", f"/api/missions/{revision['id']}/version")
            require(revision_info["seriesId"] == mission["id"] and revision_info["previousId"] == mission["id"] and revision_info["author"]["role"] == "Master",
                    "Revision metadata binds its exact parent and authenticated author")
            request("POST", revisions_path, revision_draft, 409, request_id=str(uuid.uuid4()))
            concurrent_path = f"/api/missions/{revision['id']}/revisions"
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda index: request("POST", concurrent_path, {**draft, "name": f"Concurrent revision {index}"}, (201, 409), request_id=str(uuid.uuid4())), range(8)))
            head = next(row for row in results if "id" in row)
            require(sum("id" in row for row in results) == 1, "Concurrent revision HTTP requests from the same base accept one next version")
            require(request("POST", revisions_path, revision_draft, 201, request_id=revision_key) == revision,
                    "Accepted revision retry confirms its old result after the head has advanced")
            require(len(request("GET", "/api/mission-library")) == 1 and request("GET", "/api/mission-library")[0]["mission"]["id"] == head["id"],
                    "Mission planner catalog returns current heads without downloading all version definitions")
            first_page = request("GET", f"/api/missions/{mission['id']}/history?limit=1")
            second_page = request("GET", f"/api/missions/{mission['id']}/history?limit=1&before={first_page['nextBefore']}")
            require(first_page["versions"][0]["number"] == 3 and second_page["versions"][0]["number"] == 2,
                    "HTTP history pagination has no duplicate revision at its boundary")
            request("GET", f"/api/missions/{mission['id']}/history?limit=101", expected=400)
            request("GET", f"/api/missions/{mission['id']}/history?before=0", expected=400)
            request("GET", "/api/mission-library", expected=401, identity=None)
            require(request("GET", "/api/missions") and request("GET", f"/api/missions/{mission['id']}/history", identity="Room1")["headId"] == head["id"],
                    "Global mission library remains readable by room operators while authoring stays restricted")
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
            endpoint_draft = {"version": 1, "streamId": str(uuid.uuid4()), "address": "127.0.0.1", "port": 17777}
            request("GET", own_path + "/connection-endpoint", expected=401, identity=None)
            request("GET", own_path + "/connection-endpoint", expected=403, identity="Room2")
            request("GET", own_path + "/connection-endpoint", expected=403, identity="GameServer")
            request("GET", own_path + "/connection-endpoint", expected=404, identity="Room1")
            request("PUT", own_path + "/connection-endpoint", endpoint_draft, 403, identity="Master")
            request("PUT", own_path + "/connection-endpoint", endpoint_draft, 403, identity="Room1")
            request("GET", own_path + "/readiness", expected=401, identity=None)
            request("GET", own_path + "/readiness", expected=403, identity="Room2")
            request("GET", own_path + "/readiness", expected=403, identity="GameServer")
            readiness = request("GET", own_path + "/readiness", identity="Room1")
            require(readiness["version"] == 1 and readiness["sourceState"] == "NoRecording"
                    and readiness["players"][0]["playerId"] == first_player_id and not readiness["players"][0]["canParticipate"]
                    and readiness["players"][0]["admissionId"] == request("GET", own_path)["players"][0]["admissionId"],
                    "Readiness requires an actual accepted world and preserves the current admission")
            require(not {"head", "left", "right", "ticket", "gameServerKey"}.intersection(readiness["players"][0]),
                    "Control readiness contains no pose coordinates, player ticket or server credential")
            request("GET", "/api/rooms/readiness", expected=401, identity=None)
            request("GET", "/api/rooms/readiness", expected=403, identity="GameServer")
            room_overview = request("GET", "/api/rooms/readiness", identity="Room1")
            require(room_overview == {"version": 1, "rooms": [{"roomId": 1, "sessionId": independent[0]["id"],
                    "sessionSequence": readiness["sessionSequence"], "registered": 1, "simulatedReady": 0,
                    "trackedReady": 0, "sourceState": "NoRecording", "sourceAgeMilliseconds": None, "venueBeginReady": False}]},
                    "Room controller gets only its room's bounded aggregate without player identities")
            master_overview = request("GET", "/api/rooms/readiness")
            require([row["roomId"] for row in master_overview["rooms"]] == [1, 2, 3, 4, 5]
                    and [row["sessionId"] for row in master_overview["rooms"]] == [s["id"] for s in independent],
                    "Master room readiness identifies all five independent active sessions")
            join_key = str(uuid.uuid4())
            with ThreadPoolExecutor(max_workers=8) as pool:
                joins = list(pool.map(lambda _: request("POST", own_path + "/players", room_player, identity="Room1", request_id=join_key), range(8)))
            require(all(len(value["players"]) == 2 and value["sequence"] == 3 for value in joins), "Concurrent HTTP join retries retain one roster entry and seat")
            request("POST", own_path + "/players", {**room_player, "name": "Changed"}, 409, identity="Room1", request_id=join_key)
            request("POST", own_path + "/players", room_player, 409, request_id=join_key)
            request("POST", own_path + "/players", room_player, 403, identity="Room2", request_id=join_key)
            request("POST", own_path + "/players", room_player, 409, identity="Room1", request_id=create_key)
            room_admission = next(player["admissionId"] for player in joins[0]["players"] if player["id"] == room_player["playerId"])
            invitation = request("POST", own_path + "/players/" + room_player["playerId"] + "/join-ticket", identity="Room1", admission_id=room_admission)
            require(len(invitation["ticket"]) < 256, "Headset receives a compact player-only connection ticket")
            validate = {"sessionId": independent[0]["id"], "ticket": invitation["ticket"], "protocolVersion": 2}
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
                list(pool.map(lambda _: request("DELETE", own_path + "/players/" + room_player["playerId"], expected=204, identity="Room1", request_id=leave_key, admission_id=room_admission), range(8)))
            require(len(request("GET", own_path)["players"]) == 1, "Concurrent HTTP leave retries remove the player once")
            request("DELETE", own_path + "/players/" + player["playerId"], expected=409, identity="Room1", request_id=leave_key, admission_id=room_admission)
            require(len(request("POST", own_path + "/players", room_player, identity="Room1", request_id=join_key)["players"]) == 1,
                    "Delayed HTTP join acknowledgment does not resurrect a departed player")
            request("POST", "/api/player-tickets/validate", validate, 403, identity="GameServer")
            # A cryptographically valid old ticket must not revive when the same identity/seat is reused.
            rejoined = request("POST", own_path + "/players", room_player, identity="Room1")
            replacement = next(entry for entry in rejoined["players"] if entry["id"] == room_player["playerId"])
            require(replacement["admissionId"] != room_admission and replacement["seat"] == approved["seat"],
                    "Same-ID same-seat reentry has a new durable admission")
            request("POST", "/api/player-tickets/validate", validate, 403, identity="GameServer")
            request("POST", "/api/player-tickets/validate", {key: value for key, value in validate.items() if key != "protocolVersion"}, 400, identity="GameServer")
            request("POST", own_path + "/players/" + room_player["playerId"] + "/join-ticket", expected=400, identity="Room1")
            request("POST", own_path + "/players/" + room_player["playerId"] + "/join-ticket", expected=400, identity="Room1", admission_id="not-a-uuid")
            request("POST", own_path + "/players/" + room_player["playerId"] + "/join-ticket", expected=409, identity="Room1", admission_id=room_admission)
            stale_bundle = {"address": "192.168.1.100", "port": 7777, "players": [
                {"playerId": p["id"], "admissionId": p["admissionId"]} for p in joins[0]["players"]]}
            request("POST", own_path + "/rooms/1/join-ticket-bundle", stale_bundle, 409, identity="Room1")
            fresh = request("POST", own_path + "/players/" + room_player["playerId"] + "/join-ticket", identity="Room1", admission_id=replacement["admissionId"])
            current_claims = request("POST", "/api/player-tickets/validate", {**validate, "ticket": fresh["ticket"]}, identity="GameServer")
            require(fresh["ticket"].startswith("v2.") and current_claims["admissionId"] == replacement["admissionId"]
                    and current_claims["throughSequence"] == rejoined["sequence"] and current_claims["expiresAtUtc"] == fresh["expiresAtUtc"],
                    "V2 validation returns exact admission, roster observation and expiry")
            before_fence = request("GET", own_path)
            request("DELETE", own_path + "/players/" + room_player["playerId"], expected=400, identity="Room1")
            request("DELETE", own_path + "/players/" + room_player["playerId"], expected=400, identity="Room1", admission_id=str(uuid.UUID(int=0)))
            request("DELETE", own_path + "/players/" + room_player["playerId"], expected=409, identity="Room1", admission_id=room_admission)
            request("DELETE", own_path + "/players/" + room_player["playerId"], expected=204, identity="Room1", request_id=leave_key, admission_id=room_admission)
            request("DELETE", own_path + "/players/" + room_player["playerId"], expected=409, identity="Room1", request_id=leave_key, admission_id=replacement["admissionId"])
            require(request("GET", own_path) == before_fence, "Rejected stale removals and accepted old retries do not mutate a replacement admission")
            request("DELETE", own_path + "/players/" + room_player["playerId"], expected=204, identity="Room1", admission_id=replacement["admissionId"])
            command = {"commandId": str(uuid.uuid4()), "action": "SetEnvironment", "environment": draft["environment"]}
            request("POST", own_path + "/commands", command, identity="Room1")
            request("POST", own_path + "/commands", command, 409)  # another identity cannot claim this retry
            own_events = request("GET", own_path + "/events", identity="Room1")
            require(own_events[-1]["actor"]["id"] == "room-1" and own_events[-1]["schemaVersion"] == 7,
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
            for room in range(1, 6):
                roster = sorted((p for p in current["players"] if p["roomId"] == room), key=lambda p: p["seat"])
                route = f"{session_path}/rooms/{room}/join-ticket-bundle"
                bundle = {"address": "192.168.1.100", "port": 7777, "players": [
                    {"playerId": p["id"], "admissionId": p["admissionId"]} for p in roster]}
                if room == 1:
                    request("POST", route, bundle, 401, identity=None)
                    request("POST", route, bundle, 403, identity="Room2")
                    request("POST", route, bundle, 403, identity="GameServer")
                    request("POST", route, {**bundle, "address": "127.1"}, 400)
                    request("POST", route, {**bundle, "port": 65536}, 400)
                    request("POST", route, {**bundle, "players": []}, 400)
                    request("POST", route, {**bundle, "players": [bundle["players"][0]] * 2}, 400)
                    request("POST", route, {**bundle, "players": bundle["players"][:-1]}, 409)
                payload, headers = request("POST", route, bundle, identity=f"Room{room}" if room != 5 else "Master", raw=True)
                require(headers.get("Cache-Control") == "no-store" and headers.get("Content-Type") == "application/zip"
                        and f"room-{room:02}-connections.zip" in headers.get("Content-Disposition", ""),
                        "Room bundle is a private ZIP download")
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    names = [f"room-{room:02}-seat-{p['seat'] + 1:02}.json" for p in roster]
                    require(archive.namelist() == names and len(names) == 5, "Each ZIP has only its five seat files")
                    for name, participant in zip(names, roster):
                        config = json.loads(archive.read(name))
                        require(set(config) == {"role", "address", "port", "joinTicket"} and config["role"] == "Client"
                                and config["address"] == bundle["address"] and config["port"] == bundle["port"],
                                "Seat file retains the four-field player connection contract")
                        claims = request("POST", "/api/player-tickets/validate", {"sessionId": session["id"],
                            "ticket": config["joinTicket"], "protocolVersion": 2}, identity="GameServer")
                        require(claims["playerId"] == participant["id"] and claims["admissionId"] == participant["admissionId"]
                                and claims["roomId"] == room and claims["seat"] == participant["seat"],
                                "Seat file admits the exact current player in its own room")
            require(request("GET", session_path) == current, "Room bundles leave the roster and session sequence unchanged")
            require(current["state"] == "Preparing" and current["startedAtUtc"] is None,
                    "Creating a session does not start the mission")
            request("POST", session_path + "/players/" + player["playerId"] + "/join-ticket", expected=404)
            require(request("GET", session_path, identity="Room1")["id"] == session["id"],
                    "Room controllers may read the shared linked scene")
            request("POST", session_path + "/commands", {"commandId": str(uuid.uuid4()), "action": "Begin", "actor": {"id": "master", "role": "Master"}}, 403, identity="Room1")
            request("POST", session_path + "/commands", {"commandId": str(uuid.uuid4()), "action": "Begin"}, 403, identity="GameServer")
            request("DELETE", session_path, expected=403, identity="Room1")
            rejected_startup("session-writer-conflict", {}, "Cannot acquire the session event-store writer lease.")
            rejected_startup("mission-writer-conflict", {"SessionDataDirectory": str(test_directory / "competing-sessions")},
                             "Cannot acquire the mission library writer lease.")
            require(request("GET", session_path) == current, "Rejected competing process leaves active state intact")
            request("POST", session_path + "/players", {**player, "playerId": str(uuid.uuid4())}, 409)
            require(all(r["playerCount"] == 5 for r in request("GET", "/api/rooms")), "Every room remains at capacity after overflow rejection")
            request("DELETE", session_path + "/players/" + current["players"][0]["id"], expected=403, identity="Room2")
            request("DELETE", session_path + "/players/" + current["players"][0]["id"], expected=204, identity="Room1", admission_id=current["players"][0]["admissionId"])
            request("POST", session_path + "/players", {**player, "roomId": 2}, 403, identity="Room1")
            request("POST", session_path + "/players", player, identity="Room1")
            live_admission = next(entry["admissionId"] for entry in request("GET", session_path)["players"] if entry["id"] == player["playerId"])
            live_ticket = request("POST", session_path + "/players/" + player["playerId"] + "/join-ticket", identity="Room1", admission_id=live_admission)
            live_validation = {"sessionId": session["id"], "ticket": live_ticket["ticket"], "protocolVersion": 2}
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
            request("GET", session_path + "/report.csv", expected=409)
            request("GET", session_path + "/reports.zip", expected=409)
            request("GET", session_path + "/report.csv", expected=403, identity="GameServer")
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
            require(len(combat_events) == 7 and all(event["actor"]["id"] == "game-server" and event["schemaVersion"] == 7 for event in combat_events),
                    "Combat and management share a versioned, authenticated event stream")
            with closing(sqlite3.connect(test_directory / "sessions/events.db")) as database:
                stored = database.execute("SELECT COUNT(*) FROM session_events WHERE session_id=?", (session["id"],)).fetchone()[0]
            require(stored == current["sequence"], "SQLite stores exactly one row per accepted management or combat event")
            require(not any(token in json.dumps(events) for token in tokens.values()),
                    "Event history contains console identity without credential values")
            require(live_ticket["ticket"] not in json.dumps(events), "Player admission ticket is never written into event history")
            require(len(events) == current["sequence"] and [e["sequence"] for e in events] == list(range(1, len(events) + 1)),
                    "Ordered event stream covers accepted mutations without gaps")
            payload, headers = request("GET", session_path + "/overview", raw=True)
            require(len(events) > 20 and headers["Cache-Control"] == "no-store"
                    and json.loads(payload) == {"session": current, "statistics": statistics, "recentEvents": events[-20:]},
                    "Operator overview returns the same revision, statistics and exact last twenty events")
            request("GET", session_path + "/overview", expected=401, identity=None)
            request("GET", f"/api/sessions/{independent[1]['id']}/overview", expected=403, identity="Room1")
            page = request("GET", session_path + "/events?after=1&limit=2")
            require([e["sequence"] for e in page] == [2, 3], "HTTP event cursor is exclusive")
            request("GET", session_path + "/events?after=-1", expected=400)
            request("GET", session_path + "/events?limit=501", expected=400)

            stop(process)
            process = launch(use_key_file=True)
            wait_ready(process)
            recovered = request("GET", session_path)
            require(recovered == current, "Process restart reconstructs active state, players and control settings")
            require(request("GET", f"/api/missions/{mission['id']}") == mission and request("GET", "/api/mission-library")[0]["mission"]["id"] == head["id"],
                    "API restart retains old mission snapshots and the current library head")
            require(request("POST", revisions_path, revision_draft, 201, request_id=revision_key) == revision
                    and request("POST", "/api/missions", draft, 201, request_id=mission_key) == mission,
                    "Mission creation and revision request receipts survive API process restart")
            require(recovered["mission"]["id"] == mission["id"] and recovered["mission"]["definition"] == draft,
                    "Existing session recovery keeps its original version despite later library revisions")
            old_archive = request("GET", own_path)
            require(request("POST", "/api/sessions", creation_body, 201, request_id=create_key) == old_archive,
                    "HTTP creation retry after restart returns its archived session despite a new linked reservation")
            require(request("POST", own_path + "/players", room_player, identity="Room1", request_id=join_key) == old_archive,
                    "HTTP join key is recovered from SQLite and remains valid after archival")
            request("DELETE", own_path + "/players/" + room_player["playerId"], expected=204, identity="Room1", request_id=leave_key, admission_id=room_admission)
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
            request("POST", session_path + "/rooms/5/join-ticket-bundle", bundle, 409, identity="Room5")
            request("POST", "/api/player-tickets/validate", live_validation, 403, identity="GameServer")
            require(request("GET", session_path + "/statistics")["players"] == statistics["players"], "Ended session preserves combat statistics")
            final_csv, final_headers = request("GET", session_path + "/report.csv", raw=True)
            final_rows = list(csv.DictReader(io.StringIO(final_csv.decode("utf-8-sig"), newline="")))
            require(final_csv.startswith(b"\xef\xbb\xbf") and final_headers.get_content_type() == "text/csv"
                    and final_headers["Cache-Control"] == "no-store" and "attachment;" in final_headers["Content-Disposition"],
                    "Final CSV is an authenticated UTF-8 BOM attachment with no-store caching")
            require(len(final_rows) == len(statistics["players"]) and all(row["origin"] == "Simulation" and row["reportVersion"] == "1" for row in final_rows),
                    "Final CSV includes every historical ledger player and explicit Simulation provenance")
            final_view = request("GET", session_path)
            require(all(int(row["throughSequence"]) == final_view["sequence"] and row["sessionId"] == final_view["id"] for row in final_rows),
                    "CSV identifies the same final durable session boundary")
            for row in final_rows:
                metric = next(value for value in statistics["players"] if value["playerId"] == row["playerId"])
                require(all(float(row[name]) == metric[name] for name in ("ammoUsed", "shotsHit", "kills", "damageTaken", "hitsReceived", "accuracyPercent", "health")),
                        "Parsed final CSV agrees with every accepted player statistic")
            require(request("GET", session_path + "/report.csv", identity="Room1", raw=True)[0] == final_csv,
                    "Linked room controller exports the same report under existing full-session read policy")
            scoped_url = session_path + "/rooms/1/report.csv"
            scoped, scoped_headers = request("GET", scoped_url, identity="Room1", raw=True)
            scoped_rows = list(csv.DictReader(io.StringIO(scoped.decode("utf-8-sig"))))
            require(scoped_rows == [dict(row, reportRoomId="1") for row in final_rows if row["playerRoomId"] == "1"]
                    and scoped_headers.get("Cache-Control") == "no-store"
                    and "-room-01.csv" in scoped_headers.get("Content-Disposition", ""),
                    "Room report exports only its final ledger rows with the original metadata and a marked scope")
            require(request("GET", scoped_url, raw=True)[0] == scoped, "Master downloads the same exact room report bytes")
            personal = next(row for row in final_rows if row["playerRoomId"] == "1")
            personal_url = session_path + f'/players/{personal["playerId"]}/report.csv'
            private_csv, private_headers = request("GET", personal_url, identity="Room1", raw=True)
            require(list(csv.DictReader(io.StringIO(private_csv.decode("utf-8-sig")))) == [personal]
                    and private_headers.get_content_type() == "text/csv" and private_headers["Cache-Control"] == "no-store"
                    and f'-player-{personal["playerId"]}.csv' in private_headers.get("Content-Disposition", ""),
                    "Authorized personal CSV contains exactly its original sealed row")
            require(request("GET", personal_url, raw=True)[0] == private_csv, "Master sees the same exact personal CSV bytes")
            request("GET", personal_url, identity="Room2", expected=404)
            request("GET", session_path + f"/players/{uuid.uuid4()}/report.csv", identity="Room2", expected=404)
            request("GET", personal_url, identity="GameServer", expected=403)
            request("GET", personal_url, identity=None, expected=401)
            request("GET", scoped_url, identity="Room2", expected=403)
            request("GET", scoped_url, identity="GameServer", expected=403)
            request("GET", scoped_url, identity=None, expected=401)
            request("GET", session_path + "/rooms/6/report.csv", expected=400)
            request("GET", session_path + "/report.csv", expected=401, identity=None)
            request("GET", session_path + "/report.csv", expected=403, identity="GameServer")
            reports_url = session_path + "/reports.zip"
            reports, report_headers = request("GET", reports_url, raw=True)
            prefix = f'vr-command-report-v1-{final_view["id"]}'
            expected_files = {prefix + ".csv": final_csv}
            for room in range(1, 6):
                expected_files[f"{prefix}-room-{room:02}.csv"] = request("GET", session_path + f"/rooms/{room}/report.csv", raw=True)[0]
            with zipfile.ZipFile(io.BytesIO(reports)) as archive:
                require(archive.namelist() == list(expected_files) and archive.testzip() is None
                        and all(archive.read(name) == content for name, content in expected_files.items()),
                        "Linked report ZIP contains precisely the same full and five scoped CSVs")
            require(report_headers.get_content_type() == "application/zip" and report_headers["Cache-Control"] == "no-store"
                    and f'vr-command-reports-v1-{final_view["id"]}.zip' in report_headers["Content-Disposition"],
                    "Linked report ZIP is a no-store attachment named for the exact session")
            request("GET", reports_url, expected=401, identity=None)
            request("GET", reports_url, expected=403, identity="Room1")
            request("GET", reports_url, expected=403, identity="GameServer")
            request("GET", own_path + "/reports.zip", expected=400)
            require(request("GET", session_path) == final_view, "ZIP export leaves the original session intact")
            require(report(fired)["duplicate"], "Combat report retry is available after session end")
            report({**fired, "reportId": str(uuid.uuid4()), "shotId": str(uuid.uuid4())}, 409)
            require(request("GET", "/api/sessions") == [], "Active list excludes archived sessions")
            require(len(request("GET", "/api/sessions?includeEnded=true")) == 6, "History list includes independent and linked sessions")
            require(all(r["sessionId"] is None and r["playerCount"] == 0 for r in request("GET", "/api/rooms")), "Ending releases all room reservations and player slots")
            require(len(request("GET", "/api/missions")) == 3 and len(request("GET", "/api/mission-library")) == 1, "All immutable mission revisions survive session cleanup with one current catalog head")
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
            require(request("GET", session_path + "/report.csv", raw=True)[0] == final_csv,
                    "Real HTTP CSV bytes survive API restart and operator-key rotation")
            require(request("GET", scoped_url, identity="Room1", raw=True)[0] == scoped,
                    "Scoped CSV bytes survive API restart and operator-key rotation")
            require(request("GET", personal_url, identity="Room1", raw=True)[0] == private_csv,
                    "Personal CSV bytes survive API restart and operator-key rotation")
            require(request("GET", reports_url, raw=True)[0] == reports,
                    "Linked ZIP bytes survive API restart and operator-key rotation")
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
            require(request("POST", "/api/player-tickets/validate", {"sessionId": plan["sessionId"], "ticket": client_config["joinTicket"], "protocolVersion": 2},
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
            guarded = request("POST", "/api/sessions", {"missionId": mission["id"], "mode": "Independent", "roomIds": [1]}, 201)
            guarded_path = "/api/sessions/" + guarded["id"]
            guarded_route = guarded_path + "/combat-stream/guarded-open"
            stream = {"streamId": str(uuid.uuid4()), "origin": "Simulation", "missionClockVersion": 1, "roomEnemyPolicyVersion": 1}
            request("POST", guarded_route, {**stream, "expectedSequence": guarded["sequence"]}, 403)
            request("POST", guarded_route, stream, 400, identity="GameServer")
            request("POST", guarded_route, {**stream, "expectedSequence": 0}, 400, identity="GameServer")
            edited = request("POST", guarded_path + "/commands", {"commandId": str(uuid.uuid4()), "action": "SetEnvironment",
                             "expectedSequence": guarded["sequence"], "environment": guarded["environment"]})["session"]
            request("POST", guarded_route, {**stream, "expectedSequence": guarded["sequence"]}, 409, identity="GameServer")
            require(request("GET", guarded_path) == edited and edited["combatStream"] is None,
                    "Guarded source conflict leaves the exact edited Preparing state unbound")
            approved = {**stream, "expectedSequence": edited["sequence"]}
            opened = request("POST", guarded_route, approved, identity="GameServer")
            latest = request("GET", guarded_path)
            require(opened["expectedSequence"] == edited["sequence"] and latest["combatStream"] == opened
                    and latest["sequence"] == edited["sequence"] + 1, "Guarded source receipt echoes the preceding session revision")
            request("POST", guarded_path + "/combat-stream", stream, 409, identity="GameServer")
            require(request("POST", guarded_route, approved, identity="GameServer") == opened
                    and request("GET", guarded_path) == latest, "Exact guarded source retry appends no event")
            request("DELETE", guarded_path, expected=204)
            venue_route = "/api/venue/combat-streams"
            prepared = request("POST", "/api/sessions/independent-set", {"missionId": mission["id"]}, 201,
                               request_id=str(uuid.uuid4()))["sessions"]
            candidates = [{"sessionId": row["id"], "streamId": str(uuid.uuid4()), "origin": "Simulation",
                           "expectedSequence": row["sequence"]} for row in prepared]
            batch = {"version": 1, "launchId": str(uuid.uuid4()), "topology": "Independent", "servers": candidates}
            request("PUT", venue_route, batch, 403)
            changed_path = "/api/sessions/" + prepared[-1]["id"]
            last = request("POST", changed_path + "/commands", {"commandId": str(uuid.uuid4()), "action": "SetEnvironment",
                           "expectedSequence": prepared[-1]["sequence"], "environment": prepared[-1]["environment"]})["session"]
            request("PUT", venue_route, batch, 409, identity="GameServer")
            originals = [request("GET", "/api/sessions/" + row["id"]) for row in prepared]
            require(originals == [*prepared[:-1], last] and all(row["combatStream"] is None for row in originals),
                    "A stale fifth candidate leaves all five original sessions unbound")
            review_path = "/api/venue/server-launch-review"
            review_targets = [{"sessionId": row["id"], "roomIds": row["roomIds"], "streamId": None, "udp": None} for row in prepared]
            review = {"version": 1, "instanceId": launch_review_instance, "launchId": batch["launchId"],
                      "topology": "Independent", "servers": review_targets[::-1]}
            request("POST", review_path, review, 403, identity="Room1")
            request("POST", review_path, review, 403, identity="GameServer")
            request("POST", review_path, {**review, "workDirectory": "private-fixture-path"}, 400)
            mismatch = request("POST", review_path, {**review, "instanceId": str(uuid.uuid4())}, 409)
            require(mismatch["code"] == "venue-launch-instance-mismatch", "Launch review rejects a different configured instance")
            inspected = request("POST", review_path, review)
            require(inspected["instanceVerified"] and inspected["launchId"] == batch["launchId"]
                    and [row["sessionId"] for row in inspected["servers"]] == [row["id"] for row in prepared]
                    and all(row["phase"] == "Preparing" and row["sourceState"] == "unbound"
                            and row["endpointState"] == "not-checked" for row in inspected["servers"]),
                    "Launch review identifies the exact five unbound Preparing sessions in room order")
            candidates[-1]["expectedSequence"] = last["sequence"]
            attached = request("PUT", venue_route, batch, identity="GameServer")
            require(attached["launchId"] == batch["launchId"]
                    and [row["sessionId"] for row in attached["servers"]] == [row["id"] for row in prepared]
                    and all(row["stream"]["venueLaunchId"] == batch["launchId"] for row in attached["servers"]),
                    "A valid venue batch returns all original source identities together")
            require(request("PUT", venue_route, {**batch, "servers": candidates[::-1]}, identity="GameServer") == attached,
                    "Reordered venue retry returns the same source receipt")
            inspected = request("POST", review_path, review)
            require([row["streamId"] for row in inspected["servers"]] == [row["streamId"] for row in candidates]
                    and all(row["sourceState"] == "original-source" and row["endpointState"] == "not-published"
                            for row in inspected["servers"]), "Launch review reads the original persisted batch before endpoint publication")
            other = request("POST", review_path, {**review, "launchId": str(uuid.uuid4())})
            require(all(row["sourceState"] == "different-source" and row["streamId"] is None for row in other["servers"]),
                    "Launch review never treats a source from a different batch as the original")
            changed_room = {**review_targets[0], "sessionId": str(uuid.uuid4())}
            absent = request("POST", review_path, {**review, "servers": [changed_room, *review_targets[1:]]})
            require(absent["servers"][0]["sourceState"] == "missing-session"
                    and absent["servers"][0]["sessionId"] == changed_room["sessionId"],
                    "Launch review does not substitute the current occupant for an unknown original session")
            require(all(request("GET", "/api/sessions/" + row["id"])["sequence"] == candidate["expectedSequence"] + 1
                        for row,candidate in zip(prepared,candidates,strict=True)), "Launch review does not append session events")
            for row in prepared:
                request("DELETE", "/api/sessions/" + row["id"], expected=204)
            require(all(row["phase"] == "Ended" and row["sourceState"] == "original-source"
                        for row in request("POST", review_path, review)["servers"]), "Launch review reads the original ended sessions")
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
            request("GET", stream_path + "/report.csv", expected=409)
            request("GET", stream_path + "/reports.zip", expected=409)
            request("GET", stream_path + "/report.csv", expected=403, identity="Room2")
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
            pending = request("GET", stream_path + "/overview", identity="Room1")
            require(pending["session"]["state"] == "Ended" and not pending["session"]["combatStream"]["sealed"]
                    and pending["statistics"] == accepted["statistics"]
                    and pending["recentEvents"][-1]["sequence"] == pending["session"]["sequence"] == pending["statistics"]["throughSequence"],
                    "Operator overview pairs pending totals with the exact accepted tail while the stream remains unsealed")
            feedback = stream_path + "/rooms/1/hardware-feedback"
            request("GET", feedback, expected=401, identity=None)
            request("GET", feedback, expected=403, identity="Room2")
            request("GET", feedback, expected=403, identity="GameServer")
            request("GET", feedback + "?after=-1", expected=400, identity="Room1")
            attached = request("GET", feedback, identity="Room1")
            payload, headers = request("GET", feedback + f"?after={ended_sequence}", identity="Room1", raw=True)
            page = json.loads(payload)
            require(attached["resetReason"] == "attached" and attached["signals"] == [] and headers["Cache-Control"] == "no-store"
                    and page["state"] == "Ended" and page["resetReason"] == "inactive" and page["signals"] == []
                    and page["throughSequence"] == attached["throughSequence"] == accepted["statistics"]["throughSequence"],
                    "Room-scoped hardware reads attach without replay and suppress late accepted reports after End")
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
            final_overview = request("GET", stream_path + "/overview", identity="Room1")
            require(final_overview["session"]["combatStream"]["sealed"] and final_overview["statistics"] == delivered["statistics"]
                    and final_overview["recentEvents"][-1]["kind"] == "CombatStreamSealed"
                    and final_overview["recentEvents"][-1]["sequence"] == final_overview["session"]["sequence"] == final_overview["statistics"]["throughSequence"],
                    "Operator overview pairs final statistics and seal in the same restored revision")
            sealed_csv, _ = request("GET", stream_path + "/report.csv", raw=True)
            sealed_rows = list(csv.DictReader(io.StringIO(sealed_csv.decode("utf-8-sig"))))
            require(len(sealed_rows) == 1 and int(sealed_rows[0]["finalStreamSequence"]) == 6
                    and sealed_rows[0]["streamId"] == first["streamId"] and sealed_rows[0]["origin"] == "Simulation",
                    "Recovered exact seal unlocks a CSV naming the precise stream and final boundary")
            require((player_stats["ammoUsed"], player_stats["shotsHit"], player_stats["kills"], player_stats["hitsReceived"], player_stats["damageTaken"], player_stats["health"], player_stats["accuracyPercent"]) == (2, 2, 1, 1, 20, 80, 100),
                    "Recovered geometric combat preserves every requested statistic without double counting the lost-response prefix")
            history = request("GET", stream_path + "/events?limit=500")
            require(sum(event["kind"] == "StreamCombatRecorded" for event in history) == 6 and sum(event["kind"] == "CombatStreamSealed" for event in history) == 1,
                    "Six ordered reports and one seal remain in durable event history")
            retry = subprocess.run(relay_args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
            require(retry.returncode == 0 and json.loads(retry.stdout)["statistics"] == delivered["statistics"], "Running recovery again returns unchanged sealed statistics")
            bad_draft = {**draft, "name": "Saved invalid layout", "props": [blocked_prop]}
            bad_mission = request("POST", "/api/missions", bad_draft, 201)
            before_rooms = request("GET", "/api/rooms")
            room = next(row["id"] for row in before_rooms if row["sessionId"] is None)
            failed_key = str(uuid.uuid4())
            rejection = request("POST", "/api/sessions", {"missionId": bad_mission["id"], "mode": "Independent", "roomIds": [room]}, 400, request_id=failed_key)
            require(not rejection["layout"]["canStart"] and any(i["code"] == "SpawnBlocked" for i in rejection["layout"]["issues"]),
                    "Server rejects an invalid saved VR mission even when the UI gate is bypassed")
            require(request("GET", "/api/rooms") == before_rooms and request("GET", f"/api/missions/{bad_mission['id']}")["definition"] == bad_draft,
                    "Rejected start leaves reservations and immutable mission content unchanged")
            denied = request("POST", "/api/sessions", {"missionId": bad_mission["id"], "mode": "Independent", "roomIds": [2]}, 403, identity="Room1")
            require("layout" not in denied, "Room scope is checked before a layout rejection can reveal operation details")
            fixed = request("POST", f"/api/missions/{bad_mission['id']}/revisions", {**bad_draft, "props": []}, 201, request_id=str(uuid.uuid4()))
            accepted = request("POST", "/api/sessions", {"missionId": fixed["id"], "mode": "Independent", "roomIds": [room]}, 201, request_id=failed_key)
            require(accepted["mission"]["id"] == fixed["id"], "An unaccepted validation failure does not consume the lifecycle idempotency key")
            request("POST", f"/api/sessions/{accepted['id']}/commands", {"commandId": str(uuid.uuid4()), "action": "End"})
            compact_props = [{"assetId": "sandbag", "position": {"x": x, "y": 0, "z": z}, "yawDegrees": 0}
                             for z in (2, 4) for x in (-3, -1, 1, 3)]
            compact_mission = request("POST", "/api/missions", {**draft, "name": "Live enemy capacity", "props": compact_props}, 201)
            compact = request("POST", "/api/sessions", {"missionId": compact_mission["id"], "mode": "Independent", "roomIds": [room]}, 201)
            compact_path = f"/api/sessions/{compact['id']}"
            update = {"commandId": str(uuid.uuid4()), "action": "SetEnemies", "expectedSequence": compact["sequence"],
                      "enemies": {"count": 85, "behavior": "Patrol", "autoAttack": False}}
            rejected = request("POST", compact_path + "/commands", update, 400)
            require(rejected["code"] == "enemy-capacity-exceeded" and rejected["maxCount"] == 84
                    and request("GET", compact_path) == compact,
                    "A rejected reinforcement names its saved layout capacity and leaves management untouched")
            update["enemies"]["count"] = 84
            result = request("POST", compact_path + "/commands", update)
            require(result["session"]["enemies"] == update["enemies"] and not result["duplicate"]
                    and request("POST", compact_path + "/commands", update)["duplicate"],
                    "Exact capacity is accepted and the same command can safely confirm its receipt")
            request("POST", compact_path + "/commands", {"commandId": str(uuid.uuid4()), "action": "End"})
            mr_environment = {**draft["environment"], "mode": "MR"}
            mr_mission = request("POST", "/api/missions", {**draft, "name": "Operator MR start", "environment": mr_environment, "props": []}, 201)
            mr = request("POST", "/api/sessions", {"missionId": mr_mission["id"], "mode": "Independent", "roomIds": [room]}, 201)
            mr_path = f"/api/sessions/{mr['id']}"
            player = {"playerId": str(uuid.uuid4()), "name": "Mixed reality player", "roomId": room}
            request("POST", mr_path + "/players", {**player, "headset": "ViveXr"}, 409)
            joined_mr = request("POST", mr_path + "/players", {**player, "headset": "Quest3"})
            begin_mr = {"commandId": str(uuid.uuid4()), "action": "Begin"}
            require(request("POST", mr_path + "/commands", begin_mr, 409)["code"] == "mr-readiness-required",
                    "MR Begin names its readiness conflict without changing generic conflict handling")
            request("POST", mr_path + "/combat-stream", {"streamId": str(uuid.uuid4()), "origin": "Simulation"}, 409, identity="GameServer")
            require(request("GET", mr_path) == joined_mr, "Rejected MR Begin and simulation attachment leave the exact Preparing roster untouched")
            mr_player = joined_mr["players"][0]
            ticket_route = f"{mr_path}/players/{mr_player['id']}/join-ticket"
            bundle_route = f"{mr_path}/rooms/{room}/join-ticket-bundle"
            bundle_request = {"address": "192.168.1.100", "port": 7777,
                              "players": [{"playerId": mr_player["id"], "admissionId": mr_player["admissionId"]}]}
            unpinned = request("POST", ticket_route, expected=409, identity=f"Room{room}", admission_id=mr_player["admissionId"])
            unpinned_bundle = request("POST", bundle_route, bundle_request, 409, identity=f"Room{room}")
            require(unpinned["code"] == unpinned_bundle["code"] == "mr-alignment-required",
                    "MR single and room-bundle ticket issuance require a locked alignment")
            alignment = {f"room{room}": "a" * 64}
            pin = {"commandId": str(uuid.uuid4()), "action": "SetRoomAlignment", "expectedSequence": joined_mr["sequence"],
                   "roomAlignment": alignment}
            request("POST", mr_path + "/commands", pin, 403, identity=f"Room{room}")
            request("POST", mr_path + "/commands", {**pin, "roomAlignment": {f"room{room}": "invalid"}}, 400)
            pinned = request("POST", mr_path + "/commands", pin)
            duplicate_pin = request("POST", mr_path + "/commands", pin)
            require(pinned["session"]["roomAlignment"][f"room{room}"] == alignment[f"room{room}"]
                    and duplicate_pin["duplicate"] and duplicate_pin["appliedAtSequence"] == pinned["appliedAtSequence"],
                    "Only the master pins MR alignment, and an exact retry returns its original sequence")
            request("POST", mr_path + "/commands", {**pin, "commandId": str(uuid.uuid4()),
                    "expectedSequence": pinned["session"]["sequence"], "roomAlignment": {f"room{room}": "b" * 64}}, 409)
            require(request("GET", mr_path) == pinned["session"], "Rejected MR pin replacement leaves the original Preparing session intact")
            raw_ticket, ticket_headers = request("POST", ticket_route, identity=f"Room{room}", admission_id=mr_player["admissionId"], raw=True)
            invitation = json.loads(raw_ticket)
            raw_bundle, bundle_headers = request("POST", bundle_route, bundle_request, identity=f"Room{room}", raw=True)
            with zipfile.ZipFile(io.BytesIO(raw_bundle)) as archive:
                config = json.loads(archive.read(f"room-{room:02}-seat-01.json"))
            require(set(config) == {"role", "address", "port", "joinTicket", "roomAlignmentSha256"}
                    and config["roomAlignmentSha256"] == invitation["roomAlignmentSha256"] == alignment[f"room{room}"]
                    and ticket_headers["Cache-Control"] == bundle_headers["Cache-Control"] == "no-store",
                    "Both MR download paths carry exactly the locked room hash and no cacheable response")
            admission = request("POST", "/api/player-tickets/validate", {"sessionId": mr["id"],
                                "ticket": config["joinTicket"], "protocolVersion": 2}, identity="GameServer")
            require(admission["admissionId"] == mr_player["admissionId"], "The MR connection file retains the original signed admission and ticket protocol")
            change = {"commandId": str(uuid.uuid4()), "action": "SetEnvironment"}
            request("POST", mr_path + "/commands", {**change, "environment": {**mr_environment, "mode": "VR"}}, 409)
            receipt = request("POST", mr_path + "/commands", {**change, "environment": {**mr_environment, "weather": "Storm", "lightning": True}})
            require(receipt["session"]["environment"]["mode"] == "MR" and receipt["session"]["environment"]["weather"] == "Storm",
                    "MR retains the selected mode and accepts environment controls through the same command entry point")
            request("POST", mr_path + "/commands", {"commandId": str(uuid.uuid4()), "action": "End"})
            check_venue_deployment(mr_mission["id"])
            check_independent_set(mr_mission["id"], compact_mission["id"], bad_mission["id"])
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
