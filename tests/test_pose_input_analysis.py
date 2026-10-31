"""Synthetic counterexamples for input timing attribution, not native evidence."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pose_input_analysis', ROOT / 'scripts/analyze-pose-input.py')
analysis = importlib.util.module_from_spec(spec); spec.loader.exec_module(analysis)


class PoseInputAnalysisTests(unittest.TestCase):
    def fixture(self, directory):
        start = datetime(2026, 10, 31, tzinfo=timezone.utc); epoch = analysis.common.ticks(start.isoformat())
        periods = {'baseline-start': .05, 'baseline-end': .6, 'shot-1-start': .7, 'shot-1-end': 1.2,
                   'shot-2-start': 1.25, 'shot-2-end': 2, 'shot-3-start': 2.1, 'shot-3-end': 2.8, 'observation-end': 2.95}
        (directory / 'input-stages.json').write_text(json.dumps([{'phase': name, 'utc': (start + timedelta(seconds=seconds)).isoformat()}
                                                               for name, seconds in periods.items()]))
        def row(point, seconds, connection=0, duration=0):
            return {'point': point, 'seconds': seconds, 'engineSeconds': seconds + 5, 'durationSeconds': duration,
                    'poseAgeSeconds': .6 if point == 'BodyConnection' else -1, 'utcTicks': epoch + round(seconds * 10_000_000),
                    'frame': int(seconds * 60), 'connection': connection, 'source': 1, 'connected': False}
        for name, role, connection in [('player','Client',2), ('peer','Client',1), ('server','Server',0)]:
            rows = []
            for index in range(61):
                seconds = index * .05
                for identity in ([1, 2] if name == 'server' else [connection]):
                    if identity == 2 and .8 <= seconds < 1.65: continue
                    rows.append(row('PoseReceive' if name == 'server' else 'PoseSend', seconds, identity))
                    if name == 'server': rows.append(row('PoseAccepted', seconds, identity))
            gap_end = {'player': 1.55, 'peer': 1.6, 'server': 1.5}[name]
            rows.append(row('MainThreadGap', gap_end, duration=.7))
            if name == 'server': rows.append(row('BodyConnection', 1.4, 2))
            path = directory / f'runtime-snapshot/pose-input-{name}-trace/report.json'; path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'schemaVersion':1, 'source':'NativeWindowsMonotonicTiming', 'role':role,
                'complete':True, 'truncated':False, 'error':'', 'capacity':32768, 'endedSeconds':3.1, 'rows':sorted(rows, key=lambda r:r['seconds'])}))
        hud = directory / 'runtime-snapshot/pose-input-hud/report.json'; hud.parent.mkdir()
        hud.write_text(json.dumps({'complete':True, 'error':'', 'hudTransitionsTruncated':False, 'mode':'hud-trace',
            'captures':[], 'audioSamples':0, 'callbackCount':0, 'startedAtUtc':start.isoformat(),
            'hudTransitions':[{'seconds':1.45, 'hud':{'status':'POSE STREAM STALE', 'poseAccepted':True, 'connected':False}}]}))

    def run_case(self, action):
        with tempfile.TemporaryDirectory(prefix='vr-pose-input-') as temporary:
            directory = Path(temporary).resolve()
            self.assertEqual(directory.parent, Path(tempfile.gettempdir()).resolve())
            self.assertTrue(directory.name.startswith('vr-pose-input-'))
            self.fixture(directory); action(directory)

    def edit(self, directory, name, change):
        path = directory / f'runtime-snapshot/pose-input-{name}-trace/report.json'
        value = json.loads(path.read_text()); change(value); path.write_text(json.dumps(value))

    def test_peer_traffic_cannot_hide_visible_receiver_gap(self):
        def verify(d):
            value = analysis.analyze(d)
            self.assertGreater(value['phases']['observation']['Visible']['serverReceive']['maximumGapSeconds'], .8)
            self.assertLess(value['phases']['observation']['Peer']['serverReceive']['maximumGapSeconds'], .06)
            self.assertEqual(value['connectionIds'], {'Visible':2, 'Peer':1})
            self.assertEqual(len(value['phases']['observation']['Visible']['publishedStale']), 1)
            self.assertEqual(value['phases']['observation']['Peer']['publishedStale'], [])
        self.run_case(verify)

    def test_gap_spanning_phase_boundary_is_retained(self):
        self.run_case(lambda d: self.assertGreater(analysis.analyze(d)['phases']['shot-1']['Visible']['rpcCall']['maximumGapSeconds'], .8))

    def test_three_interval_intersection_reports_only_common_time(self):
        def verify(d):
            value = analysis.analyze(d)
            self.assertTrue(value['clockJoinValid'])
            self.assertEqual(len(value['overlappingThreeProcessMainThreadGaps']), 1)
            self.assertAlmostEqual(value['overlappingThreeProcessMainThreadGaps'][0]['seconds'], .6)
        self.run_case(verify)

    def test_nonoverlapping_gaps_do_not_manufacture_shared_stall(self):
        def verify(d):
            self.edit(d, 'peer', lambda r: r['rows'].__setitem__(slice(None), [x for x in r['rows'] if x['point'] != 'MainThreadGap']))
            self.assertEqual(analysis.analyze(d)['overlappingThreeProcessMainThreadGaps'], [])
        self.run_case(verify)

    def test_clock_step_withholds_all_cross_process_phase_joins(self):
        def verify(d):
            self.edit(d, 'peer', lambda r: r['rows'][5].__setitem__('utcTicks', r['rows'][5]['utcTicks'] + 2_000_000))
            value = analysis.analyze(d); self.assertFalse(value['clockJoinValid'])
            self.assertIsNone(value['overlappingThreeProcessMainThreadGaps']); self.assertIsNone(value['phases'])
        self.run_case(verify)

    def test_connection_changes_require_separate_evidence(self):
        def verify(d):
            self.edit(d, 'player', lambda r: r['rows'][0].__setitem__('connection', 3))
            with self.assertRaises(ValueError): analysis.analyze(d)
        self.run_case(verify)

    def test_incomplete_trace_is_not_successful_timing(self):
        def verify(d):
            self.edit(d, 'server', lambda r: r.__setitem__('truncated', True))
            with self.assertRaises(AssertionError): analysis.analyze(d)
        self.run_case(verify)

    def test_native_gpu_or_audio_capture_cannot_claim_trace_only(self):
        def verify(d):
            path = d / 'runtime-snapshot/pose-input-hud/report.json'; value = json.loads(path.read_text())
            value['captures'] = ['not-allowed.png']; path.write_text(json.dumps(value))
            with self.assertRaises(ValueError): analysis.analyze(d)
        self.run_case(verify)

    def test_hud_stale_tail_is_not_a_zero_duration_or_recovery(self):
        def verify(d):
            tail = analysis.analyze(d)['hudStaleTransitions'][0]
            self.assertTrue(tail['rightCensored']); self.assertIsNone(tail['durationSeconds']); self.assertIsNone(tail['nextStatus'])
            path = d / 'runtime-snapshot/pose-input-hud/report.json'; value = json.loads(path.read_text())
            value['hudTransitions'].append({'seconds':1.7, 'hud':{'status':'ACTIVE', 'poseAccepted':True, 'connected':True}})
            path.write_text(json.dumps(value)); interval = analysis.analyze(d)['hudStaleTransitions'][0]
            self.assertFalse(interval['rightCensored']); self.assertAlmostEqual(interval['durationSeconds'], .25)
            self.assertEqual(interval['nextStatus'], 'ACTIVE')
        self.run_case(verify)

    def test_post_trace_hud_stale_is_retained_without_attributing_it_to_observation(self):
        def verify(d):
            path = d / 'runtime-snapshot/pose-input-hud/report.json'; value = json.loads(path.read_text())
            value['hudTransitions'][0]['seconds'] = 3.5; path.write_text(json.dumps(value))
            interval = analysis.analyze(d)['hudStaleTransitions'][0]
            self.assertFalse(interval['withinPoseObservation']); self.assertTrue(interval['rightCensored'])
        self.run_case(verify)

    def test_declared_heartbeat_cannot_silently_lose_its_report(self):
        def verify(d):
            (d / 'input-timing-result.json').write_text(json.dumps({'independentHeartbeat':True}))
            with self.assertRaises(ValueError): analysis.analyze(d)
        self.run_case(verify)

    def test_declared_player_loop_cannot_silently_lose_its_report(self):
        def verify(d):
            (d/'input-timing-result.json').write_text(json.dumps({'playerLoop':True}))
            with self.assertRaises(ValueError):analysis.analyze(d)
        self.run_case(verify)

    def empty_loop(self):
        # Observed Windows JsonUtility representation of a null report field.
        return {'version':1,'capacity':4096,'maximumNodes':512,'source':'NativeWindowsPlayerLoopBoundaries',
            'complete':False,'truncated':False,'detached':False,'callbacks':0,'firstUtcTicks':0,'lastUtcTicks':0,
            'firstSeconds':0.,'lastSeconds':0.,'maximumClockStepSeconds':0.,'boundaries':[],'gaps':[]}

    def test_actual_serialized_empty_class_requires_explicit_disabled_mode(self):
        def verify(d):
            for name in ('player','peer','server'):self.edit(d,name,lambda r:r.__setitem__('playerLoop',self.empty_loop()))
            with self.assertRaises(ValueError):analysis.analyze(d)
            (d/'input-timing-result.json').write_text(json.dumps({'playerLoop':False}))
            self.assertIsNone(analysis.analyze(d)['playerLoop'])
            (d/'input-timing-result.json').write_text(json.dumps({'playerLoop':True}))
            with self.assertRaises(ValueError):analysis.analyze(d)
        self.run_case(verify)

    def test_disabled_mode_does_not_hide_nonempty_or_failed_loop_evidence(self):
        def verify(d):
            (d/'input-timing-result.json').write_text(json.dumps({'playerLoop':False}))
            raw=self.empty_loop();raw['callbacks']=1
            self.edit(d,'player',lambda r:r.__setitem__('playerLoop',raw))
            with self.assertRaises(ValueError):analysis.analyze(d)
        self.run_case(verify)

    def test_observation_phase_names_do_not_require_shooting_stages(self):
        def verify(d):
            path=d/'input-stages.json';rows=json.loads(path.read_text())
            for row in rows:row['phase']=row['phase'].replace('shot-1','window-review').replace('shot-2','quiet-after')
            rows=[row for row in rows if not row['phase'].startswith('shot-3')];path.write_text(json.dumps(rows))
            value=analysis.analyze(d);self.assertIn('window-review',value['phases']);self.assertIn('quiet-after',value['phases'])
            self.assertNotIn('shot-1',value['phases'])
        self.run_case(verify)


if __name__ == '__main__': unittest.main()
