"""Bounded Windows Development batch-client generated movement/fire/reload over the original native RPC path.

Automated Simulation input, not physical operators, XR tracking, LAN or capacity acceptance.
"""
import argparse,concurrent.futures,hashlib,importlib.util,io,json,math,os,re,sys,time,urllib.request,uuid,zipfile
from collections import deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
capacity=module('exercise_capacity','check-desktop-capacity.py');vm=capacity.venue_module;debrief=module('exercise_debrief','check-desktop-debrief.py')
active=module('exercise_active','check-desktop-active.py')
udp=module('exercise_udp','udp_gate.py')
continuity=module('exercise_continuity','check-desktop-multiplayer-long.py')

def validate_control_receipts(responses,session_id,command_ids,previous_sequence):
    if len(responses)!=2 or len(set(command_ids))!=2:raise ValueError('Expected two distinct operator intents')
    previous=previous_sequence
    for response,identity in zip(responses,command_ids):
        sequence=response.get('appliedAtSequence')
        if response.get('commandId')!=identity or response.get('duplicate') is not False or response.get('session',{}).get('id')!=session_id or type(sequence) is not int or sequence<=previous:
            raise ValueError('Operator receipt differs from its original intent/session/order')
        previous=sequence
    return previous

def match_control_reference(value,references,matched):
    sequence=value['packet']['sequence']
    if sequence in references:
        expected=references[sequence]
        if value['packet']!=expected['packet'] or value['statistics']!=expected['statistics']:raise ValueError('Operator source checkpoint differs from its original replay')
        matched.add(sequence)

def operator_phase(v,entry,environment,behavior):
    before=v.frame(entry,measure=True);commands=[str(uuid.uuid4()),str(uuid.uuid4())]
    witness={'transport':'ManagementApi','physicalOperators':0,'environment':environment,'behavior':behavior,'commandIds':commands,'before':before,'receipts':[],'applied':None}
    entry.setdefault('operatorControls',[]).append(witness)
    def save():v.save(entry['name']+'-operator-controls.json',entry['operatorControls'])
    save()
    for identity,action,payload in [(commands[0],'SetEnvironment',{'environment':environment}),(commands[1],'SetEnemies',{'enemies':{'count':len(entry['roomIds']),'behavior':behavior,'autoAttack':False}})]:
        expected=v.state(entry)['sequence']
        response=v.command(entry,action,commandId=identity,expectedSequence=expected,**payload)
        witness['receipts'].append(response);save()
    fence=validate_control_receipts(witness['receipts'],entry['id'],commands,before['packet']['observedSequence']);witness['acceptedSequence']=fence;save()
    def observed():
        value=v.frame(entry,measure=True)
        try:
            active.validate_operator_packet(value,environment,behavior,fence,before['packet']['frame']['tick']+20)
            frame=validate_frame(value,entry['players'],begin_sequence=entry['beginSequence'])
            distances=active.validate_enemy_motion(before['packet']['frame'],frame)
            if any(d<=.01 for d in distances.values()):return None
            if not all(p['walking'] for p in frame['players']):return None
        except ValueError:return None
        return value,distances
    value,distances=v.wait(observed,15,'generated clients plus operator '+behavior)
    witness['applied']=value;witness['enemyMovementMeters']=distances;save()
    if v.args.check_policy_frames:
        tail=value['packet']['sequence']
        witness['liveEnvironmentLookup']=v.request(f'/api/sessions/{entry["id"]}/world/policy-neighbor?throughFrame={tail}'
            f'&fromFrame={tail}&direction=previous&includeFrom=true&change=environment')
        save()
    references=entry.setdefault('operatorReferences',{})
    for point in [before,value]:references[point['packet']['sequence']]=point
    validate_roster(v.state(entry),entry['players'])
    return witness

def validate_roster(session,players):
    expected={p['id']:p for p in players};source={p['id']:p for p in session['players']}
    if set(source)!=set(expected) or any(source[k]['admissionId']!=p['admissionId'] or source[k]['roomId']!=p['roomId'] or source[k]['seat']!=p['seat'] for k,p in expected.items()):raise ValueError('Original API roster changed an admission, seat or room')

def validate_frame(value,players,pause=None,begin_sequence=1,*,damage_since=None):
    packet=value['packet'];frame=packet['frame'];expected={p['id']:p for p in players};actual=frame['players'];observed=packet['observedSequence']
    if packet.get('suspended') or frame['phase'] not in ('Running','Paused') or len(actual)!=len(expected) or {p['id'] for p in actual}!=set(expected):raise ValueError('Missing, suspended or unexpected phase/body')
    if type(observed) is not int or observed<begin_sequence:raise ValueError('Source has not applied this original Begin')
    if frame['phase']=='Paused' and (pause is None or observed<pause['accepted'] or pause.get('resumed') is not None and observed>=pause['resumed']):raise ValueError('Unexpected pause cannot be ignored')
    for p in actual:
        owner=expected[p['id']];head=p['head'];x=(owner['roomId']-3)*14+(owner['seat']-2)*1.5
        healthy = p['health']==100 if damage_since is None or observed<damage_since else 0<p['health']<=100
        if not p['connected'] or not healthy or p['roomId']!=owner['roomId'] or p['rig']['kind']!='Simulated':raise ValueError('Original native body became inactive or changed identity')
        if not all(type(head[a]) in (int,float) and math.isfinite(head[a]) for a in ('x','y','z')) or abs(head['x']-x)>.1 or not -3.4<=head['z']<=-1.6 or abs(head['y']-1.65)>.02:raise ValueError('Generated motion left its own bounded standing lane')
    return frame

def validate_report(report,owner,expected_fires=2,expected_reloads=1,minimum_ticks=0,endurance=False):
    if report.get('version')!=1 or report.get('mode')!='AutomatedSimulation' or report.get('role')!='Client' or report.get('physicalInput') is not False or type(report.get('headsets')) is not int or report['headsets']!=0:raise ValueError('Not an explicit synthetic client input report')
    if report.get('complete') is not True or report.get('truncated') is not False or report.get('reason')!='Requested' or report.get('fault') not in (None,''):raise ValueError('Exercise did not explicitly finish cleanly')
    if report['pid']!=owner['pid'] or report['playerId']!=owner['playerId'] or report['room']!=owner['roomId'] or report['connection']!=owner['nativeConnectionId']:raise ValueError('Exercise owner differs from original native process/connection')
    if report['fireSubmissions']!=expected_fires or report['reloadSubmissions']!=expected_reloads or report['movementFrames']<1 or report['activeFrames']<report['movementFrames'] or not 0<=report['firstTick']<report['lastTick'] or report['lastTick']-report['firstTick']<minimum_ticks:raise ValueError('Not all bounded production-path input attempts were made')
    if endurance and (report.get('profile')!='Endurance' or report.get('motion')!='LocalPositionFeedback' or report.get('maximumActiveTicks')!=19000 or report.get('maximumCollectionSeconds')!=1200):raise ValueError('Not the explicit bounded endurance feedback profile')

def validate_endurance_cycles(cycles,expected):
    if set(cycles)!=set(range(expected)):raise ValueError('Endurance replay is missing a complete scheduled cycle')
    for index,sample in cycles.items():
        if not all(type(sample[k]) in (int,float) and math.isfinite(sample[k]) for k in ('min','max')) or sample['max']-sample['min']<.1 or sample['reload'] is not True or sample['ammoMax']!=2*(index+1) or sample['frames']<1 or sample['walkingFrames']<1:
            raise ValueError('Endurance cycle lacks accepted movement, reload or exact cumulative shots')

