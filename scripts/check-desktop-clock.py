"""Two genuine Windows Unity rooms: explicit deadline versus legacy manual policy. Simulation rigs only."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('clock_venue', ROOT / 'scripts/start-desktop-venue.py')
vm = importlib.util.module_from_spec(spec); spec.loader.exec_module(vm)


def replay(venue, entry, sealed):
    request = urllib.request.Request(venue.base + f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4',
        headers={'Authorization': 'Bearer ' + venue.tokens['Master']})
    previous, last, kind = 0, None, ''
    with urllib.request.urlopen(request, timeout=10) as response:
        for raw in response:
            line = raw.decode().strip()
            if line.startswith('event: '): kind = line[7:]
            if kind == 'frame' and line.startswith('data: '):
                row = json.loads(line[6:]); packet = row['packet']
                if packet['sequence'] != previous + 1: raise RuntimeError('Replay lost a frame')
                if entry['name'] == 'clock-auto' and packet['frame']['tick'] > 1200: raise RuntimeError('Combat advanced after the deadline')
                previous, last = packet['sequence'], row
    if previous != sealed['world']['acceptedSequence'] or last['packet']['frame']['phase'] != 'Ended' or last['statistics'] != venue.frame(entry)['statistics']:
        raise RuntimeError('Replay differs from the final seal')
    return {'frames': previous, 'finalTick': last['packet']['frame']['tick'], 'allFramesChecked': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--inspect-seconds', type=int, default=0, choices=range(0, 61))
    args = parser.parse_args(); args.duration = 240; args.job_workers = 2; args.visible_room = 1; args.check = True
    vm.verify_player(args); venue = vm.Venue(args, artifact_family='desktop-clock'); report = None
    try:
        venue.start()
        mission = venue.request('/api/missions', {'name': 'One minute PC mission', 'briefing': 'Authoritative ticks, pause and explicit automatic End',
            'durationSeconds': 60, 'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False},
            'enemies': {'count': 0, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
        automatic = venue.create(mission, [1], 'clock-auto'); manual = venue.create(mission, [2], 'clock-manual')
        venue.clients([manual, automatic])
        venue.command(automatic, 'SetMissionClock', missionClock={'autoEnd': True})
        venue.command(manual, 'Begin'); venue.command(automatic, 'Begin')
        venue.wait(lambda: venue.frame(automatic)['packet']['frame']['tick'] >= 100, 20, 'first five active seconds')
        venue.command(automatic, 'Pause')
        paused = venue.wait(lambda: (f if (f := venue.frame(automatic))['packet']['frame']['phase'] == 'Paused' else None), 10, 'accepted pause')
        tick = paused['packet']['frame']['tick']; paused_at = time.monotonic()
        venue.stage('paused-clock', tick=tick, inspectSeconds=args.inspect_seconds)
        while time.monotonic() - paused_at < max(5, args.inspect_seconds):
            if venue.frame(automatic)['packet']['frame']['tick'] != tick: raise RuntimeError('Paused clock consumed time')
            time.sleep(.2)
        pause_seconds = time.monotonic() - paused_at
        venue.command(automatic, 'Resume')
        venue.wait(lambda: venue.state(automatic)['state'] == 'Ended', 110, 'automatic durable End', required={'api', 'clock-auto-server', 'clock-manual-server'})
        if venue.state(manual)['state'] != 'Running': raise RuntimeError('Manual room was automatically ended')
        manual_tick = venue.frame(manual)['packet']['frame']['tick']
        if manual_tick <= 1200: raise RuntimeError('Manual compatibility did not exceed the planned duration')
        sealed_auto = venue.seal(automatic)
        if not venue.wait_for_player_results(automatic)['allAcknowledged']: raise RuntimeError('Automatic result was not acknowledged')
        sealed_manual = venue.seal(manual)
        if not venue.wait_for_player_results(manual)['allAcknowledged']: raise RuntimeError('Manual result was not acknowledged')
        events = venue.request(f'/api/sessions/{automatic["id"]}/events?after=0&limit=500')
        expiry = [e for e in events if e['kind'] == 'ControlApplied' and e['payload'].get('clockExpiration')]
        if len(expiry) != 1 or expiry[0]['actor']['id'] != 'mission-clock' or expiry[0]['schemaVersion'] != 7 or expiry[0]['payload']['clockExpiration']['tick'] != 1200:
            raise RuntimeError('Missing exact single automatic End evidence')
        if venue.state(manual).get('missionClock') is not None: raise RuntimeError('Manual default was silently modified')
        report = {'complete': False, 'source': 'Genuine Windows Unity UDP; Simulation rigs', 'headsets': 0, 'playerBuildReceipt': venue.receipt,
            'pausedTick': tick, 'pauseSeconds': pause_seconds, 'manualRunningTick': manual_tick, 'automaticEnd': expiry[0],
            'automaticReplay': replay(venue, automatic, sealed_auto), 'manualReplay': replay(venue, manual, sealed_manual),
            'automaticSealed': sealed_auto, 'manualSealed': sealed_manual, 'checks': 8}
    finally:
        cleanup = venue.cleanup()
        if report is not None:
            report['complete'] = cleanup; venue.save('checks.json', report)
        print('Artifacts:', venue.directory, flush=True)
        if not cleanup: raise RuntimeError('Owned native fixture cleanup failed')
    if not report or not report['complete']: raise RuntimeError('Clock checks incomplete')
    print('PASS: 8 native clock checks; two rooms, no headsets or load acceptance', flush=True)


if __name__ == '__main__': main()
