"""Real two-client 10000-character mission briefing, native B / Space / Escape input only."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('briefing_debrief', ROOT / 'scripts/check-desktop-debrief.py')
debrief = importlib.util.module_from_spec(spec); spec.loader.exec_module(debrief)
vm = debrief.venue_module


def dotnet_text(value):
    data = value.encode('utf-8'); count = len(data); prefix = bytearray()
    while count >= 128: prefix.append((count & 127) | 128); count >>= 7
    prefix.append(count); return bytes(prefix) + data


def digest(name, text): return hashlib.sha256(struct.pack('<i', 1) + dotnet_text(name) + dotnet_text(text)).hexdigest()


def tool_fingerprint():
    checksum = hashlib.sha256()
    for name in ['check-desktop-briefing.py', 'check-desktop-debrief.py', 'start-desktop-venue.py']:
        checksum.update(name.encode()); checksum.update((ROOT / 'scripts' / name).read_bytes())
    return checksum.hexdigest()


class BriefingVenue(vm.Venue):
    def launch(self, name, config, visible=False, *, extra_args=()):
        probe = self.runtime_directory / (name + '-replica')
        super().launch(name, config, visible, extra_args=(*extra_args, '--vr-replication-probe', str(probe)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--player-exe', type=Path, default=ROOT / 'artifacts/desktop/VrCommand.exe')
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    args = parser.parse_args(); args.duration = 300; args.job_workers = 2; args.visible_room = 3; args.check = True
    vm.verify_player(args); original_tool = tool_fingerprint(); venue = BriefingVenue(args, artifact_family='desktop-briefing'); report = None
    try:
        venue.start()
        name = '繁中任務簡報驗證'
        first = ['任務第一頁：守住防線。', '<b>原文標籤必須保留</b>', '請觀察天氣與隊友位置。', '保持原本的安全界線。', '本頁以繁體中文顯示。', '測試簡報時禁止誤射。', '姿態仍應持續同步。', '下一頁進入救援任務。']
        second = ['任務第二頁：救援隊前進。'] + ['本機閱讀不會暫停全場。'] * 9
        text = '\n'.join(first + second) + '\n'
        text = (text + '長文內容完整同步，任務資料不得截斷。' * 600)[:10000]
        expected = digest(name, text)
        mission = venue.request('/api/missions', {'name': name, 'briefing': text, 'durationSeconds': 300,
            'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False}, 'enemies': {'count': 0, 'behavior': 'Hold', 'autoAttack': False}, 'props': []}, expected=201)
        entry = venue.create(mission, [3], 'briefing'); venue.clients([entry]); visible = 'briefing-client-3'
        counters = {}
        def capture(process):
            number = counters.get(process, 0) + 1; counters[process] = number
            if number > 64: raise RuntimeError('Native capture limit exceeded')
            directory = venue.runtime_directory / (process + '-replica'); vm.atomic_json(directory / 'capture.request', number)
            result = venue.wait(lambda: vm.read_json(directory / f'capture-{number}.json') if (directory / f'capture-{number}.json').exists() else None, 5, 'briefing snapshot')
            if not result['briefingValid'] or result['briefingCharacters'] != 10000 or result['briefingChunks'] != 79 or result['briefingDigest'] != expected:
                raise RuntimeError('Native mission briefing differs from the entire saved definition')
            return result
        preparing = capture(visible); server = capture('briefing-server')
        venue.stage('awaiting-open', instruction='Press B in the visible player; inspect literal Chinese page 1')
        venue.wait(lambda: (venue.directory / 'opened.done').exists(), 80, 'actual B / first-page observation')
        opened = capture(visible)
        if not opened['briefingOpen'] or opened['briefingPage'] != 0 or opened['briefingPages'] < 40: raise RuntimeError('Briefing did not open on its first bounded page')
        identity = str(uuid.uuid4()); state = venue.request(f'/api/sessions/{entry["id"]}/players', {'playerId': identity, 'roomId': 3, 'name': 'Late briefing peer', 'headset': 'Quest3'}, role='Room3')
        peer = next(value for value in state['players'] if value['id'] == identity); entry['players'].append(peer)
        venue.command(entry, 'Begin'); venue.launch('briefing-late', venue.client_config(entry, venue.ticket(entry, peer)))
        venue.wait(lambda: venue.connected(entry), 45, 'both actual rigs after late connection')
        late = capture('briefing-late'); running = capture(visible)
        if not running['briefingOpen']: raise RuntimeError('Normal management updates or late join reset the reader')
        before = venue.frame(entry)['packet']['frame']['tick']
        venue.stage('awaiting-blocked-fire', instruction='Press Space while the briefing is open')
        venue.wait(lambda: (venue.directory / 'blocked-fire.done').exists(), 50, 'real blocked Space press')
        blocked = capture(visible); after = venue.frame(entry)
        if blocked['briefingSuppressedInputs'] < 1 or not blocked['briefingOpen'] or any(p['ammoUsed'] for p in after['statistics']) or after['packet']['frame']['tick'] <= before:
            raise RuntimeError('Briefing stopped the global clock, failed to observe input or allowed a shot')
        venue.stage('awaiting-next', instruction='Press B and inspect Chinese page 2')
        venue.wait(lambda: (venue.directory / 'next.done').exists(), 50, 'actual page turn')
        next_page = capture(visible)
        if not next_page['briefingOpen'] or next_page['briefingPage'] != 1: raise RuntimeError('Second page was not selected')
        venue.stage('awaiting-close-shot', instruction='Press Escape, then release and press Space once')
        venue.wait(lambda: (venue.directory / 'closed-shot.done').exists(), 50, 'actual close / release / Space')
        closed = capture(visible)
        venue.wait(lambda: any(p['playerId'] == entry['players'][0]['id'] and p['ammoUsed'] == 1 for p in venue.frame(entry)['statistics']), 10, 'accepted post-close shot')
        if closed['briefingOpen']: raise RuntimeError('Panel remained open')
        venue.stage('awaiting-license', instruction='B opens again, L shows font license; inspect then Escape')
        venue.wait(lambda: (venue.directory / 'license.done').exists(), 50, 'bundled font license observation')
        captures = {'preparing': preparing, 'server': server, 'opened': opened, 'running': running, 'late': late, 'blocked': blocked, 'next': next_page, 'closed': closed}
        pose_continuity = None
        for process in ['briefing-server', visible, 'briefing-late']:
            directory = venue.runtime_directory / (process + '-replica'); (directory / 'finish.request').write_text('finish\n')
            observation = venue.wait(lambda d=directory: vm.read_json(d / 'report.json') if (d / 'report.json').exists() else None, 5, 'complete native probe')
            if not observation['complete'] or observation['truncated'] or observation['sendQueueErrors']: raise RuntimeError('Incomplete or overflowing diagnostic evidence')
            if process == 'briefing-server':
                rows = [row for row in observation['rows'] if running['utcTicks'] <= row['utcTicks'] <= closed['utcTicks'] and row['phase'] == 1]
                bad = [row for row in rows if row['players'] != 2 or row['connected'] != 2 or not row['ready'] or not row['coherent']]
                if not rows or bad: raise RuntimeError('Open-reader running interval lost accepted body continuity')
                pose_continuity = {'runningRows': len(rows), 'badRows': len(bad), 'scope': 'server changed-tick snapshots during stable two-player reading interval'}
        sealed = venue.seal(entry)
        if not venue.wait_for_player_results(entry)['allAcknowledged']: raise RuntimeError('Final results not acknowledged')
        results = []
        for process, player in [(visible, entry['players'][0]), ('briefing-late', peer)]:
            result = debrief.final_result(venue, process); debrief.validate_result(result, entry, player, sealed); results.append(result)
        if results[0]['ammoUsed'] != 1 or results[1]['ammoUsed'] != 0: raise RuntimeError('Local briefing state affected the peer weapon ledger')
        if venue.state(entry)['mission']['definition']['briefing'] != text: raise RuntimeError('Reading changed the saved mission')
        report = {'complete': False, 'source': 'Actual Windows Unity / keyboard / GPU observation, Simulation rigs', 'headsets': 0, 'characters': len(text), 'expectedDigest': expected,
            'toolFingerprint': original_tool, 'playerBuildReceipt': venue.receipt, 'captures': captures, 'poseContinuity': pose_continuity, 'sealed': sealed, 'results': results,
            'checks': ['complete 10000-character source reaches server and both clients including late join', 'Chinese literal text and page turn observed in native GPU',
                       'open reader survives management updates and late connection', 'real blocked input leaves ammo unchanged while poses and tick advance',
                       'close / release permits exactly one real shot, peer unchanged', 'bundled font license is viewable', 'original saved mission unchanged', 'both targeted results / seals match ledger']}
    finally:
        cleanup = venue.cleanup()
        if report is not None:
            if tool_fingerprint() != original_tool: raise RuntimeError('Briefing tool source changed during the run')
            report['complete'] = cleanup; venue.save('checks.json', report)
        print('Artifacts:', venue.directory, flush=True)
        if not cleanup: raise RuntimeError('Briefing fixture cleanup failed')
    if not report or not report['complete']: raise RuntimeError('Briefing acceptance incomplete')
    print('PASS: 8 native mission briefing / local input checks; no headsets', flush=True)


if __name__ == '__main__': main()