def summarize_link_report(report, owner):
    if (report['version'] != 1 or report['complete'] is not True or report['reason'] != 'Limit'
            or report['processId'] != owner['pid'] or report['connection'] != owner['nativeConnectionId']
            or report['batchMode'] is not True or report['graphicsDeviceActive'] is not False):
        raise ValueError('Link report does not belong to the original headless client')
    samples = report['samples']
    if len(samples) != 30 or [row['sequence'] for row in samples] != list(range(1, 31)):
        raise ValueError('Link report lost part of its bounded sample window')
    rtts = []
    previous_tick = 0
    for row in samples:
        tick, frames, window, rtt = (row[key] for key in ('tick', 'playerLoopFrames', 'windowSeconds', 'roundTripMilliseconds'))
        if (type(tick) is not int or tick < previous_tick or type(frames) is not int or frames < 1
                or type(window) not in (int, float) or not math.isfinite(window) or window < 1
                or type(rtt) not in (int, float) or not math.isfinite(rtt) or rtt < 0):
            raise ValueError('Invalid link sample timing or player loop count')
        previous_tick = tick
        if row['result'] == 'Reply' and rtt < 900:
            rtts.append(rtt)
        elif row['result'] not in ('Timeout', 'Interrupted') or rtt != 0:
            raise ValueError('Link outcome cannot be counted as a measured reply')
    if not rtts:
        raise ValueError('No original probe replies were observed')
    rtts.sort()
    return {**owner, 'attempts': len(samples), 'replies': len(rtts),
            'timeouts': sum(row['result'] == 'Timeout' for row in samples),
            'interruptions': sum(row['result'] == 'Interrupted' for row in samples),
            'p50RoundTripMilliseconds': rtts[math.ceil(len(rtts) * .5) - 1],
            'p95RoundTripMilliseconds': rtts[math.ceil(len(rtts) * .95) - 1],
            'playerLoopHz': sum(row['playerLoopFrames'] for row in samples) / sum(row['windowSeconds'] for row in samples)}


AUTHORITY_MARKERS = {
    'VR_MANAGEMENT_REFRESH_FAILED': re.compile(
        r'reason=(ProtocolError|ConnectionError|DataProcessingError|InvalidSnapshot|UnsupportedMrRole|MissingMrAlignment|ApplyRejected)'
        r' httpStatus=\d{1,3} elapsedSeconds=\d+\.\d{3} monotonicSeconds=\d+\.\d{3}'),
    'VR_AUTHORITY_SUSPENDED': re.compile(
        r'reason=(ManagementRefresh|ManagementWatchdog|TelemetryFault) observedSequence=\d+'
        r' managementAgeSeconds=(?:\d+\.\d{3}|Infinity) monotonicSeconds=\d+\.\d{3}'),
    'VR_AUTHORITY_RESUMED': re.compile(
        r'observedSequence=\d+ phase=(Preparing|Running|Paused|Ended) monotonicSeconds=\d+\.\d{3}'),
}


def summarize_authority_log(lines):
    counts = dict.fromkeys(AUTHORITY_MARKERS, 0)
    recent = deque(maxlen=32)
    unrecognized = 0
    for line in lines:
        marker, _, details = line.rstrip('\r\n').partition(' ')
        if marker not in AUTHORITY_MARKERS:
            continue
        if not AUTHORITY_MARKERS[marker].fullmatch(details):
            unrecognized += 1
            continue
        counts[marker] += 1
        recent.append(marker + ' ' + details)
    return {'counts': counts, 'unrecognizedMarkers': unrecognized, 'recentMarkers': list(recent),
            'truncated': sum(counts.values()) > len(recent)}


class ExerciseVenue(continuity.DiagnosticVenue):
    def __init__(self,args):
        super().__init__(args,artifact_family='desktop-exercise')
        self.exercise={};self.receipts=[];self.pauses={};self.link_reports={}
        self.udp_meter=None
        self.udp_relays={}

    def launch(self,name,config,visible=False,*,extra_args=()):
        relay=None
        if config['role']=='Client':
            directory=self.runtime_directory/(name+'-exercise');self.exercise[name]=directory
            extra_args=(*extra_args,'--vr-desktop-endurance' if self.args.endurance else '--vr-desktop-exercise',str(directory))
            if self.args.link_metrics:
                report=self.runtime_directory/(name+'-link-metrics.json');self.link_reports[name]=report
                extra_args=(*extra_args,'--vr-link-metrics',str(report))
            if self.udp_meter is not None:
                if config['address']!='127.0.0.1':raise ValueError('Only the owned loopback server can be measured')
                mode = 'periodic-loss' if self.args.udp_periodic_loss else 'measure'
                relay=udp.LoopbackGate(config['port'],None,mode=mode,traffic=self.udp_meter,peer=name).start()
                self.udp_relays[name]=relay
                config={**config,'port':relay.port}
        try:
            super().launch(name,config,visible,extra_args=extra_args)
        except BaseException:
            if relay is not None:relay.close()
            raise

    def stop(self,name):
        try:
            super().stop(name)
        finally:
            if name in self.udp_relays:self.udp_relays[name].close()

    def cleanup(self):
        clean=super().cleanup()
        if clean:
            sources = []
            for entry in self.rounds:
                name = entry['name']
                path = self.directory / (name + '-server.log')
                if path.is_file():
                    with path.open(encoding='utf-8-sig', errors='replace') as stream:
                        sources.append({'round': name, 'sessionId': entry['id'], **summarize_authority_log(stream)})
                else:
                    sources.append({'round': name, 'sessionId': entry['id'], 'missingLog': True})
            self.save('authority-diagnostics.json', {'sources': sources})
        if self.args.udp_traffic:
            relays={name:relay.report() for name,relay in self.udp_relays.items()}
            self.save('udp-relay-cleanup.json',relays)
            clean=clean and all(row['threadStopped'] and row['error'] is None and row['foreignDropped']==0 for row in relays.values())
        return clean

def check_frame_review(v, entry, frames):
    route = f'/api/sessions/{entry["id"]}/world'
    first = next((index for index, frame in enumerate(frames[:-1])
                  if any(event['kind'] == 'ShotFired' for event in frame['packet']['events'])), None)
    if first is None:
        raise RuntimeError('No accepted native shot frame to inspect')
    sequence = first + 1
    exact = v.request(f'{route}/frames/{sequence}')
    request = urllib.request.Request(v.base + f'{route}/watch?mode=replay&fromFrame={sequence}&rate=4',
                                     headers={'Authorization': 'Bearer ' + v.tokens['Master']})
    with urllib.request.urlopen(request, timeout=10) as response:
        stream = capacity.sse_frames(response)
        resumed = [next(stream), next(stream)]
    if exact != frames[first] or resumed != frames[first:first + 2]:
        raise RuntimeError('Native shot frame or exact resume differed from the accepted full replay')
    searches = []
    through = len(frames)
    stream_id = entry['sealed']['world']['header']['streamId']
    scopes = [(room, None) for room in entry['roomIds']]
    scopes.extend((None, player['id']) for player in entry['players'])
    for room, player_id in scopes:
        expected = []
        for frame in frames:
            players = ({player_id} if player_id else
                       {player['playerId'] for player in frame['statistics'] if player['roomId'] == room})
            packet = frame['packet']
            count = sum(event['kind'] == 'ShotFired' and event['playerId'] in players for event in packet['events'])
            if count:
                expected.append({'frameSequence': packet['sequence'], 'elapsedMilliseconds': packet['elapsedMilliseconds'],
                                 'matchCount': count})
        if not expected:
            raise RuntimeError('No saved shot event attributed to an original room or player')
        filters = f'playerId={player_id}' if player_id else f'roomId={room}'
        after, hits, pages = 0, [], []
        while after < through:
            page = v.request(f'{route}/event-frames?throughFrame={through}&afterFrame={after}&{filters}&kind=ShotFired')
            scanned = page['scannedThroughFrame']
            if (page['sessionId'] != entry['id'] or page['streamId'] != stream_id or page['throughFrame'] != through
                    or page['afterFrame'] != after or page['playerId'] != player_id or not after < scanned <= min(after + 128, through)
                    or page['nextAfterFrame'] != (scanned if scanned < through else None)
                    or page['frames'] != [hit for hit in expected if after < hit['frameSequence'] <= scanned]
                    or len(page['frames']) > 24):
                raise RuntimeError('Native event search did not match the scoped accepted replay or cursor')
            hits.extend(page['frames'])
            pages.append(page)
            after = scanned
        if hits != expected:
            raise RuntimeError('Native event search omitted or repeated saved shot frames')
        count = sum(hit['matchCount'] for hit in hits)
        if player_id and count != next(player['ammoUsed'] for player in entry['sealed']['statistics']['players']
                                       if player['playerId'] == player_id):
            raise RuntimeError('Player event search does not reconcile with final ammunition')
        searches.append({'roomId': room, 'playerId': player_id, 'matchingEvents': count, 'pages': pages})
    by_shot = {}
    shot_kinds = {'ShotFired', 'ShotHit', 'EnemyEliminated'}
    for frame in frames:
        packet = frame['packet']
        rooms = {player['playerId']: player['roomId'] for player in frame['statistics']}
        for event in packet['events']:
            if event['kind'] not in shot_kinds:
                continue
            by_shot.setdefault((event['playerId'], event['shotId']), []).append({
                'eventId': event['eventId'], 'kind': event['kind'], 'frameSequence': packet['sequence'],
                'elapsedMilliseconds': packet['elapsedMilliseconds'], 'roomId': rooms[event['playerId']]})
    traces = []
    for (player_id, shot_id), events in by_shot.items():
        anchor = events[-1]
        from_frame, event_id, room = anchor['frameSequence'], anchor['eventId'], anchor['roomId']
        trace = v.request(f'{route}/shot-trace?fromFrame={from_frame}&throughFrame={through}&eventId={event_id}&roomId={room}')
        if trace != {'sessionId': entry['id'], 'streamId': stream_id, 'fromFrame': from_frame, 'throughFrame': through,
                     'eventId': event_id, 'shotId': shot_id, 'playerId': player_id, 'roomId': room, 'events': events}:
            raise RuntimeError('Native shot trace differs from its original saved records')
        traces.append(trace)
    if {trace['playerId'] for trace in traces} != {player['id'] for player in entry['players']}:
        raise RuntimeError('No original saved shot trace for every admitted player')
    v.save(entry['name'] + '-frame-review.json', {'complete': True, 'sequence': sequence,
           'resumedSequences': [frame['packet']['sequence'] for frame in resumed], 'frame': exact,
           'searches': searches, 'shotTraces': traces})

