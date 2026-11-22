"""Provision a new managed session and per-player short-lived Unity connection files."""

import argparse
import ipaddress
import json
from pathlib import Path
import tempfile
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base-url", default="http://127.0.0.1:5080")
parser.add_argument("--key-file", type=Path, default=ROOT / "data/operator-keys.local.json")
parser.add_argument("--output", type=Path, default=ROOT / "data/vr-connections")
parser.add_argument("--room", type=int, choices=range(1, 6), default=1)
parser.add_argument("--players", type=int, choices=range(1, 6), default=2)
parser.add_argument("--server-address", required=True, help="Game server LAN address reachable from Quest headsets")
parser.add_argument("--port", type=int, default=7777)
args = parser.parse_args()
if not 1024 <= args.port <= 65535:
    parser.error("port must be between 1024 and 65535")
try:
    address = ipaddress.IPv4Address(args.server_address)
except ipaddress.AddressValueError:
    parser.error("use the game server's venue IPv4 address for Quest players")
if address.is_loopback or not 0 < address.packed[0] < 224:
    parser.error("Quest players need a unicast IPv4 address reachable outside the server computer")
keys = json.loads(args.key_file.read_text(encoding="utf-8-sig"))["OperatorKeys"]
if not keys.get("GameServer"):
    raise SystemExit("The local credential file needs a GameServer credential.")


def api(method, path, body=None, admission_id=None):
    request = urllib.request.Request(args.base_url.rstrip("/") + path,
        data=None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8"), method=method,
        headers={"Authorization": "Bearer " + keys["Master"], "Content-Type": "application/json; charset=utf-8", **({"If-Match-Admission": admission_id} if admission_id else {})})
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = response.read()
        return json.loads(payload) if payload else None


if next(room for room in api("GET", "/api/rooms") if room["id"] == args.room)["sessionId"] is not None:
    raise SystemExit("Room is already in use. Existing sessions were not changed.")
draft = json.loads((ROOT / "examples/mission.json").read_text(encoding="utf-8"))
draft["name"] = "Quest 3 共享場景接入"
output_root = args.output.resolve()
output_root.mkdir(parents=True, exist_ok=True)
mission = api("POST", "/api/missions", draft)
session = api("POST", "/api/sessions", {"missionId": mission["id"], "mode": "Independent", "roomIds": [args.room]})
path = "/api/sessions/" + session["id"]
output = output_root / session["id"]
try:
    server = {"role": "Server", "address": args.server_address, "listenAddress": "0.0.0.0", "port": args.port, "sessionId": session["id"],
              "managementApiUrl": args.base_url.rstrip("/"), "gameServerKey": keys["GameServer"],
              "telemetryOrigin": "Simulation", "telemetryDirectory": str(ROOT / "data/telemetry")}
    files = {"server.json": server}
    players = []
    for index in range(1, args.players + 1):
        player_id = str(uuid.uuid4())
        joined = api("POST", path + "/players", {"playerId": player_id, "name": f"Quest3-{index}", "roomId": args.room, "headset": "Quest3"})
        admission_id = next(player["admissionId"] for player in joined["players"] if player["id"] == player_id)
        invitation = api("POST", path + f"/players/{player_id}/join-ticket", admission_id=admission_id)
        filename = f"player-{index}.json"
        client = {"role": "Client", "address": args.server_address, "port": args.port, "joinTicket": invitation["ticket"]}
        files[filename] = client
        players.append({"playerId": player_id, "file": filename, "expiresAtUtc": invitation["expiresAtUtc"]})
    with tempfile.TemporaryDirectory(prefix=".preparing-", dir=output_root) as temporary:
        staging = Path(temporary)
        for name, config in files.items():
            (staging / name).write_text(json.dumps(config, indent=2), encoding="utf-8")
        if output.exists():
            raise FileExistsError("The session output directory already exists.")
        staging.rename(output)
except BaseException:
    api("POST", path + "/commands", {"commandId": str(uuid.uuid4()), "action": "End"})
    raise
print(json.dumps({"sessionId": session["id"], "state": "Preparing", "directory": str(output), "players": players}, indent=2))
