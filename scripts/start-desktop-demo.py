"""Run the current playable Windows Simulation in its own API and runtime.

Uses the same source verification, admission, freshness and exact-seal lifecycle
as the five-room venue. Close the visible player, send operator End, create the
run's end.request, press Ctrl+C, or let --duration expire to finish.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('practice_venue', ROOT / 'scripts/start-desktop-venue.py')
venue_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(venue_module)


def save_report(venue, entry, statistics):
    request = urllib.request.Request(venue.base + f'/api/sessions/{entry["id"]}/report.csv',
        headers={'Authorization': 'Bearer ' + venue.tokens['Master']})
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.headers.get_content_type() != 'text/csv': raise RuntimeError('Final report is not CSV')
        content = response.read()
    if not content.startswith(b'\xef\xbb\xbf'): raise RuntimeError('Final report UTF-8 BOM is missing')
    rows = list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline='')))
    if len(rows) != len(statistics['players']) or {row['playerId'] for row in rows} != {p['playerId'] for p in statistics['players']}:
        raise RuntimeError('Final report has a different player roster')
    current = venue.state(entry)
    for row in rows:
        player = next((p for p in statistics['players'] if p['playerId'] == row['playerId']), None)
        if player is None or row['origin'] != 'Simulation' or row['sessionId'] != entry['id'] or row['reportVersion'] != '1' or row['rowType'] != 'Player' \
            or row['missionId'] != entry['mission']['id'] or int(row['throughSequence']) != statistics['throughSequence'] \
            or row['playerName'] != player['name'] or int(row['playerRoomId']) != player['roomId'] \
            or row['streamId'] != current['combatStream']['streamId'] \
            or int(row['finalStreamSequence']) != current['combatStream']['acceptedSequence'] \
            or any(Decimal(row[key]) != Decimal(str(player[key])) for key in ('ammoUsed','shotsHit','kills','hitsReceived','damageTaken','health','accuracyPercent')):
            raise RuntimeError('Final report does not match the sealed ledger')
    destination = venue.directory / 'final-report.csv'
    destination.write_bytes(content)
    return {'path': str(destination), 'sha256': hashlib.sha256(content).hexdigest(), 'players': len(rows), 'verified': True}


def run(venue):
    venue.start()
    mission = venue.request('/api/missions', {'name': 'Desktop practice - Simulation',
        'briefing': 'Keyboard / mouse practice; synthetic head and hands, no headset.',
        'durationSeconds': venue.args.duration,
        'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
        'enemies': {'count': venue.args.enemies, 'behavior': 'Hold', 'autoAttack': False},
        'props': [{'assetId': 'sandbag', 'position': {'x': 0, 'y': 0, 'z': 2}, 'yawDegrees': 0},
                  {'assetId': 'barrel', 'position': {'x': 2, 'y': 0, 'z': 2}, 'yawDegrees': 30}]}, expected=201)
    state = venue.request('/api/sessions', {'missionId': mission['id'], 'mode': 'Independent', 'roomIds': [5]}, expected=201)
    entry = venue.adopt(state, 'practice')  # Track the reservation before any later join/start can fail.
    for index in range(venue.args.peers + 1):
        identity = str(uuid.uuid4())
        state = venue.request(f'/api/sessions/{entry["id"]}/players',
            {'playerId': identity, 'name': 'Desktop ' + str(index + 1), 'roomId': 5, 'headset': 'Quest3'})
        entry['players'].append(next(player for player in state['players'] if player['id'] == identity))
    venue.wait(lambda: venue.request(f'/api/sessions/{entry["id"]}/world', optional=True), 90, 'practice recording')
    visible_name = None
    for index in reversed(range(len(entry['players']))):
        player = entry['players'][index]
        name = 'practice-client-' + player['admissionId']
        visible = index == 0 and not venue.args.headless
        venue.launch(name, venue.client_config(entry, venue.ticket(entry, player)), visible)
        if visible: visible_name = name
    venue.wait(lambda: venue.connected(entry), 100, 'all practice clients')
    venue.command(entry, 'Begin')
    venue.wait(lambda: (frame if (frame := venue.frame(entry, measure=True))['packet']['frame']['phase'] == 'Running' else None), 30, 'practice Running')
    ready = {'schemaVersion': 1, 'baseUrl': venue.base, 'consoleUrl': venue.base + '/console/',
        'sessionId': entry['id'], 'directory': str(venue.directory), 'runtimeDirectory': str(venue.runtime_directory),
        'playerIds': [player['id'] for player in entry['players']], 'source': 'Simulation', 'headsets': 0,
        'processIds': [child.pid for child in venue.processes.values()], 'playerBuildReceipt': venue.receipt,
        'visibleClientProcessId': venue.processes[visible_name].pid if visible_name else None,
        'jobWorkersPerProcess': venue.args.job_workers}
    venue.save('ready.json', ready)
    venue.stage('ready', consoleUrl=ready['consoleUrl'], source='Simulation', headsets=0)
    print('WASD: move; right drag / arrows: aim; click / Space: fire; R: reload. Close the game or Ctrl+C to finish.', flush=True)
    print('Only this run uses its temporary keys.json; keep it and player connection files private.', flush=True)
    deadline = time.monotonic() + venue.args.duration
    reason = 'durationElapsed'
    try:
        while time.monotonic() < deadline:
            if (venue.directory / 'end.request').exists(): reason = 'endRequested'; break
            if visible_name and venue.processes[visible_name].poll() is not None:
                # A known normal close must not poison Venue.wait's live-child fence during seal.
                venue.stop(visible_name); reason = 'windowClosed'; break
            failed = [name for name, child in venue.processes.items() if child.poll() is not None]
            if failed:
                for name in failed:
                    if name.startswith('practice-client-'): venue.stop(name)
                raise RuntimeError('A required practice process stopped; preserve journals and inspect this run')
            if venue.state(entry)['state'] == 'Ended': reason = 'operatorEnded'; break
            frame = venue.frame(entry, measure=True)
            venue.save('latest-frame.json', frame)
            venue.save('latest-statistics.json', venue.request(f'/api/sessions/{entry["id"]}/statistics'))
            time.sleep(.25)
    except KeyboardInterrupt:
        reason = 'interrupt'
    if venue.state(entry)['state'] != 'Ended': venue.command(entry, 'End')
    # Only the authority and API are required to confirm the final boundary.
    # Retire known closing clients before entering the strict live-child wait.
    for name in list(venue.processes):
        if name.startswith('practice-client-'): venue.stop(name)
    sealed = venue.seal(entry)
    venue.save('latest-frame.json', venue.frame(entry))
    venue.save('latest-statistics.json', sealed['statistics'])
    report = save_report(venue, entry, sealed['statistics'])
    venue.summary()
    summary = json.loads((venue.directory / 'summary.json').read_text(encoding='utf-8'))
    # Preserve the earlier practice summary's top-level API while retaining venue evidence.
    summary.update(source='Simulation', stopReason=reason, world=sealed['world'], statistics=sealed['statistics'],
                   replayStatisticsMatch=True, finalReport=report)
    venue.save('summary.json', summary)
    venue.stage('sealed', stopReason=reason, finalReport='final-report.csv', frames=sealed['world']['acceptedSequence'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--duration', type=int, choices=range(60, 1801), default=900, metavar='60..1800')
    parser.add_argument('--enemies', type=int, choices=range(0, 13), default=3, metavar='0..12')
    parser.add_argument('--peers', type=int, choices=range(0, 5), default=1, help='Additional headless desktop clients, 0..4')
    parser.add_argument('--runtime-root', type=Path, help='Explicit fresh runtime on SSD; closed snapshot copied back to F')
    parser.add_argument('--job-workers', type=int, choices=range(1, 17), default=2)
    parser.add_argument('--headless', action='store_true', help='Unattended native diagnostics; no visible player or GPU claim')
    args = parser.parse_args(); args.check = False
    try: venue_module.verify_player(args)
    except (OSError, RuntimeError, ValueError) as error: parser.error(str(error))
    venue = venue_module.Venue(args, artifact_family='desktop-demo')
    try:
        venue.stage('starting', source='Simulation', headsets=0)
        run(venue)
    except BaseException as error:
        venue.stage('failed', errorType=type(error).__name__)
        raise
    finally:
        cleaned = venue.cleanup()
        if not cleaned and sys.exc_info()[0] is None:
            venue.stage('failed', errorType='CleanupError')
            raise RuntimeError('Practice cleanup / snapshot failed; inspect cleanup.json')


if __name__ == '__main__': main()