def marksmanship_props():
    # Standard floor placement excludes the other candidates in the first enemy row.
    return [{'assetId': 'barrel', 'position': {'x': x, 'y': 0, 'z': -1}, 'yawDegrees': 0}
            for x in (-4.125, -2.25, -.75, .75, 2.25, 4.125)]


def marksmanship_targets(value, players):
    enemies = value['packet']['frame']['enemies']
    targets = {}
    for player in players:
        room = player['roomId']
        x = (room - 3) * 14 + (player['seat'] - 2) * 1.5
        candidates = [enemy for enemy in enemies if enemy['roomId'] == room and enemy['health'] == 100
                      and enemy['feet'] == {'x': x, 'y': 0, 'z': -1}]
        if len(candidates) != 1:
            raise ValueError('Each original seat must face exactly one native target')
        targets[player['id']] = candidates[0]['id']
    if len(targets) != len(enemies) or len(set(targets.values())) != len(enemies):
        raise ValueError('Unexpected or reused marksmanship target')
    return targets


def replenish_marksmanship(v, entry, value):
    waves = entry['marksmanshipWaves']
    if len(waves) >= v.args.seconds // 20:
        return
    targets = entry['marksmanshipTargets']
    if {enemy['id']: enemy['health'] for enemy in value['packet']['frame']['enemies']} != dict.fromkeys(targets.values(), 0):
        return
    statistics = {row['playerId']: row for row in value['statistics']}
    if set(statistics) != set(targets) or any(
            (row['ammoUsed'], row['shotsHit'], row['kills']) != (2 * len(waves), 2 * len(waves), len(waves))
            for row in statistics.values()):
        raise ValueError('Target replenishment needs the exact completed original weapon cycle')
    evidence = {'previousTargets': targets, 'commands': [], 'checkpoints': {'eliminated': value}}
    name = entry['name'] + '-wave-' + str(len(waves) + 1) + '.json'
    references = entry.setdefault('operatorReferences', {})
    references[value['packet']['sequence']] = value
    for count in (0, len(entry['players'])):
        identity = str(uuid.uuid4())
        expected = v.state(entry)['sequence']
        policy = {'count': count, 'behavior': 'Hold', 'autoAttack': False}
        receipt = v.command(entry, 'SetEnemies', commandId=identity, expectedSequence=expected, enemies=policy)
        sequence = receipt['appliedAtSequence']
        if (receipt['commandId'] != identity or receipt['duplicate'] is not False or receipt['session']['id'] != entry['id']
                or receipt['session']['enemies'] != policy or sequence <= expected):
            raise ValueError('Target replenishment receipt differs from the original command')
        evidence['commands'].append(receipt)
        v.save(name, evidence)

        def observed():
            sample = v.frame(entry, measure=True)
            packet = sample['packet']
            if (packet['observedSequence'] >= sequence and not packet['suspended']
                    and packet['frame']['phase'] == 'Running' and len(packet['frame']['enemies']) == count):
                return sample
        value = v.wait(observed, 12, entry['name'] + ' target replenishment')
        references[value['packet']['sequence']] = value
        evidence['checkpoints'][str(count)] = value
        v.save(name, evidence)
    next_targets = marksmanship_targets(value, entry['players'])
    previous_ids = {target for wave in waves for target in wave.values()}
    if set(next_targets.values()) & previous_ids:
        raise ValueError('A replenished enemy reused an earlier native target')
    validate_roster(v.state(entry), entry['players'])
    waves.append(next_targets)
    entry['marksmanshipTargets'] = next_targets
    evidence['nextTargets'] = next_targets
    v.save(name, evidence)
    v.save(entry['name'] + '-marksmanship-waves.json', waves)


