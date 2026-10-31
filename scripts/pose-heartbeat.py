"""Bounded independent process wake timing; no game / network / UI access.

Keeps gaps and clock anchors in memory, writes once after explicit finish or the
240-second cap. Normal process priority and normal sleep; no system settings.
"""
import argparse
import json
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    if not args.directory.is_absolute(): parser.error('Use a fresh absolute directory')
    directory = args.directory.resolve(); directory.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter_ns(); previous = started; previous_utc = time.time_ns(); started_utc = previous_utc; previous_cpu = time.process_time_ns()
    gaps = []; anchors = []; wakes = 0; maximum = 0; clock_error = 0; next_check = started; next_anchor = started
    explicit = False; truncated = False
    while True:
        time.sleep(.01)
        now = time.perf_counter_ns(); utc = time.time_ns(); cpu = time.process_time_ns()
        delta = now - previous; maximum = max(maximum, delta); wakes += 1
        clock_error = max(clock_error, abs((utc - previous_utc) - delta))
        if delta > 100_000_000:
            if len(gaps) < 4096:
                gaps.append({'fromCounterNs': previous, 'toCounterNs': now, 'fromUnixNs': previous_utc, 'toUnixNs': utc,
                             'durationNs': delta, 'processCpuNs': cpu - previous_cpu})
            else: truncated = True
        if now >= next_anchor:
            if len(anchors) < 256: anchors.append({'counterNs': now, 'unixNs': utc})
            else: truncated = True
            next_anchor = now + 1_000_000_000
        previous = now; previous_utc = utc; previous_cpu = cpu
        if now - started >= 240_000_000_000: break
        if now >= next_check:
            next_check = now + 250_000_000
            if (directory / 'finish.request').exists(): explicit = True; break
    # The output write and serialization are outside the observation window.
    report = {'schemaVersion': 1, 'source': 'IndependentPythonWakeTiming', 'complete': explicit and not truncated,
        'truncated': truncated, 'maximumSeconds': 240, 'sampleSeconds': .01, 'maximumGapRows': 4096,
        'wakes': wakes, 'startedCounterNs': started, 'endedCounterNs': previous, 'durationNs': previous - started,
        'startedUnixNs': started_utc, 'endedUnixNs': previous_utc,
        'maximumGapNs': maximum, 'maximumClockStepNs': clock_error, 'gaps': gaps, 'anchors': anchors}
    (directory / 'report.json').write_text(json.dumps(report), encoding='utf-8')


if __name__ == '__main__': main()
