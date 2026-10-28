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

ROOT = Path(__file__).resolve().parents[1]
DLL = ROOT / "src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll"
if not DLL.exists():
    raise SystemExit("Build first: dotnet build VrCommand.slnx --configuration Release")

with socket.socket() as reservation:
    reservation.bind(("127.0.0.1", 0))
    port = reservation.getsockname()[1]
base_url = f"http://127.0.0.1:{port}"
checks = 0


def request(method, path, body=None, expected=200):
    global checks
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base_url + path, data=data, method=method,
        headers={"Content-Type": "application/json; charset=utf-8"},
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
    environment = os.environ.copy()
    environment["DataDirectory"] = str(test_directory / "missions")
    environment["ASPNETCORE_ENVIRONMENT"] = "Production"
    environment["Logging__LogLevel__Default"] = "Warning"
    with (test_directory / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            ["dotnet", str(DLL), "--urls", base_url], cwd=ROOT, env=environment,
            stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
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

            rooms = request("GET", "/api/rooms")
            require(len(rooms) == 5 and all(r["capacity"] == 5 for r in rooms), "Five rooms expose five slots each")
            draft = json.loads((ROOT / "examples/mission.json").read_text(encoding="utf-8"))
            mission = request("POST", "/api/missions", draft, 201)
            loaded = request("GET", f"/api/missions/{mission['id']}")
            require(loaded["definition"] == draft, "Mission round-trips through JSON persistence")
            require(len(request("GET", "/api/missions")) == 1, "Saved mission appears in list")
            request("POST", "/api/missions", {**draft, "durationSeconds": 0}, 400)
            request("POST", "/api/missions", {**draft, "props": None}, 400)
            request("GET", f"/api/missions/{uuid.uuid4()}", expected=404)

            def start(mode, room_ids, expected=201):
                return request("POST", "/api/sessions", {
                    "missionId": mission["id"], "mode": mode, "roomIds": room_ids,
                }, expected)

            start("Linked", [1, 2, 3, 4, 4], 400)
            start("Linked", None, 400)
            independent = [start("Independent", [room]) for room in range(1, 6)]
            start("Linked", [1, 2, 3, 4, 5], 409)
            first_player_id = str(uuid.uuid4())
            player = {"playerId": first_player_id, "name": "Alpha", "roomId": 1, "headset": "Quest3"}
            request("POST", f"/api/sessions/{independent[0]['id']}/players", player)
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
            request("POST", session_path + "/players", {**player, "playerId": str(uuid.uuid4())}, 409)
            require(all(r["playerCount"] == 5 for r in request("GET", "/api/rooms")), "Every room remains at capacity after overflow rejection")
            request("DELETE", session_path + "/players/" + current["players"][0]["id"], expected=204)
            request("POST", session_path + "/players", player)
            request("DELETE", session_path, expected=204)
            request("GET", session_path, expected=404)
            require(all(r["sessionId"] is None and r["playerCount"] == 0 for r in request("GET", "/api/rooms")), "Ending releases all room reservations and player slots")
            require(len(request("GET", "/api/missions")) == 1, "Mission survives session cleanup")
        except BaseException:
            log.flush()
            print((test_directory / "server.log").read_text(encoding="utf-8"))
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
finally:
    temporary.cleanup()

print(f"All {checks} HTTP assertions passed; this is not a headset or gameplay load test.")