def reconcile_marksmanship(frames, targets, incoming=None, *, waves=None):
    pattern = ['ShotFired', 'ShotHit', 'ReloadStarted', 'ReloadCompleted',
               'ShotFired', 'ShotHit', 'EnemyEliminated']
    target_waves = [targets] if waves is None else waves
    enemy_ids = [enemy for wave in target_waves for enemy in wave.values()]
    if (not target_waves or any(set(wave) != set(targets) for wave in target_waves)
            or len(set(enemy_ids)) != len(enemy_ids)):
        raise ValueError('Target waves must preserve original players and distinct native enemies')
    complete_pattern = pattern * len(target_waves)
    progress = {player: [] for player in targets}
    active_shots = {}
    event_ids, shot_ids = set(), set()
    last_event = combat_count = 0
    damage = {player: 0 for player in targets}
    hits_received = dict.fromkeys(targets, 0)
    pending = None
    for value in frames:
        packet = value['packet']
        frame = packet['frame']
        for event in packet['events']:
            player, kind = event['playerId'], event['kind']
            if event['sequence'] != last_event + 1 or event['eventId'] in event_ids:
                raise ValueError('Duplicate or out-of-order native weapon event')
            last_event = event['sequence']
            event_ids.add(event['eventId'])
            if incoming and kind in ('EnemyShot', 'PlayerDamaged'):
                enemy = event['enemyId']
                attack = (event['tick'], enemy, player)
                room = incoming['rooms'].get(player)
                if (room is None or incoming['attackers'].get(enemy) != room or frame['phase'] != 'Running'
                        or packet['suspended'] or not frame['autoAttack']
                        or not incoming['enabled'] <= packet['observedSequence'] < incoming['disabled']
                        or any(actions != complete_pattern for actions in progress.values())):
                    raise ValueError('Enemy attack left the original room or enabled window')
                if kind == 'EnemyShot' and pending is None and event['hasRay'] and event['hit'] == 'Friendly' and event['targetId'] == player:
                    pending = attack
                elif kind == 'PlayerDamaged' and pending == attack and event['damage'] == 20 and damage[player] + 20 < 100:
                    damage[player] += 20
                    hits_received[player] += 1
                    combat_count += 1
                    pending = None
                else:
                    raise ValueError('Enemy ray and nonlethal player damage do not form one accepted pair')
                continue
            actions = progress.get(player)
            if pending or actions is None or len(actions) == len(complete_pattern) or kind != pattern[len(actions) % len(pattern)]:
                raise ValueError('Unexpected native fire, hit, reload or elimination order')
            target = target_waves[len(actions) // len(pattern)][player]
            if kind == 'ShotFired':
                shot = event['shotId']
                if not shot or shot in shot_ids or not event['hasRay'] or event['hit'] != 'Enemy' or event['targetId'] != target:
                    raise ValueError('Native shot ray did not hit its original seat target')
                active_shots[player] = shot
                shot_ids.add(shot)
            elif kind in ('ShotHit', 'EnemyEliminated'):
                if event['shotId'] != active_shots[player] or event['enemyId'] != target:
                    raise ValueError('Native hit or elimination did not match its accepted ray')
            actions.append(kind)
            combat_count += int(kind not in ('ReloadStarted', 'ReloadCompleted'))
        if packet['throughCombatSequence'] != combat_count:
            raise ValueError('Weapon replay differs from the combat ledger boundary')
        for statistics in value['statistics']:
            player = statistics['playerId']
            actions = progress[player]
            shots, hits, kills = (actions.count(kind) for kind in ('ShotFired', 'ShotHit', 'EnemyEliminated'))
            if (statistics['ammoUsed'], statistics['shotsHit'], statistics['kills'], statistics['accuracyPercent']) != (
                    shots, hits, kills, (100 * hits / shots if shots else 0)):
                raise ValueError('Saved statistics do not match the weapon event prefix')
            if incoming and (statistics['roomId'], statistics['hitsReceived'], statistics['damageTaken'], statistics['health']) != (
                    incoming['rooms'][player], hits_received[player], damage[player], 100 - damage[player]):
                raise ValueError('Saved statistics do not match the incoming damage prefix')
        if incoming and packet['observedSequence'] >= incoming['enabled']:
            rows = {row['playerId']: row['health'] for row in value['statistics']}
            bodies = {body['id']: body['health'] for body in frame['players']}
            if (len(rows) != len(value['statistics']) or rows != {player: 100 - lost for player, lost in damage.items()}
                    or bodies != rows):
                raise ValueError('Saved bodies or ledger omit an original player or disagree on remaining health')
    if not progress or any(actions != complete_pattern for actions in progress.values()):
        raise ValueError('Each original player must hit twice, reload once and eliminate its target')
    final = frames[-1]
    expected_enemies = dict.fromkeys(incoming['attackers'], 100) if incoming else dict.fromkeys(target_waves[-1].values(), 0)
    if {enemy['id']: enemy['health'] for enemy in final['packet']['frame']['enemies']} != expected_enemies:
        raise ValueError('Sealed target roster or health differs')
    if {row['playerId'] for row in final['statistics']} != set(targets):
        raise ValueError('Sealed marksmanship statistics omit original players')
    proof = {'players': len(progress), 'shots': len(shot_ids), 'hits': 2 * len(progress) * len(target_waves),
             'eliminations': len(progress) * len(target_waves), 'combatEvents': combat_count}
    if waves is not None:
        proof['waves'] = len(target_waves)
    if incoming:
        if pending or not all(hits_received.values()):
            raise ValueError('Every original player must have a complete incoming damage witness')
        proof.update(hitsReceived=sum(hits_received.values()), damageTaken=sum(damage.values()))
    return proof


def exercise_incoming_fire(v, entry):
    rooms = {player['id']: player['roomId'] for player in entry['players']}
    targets = entry['marksmanshipTargets']
    evidence = {'commands': [], 'checkpoints': {}}
    references = entry.setdefault('operatorReferences', {})
    name = entry['name'] + '-incoming-fire.json'

    def environment(weather, night):
        identity = str(uuid.uuid4())
        expected = v.state(entry)['sequence']
        policy = {'mode': 'VR', 'weather': weather, 'timeOfDay': 'Night' if night else 'Day', 'lightning': weather == 'Storm'}
        receipt = v.command(entry, 'SetEnvironment', commandId=identity, expectedSequence=expected, environment=policy)
        sequence = receipt['appliedAtSequence']
        if (receipt['commandId'] != identity or receipt['duplicate'] is not False or receipt['session']['id'] != entry['id']
                or receipt['session']['environment'] != policy or sequence <= expected):
            raise ValueError('Incoming-fire environment receipt does not match the original command')
        evidence['commands'].append(receipt)
        v.save(name, evidence)
        return checkpoint(weather + ' environment', sequence, lambda value: value['packet']['weather'] == weather
                          and value['packet']['lightning'] == policy['lightning']
                          and value['packet']['frame']['night'] == night)

    def command(count, attack):
        identity = str(uuid.uuid4())
        expected = v.state(entry)['sequence']
        policy = {'count': count, 'behavior': 'Hold', 'autoAttack': attack}
        receipt = v.command(entry, 'SetEnemies', commandId=identity, expectedSequence=expected, enemies=policy)
        sequence = receipt['appliedAtSequence']
        if (receipt['commandId'] != identity or receipt['duplicate'] is not False or receipt['session']['id'] != entry['id']
                or receipt['session']['enemies'] != policy or sequence <= expected):
            raise ValueError('Incoming-fire policy receipt does not match the original command')
        evidence['commands'].append(receipt)
        v.save(name, evidence)
        return sequence

    def checkpoint(label, fence, accept):
        def observe():
            value = v.frame(entry, measure=True)
            packet = value['packet']
            if (packet['observedSequence'] >= fence and not packet['suspended']
                    and packet['frame']['phase'] == 'Running' and accept(value)):
                return value
        value = v.wait(observe, 12, entry['name'] + ' ' + label)
        references[value['packet']['sequence']] = value
        evidence['checkpoints'][label] = value
        v.save(name, evidence)
        return value

    checkpoint('original targets eliminated', entry['beginSequence'], lambda value:
               {enemy['id']: enemy['health'] for enemy in value['packet']['frame']['enemies']} == dict.fromkeys(targets.values(), 0))
    cleared = command(0, False)
    checkpoint('original enemies cleared', cleared, lambda value: not value['packet']['frame']['enemies'])
    if v.args.incoming_environment:
        environment('Storm', True)
    enabled = command(len(rooms), True)
    live = checkpoint('original players damaged', enabled, lambda value: value['packet']['frame']['autoAttack']
                      and {row['playerId'] for row in value['statistics'] if row['hitsReceived'] > 0} == rooms.keys())
    disabled = command(len(rooms), False)
    quiet = checkpoint('attack disabled', disabled, lambda value: not value['packet']['frame']['autoAttack'])
    if v.args.incoming_environment:
        environment('Fog', False)
    attackers = {enemy['id']: enemy['roomId'] for enemy in live['packet']['frame']['enemies']}
    if (attackers.keys() & set(targets.values()) or sorted(attackers.values()) != sorted(rooms.values())
            or attackers != {enemy['id']: enemy['roomId'] for enemy in quiet['packet']['frame']['enemies']}):
        raise ValueError('Incoming fire must originate from the new native enemies in the original rooms')
    validate_roster(v.state(entry), entry['players'])
    entry['incomingFire'] = {'rooms': rooms, 'attackers': attackers, 'enabled': enabled, 'disabled': disabled}
    evidence['window'] = entry['incomingFire']
    v.save(name, evidence)


def verify_marksmanship_bundle(v, entry, csv_report):
    route = f'/api/sessions/{entry["id"]}'
    def download(suffix, mime):
        request = urllib.request.Request(v.base + route + suffix, headers={'Authorization': 'Bearer ' + v.tokens['Master']})
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.headers.get_content_type() != mime or response.headers['Cache-Control'] != 'no-store':
                raise ValueError('Invalid linked marksmanship export response')
            return response.read()

    prefix = f'vr-command-report-v1-{entry["id"]}'
    expected = {prefix + '.csv': Path(csv_report['path']).read_bytes()}
    for room in entry['roomIds']:
        expected[f'{prefix}-room-{room:02}.csv'] = download(f'/rooms/{room}/report.csv', 'text/csv')
    raw = download('/reports.zip', 'application/zip')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.namelist() != list(expected) or archive.testzip() is not None or any(
                archive.read(name) != content for name, content in expected.items()):
            raise ValueError('Linked marksmanship ZIP does not contain the exact full and five scoped CSVs')
    (v.directory / 'linked-marksmanship-reports.zip').write_bytes(raw)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'files': len(expected)}


