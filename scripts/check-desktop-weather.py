"""Verify actual native desktop weather rendering and this player's DSP output.

Uses a fresh isolated API / server / visible Simulation client, no microphone or
OS audio capture. Development player opt-in records its own listener mix and GPU
backbuffer. This is not a physical speaker, headset or human listening test.
"""
import argparse
import array
import bisect
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('desktop_venue', ROOT / 'scripts/start-desktop-venue.py')
venue_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(venue_module)


def run(venue):
    from PIL import Image, ImageStat
    venue.start()
    mission = venue.request('/api/missions', {'name': 'Native weather DSP - Simulation', 'briefing': 'No microphone / OS loopback; no injected gameplay', 'durationSeconds': 180,
        'environment': {'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Night', 'lightning': True},
        'enemies': {'count': 0, 'behavior': 'Hold', 'autoAttack': False},
        'props': [{'assetId': 'sandbag', 'position': {'x': -3, 'y': 0, 'z': 0}, 'yawDegrees': 0}]}, expected=201)
    entry = venue.create(mission, [3], 'weather', role='Room3')
    venue.wait(lambda: venue.request('/api/sessions/' + entry['id'] + '/world', optional=True), 90, 'native recording')
    directory = venue.runtime_directory / 'weather-probe'
    venue.stage('weather_starting', source='Simulation', headsets=0, probeDirectory=str(directory))
    player = entry['players'][0]; ticket = venue.ticket(entry, player)
    venue.launch('weather-client', venue.client_config(entry, ticket), True, extra_args=['--vr-weather-probe', str(directory.resolve())])

    def status():
        try: value = json.loads((directory / 'status.json').read_text(encoding='utf-8-sig'))
        except (FileNotFoundError, json.JSONDecodeError): return None
        if value['error']: raise RuntimeError('Native weather probe: ' + value['error'])
        return value

    def until(predicate, label, seconds=20):
        def ready():
            venue.frame(entry, measure=True)
            value = status()
            return value if value and value['frame'] and predicate(value) else None
        return venue.wait(ready, seconds, label)

    venue.wait(lambda: venue.connected(entry), 30, 'native accepted Simulation player')
    until(lambda s: s['callbackCount'] > 5, 'real listener DSP callbacks')
    venue.command(entry, 'Begin')
    until(lambda s: 'night' in s['captures'], 'native night GPU capture')
    first = until(lambda s: s['frame']['thunderPlaying'] and 'flash' in s['captures'], 'flash then delayed thunder', 20)
    until(lambda s: s['frame']['seconds'] > first['frame']['seconds'] + .7, 'thunder output interval')
    venue.command(entry, 'Pause')
    paused = until(lambda s: s['frame']['phase'] == 'Paused' and not s['frame']['thunderPlaying'], 'Pause stops native thunder')
    until(lambda s: s['frame']['seconds'] > paused['frame']['seconds'] + 1.2, 'paused silence interval')
    venue.command(entry, 'SetEnvironment', environment={'mode': 'VR', 'weather': 'Rain', 'timeOfDay': 'Day', 'lightning': False})
    venue.command(entry, 'Resume')
    raining = until(lambda s: s['frame']['weather'] == 1 and s['frame']['rainPlaying'] and s['frame']['vertices'] == 128 and 'rain' in s['captures'] and 'day' in s['captures'], 'actual rain mesh / audio and day capture')
    until(lambda s: s['frame']['seconds'] > raining['frame']['seconds'] + 1.5, 'rain output interval')
    venue.command(entry, 'SetEnvironment', environment={'mode': 'VR', 'weather': 'Storm', 'timeOfDay': 'Night', 'lightning': True})
    storm = until(lambda s: s['frame']['weather'] == 3 and s['frame']['vertices'] == 256 and s['frame']['thunderPlaying'] and 'storm' in s['captures'], 'storm rain mesh plus next delayed thunder', 20)
    until(lambda s: s['frame']['seconds'] > storm['frame']['seconds'] + .7, 'storm output interval')
    venue.command(entry, 'SetEnvironment', environment={'mode': 'VR', 'weather': 'Clear', 'timeOfDay': 'Day', 'lightning': False})
    clear = until(lambda s: s['frame']['weather'] == 0 and not s['frame']['rainPlaying'] and not s['frame']['thunderPlaying'], 'Clear stops rain; existing thunder tail finishes')
    until(lambda s: s['frame']['seconds'] > clear['frame']['seconds'] + 1.2, 'clear silence interval')
    venue.seal(entry)
    def final_report():
        try: value = json.loads((directory / 'report.json').read_text(encoding='utf-8-sig'))
        except (FileNotFoundError, json.JSONDecodeError): return None
        return value if value['complete'] else None
    report = venue.wait(final_report, 15, 'native WAV / final report')
    assert report['complete'] and not report['error'] and not report['truncated'] and not report['formatChanged']
    assert report['callbackCount'] == len(report['audio']) > 100
    frames = report['frames']; times = [f['seconds'] for f in frames]
    flash_tick = next(f['tick'] for f in frames if f['flash'])
    thunder_tick = next(f['tick'] for f in frames if f['weather'] == 0 and f['lightning'] and f['thunderPlaying'])
    cue_tick = (flash_tick // 140) * 140 + 40
    assert cue_tick <= thunder_tick <= cue_tick + 4, 'Native thunder start is outside the 10 Hz observation tolerance'
    groups = {name: [] for name in ['thunder', 'rain', 'storm', 'paused', 'clear']}
    def state_key(frame):
        return tuple(frame[key] for key in ['phase', 'weather', 'night', 'lightning', 'rainPlaying', 'thunderPlaying'])
    for window in report['audio']:
        index = bisect.bisect_right(times, window['seconds']) - 1
        if index < 0: continue
        frame = frames[index]
        previous = frames[max(0, index - 3)]
        following = frames[min(len(frames) - 1, index + 1)]
        # DSP callbacks and 10 Hz main-thread observations are asynchronous.
        # Exclude BOTH edges of a state transition; a resumed audio callback may
        # precede the next logged Running frame and must not be called Paused.
        if state_key(frame) != state_key(previous) or state_key(frame) != state_key(following): continue
        if frame['phase'] == 'Paused': groups['paused'].append(window['rms'])
        elif frame['phase'] == 'Running':
            if frame['weather'] == 0 and frame['lightning'] and frame['thunderPlaying'] and previous['thunderPlaying']: groups['thunder'].append(window['rms'])
            elif frame['weather'] == 1: groups['rain'].append(window['rms'])
            elif frame['weather'] == 3: groups['storm'].append(window['rms'])
            elif not frame['lightning'] and not frame['thunderPlaying'] and not previous['thunderPlaying']: groups['clear'].append(window['rms'])
    for name in ['thunder', 'rain', 'storm']: assert len(groups[name]) > 10 and max(groups[name]) > 1e-5, name + ' has no actual DSP output'
    for name in ['paused', 'clear']: assert len(groups[name]) > 10 and max(groups[name]) < 1e-6, name + ' is not silent'
    with wave.open(str(directory / 'audio.wav'), 'rb') as wav:
        assert wav.getnchannels() == report['channels'] and wav.getframerate() == report['sampleRate'] and wav.getsampwidth() == 2
        samples = array.array('h', wav.readframes(wav.getnframes()))
    assert len(samples) == report['audioSamples'] == sum(w['samples'] for w in report['audio'])
    rms = math.sqrt(sum((sample / 32767) ** 2 for sample in samples) / len(samples))
    measured = math.sqrt(sum(w['rms'] ** 2 * w['samples'] for w in report['audio']) / len(samples))
    assert rms > 1e-5 and abs(rms - measured) < 1e-4
    night = Image.open(directory / 'night.png').convert('RGB'); flash = Image.open(directory / 'flash.png').convert('RGB')
    assert night.size == flash.size
    box = (int(night.width * .1), int(night.height * .6), int(night.width * .9), int(night.height * .9))
    luminance = lambda image: sum(ImageStat.Stat(image.crop(box)).mean) / 3
    difference = luminance(flash) - luminance(night)
    assert difference > 3, 'GPU flash did not brighten the visible floor / cover'
    assert any(f['flash'] and f['sun'] > 2 for f in frames) and any(f['night'] and not f['flash'] and f['sun'] < .1 for f in frames)
    venue.evidence.extend(['Actual GPU night / flash / day / rain captures', 'Actual listener thunder / rain / storm DSP; Pause / Clear silence', 'Captured PCM WAV agrees with callback energy; not a microphone or OS recording'])
    venue.summary()
    venue.save('weather-result.json', {'source': 'Actual Windows development player; Simulation', 'headsets': 0, 'probeDirectory': str(directory),
        'sampleRate': report['sampleRate'], 'channels': report['channels'], 'audioSamples': len(samples), 'wavRms': rms,
        'audioGroups': {key: {'windows': len(value), 'maxRms': max(value)} for key, value in groups.items()}, 'flashLuminanceIncrease': difference,
        'firstObservedFlashTick': flash_tick, 'firstObservedThunderTick': thunder_tick, 'expectedThunderTick': cue_tick,
        'captures': report['captures'], 'playerBuildReceipt': venue.receipt})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--player-exe', type=Path, default=Path(os.environ.get('VR_COMMAND_UNITY_PLAYER', ROOT / 'artifacts/desktop/VrCommand.exe')))
    parser.add_argument('--api-dll', type=Path, default=Path(os.environ.get('VR_COMMAND_API_DLL', ROOT / 'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')))
    parser.add_argument('--runtime-root', type=Path)
    args = parser.parse_args(); args.visible_room = 3; args.job_workers = 2; args.duration = 180; args.check = False
    if importlib.util.find_spec('PIL') is None: parser.error('Image analysis requires Pillow (tested 12.3.0); use a Python environment with Pillow installed.')
    try: venue_module.verify_player(args)
    except (OSError, RuntimeError, ValueError) as error: parser.error(str(error))
    venue = venue_module.Venue(args)
    try: run(venue)
    except BaseException as error: venue.stage('failed', errorType=type(error).__name__); raise
    finally:
        if not venue.cleanup() and sys.exc_info()[0] is None: raise RuntimeError('Weather fixture cleanup failed; inspect cleanup.json')


if __name__ == '__main__': main()
