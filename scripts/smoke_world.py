"""Real WebSocket publisher, authenticated SSE observation and SQLite restart checks."""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

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


class WebSocket:
    def __init__(self, port, route, token):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=10)
        self.file = self.sock.makefile("rb")
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        self.sock.sendall((f"GET {route} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nAuthorization: Bearer {token}\r\n\r\n").encode())
        status = self.file.readline().decode()
        headers = {}
        while (line := self.file.readline()) not in (b"\r\n", b""):
            name, value = line.decode().split(":", 1)
            headers[name.lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        if " 101 " not in status or headers.get("sec-websocket-accept") != expected:
            self.close()
            raise AssertionError("WebSocket handshake rejected: " + status.strip())

    def send(self, value, opcode=1):
        data = json.dumps(value, separators=(",", ":")).encode()
        size = len(data)
        head = bytes([0x80 | opcode, 0x80 | size]) if size < 126 else bytes([0x80 | opcode, 0x80 | 126]) + struct.pack("!H", size) if size < 65536 else bytes([0x80 | opcode, 0x80 | 127]) + struct.pack("!Q", size)
        mask = secrets.token_bytes(4)
        self.sock.sendall(head + mask + bytes(value ^ mask[index % 4] for index, value in enumerate(data)))
        body = b""
        while True:
            header = self.file.read(2)
            if len(header) != 2 or header[0] & 15 == 8:
                raise AssertionError("World publisher closed without an acknowledgment")
            size = header[1] & 127
            if size == 126:
                size = struct.unpack("!H", self.file.read(2))[0]
            elif size == 127:
                size = struct.unpack("!Q", self.file.read(8))[0]
            if size > 1024 * 1024:
                raise AssertionError("Unbounded WebSocket response")
            body += self.file.read(size)
            if header[0] & 0x80:
                return json.loads(body)

    def close(self):
        self.file.close()
        self.sock.close()


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

    def request(route, role="Master", expected=200):
        req = urllib.request.Request(base + route, headers={"Authorization": "Bearer " + tokens.get(role, role)})
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
        check(info["complete"] and info["acceptedSequence"] == result["frames"] == 44, "All ordered source frames durably seal after combat confirmation")
        check(len(info["header"]["props"]) == 2, "World archive uses actual canonical mission geometry")
        check(any(player["rig"]["kind"] == "Simulated" for row in frames if row["type"] == "frame" for player in row["payload"]["frame"]["players"]), "Head and both hands retain explicit synthetic rig provenance")
        with request(route + "/watch?mode=replay&fromMs=200&rate=4") as stream:
            check(event(stream)[0] == "header", "Persisted replay starts with versioned metadata")
            replay = []
            while True:
                kind, data = event(stream)
                if kind == "frame":
                    replay.append(data)
                if kind == "complete":
                    break
            check(replay[0]["packet"]["elapsedMilliseconds"] <= 200 and replay[0]["packet"]["sequence"] > 1, "Indexed replay seeks to the preceding stored frame")
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
        process.terminate()
        process.wait(timeout=10)
        process = start()
        check(request(route) == info, "SQLite restart restores recording identity, cursor, time and completion")
        recovery = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30)
        check(recovery.returncode == 0 and json.loads(recovery.stdout)["complete"], "A second native process replays the full saved source idempotently")
        check(request(route) == info, "Whole-source retry changes no frame or archive metadata")
        check(request("/api/sessions/" + session)["players"][0]["name"] == "World Simulation", "Observer creates no extra player seat")
        print(f"All {count} world streaming checks passed. No Unity or headset execution.")
    finally:
        if demo is not None and demo.poll() is None:
            demo.terminate()
            demo.wait(timeout=10)
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        log.close()