def check_policy_frames(v, entry, rows):
    expected = []
    previous = {}
    groups = {'phase': ('phase',), 'suspension': ('suspended',),
              'environment': ('weather', 'night', 'lightning'), 'enemies': ('behavior', 'autoAttack')}
    for row in rows:
        packet = row['packet']
        frame = packet['frame']
        policy = {name: frame[name] for name in ('phase', 'night', 'behavior', 'autoAttack')}
        policy.update(weather=packet['weather'], lightning=packet['lightning'], suspended=packet.get('suspended', False))
        changes = [name for name, fields in groups.items() if any(policy[field] != previous.get(field) for field in fields)]
        if changes:
            expected.append({'frameSequence': packet['sequence'], 'elapsedMilliseconds': packet['elapsedMilliseconds'],
                             'policy': policy, 'changes': changes if previous else ['initial']})
        previous = policy
    if not all(sum(group in hit['changes'] for hit in expected) >= 2 for group in ('environment', 'enemies')):
        raise ValueError('Operator policy changes are missing from the original native replay')
    through = rows[-1]['packet']['sequence']
    stream = entry['sealed']['world']['header']['streamId']
    def read_pages(change=None):
        found, pages, cursor = [], [], 0
        suffix = f'&change={change}' if change else ''
        while cursor < through:
            page = v.request(f'/api/sessions/{entry["id"]}/world/policy-frames?throughFrame={through}&afterFrame={cursor}{suffix}')
            end = page['scannedThroughFrame']
            if (page['sessionId'], page['streamId'], page['throughFrame'], page['afterFrame'], page['nextAfterFrame'], page.get('change')) != (
                    entry['id'], stream, through, cursor, end if end < through else None, change) or not cursor < end <= min(through, cursor + 1024):
                raise ValueError('Policy page left the original native recording or saved boundary')
            # Older management builds omitted the false suspension flag.
            for hit in page['frames']:
                hit['policy'].setdefault('suspended', False)
            found.extend(page['frames'])
            pages.append(page)
            cursor = end
        return found, pages

    found, pages = read_pages()
    environment, environment_pages = read_pages('environment')
    if found != expected or environment != [row for row in expected if 'environment' in row['changes']]:
        raise ValueError('Policy timeline differs from the original complete native replay')
    neighbors = []
    for first, second in zip(environment, environment[1:]):
        for direction, anchor, target in (('next', first, second), ('previous', second, first)):
            start = anchor['frameSequence']
            item = v.request(f'/api/sessions/{entry["id"]}/world/policy-neighbor?throughFrame={through}&change=environment'
                             f'&fromFrame={start}&direction={direction}')
            if item['frame'] is not None:
                item['frame']['policy'].setdefault('suspended', False)
            if (item['sessionId'], item['streamId'], item['throughFrame'], item['fromFrame'], item['direction'], item['change'],
                    item['scannedToFrame'], item['nextFromFrame'], item['frame']) != (
                    entry['id'], stream, through, start, direction, 'environment', target['frameSequence'], None, target):
                raise ValueError('Policy neighbor differs from the original native environment transition')
            neighbors.append(item)
    live_lookups = []
    for witness in entry.get('operatorControls', []):
        item = witness['liveEnvironmentLookup']
        before, tail = (witness[key]['packet']['sequence'] for key in ('before', 'applied'))
        target = next(row for row in reversed(environment) if row['frameSequence'] <= tail)
        if (item['sessionId'], item['streamId'], item['throughFrame'], item['fromFrame'], item['direction'], item.get('includeFrom'),
                item['change'], item['scannedToFrame'], item['nextFromFrame'], item['frame']) != (
                entry['id'], stream, tail, tail, 'previous', True, 'environment', target['frameSequence'], None, target) or not (
                before < target['frameSequence'] <= tail < through and target['policy']['weather'] == witness['environment']['weather']):
            raise ValueError('Live environment lookup differs from the first saved frame of the original applied change')
        live_lookups.append(item)
    v.save(entry['name']+'-policy-frames.json', {'complete': True, 'pages': pages, 'matchedFrames': len(found),
                                               'environmentPages': environment_pages, 'matchedEnvironmentFrames': len(environment),
                                               'environmentNeighbors': neighbors, 'liveEnvironmentLookups': live_lookups})


def replay(v,entry,pause):
    request=urllib.request.Request(v.base+f'/api/sessions/{entry["id"]}/world/watch?mode=replay&fromMs=0&rate=4',headers={'Authorization':'Bearer '+v.tokens['Master']})
    rows=[];faults=[];previous=0;last=None;ranges={p['id']:{'min':None,'max':None,'reload':False,'cycles':{}} for p in entry['players']};last_running=None;running=0
    references=entry.get('operatorReferences',{});matched=set()
    deadline=time.monotonic()+entry['sealed']['world']['durationMilliseconds']/4000+30
    with urllib.request.urlopen(request,timeout=10) as response:
        for value in capacity.sse_frames(response):
            if time.monotonic()>deadline:raise RuntimeError('Bounded full replay expired')
            number=value['packet']['sequence']
            if number!=previous+1:raise RuntimeError('Replay skipped or repeated an accepted frame')
            previous=number;last=value;rows.append(value);match_control_reference(value,references,matched)
            if value['packet']['frame']['phase'] not in ('Running','Paused'):continue
            try:frame=validate_frame(value,entry['players'],pause,entry.get('beginSequence',1),
                                     damage_since=entry.get('incomingFire',{}).get('enabled'))
            except ValueError as error:faults.append({'sequence':number,'reason':str(error)});continue
            if frame['phase']=='Running':
                elapsed=value['packet']['elapsedMilliseconds']
                if last_running is not None and elapsed-last_running>=1500:faults.append({'sequence':number,'reason':'Running source capture gap >=1500ms'})
                last_running=elapsed;running+=1
                for p in frame['players']:
                    span=ranges[p['id']];z=p['head']['z'];span['min']=z if span['min'] is None else min(span['min'],z);span['max']=z if span['max'] is None else max(span['max'],z);span['reload']|=p['reloading']
                    if entry.get('endurance'):
                        report=entry['inputReports'][p['id']];relative=frame['tick']-report['firstTick'];cycle=relative//400
                        if 0<=relative and cycle<entry['expectedCycles'] and frame['tick']<=report['lastTick']:
                            sample=span['cycles'].setdefault(cycle,{'min':z,'max':z,'reload':False,'ammoMax':0,'frames':0,'walkingFrames':0})
                            sample['min']=min(sample['min'],z);sample['max']=max(sample['max'],z);sample['reload']|=p['reloading'];sample['frames']+=1;sample['walkingFrames']+=int(p['walking'])
                            sample['ammoMax']=max(sample['ammoMax'],next(s['ammoUsed'] for s in value['statistics'] if s['playerId']==p['id']))
            else:last_running=None
    if last is None or previous!=entry['sealed']['world']['acceptedSequence'] or last['packet']['frame']['phase']!='Ended':raise RuntimeError('Replay did not reach exact final world seal')
    if matched!=set(references):raise RuntimeError('Replay did not retain every original operator checkpoint')
    for identity,span in ranges.items():
        if not all(span[k] is not None and math.isfinite(span[k]) for k in ['min','max']) or span['max']-span['min']<.1 or not span['reload']:faults.append({'playerId':identity,'reason':'No accepted movement/reload witness'})
        if entry.get('endurance'):
            try:validate_endurance_cycles(span['cycles'],entry['expectedCycles'])
            except ValueError as error:faults.append({'playerId':identity,'reason':str(error)})
    result={'complete':not faults,'frames':previous,'runningFrames':running,'faults':faults,'ranges':ranges,'operatorReferences':len(matched),'scope':'Full accepted native replay, generated input only; original continuity policies retained'}
    v.save(entry['name']+'-full-replay.json',rows);v.save(entry['name']+'-replay-checks.json',result)
    if entry.get('marksmanshipTargets') and result['complete']:
        waves = entry.get('marksmanshipWaves')
        if waves is not None and len(waves) != entry['expectedCycles']:
            raise ValueError('The original task did not produce every required target wave')
        proof=reconcile_marksmanship(rows,entry['marksmanshipTargets'],entry.get('incomingFire'),waves=waves)
        if proof['combatEvents']!=v.state(entry)['combatStream']['acceptedSequence'] or last['statistics']!=entry['sealed']['statistics']['players']:
            raise ValueError('Marksmanship replay differs from the final sealed ledger')
        v.save(entry['name']+'-marksmanship-replay.json',proof)
    if v.args.check_frame_review and result['complete']:
        check_frame_review(v, entry, rows)
    if v.args.check_policy_frames and result['complete']:
        check_policy_frames(v, entry, rows)
    return result

