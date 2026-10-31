"""Compare closed native long-run evidence without reopening SQLite.

This is a factual comparison, never a causal / capacity / device verdict.
Native handles must be confirmed terminal before invoking the comparison.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition: raise ValueError(message)


def count(value):
    require(type(value) is int and value >= 0, 'Expected a nonnegative integer')
    return value


def summarize(checks, cleanup, diagnostic_manifest_exists):
    require(checks['executionFinished'] is True and not cleanup['errors'] and not cleanup['remainingTrackedChildren'], 'Fixture has not finished its declared cleanup')
    require(type(checks['acceptancePassed']) is bool and checks['complete'] is checks['acceptancePassed'], 'Completion and acceptance disagree after cleanup')
    require(checks.get('fixtureKind') is None, 'Controlled calibration is not a natural long-run comparison')
    participants = count(checks['participants']); require(participants > 0, 'Empty roster')
    sealed, replay, live = checks['sealed'], checks['replay'], checks['live']; header = sealed['world']['header']
    require(sealed['world']['complete'] is True and sealed['statistics']['pendingTelemetry'] is False, 'Both exact seals are required')
    require(header['origin'] == 'Simulation' and checks['headsets'] == 0 and checks['hosts'] == 1 and checks['networkCapacityAccepted'] is False, 'Unsupported evidence scope')
    require(count(replay['frames']) == sealed['world']['acceptedSequence'] and count(replay['finalTick']) == 18000 and checks['durationSeconds'] == 900, 'Replay or mission boundary differs')
    require(count(replay['expectedParticipantObservations']) == count(replay['runningFrames']) * participants and replay['finalPacketAndStatisticsMatch'] is True, 'Participant observation accounting differs')
    require(count(live['badFrames']) <= live['frames'] and count(replay['badFrames']) <= replay['frames'], 'Invalid bad-frame count')
    expected_pass = (live['runningFrames'] > 0 and live['badFrames'] == 0 and replay['runningFrames'] > 0 and replay['badFrames'] == 0
        and replay['captureGapsAtLeast1500ms'] == 0 and checks['sourceAge']['badSamples'] == 0 and not checks['nativeLogFindings'])
    require(checks['acceptancePassed'] is expected_pass, 'Reported acceptance disagrees with recorded counters')
    require(len(checks['clientResults']) == participants and len({p['playerId'] for p in checks['clientResults']}) == participants, 'Individual results are incomplete or duplicated')
    expected = {p['playerId']: p for p in sealed['statistics']['players']}
    require(len(expected) == participants, 'Sealed statistics roster differs')
    require(set(replay['perPlayerBadFrames']) <= set(expected) and all(0 < count(v) <= replay['badFrames'] for v in replay['perPlayerBadFrames'].values()), 'Per-player bad-frame accounting differs')
    require(len({count(p['finalStreamSequence']) for p in checks['clientResults']}) == 1, 'Individual combat seal sequences differ')
    for result in checks['clientResults']:
        require(result['playerId'] in expected and result['worldSequence'] == sealed['world']['acceptedSequence'] and result['streamId'] == header['streamId']
            and result['throughSequence'] == sealed['statistics']['throughSequence'] and result['origin'] == 'Simulation', 'Individual result boundary differs')
        require(all(result[key] == expected[result['playerId']][key] for key in ('ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken', 'health', 'accuracyPercent')), 'Individual result ledger differs')
    require(checks['originalConnectionsAfterExpiry']['allOriginalAdmissions'] is True and checks['originalConnectionsAfterExpiry']['participants'] == participants, 'Expiry continuity is unproven')
    fingerprint = checks['playerBuildReceipt']['sourceFingerprint']; require(re.fullmatch('[a-f0-9]{64}', fingerprint) is not None, 'Build source fingerprint is missing')
    if 'poseContinuity' not in checks:
        mode = 'NotRecorded'; require(not diagnostic_manifest_exists, 'Legacy mode is ambiguous with a diagnostic manifest')
    elif checks['poseContinuity'] is None:
        mode = 'DisabledByTool'; require(not diagnostic_manifest_exists, 'Disabled mode has a diagnostic manifest')
    else:
        mode = 'Sparse'; diagnostic = checks['poseContinuity']
        require(diagnostic_manifest_exists and diagnostic['complete'] is True and len(diagnostic['programs']) == participants + 1, 'Sparse collection is incomplete')
    return {'sourceFingerprint': fingerprint, 'diagnosticMode': mode, 'participants': participants, 'durationSeconds': 900,
        'rooms': header['roomIds'], 'origin': header['origin'], 'rulesVersion': header['rulesVersion'], 'assetSet': header['assetSet'],
        'acceptancePassed': checks['acceptancePassed'], 'worldFrames': replay['frames'], 'runningFrames': replay['runningFrames'],
        'participantObservations': replay['expectedParticipantObservations'], 'badFrames': replay['badFrames'],
        'badParticipantRows': sum(count(v) for v in replay['perPlayerBadFrames'].values()), 'perPlayerFailures': len(replay['perPlayerBadFrames']),
        'maximumCaptureGapMilliseconds': replay['maximumCaptureGapMilliseconds'], 'captureGapsAtLeast1500ms': replay['captureGapsAtLeast1500ms'],
        'badSourceAges': checks['sourceAge']['badSamples'], 'maximumSourceAgeSeconds': checks['sourceAge']['maximumSourceAgeSeconds'],
        'sendQueueLogFindings': checks['nativeLogFindings'], 'individualResults': len(checks['clientResults']), 'afterExpiry': checks['originalConnectionsAfterExpiry']}


def load_evidence(directory):
    directory = directory.resolve(strict=True)
    require(directory.parent == (ROOT / 'artifacts/desktop-long').resolve() and re.fullmatch(r'\d{8}-\d{6}-[a-f0-9]{8}', directory.name), 'Use an explicit owned desktop-long evidence directory')
    def read(name): return json.loads((directory / name).read_text(encoding='utf-8'))
    checks = read('multiplayer-checks.json'); summary = summarize(checks, read('cleanup.json'), (directory / 'multiplayer-continuity.json').is_file())
    if summary['diagnosticMode'] == 'Sparse':
        require(read('multiplayer-continuity.json') == checks['poseContinuity'], 'Independent diagnostic manifest differs')
    require(read('long-multi-sealed.json') == checks['sealed'], 'Independent sealed artifact differs')
    roster = read('multiplayer-native-clients.json'); require(len(roster) == summary['participants'], 'Native roster size differs')
    owners = {p['playerId']: p for p in roster}; require(len(owners) == len(roster) and len({p['admissionId'] for p in roster}) == len(roster), 'Native admission identities alias')
    for result in checks['clientResults']:
        require(result['playerId'] in owners and result['admissionId'] == owners[result['playerId']]['admissionId'] and result['roomId'] == owners[result['playerId']]['roomId'], 'Final admission / room differs from original native process')
    delivery = read('long-multi-player-results.json')
    require(delivery['allAcknowledged'] is True and len(delivery['phases']) == len(roster) and all(value == 'acknowledged' for value in delivery['phases'].values()), 'Not all original results were acknowledged')
    csv_path = directory / 'final-report.csv'; content = csv_path.read_bytes(); record = checks['finalReportCsv']
    require(hashlib.sha256(content).hexdigest() == record['sha256'] and record['verified'] is True, 'CSV fingerprint differs')
    rows = list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline='')))
    require(len(rows) == len(roster) and {r['playerId'] for r in rows} == set(owners), 'CSV roster differs')
    results = {p['playerId']: p for p in checks['clientResults']}
    for row in rows:
        result = results[row['playerId']]
        require(int(row['finalStreamSequence']) == result['finalStreamSequence'] and row['streamId'] == result['streamId'] and int(row['throughSequence']) == result['throughSequence'], 'CSV seal boundary differs')
        require(all(Decimal(row[k]) == Decimal(str(result[k])) for k in ('ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken', 'health', 'accuracyPercent')), 'CSV statistics differ')
    evidence_names = ['multiplayer-checks.json', 'cleanup.json', 'long-multi-sealed.json', 'multiplayer-native-clients.json', 'long-multi-player-results.json', 'final-report.csv']
    if summary['diagnosticMode'] == 'Sparse': evidence_names.append('multiplayer-continuity.json')
    summary.update(run=directory.name, evidenceHashes={name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in evidence_names})
    return summary


def comparison(rows):
    require(len(rows) >= 2 and len({r['run'] for r in rows}) == len(rows), 'Compare at least two distinct closed runs')
    conditions = ('sourceFingerprint', 'participants', 'durationSeconds', 'rooms', 'origin', 'rulesVersion', 'assetSet', 'diagnosticMode')
    differences = {key: [r[key] for r in rows] for key in conditions if any(r[key] != rows[0][key] for r in rows[1:])}
    return {'version': 1, 'complete': True, 'runs': rows, 'comparedFields': list(conditions), 'recordedConditionDifferences': differences, 'causalRootProven': False,
        'networkCapacityAccepted': False, 'scope': 'Closed same-host stationary Simulation evidence; observed metadata is not randomized control or device / active-input / network-capacity proof'}


def markdown(report):
    lines = ['# PC 長任務跨場對照', '', '此表列事實，不判定根因或修復；不同版本／診斷條件及未量測的主機狀態仍可能影響結果。', '',
        '| 場次 | Source SHA | 診斷模式 | 玩家程序 | Running幀 | 應核對人次 | 失效幀／人次 | 個別結果 | 本場接受 |',
        '|---|---|---|---:|---:|---:|---:|---:|---|']
    for r in report['runs']:
        lines.append(f"| {r['run']} | {r['sourceFingerprint'][:12]} | {r['diagnosticMode']} | {r['participants']} | {r['runningFrames']} | {r['participantObservations']} | {r['badFrames']}／{r['badParticipantRows']} | {r['individualResults']} | {'通過' if r['acceptancePassed'] else '未通過'} |")
    lines += ['', '模式 NotRecorded 表示舊報告未保存欄位，不能由缺少資料推成 DisabledByTool。', '',
        '記錄條件差異：' + ('、'.join(report['recordedConditionDifferences']) or '上述欄位相同；未量測條件不因此相同。'), '',
        '保存SQLite未開連線，未重寫原始報告；complete表示比較完成，不表示每場成功、根因已解或完整目標完成。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('directories', nargs='+', type=Path); parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    output = args.output.resolve(); require(output.is_relative_to((ROOT / 'artifacts').resolve()) and not output.exists(), 'Write into a new artifacts directory')
    report = comparison([load_evidence(p) for p in args.directories]); output.mkdir(parents=True, exist_ok=False)
    (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (output / 'comparison.md').write_text(markdown(report), encoding='utf-8')
    print(json.dumps({'complete': True, 'runs': len(report['runs']), 'recordedConditionDifferences': list(report['recordedConditionDifferences']), 'causalRootProven': False, 'output': str(output)}))


if __name__ == '__main__': main()
