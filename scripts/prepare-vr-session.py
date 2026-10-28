"""Provision a new managed session and per-player short-lived Unity connection files."""

import argparse
import json
from pathlib import Path
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
keys = json.loads(args.key_file.read_text(encoding="utf-8-sig"))["OperatorKeys"]
if not keys.get("GameServer"):
    raise SystemExit("The local credential file needs a GameServer credential.")


def api(method, path, body=None):
    request = urllib.request.Request(args.base_url.rstrip("/") + path,
        data=None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8"), method=method,
        headers={"Authorization": "Bearer " + keys["Master"], "Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = response.read()
        return json.loads(payload) if payload else None


if next(room for room in api("GET", "/api/rooms") if room["id"] == args.room)["sessionId"] is not None:
    raise SystemExit("Room is already in use. Existing sessions were not changed.")
draft = json.loads((ROOT / "examples/mission.json").read_text(encoding="utf-8"))
draft["name"] = "Quest 3 共享場景接入"
mission = api("POST", "/api/missions", draft)
session = api("POST", "/api/sessions", {"missionId": mission["id"], "mode": "Independent", "roomIds": [args.room]})
path = "/api/sessions/" + session["id"]
output = args.output.resolve() / session["id"]
try:
    output.mkdir(parents=True, exist_ok=False)
    server = {"role": "Server", "address": "0.0.0.0", "port": args.port, "sessionId": session["id"],
              "managementApiUrl": args.base_url.rstrip("/"), "gameServerKey": keys["GameServer"]}
    (output / "server.json").write_text(json.dumps(server, indent=2), encoding="utf-8")
    players = []
    for index in range(1, args.players + 1):
        player_id = str(uuid.uuid4())
        api("POST", path + "/players", {"playerId": player_id, "name": f"Quest3-{index}", "roomId": args.room, "headset": "Quest3"})
        invitation = api("POST", path + f"/players/{player_id}/join-ticket")
        filename = f"player-{index}.json"
        client = {"role": "Client", "address": args.server_address, "port": args.port, "joinTicket": invitation["ticket"]}
        (output / filename).write_text(json.dumps(client, indent=2), encoding="utf-8")
        players.append({"playerId": player_id, "file": filename, "expiresAtUtc": invitation["expiresAtUtc"]})
except BaseException:
    api("POST", path + "/commands", {"commandId": str(uuid.uuid4()), "action": "End"})
    raise
print(json.dumps({"sessionId": session["id"], "state": "Preparing", "directory": str(output), "players": players}, indent=2))