def run(v):
    v.start();modes=[]
    def check(value,label):
        if not value:raise ValueError(label)
        v.evidence.append(label);v.stage('checking',check=label)
    for mode in (['linked','independent'] if v.args.mode=='both' else [v.args.mode]):
        entries=[];native=[];pause=None
        if v.args.udp_traffic:
            v.udp_meter = udp.UdpTrafficMeter(periodic_loss=v.args.udp_periodic_loss)
        for rooms in ([list(range(1,6))] if mode=='linked' else [[r] for r in range(1,6)]):
            definition={'name':'Generated native input '+mode,'briefing':'Automated Simulation exercise; no physical operators or headsets','durationSeconds':1800 if v.args.endurance else 600,'environment':{'mode':'VR','weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':len(rooms) if v.args.operator_controls else 0,'behavior':'Hold','autoAttack':False},'props':[]}
            if v.args.marksmanship:
                definition['enemies']['count']=5*len(rooms)
                definition['props']=marksmanship_props()
            mission=v.request('/api/missions',definition,expected=201);entry=v.create(mission,rooms,mode+'-'+str(rooms[0]))
            for room in rooms:
                for seat in range(1,v.args.players_per_room):
                    identity=str(uuid.uuid4());state=v.request(f'/api/sessions/{entry["id"]}/players',{'playerId':identity,'name':'Generated '+str(room)+'-'+str(seat),'roomId':room,'headset':'Quest3'},role='Room'+str(room));entry['players'].append(next(p for p in state['players'] if p['id']==identity))
            entries.append(entry)
        for e in entries:v.wait(lambda e=e:v.request(f'/api/sessions/{e["id"]}/world',optional=True),90,'new exercise world')
        for e,p in [(e,p) for e in entries for p in sorted(e['players'],key=lambda p:(p['seat'],p['roomId']))]:
            capacity.require_memory(capacity.memory_status());name=e['name']+'-client-'+p['admissionId'];v.launch(name,v.client_config(e,v.ticket(e,p)))
            native.append({'name':name,'sessionId':e['id'],'playerId':p['id'],'admissionId':p['admissionId'],'roomId':p['roomId'],'seat':p['seat'],'pid':v.processes[name].pid})
        for e in entries:
            admitted=v.wait(lambda e=e:v.connected(e),100,'all exercise admissions')
            capacity.validate_frame(admitted,e['players'])
            if v.args.marksmanship:
                e['marksmanshipTargets']=marksmanship_targets(admitted,e['players'])
                v.save(e['name']+'-marksmanship-layout.json',{'targets':e['marksmanshipTargets'],'source':admitted})
                if v.args.endurance:
                    e['marksmanshipWaves'] = [e['marksmanshipTargets']]
                    v.save(e['name'] + '-marksmanship-waves.json', e['marksmanshipWaves'])
        for row in native:
            ids=set(re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',debrief.log_text(v,row['name'])))
            if len(ids)!=1:raise RuntimeError('Client connection not uniquely witnessed')
            row['nativeConnectionId']=int(ids.pop())
        for e in entries:
            owners=[r for r in native if r['sessionId']==e['id']]
            if len({r['nativeConnectionId'] for r in owners})!=len(owners):raise RuntimeError('Native connection IDs are not unique within this server')
        if len({r['pid'] for r in native})!=len(native):raise RuntimeError('Native players did not retain distinct original processes')
        v.save(mode+'-native-clients.json',native);check(len(native)==5*v.args.players_per_room,mode+': original native clients admitted before generated input')
        if v.args.udp_periodic_loss:
            v.udp_meter.start_loss()
        for e in entries:
            validate_roster(v.state(e),e['players']);receipt=v.command(e,'Begin')
            if receipt['duplicate'] is not False or receipt['session']['id']!=e['id']:raise RuntimeError('Begin receipt belongs to another intent/session')
            e['beginSequence']=receipt['appliedAtSequence'];v.receipts.append(receipt)
        v.save(mode+'-begin-receipts.json',v.receipts);v.stage('running',mode=mode,automatedClients=len(native),seconds=v.args.seconds)
        started=time.monotonic();deadline=started+v.args.seconds;pause_at=started+2;resume_at=None;live=[];next_progress=started+30
        traffic_boundaries=[]
        while time.monotonic()<deadline:
            if mode=='independent' and pause is None and time.monotonic()>=pause_at:
                others={e['id']:v.frame(e)['packet']['frame']['tick'] for e in entries[1:]}
                receipt=v.command(entries[0],'Pause');pause={'accepted':receipt['appliedAtSequence'],'resumed':None,'receipt':receipt,'otherStartTicks':others};v.pauses[entries[0]['id']]=pause;v.save(mode+'-pause.json',pause)
                def paused_source():
                    value=v.frame(entries[0],measure=True)
                    return value if value['packet']['frame']['phase']=='Paused' and value['packet']['observedSequence']>=pause['accepted'] else None
                witness=v.wait(paused_source,15,'original room Pause applied');validate_frame(witness,entries[0]['players'],pause)
                pause['pausedTick']=witness['packet']['frame']['tick'];pause['pausedSourceSequence']=witness['packet']['sequence'];resume_at=time.monotonic()+2;v.save(mode+'-pause.json',pause)
            if resume_at is not None and time.monotonic()>=resume_at:
                still=v.frame(entries[0],measure=True);validate_frame(still,entries[0]['players'],pause)
                if still['packet']['frame']['phase']!='Paused' or still['packet']['frame']['tick']!=pause['pausedTick']:raise RuntimeError('Paused room tick advanced unexpectedly')
                pause['otherEndTicks']={e['id']:v.frame(e)['packet']['frame']['tick'] for e in entries[1:]}
                if any(pause['otherEndTicks'][sid]<=tick for sid,tick in pause['otherStartTicks'].items()):raise RuntimeError('Other rooms did not continue while one room paused')
                receipt=v.command(entries[0],'Resume');pause['resumed']=receipt['appliedAtSequence'];pause['resumeReceipt']=receipt;resume_at=None;v.save(mode+'-pause.json',pause)
            traffic_worlds=[]
            for e in entries:
                value=v.frame(e,measure=True)
                if value['packet']['frame']['phase']=='Preparing':continue
                try:validate_frame(value,e['players'],pause if e is entries[0] else None,e['beginSequence'])
                except ValueError:
                    v.save('exercise-live-failure.json', {'round': e['id'], 'value': value,
                           'previousObservations': [row for row in live[-32:] if row['sessionId'] == e['id']],
                           'trafficAtFailure': v.udp_meter.snapshot() if v.udp_meter is not None else None})
                    raise
                if v.args.endurance and v.args.marksmanship:
                    replenish_marksmanship(v, e, value)
                observation={'sessionId':e['id'],'sequence':value['packet']['sequence'],'tick':value['packet']['frame']['tick'],'phase':value['packet']['frame']['phase']}
                live.append(observation)
                if v.udp_meter is not None and observation['phase']=='Running' and not value['packet']['suspended']:
                    fence=e['beginSequence']
                    if mode=='independent' and e is entries[0]:
                        fence=pause['resumed'] if pause else None
                    if fence is not None and value['packet']['observedSequence']>=fence:
                        traffic_worlds.append({**observation,'observedSequence':value['packet']['observedSequence'],'fence':fence})
            if v.udp_meter is not None:
                if traffic_boundaries and len(traffic_worlds)!=len(entries):
                    raise RuntimeError('Traffic measurement lost the common Running window')
                if len(traffic_worlds)==len(entries) and (not traffic_boundaries or
                        time.perf_counter_ns()-traffic_boundaries[-1]['monotonicNs']>=1_000_000_000):
                    if any(not v.udp_relays[row['name']].thread.is_alive() for row in native):
                        raise RuntimeError('An original UDP relay stopped before the traffic boundary')
                    traffic_boundaries.append({**v.udp_meter.snapshot(),'worlds':traffic_worlds})
            if time.monotonic()>=next_progress:
                v.stage('running',mode=mode,elapsedSeconds=round(time.monotonic()-started,2),requestedSeconds=v.args.seconds,lastSources=live[-len(entries):]);next_progress=time.monotonic()+30
            time.sleep(.05)
        v.save(mode+'-live.json',live)
        if v.udp_meter is not None:
            v.save(mode+'-udp-boundaries.json',traffic_boundaries)
            traffic=udp.summarize_traffic(traffic_boundaries,native)
            traffic['linkProbesEnabled']=v.args.link_metrics
            v.save(mode+'-udp-traffic.json',traffic)
            check(traffic['seconds']>=20,mode+': every original player forwarded bidirectional UDP payloads in a common Running window')
        if v.args.link_metrics:
            v.wait(lambda:all(v.link_reports[row['name']].is_file() for row in native),8,'bounded native link reports')
            links=[summarize_link_report(vm.read_json(v.link_reports[row['name']]),row) for row in native]
            v.save(mode+'-link-metrics.json',{'clients':links,'sameHost':True,'rendered':False,
                   'roundTrip':'Optional NGO unreliable echo, local monotonic clock, includes game and network scheduling'})
            check(len(links)==len(native),mode+': all original clients provide 30 link attempts and player loop windows')
        if v.args.operator_controls:
            for e in entries:
                v.wait(lambda e=e:all(p['ammoUsed']==2 for p in v.request(f'/api/sessions/{e["id"]}/statistics')['players']),10,'all original generated shots accepted before operator controls')
                for weather,night,behavior in [('Storm',True,'Patrol'),('Fog',False,'Advance')]:
                    operator_phase(v,e,{'mode':'VR','weather':weather,'timeOfDay':'Night' if night else 'Day','lightning':weather=='Storm'},behavior)
                    check(True,e['name']+': '+behavior+' and '+weather+' applied while every original client walked; original enemies retained and moved')
        for row in native:(v.exercise[row['name']]/'finish.request').write_text('',encoding='utf-8')
        v.wait(lambda:all((v.exercise[r['name']]/'report.json').exists() for r in native),15,'explicit exercise finish')
        reports=[]
        cycles=v.args.seconds//20 if v.args.endurance else 1;fires=cycles*2
        for row in native:
            report=vm.read_json(v.exercise[row['name']]/'report.json');validate_report(report,row,fires,cycles,max(0,v.args.seconds*20-100) if v.args.endurance else 0,v.args.endurance);reports.append(report)
        for e in entries:
            e['endurance']=v.args.endurance;e['expectedCycles']=cycles;e['inputReports']={r['playerId']:r for r in reports if r['room'] in e['roomIds']}
        v.save(mode+'-exercise-reports.json',reports);check(True,mode+': every original client submitted its exact generated fire/reload schedule and explicitly finished')
        if v.args.incoming_fire:
            for e in entries:
                exercise_incoming_fire(v,e)
                check(True,e['name']+': original players took damage after their own weapons exercise and before the observed cease-fire')
        for e in entries:
            validate_roster(v.state(e),e['players']);sealed=v.seal(e);players=sealed['statistics']['players']
            hits,kills,accuracy=(fires,cycles,100) if v.args.marksmanship else (0,0,0)
            check(all(p['ammoUsed']==fires and p['shotsHit']==hits and p['kills']==kills and p['accuracyPercent']==accuracy
                      and (0<p['health']<100 and p['damageTaken']==100-p['health']==20*p['hitsReceived'] if v.args.incoming_fire
                           else p['health']==100 and p['damageTaken']==0 and p['hitsReceived']==0) for p in players),
                  e['name']+': accepted statistics reflect the exact generated shots, hits and eliminations')
            csv=capacity.practice.save_report(v,e,sealed['statistics'],filename=e['name']+'-report.csv');delivery=v.wait_for_player_results(e);owners=[r for r in native if r['sessionId']==e['id']];results=[]
            if v.args.marksmanship and mode=='linked':
                v.save('linked-marksmanship-bundle.json',verify_marksmanship_bundle(v,e,csv))
                check(True,'Linked marksmanship ZIP matches the full and five scoped CSVs')
            if delivery['allAcknowledged'] is not True or delivery['timedOut'] or set(delivery['phases'])!={r['name'] for r in owners}:raise RuntimeError('Original player results not all acknowledged')
            for row in owners:
                result=debrief.final_result(v,row['name']);player=next(p for p in e['players'] if p['id']==row['playerId']);debrief.validate_result(result,e,player,sealed)
                if result['finalStreamSequence']!=v.state(e)['combatStream']['acceptedSequence']:raise RuntimeError('Wrong final combat boundary')
                results.append(result)
            acknowledgments=[int(x) for x in re.findall(r'VR_SERVER_DEBRIEF_ACK id=(\d+)',debrief.log_text(v,e['name']+'-server'))]
            if len(acknowledgments)!=len(owners) or set(acknowledgments)!={r['nativeConnectionId'] for r in owners} or 'VR_SERVER_DEBRIEF_TIMEOUT ' in debrief.log_text(v,e['name']+'-server'):raise RuntimeError('Server ACK differs from original native connections')
            if any(debrief.log_text(v,r['name']).count('VR_CLIENT_CONNECTED id=')!=1 for r in owners):raise RuntimeError('A client changed connection before its final result')
            v.save(e['name']+'-results.json',{'delivery':delivery,'results':results,'serverAcknowledgments':acknowledgments,'csv':csv})
            if v.args.udp_periodic_loss and e is entries[-1]:
                loss = udp.summarize_periodic_loss(traffic_boundaries, v.udp_meter.snapshot(), native)
                v.save(mode+'-udp-periodic-loss.json', loss)
                check(True, mode+': every original connection experienced verified bidirectional periodic loss and delivered its original result')
            if v.args.pose_continuity:
                v.finish_continuity()
                check(True, 'linked: original native processes completed sparse pose diagnostics')
            v.stop_round(e)
            if not v.args.endurance:
                playback=replay(v,e,pause if e is entries[0] else None);check(playback['complete'],e['name']+': all replay frames retain original bodies, movement/reload, seals and results')
                if v.args.incoming_fire:
                    check(True,e['name']+': full replay reconciles original player shots and same-room enemy damage with each saved statistics prefix')
                if v.args.check_frame_review:
                    check(True, e['name'] + ': exact shot frame, resumed frames, room/player search and shot traces match the native archive')
                if v.args.check_policy_frames:
                    check(True, e['name'] + ': phase, environment and enemy changes match the complete original native replay')
        if v.args.endurance:
            # All native sources are stopped first. Each independent reader still
            # consumes every frame at the original rate4 and its original deadline.
            with concurrent.futures.ThreadPoolExecutor(max_workers=v.args.replay_workers) as pool:
                pending={pool.submit(replay,v,e,pause if e is entries[0] else None):e for e in entries}
                for future in concurrent.futures.as_completed(pending):
                    e=pending[future];playback=future.result();check(playback['complete'],e['name']+': complete endurance replay retains every original body and every movement/reload/two-shot cycle')
                    if v.args.incoming_fire:
                        check(True,e['name']+': complete endurance replay reconciles every target wave and original incoming damage')
                    if v.args.check_policy_frames:
                        check(True,e['name']+': recorded policy pages match the full endurance replay')
        findings=capacity.native_log_findings(v.directory);check(not findings,mode+': no native send queue errors')
        modes.append({'mode':mode,'clients':len(native),'automatedInputs':True,'operatorControls':v.args.operator_controls,'endurance':v.args.endurance,'marksmanship':v.args.marksmanship,'linkMetrics':v.args.link_metrics,'udpTraffic':v.args.udp_traffic,'udpPeriodicLoss':v.args.udp_periodic_loss,'requestedSeconds':v.args.seconds,'maximumReplayWorkers':v.args.replay_workers,'replayRate':4,'physicalOperators':0,'networkCapacityAccepted':False,'incomingEnvironment':v.args.incoming_environment})
        if v.args.incoming_fire:
            modes[-1]['incomingFire'] = True
    v.summary();v.save('exercise-result.json',{'complete':False,'modes':modes,'headsets':0,'hosts':1,'renderedClients':0,'posesWrittenDirectly':False,'newTestRpc':False,'automatedInput':True,'physicalOperators':0,'networkCapacityAccepted':False,'scope':'Actual Windows native clients using generated desktop movement/weapon intents through original RPCs; not humans, XR, LAN or capacity acceptance'})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--mode',choices=('linked','independent','both'),default='both');p.add_argument('--players-per-room',type=int,choices=(1,5),default=5);p.add_argument('--seconds',type=int,default=16)
    p.add_argument('--endurance',action='store_true',help='Explicit separate bounded native profile: --seconds 60 (smoke) or 900 (long); never combined with operator-controls')
    p.add_argument('--pose-continuity', action='store_true', help='Collect existing sparse pose diagnostics from the original Linked endurance processes')
    p.add_argument('--replay-workers',type=int,choices=(1,5),default=1,help='Endurance only: independent closed-source replay readers; every stream retains rate4 and all original gates')
    p.add_argument('--operator-controls',action='store_true',help='After the base motion window, apply Storm Night Patrol then Fog Day Advance through normal management commands; no console UI or physical operator input')
    p.add_argument('--check-frame-review', action='store_true', help='Verify an exact native shot frame and resume during the short exercise')
    p.add_argument('--check-policy-frames', action='store_true', help='Compare recorded policy pages with the full native exercise replay')
    p.add_argument('--marksmanship', action='store_true', help='Verify two hits and one elimination per seat and cycle; endurance replenishes targets through normal management commands')
    p.add_argument('--incoming-fire', action='store_true', help='After marksmanship, use normal AI commands to exercise damage on every original player before final results')
    p.add_argument('--incoming-environment', action='store_true', help='With incoming-fire, apply Storm Night before attack and Fog Day after the observed cease-fire')
    p.add_argument('--link-metrics', action='store_true', help='Collect 30 opt-in native link measurements per client during the 40-second short exercise')
    p.add_argument('--udp-traffic', action='store_true', help='Measure forwarded UDP payload bytes per original client in the 40-second short exercise')
    p.add_argument('--udp-periodic-loss', action='store_true', help='Measure and drop every twentieth datagram per player and direction after admission in the 40-second short exercise')
    p.add_argument('--api-dll',type=Path,default=Path(os.environ.get('VR_COMMAND_API_DLL',ROOT/'src/VrCommand.Api/bin/Release/net10.0/VrCommand.Api.dll')));p.add_argument('--player-exe',type=Path,default=ROOT/'artifacts/desktop/VrCommand.exe');args=p.parse_args();args.duration=600;args.visible_room=0;args.job_workers=2;args.check=False
    if args.endurance and (args.seconds not in (60,900) or args.operator_controls) or not args.endurance and args.seconds not in range(12,41):p.error('Short seconds must be 12..40; endurance requires 60 or 900 and no operator-controls')
    if args.replay_workers!=1 and not args.endurance:p.error('Parallel replay readers require the explicit endurance profile')
    if args.pose_continuity and (not args.endurance or args.mode != 'linked'):p.error('Pose continuity requires the Linked endurance profile')
    if args.check_frame_review and args.endurance:p.error('Frame review uses the short exercise')
    if args.check_policy_frames and not (args.operator_controls or args.incoming_environment):p.error('Policy frame review requires operator-controls or incoming-environment')
    if args.marksmanship and (args.operator_controls or args.players_per_room!=5):p.error('Marksmanship requires five players per room without operator policy changes')
    if args.incoming_environment and not args.incoming_fire:p.error('Incoming environment requires incoming-fire')
    if args.incoming_fire and (not args.marksmanship or args.link_metrics or args.udp_traffic or args.udp_periodic_loss):p.error('Incoming fire requires marksmanship without UDP or link measurement')
    if args.link_metrics and (args.endurance or args.seconds!=40):p.error('Link measurement requires the 40-second short exercise')
    if args.udp_periodic_loss:
        args.udp_traffic = True
    if args.udp_traffic and (args.endurance or args.seconds!=40):p.error('UDP traffic measurement requires the 40-second short exercise')
    vm.verify_player(args);v=ExerciseVenue(args)
    try:run(v)
    except BaseException as error:
        v.stage('failed',errorType=type(error).__name__);forensics=[]
        v.save('partial-checks.json',{'complete':False,'checks':v.evidence,'scope':'Only completed assertions before the original failure; never whole-run acceptance'})
        for directory in v.exercise.values():
            if directory.is_dir() and not (directory/'report.json').exists():(directory/'finish.request').write_text('',encoding='utf-8')
        for entry in v.rounds:
            if (v.directory/(entry['name']+'-full-replay.json')).exists():continue
            try:
                if v.request(f'/api/sessions/{entry["id"]}/world',optional=True):
                    v.seal(entry)
                    if args.pose_continuity and not (v.directory/'multiplayer-continuity.json').exists():
                        try:
                            if not v.wait_for_player_results(entry)['allAcknowledged']:
                                raise RuntimeError('Original failure case did not deliver all results before diagnostics stopped')
                            v.finish_continuity()
                            v.save('failure-pose-continuity.json', {'complete': True})
                        except Exception as issue:
                            v.save('failure-pose-continuity.json', {'complete': False, 'errorType': type(issue).__name__})
                    result=replay(v,entry,v.pauses.get(entry['id']));forensics.append({'sessionId':entry['id'],'replayRead':True,'replayContinuityPassed':result['complete'],'acceptancePassed':False})
            except Exception as issue:forensics.append({'sessionId':entry['id'],'replayRead':False,'errorType':type(issue).__name__})
        v.save('failure-forensics.json',{'originalErrorType':type(error).__name__,'rounds':forensics,'acceptancePassed':False});raise
    finally:
        failed=sys.exc_info()[0] is not None;clean=v.cleanup()
        if not clean and not failed:raise RuntimeError('Exercise cleanup incomplete')
        if clean and not failed:
            result=vm.read_json(v.directory/'exercise-result.json');result['complete']=True;v.save('exercise-result.json',result);v.stage('passed',checks=len(v.evidence))
if __name__=='__main__':main()
