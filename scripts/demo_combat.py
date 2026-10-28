"""Create an isolated simulated session, submit causal combat events, and print its archived statistics."""

import argparse
import json
from pathlib import Path
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base-url", default="http://127.0.0.1:5080")
parser.add_argument("--key-file", type=Path, default=ROOT / "data/operator-keys.local.json")
parser.add_argument("--room", type=int, choices=range(1, 6), default=1)
args = parser.parse_args()
keys = json.loads(args.key_file.read_text(encoding="utf-8-sig"))["OperatorKeys"]


def api(method, path, body=None, source="Master"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(args.base_url.rstrip("/") + path, data=data, method=method,
        headers={"Authorization": "Bearer " + keys[source], "Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = response.read()
        return json.loads(payload) if payload else None


rooms = api("GET", "/api/rooms")
if next(room for room in rooms if room["id"] == args.room)["sessionId"] is not None:
    raise SystemExit("Requested room is in use; select a free room. Existing sessions were not changed.")
draft = json.loads((ROOT / "examples/mission.json").read_text(encoding="utf-8"))
draft["name"] = "Quest 3 接入前：模擬統計驗證"
mission = api("POST", "/api/missions", draft)
session = api("POST", "/api/sessions", {"missionId": mission["id"], "mode": "Independent", "roomIds": [args.room]})
path = "/api/sessions/" + session["id"]
try:
    player_id = str(uuid.uuid4())
    api("POST", path + "/players", {"playerId": player_id, "name": "Simulated Quest3 Player", "roomId": args.room, "headset": "Quest3"})
    api("POST", path + "/commands", {"commandId": str(uuid.uuid4()), "action": "Begin"})
    shots = [str(uuid.uuid4()) for _ in range(3)]
    enemies = [str(uuid.uuid4()) for _ in range(2)]

    def report(kind, **fields):
        return api("POST", path + "/combat", {"reportId": str(uuid.uuid4()), "kind": kind,
            "origin": "Simulation", "playerId": player_id, **fields}, source="GameServer")

    for shot in shots:
        report("ShotFired", shotId=shot)
    for shot, enemy in zip(shots[:2], enemies):
        report("ShotHit", shotId=shot, enemyId=enemy)
    report("EnemyEliminated", shotId=shots[0], enemyId=enemies[0])
    report("PlayerDamaged", damage=20)
finally:
    # Only the session created by this invocation is ended. The archived record remains available.
    api("POST", path + "/commands", {"commandId": str(uuid.uuid4()), "action": "End"})

print(json.dumps(api("GET", path + "/statistics"), ensure_ascii=False, indent=2))
