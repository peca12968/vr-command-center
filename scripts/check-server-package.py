"""Exercise portable Windows packages, five rooms, Linked and owned process cleanup."""
import argparse,base64,csv,ctypes,hashlib,importlib.util,io,ipaddress,json,os,re,shutil,socket,sqlite3,subprocess,sys,tempfile,threading,time,urllib.error,urllib.request,uuid,zipfile
from contextlib import closing, contextmanager
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
package=module('server_package','package-windows-server.py');control=module('server_control_checks','check-control-package.py');venue=module('server_venue','start-desktop-venue.py');world=module('server_world','analyze-world-journal.py');debrief=module('server_debrief','check-desktop-debrief.py')
field=module('server_field_results','verify-field-results.py')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def free(kind=socket.SOCK_STREAM,address='127.0.0.1'):
    with socket.socket(socket.AF_INET,kind) as s:s.bind((address,0));return s.getsockname()[1]

def venue_browser_port():
    # Windows may assign a low port that Chromium blocks (for example 1719).
    for _ in range(64):
        port=49152+uuid.uuid4().int%16384
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as probe:
            try:probe.bind(('127.0.0.1',port))
            except OSError:continue
            return port
    raise RuntimeError('No free high loopback port for the venue browser fixture')

@contextmanager
def hold_owned_unity_threads(witness, pid):
    """Pause only the exact fixture-owned process, then undo each suspension."""
    from ctypes import wintypes
    kernel=witness.kernel
    class ThreadEntry(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('id',wintypes.DWORD),('owner',wintypes.DWORD),
                  ('base',wintypes.LONG),('delta',wintypes.LONG),('flags',wintypes.DWORD)]
    definitions={
        'GetProcessId':([wintypes.HANDLE],wintypes.DWORD),
        'CreateToolhelp32Snapshot':([wintypes.DWORD,wintypes.DWORD],wintypes.HANDLE),
        'Thread32First':([wintypes.HANDLE,ctypes.POINTER(ThreadEntry)],wintypes.BOOL),
        'Thread32Next':([wintypes.HANDLE,ctypes.POINTER(ThreadEntry)],wintypes.BOOL),
        'OpenThread':([wintypes.DWORD,wintypes.BOOL,wintypes.DWORD],wintypes.HANDLE),
        'GetProcessIdOfThread':([wintypes.HANDLE],wintypes.DWORD),
        'SuspendThread':([wintypes.HANDLE],wintypes.DWORD),
        'ResumeThread':([wintypes.HANDLE],wintypes.DWORD),
    }
    for name,(arguments,result) in definitions.items():
        function=getattr(kernel,name);function.argtypes=arguments;function.restype=result
    if kernel.GetProcessId(witness.handle)!=pid or kernel.WaitForSingleObject(witness.handle,0)!=258:
        raise RuntimeError('The original Unity process is not live')

    def thread_ids():
        snapshot=kernel.CreateToolhelp32Snapshot(4,0)
        if snapshot in (None,ctypes.c_void_p(-1).value):raise ctypes.WinError(ctypes.get_last_error())
        try:
            result=set()
            row=ThreadEntry();row.size=ctypes.sizeof(row)
            ok=kernel.Thread32First(snapshot,ctypes.byref(row))
            while ok:
                if row.owner==pid:result.add(row.id)
                row.size=ctypes.sizeof(row)
                ok=kernel.Thread32Next(snapshot,ctypes.byref(row))
            if ctypes.get_last_error()!=18:raise ctypes.WinError(ctypes.get_last_error())
            return result
        finally:
            kernel.CloseHandle(snapshot)

    held={}
    try:
        for _ in range(4):
            new=thread_ids()-held.keys()
            if not new:break
            for tid in new:
                thread=kernel.OpenThread(0x0802,False,tid)
                if not thread:
                    if ctypes.get_last_error()==87:continue
                    raise ctypes.WinError(ctypes.get_last_error())
                if kernel.GetProcessIdOfThread(thread)!=pid or kernel.WaitForSingleObject(witness.handle,0)!=258:
                    kernel.CloseHandle(thread)
                    raise RuntimeError('Thread no longer belongs to the original Unity process')
                if kernel.SuspendThread(thread)==0xffffffff:
                    kernel.CloseHandle(thread)
                    raise RuntimeError('Could not hold an original Unity thread')
                held[tid]=thread
        if not held or thread_ids()-held.keys():raise RuntimeError('Unity thread set did not stabilize')
        yield len(held)
    finally:
        failed=False
        for thread in reversed(tuple(held.values())):
            if kernel.ResumeThread(thread)==0xffffffff:failed=True
            kernel.CloseHandle(thread)
        if failed:raise RuntimeError('Could not restore the original Unity threads')

def replace_fixture_file(path, value):
    pending = path.with_suffix('.new')
    with pending.open('x', encoding='ascii') as output:
        output.write(value)
    deadline = time.monotonic() + 1
    while True:
        try:
            os.replace(pending, path)
            return
        except PermissionError as error:
            # The runtime can be opening the current command at the same instant.
            if error.winerror not in (5, 32) or time.monotonic() >= deadline:
                raise
            time.sleep(.02)

def reconcile_ai_damage(frames, owners, enabled_sequence, disabled_sequence):
    totals={player:{'roomId':room,'hitsReceived':0,'damageTaken':0} for player,room in owners.items()}
    events=set(); pending=None; last_sequence=0; damage_events=0
    for value in frames:
        packet=value['packet'];frame=packet['frame']
        enemies={enemy['id']:enemy['roomId'] for enemy in frame['enemies']}
        for event in packet['events']:
            victim=event['playerId']
            if event['sequence']!=last_sequence+1 or event['eventId'] in events or owners.get(victim) is None \
                or enemies.get(event['enemyId'])!=owners[victim] or frame['phase']!='Running' or packet['suspended'] \
                or not enabled_sequence<=packet['observedSequence']<disabled_sequence or not frame['autoAttack']:
                raise ValueError('Combat replay event violates its original room, order or enabled window')
            events.add(event['eventId']);last_sequence=event['sequence']
            attack=(event['tick'],event['enemyId'],victim)
            if event['kind']=='EnemyShot' and pending is None and event['hasRay'] and event['hit']=='Friendly' and event['targetId']==victim:
                pending=attack
            elif event['kind']=='PlayerDamaged' and pending==attack:
                row=totals[victim]
                if event['damage']!=min(20,100-row['damageTaken']) or event['damage']<=0:
                    raise ValueError('Combat replay damage does not match the remaining health')
                row['hitsReceived']+=1;row['damageTaken']+=event['damage'];damage_events+=1;pending=None
            else:
                raise ValueError('Combat replay damage must follow its original enemy shot')
        if packet['throughCombatSequence']!=damage_events:
            raise ValueError('Combat replay ledger boundary differs from its original damage events')
        seen=set()
        for row in value['statistics']:
            player=row['playerId'];total=totals.get(player)
            if player in seen or total is None or any(row[key]!=count for key,count in total.items()) \
                or row['health']!=100-total['damageTaken'] or any(row[key]!=0 for key in ('ammoUsed','shotsHit','kills','accuracyPercent')):
                raise ValueError('Combat replay statistics differ from the original event prefix')
            seen.add(player)
        if packet['observedSequence']>=enabled_sequence and seen!=owners.keys():
            raise ValueError('Combat replay statistics omit an original admission')
    if pending or not totals or any(not row['hitsReceived'] for row in totals.values()):
        raise ValueError('Combat replay must include a complete attack and damage for every original player')
    return {'damageEvents':damage_events,'players':totals}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--control-package',type=Path,required=True);p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--observe-closure-ui',action='store_true')
    p.add_argument('--player-package',type=Path,help='Launch five players per room from the API room ZIP, using this extracted player package')
    p.add_argument('--windows-release-report',type=Path,help='Pass the original release report through every packaged Windows launcher')
    p.add_argument('--check-windows-evidence-zip',action='store_true',help='Verify the original player ZIP exported by every released Windows launcher')
    p.add_argument('--game-address',type=ipaddress.IPv4Address,help='Local private IPv4 for the three-package check')
    p.add_argument('--check-lan-preflight',action='store_true',help='Release a same-PC UDP preflight before Unity binds each original game port')
    p.add_argument('--check-vr-venue-tickets',action='store_true',help='Launch all 25 players in each mode from the shipped console venue ZIP')
    p.add_argument('--check-vr-seat-files',action='store_true',help='Verify each original VR venue seat file against its live native endpoint before launch')
    p.add_argument('--check-quest-vr-deploy',action='store_true',help='Run Quest preflight and mapped mock deployment from each original VR venue ZIP')
    p.add_argument('--check-quest-vr-partial-map',action='store_true',help='Use a mixed headset roster and deploy five selected Quest seats from each original VR venue ZIP')
    p.add_argument('--check-quest-deployment-retry',action='store_true',help='Interrupt and resume the original mapped VR deployment without repeating successful seats')
    p.add_argument('--check-quest-tracking-wait',action='store_true',help='Verify that the tracked-seat wait times out against the original same-PC simulation clients')
    p.add_argument('--check-windows-venue-staging',action='store_true',help='Stage VIVE XR seats from the original VR or mixed venue ZIP')
    p.add_argument('--check-venue-openxr',action='store_true',help='Use one graphical mock OpenXR seat alongside 24 desktop peers per topology')
    p.add_argument('--check-venue-pose-review', action='store_true', help='Open the original OpenXR interruption frame and return to the same live room')
    p.add_argument('--check-venue-openxr-reconnect', action='store_true', help='Interrupt one tracked UDP client and reconnect its original process in both five-room modes')
    p.add_argument('--check-venue-live-tracking',action='store_true',help='Verify the Master-only running tracking overview during native OpenXR loss')
    p.add_argument('--peer-diagnostics',action='store_true',help='Verify observed UDP peers in Linked and absence in default Independent runs')
    p.add_argument('--check-debrief-receipts',action='store_true',help='Match published management receipts to every original native result')
    p.add_argument('--field-evidence',action='store_true',help='Verify the management ZIP with the original Linked player and server logs')
    p.add_argument('--venue-field-evidence',action='store_true',help='Verify full sealed admission evidence for both original venue End batches')
    p.add_argument('--field-players-per-room', type=int, choices=range(1, 6), default=5,
                   help='Seat count for staged venue field runs with room ticket ZIPs (default: 5)')
    p.add_argument('--venue-concurrent-roster-seconds', type=int, help='Require this many recorded seconds of concurrent play in both sealed batches')
    p.add_argument('--check-venue-concurrent-fire', action='store_true',
                   help='Drive normal exercise fire on all 25 native desktop seats and verify the sealed shared window')
    p.add_argument('--check-venue-link-metrics', action='store_true', help='Bind each packaged Windows client link report to its original sealed result')
    p.add_argument('--check-venue-field-ui',action='store_true',help='Download the original current and earlier field bundles from the shipped console')
    p.add_argument('--check-room-readiness',action='store_true',help='Verify live aggregate pose counts from the management package in both modes')
    p.add_argument('--check-room-observer',action='store_true',help='Verify room-scoped observation and instant replay on the original Linked source')
    p.add_argument('--check-live-room-navigation', action='store_true',
                   help='Switch all five live rooms in Chromium and re-read each displayed native frame after sealing')
    p.add_argument('--check-room-participation',action='store_true',help='Disconnect and restore one original VR admission in each five-room mode')
    p.add_argument('--check-vr-participation-pause',action='store_true',help='Pause and resume from the shipped room card during each native VR disconnect and recovery')
    p.add_argument('--check-room-endpoints',action='store_true',help='Verify real published UDP endpoints in the room cards and scoped API')
    p.add_argument('--check-room-clocks', action='store_true', help='Verify room clocks and the original pause/resume boundaries in both modes')
    p.add_argument('--check-venue-phase', action='store_true', help='Verify whole-venue pause and resume against both native topologies')
    p.add_argument('--check-venue-begin', action='store_true', help='Start both native topologies with one witnessed Begin per topology')
    p.add_argument('--check-venue-launcher', action='store_true', help='Use one real Windows launcher for the explicitly prepared servers of each topology')
    p.add_argument('--venue-management-https', action='store_true', help='Use a pinned HTTPS management profile for both venue launch plans')
    p.add_argument('--check-venue-plan-ui', action='store_true', help='Launch each topology with the exact plan downloaded from Chromium')
    p.add_argument('--check-venue-receipt-retry', action='store_true', help='Lose both original batch replies after commit through a loopback fixture')
    p.add_argument('--check-venue-launch-review', action='store_true', help='Import original unresolved launcher reports into the shipped Chromium console')
    p.add_argument('--check-venue-relay-readback', action='store_true', help='Use both source relay CLIs on copies of the closed original Linked journals')
    p.add_argument('--check-venue-preview', action='store_true', help='Run the shared Windows venue preview before both topology launches')
    p.add_argument('--check-venue-udp-readiness', action='store_true',
                   help='Match original UDP preflight reports to the launcher preview and actual game bindings')
    p.add_argument('--check-venue-endpoint-batch', action='store_true', help='Verify endpoint batch retries and force a last-room transaction rollback')
    p.add_argument('--check-venue-ticket-freshness', action='store_true', help='Verify ticket issuance before and after a managed Linked source stops')
    p.add_argument('--check-venue-ticket-recovery', action='store_true', help='Hold and resume the same source while one venue preview stays open')
    p.add_argument('--check-linked-room-enemies', action='store_true', help='Change one linked room through Chromium and verify original combat and replay')
    p.add_argument('--check-venue-tracking-gate', action='store_true', help='Reject full tracking Begin while the same native roster is otherwise ready')
    p.add_argument('--check-venue-participation-gate', action='store_true', help='Require all 25 effective native seats and verify their original Preparing frames')
    p.add_argument('--check-venue-end', action='store_true', help='End each native topology in one batch and read its original archives')
    p.add_argument('--check-venue-reports', action='store_true', help='Verify the original reports ZIP for each native End batch')
    p.add_argument('--check-venue-replay-ui', action='store_true', help='Open the original native archives through the shipped console')
    p.add_argument('--check-venue-replay-alignment', action='store_true', help='Switch to the original adjacent room at the same recorded UTC time')
    p.add_argument('--check-venue-mission-time', action='store_true', help='Switch original independent replays by mission tick in the shipped console')
    p.add_argument('--check-player-room-replay', action='store_true', help='Export a single room from the original native Linked combat replay')
    p.add_argument('--check-clip-statistics-csv', action='store_true', help='Download the original room player clip counters from the shipped console')
    p.add_argument('--check-venue-history-ui', action='store_true', help='Reopen and download the earlier batch after the newer native round')
    p.add_argument('--check-venue-environment', action='store_true', help='Confirm two batch environment changes in each native topology')
    p.add_argument('--check-venue-environment-ui', action='store_true', help='Open the original environment batch witness in the packaged console')
    p.add_argument('--check-venue-setting-downloads', action='store_true', help='Use original browser downloads in both sealed field evidence reports')
    p.add_argument('--check-venue-enemies', action='store_true', help='Use venue enemy policy to enable and stop native attacks')
    p.add_argument('--check-venue-enemy-ui', action='store_true', help='Verify the original enemy batch and open its live witness in the packaged console')
    p.add_argument('--check-layout-preview',action='store_true',help='Load a saved barricade opening and compare its preview with native world geometry')
    p.add_argument('--check-layout-fine-opening',action='store_true',help='Use a saved offset opening that requires 0.125m layout samples')
    p.add_argument('--check-room-reports',action='store_true',help='Verify scoped Linked CSVs and the ZIP against the full sealed native report')
    p.add_argument('--check-room-combat',action='store_true',help='Require actual enemy damage on every original admission and reconcile each replay frame and final report')
    p.add_argument('--check-hardware-feedback',action='store_true',help='Match live room feedback to the native combat reports')
    p.add_argument('--hardware-simulator-package',type=Path,help='Pass native live feedback through this extracted mock gateway package')
    p.add_argument('--prepare-independent-set',action='store_true',help='Prepare the five independent native sessions in one management request')
    p.add_argument('--check-independent-room-missions',action='store_true',help='Assign a different saved VR mission to every independent room and verify the accepted native world')
    p.add_argument('--check-independent-room-layouts-ui', action='store_true',
                   help='Use the shipped five-room layout overview to review and prepare the distinct native room missions')
    p.add_argument('--check-linked-archive-plan-ui', action='store_true', help='Recreate the original Linked mission from the packaged console and run it')
    p.add_argument('--check-venue-mission-file-ui', action='store_true', help='Download and reload the browser mission files before preparing each topology')
    p.add_argument('--mission-template',type=Path,help='Check and save an exported VR mission template, then run both native topologies with it')
    p.add_argument('--check-interrupted-replay', action='store_true', help='Play the saved native prefix after the owned launcher is killed')
    p.add_argument('--check-managed-mr', action='store_true', help='Verify the MR alignment startup gate, desktop rejection and Preparing seal')
    p.add_argument('--mr-venue-bundle-only', action='store_true', help='Verify both MR venue exports from native publishers, without starting desktop players')
    p.add_argument('--check-mr-venue-source-recovery', action='store_true', help='Hold an original signed MR ZIP while its managed Linked publisher pauses and recovers')
    p.add_argument('--check-mr-venue-write-gate', action='store_true', help='Verify a managed MR source interruption between two mock Quest writes')
    p.add_argument('--mixed-venue-bundle-only', action='store_true', help='Verify a mixed five-room console ZIP and mapped mock Quest deployment from native publishers')
    p.add_argument('--openxr-mock-only', action='store_true', help='Verify a packaged graphical OpenXR client with the installed Unity mock runtime')
    p.add_argument('--check-openxr-reconnect', action='store_true', help='Interrupt the tracked UDP client and reload its ticket with the mock right Vive menu button')
    p.add_argument('--check-openxr-revocation', action='store_true', help='Reject a revoked OpenXR ticket when the same seat receives a new admission')
    p.add_argument('--openxr-mock-pose-dll', type=Path, help='Compiled tests/fixtures/openxr-mock-pose.c for the OpenXR mock check')
    p.add_argument('--check-mapped-quest', action='store_true', help='Use full and five-seat mock ADB maps with each native MR venue export')
    p.add_argument('--check-live-reinforcement', action='store_true', help='Verify a native server accepts only supported live enemy targets and records the result')
    args=p.parse_args()
    if os.name!='nt':p.error('Actual Windows processes required')
    if args.check_mapped_quest and not args.mr_venue_bundle_only:p.error('--check-mapped-quest requires --mr-venue-bundle-only')
    if args.check_mr_venue_source_recovery and not args.mr_venue_bundle_only:
        p.error('--check-mr-venue-source-recovery requires --mr-venue-bundle-only')
    if args.check_mr_venue_write_gate and not args.check_mr_venue_source_recovery:
        p.error('--check-mr-venue-write-gate requires --check-mr-venue-source-recovery')
    if args.check_room_endpoints and not (args.check_vr_venue_tickets or args.mixed_venue_bundle_only):
        p.error('--check-room-endpoints requires --check-vr-venue-tickets or --mixed-venue-bundle-only')
    venue_only = args.mr_venue_bundle_only or args.mixed_venue_bundle_only
    if args.mr_venue_bundle_only and args.mixed_venue_bundle_only:p.error('Choose a single venue bundle check')
    if args.openxr_mock_only and (venue_only or not args.player_package):
        p.error('--openxr-mock-only requires a player package and its own native room')
    if args.check_openxr_reconnect and (not args.openxr_mock_only or args.game_address is not None):
        p.error('--check-openxr-reconnect requires --openxr-mock-only on loopback')
    if args.check_openxr_revocation and (not args.openxr_mock_only or args.check_openxr_reconnect):
        p.error('--check-openxr-revocation requires --openxr-mock-only without --check-openxr-reconnect')
    if args.check_venue_openxr and (venue_only or args.openxr_mock_only or not args.check_quest_vr_partial_map or args.check_room_participation):
        p.error('--check-venue-openxr requires --check-quest-vr-partial-map and its own venue participation check')
    if args.check_venue_live_tracking and not args.check_venue_openxr:
        p.error('--check-venue-live-tracking requires --check-venue-openxr')
    if args.check_venue_pose_review and not args.check_venue_openxr:
        p.error('--check-venue-pose-review requires --check-venue-openxr')
    if args.check_venue_openxr_reconnect and (not args.check_venue_openxr or (args.peer_diagnostics and not args.venue_field_evidence)
            or args.check_windows_venue_staging or args.check_room_combat):
        p.error('--check-venue-openxr-reconnect requires --check-venue-openxr and its own connection and combat checks')
    if (args.openxr_mock_only or args.check_venue_openxr) != bool(args.openxr_mock_pose_dll):
        p.error('Supply --openxr-mock-pose-dll with --openxr-mock-only or --check-venue-openxr')
    if venue_only:
        if not args.game_address or args.player_package:p.error('The venue bundle check needs --game-address and no player package')
    elif not args.openxr_mock_only and bool(args.player_package)!=bool(args.game_address):p.error('Provide --player-package and --game-address together')
    if args.check_lan_preflight and not args.player_package:
        p.error('--check-lan-preflight requires the three-package check')
    if args.check_vr_venue_tickets and not args.player_package:
        p.error('--check-vr-venue-tickets requires the three-package check')
    if args.check_vr_seat_files and not args.check_vr_venue_tickets:
        p.error('--check-vr-seat-files requires --check-vr-venue-tickets')
    if args.check_quest_vr_deploy and not args.check_vr_venue_tickets:
        p.error('--check-quest-vr-deploy requires --check-vr-venue-tickets')
    if args.check_quest_vr_partial_map and (not args.check_vr_venue_tickets or args.check_quest_vr_deploy):
        p.error('--check-quest-vr-partial-map requires --check-vr-venue-tickets without the full Quest fleet check')
    if args.check_quest_deployment_retry and not (args.check_quest_vr_deploy or args.check_quest_vr_partial_map):
        p.error('--check-quest-deployment-retry requires one of the mapped VR checks')
    if args.check_quest_tracking_wait and (args.check_venue_openxr or not (args.check_quest_vr_deploy or args.check_quest_vr_partial_map)):
        p.error('--check-quest-tracking-wait requires a mapped VR check with the default desktop clients')
    if args.check_windows_venue_staging and not (args.check_quest_vr_partial_map or args.mixed_venue_bundle_only):
        p.error('--check-windows-venue-staging requires --check-quest-vr-partial-map or --mixed-venue-bundle-only')
    if args.peer_diagnostics and not args.player_package:p.error('--peer-diagnostics requires the three-package check')
    if args.check_debrief_receipts and not (args.player_package or args.openxr_mock_only):
        p.error('--check-debrief-receipts requires native player package or OpenXR mock verification')
    if args.field_evidence and not args.peer_diagnostics:p.error('--field-evidence requires --peer-diagnostics')
    if args.venue_field_evidence and not (args.field_evidence and args.check_venue_end):
        p.error('--venue-field-evidence requires --field-evidence and --check-venue-end')
    players_per_room = args.field_players_per_room
    venue_players = players_per_room * 5
    if players_per_room != 5:
        if not args.venue_field_evidence:
            p.error('--field-players-per-room requires --venue-field-evidence')
        if args.check_vr_venue_tickets or args.check_room_observer:
            p.error('The console venue ticket and room observer fixtures require the original five seats per room')
        if args.check_venue_participation_gate:
            p.error('--check-venue-participation-gate exercises a successful full-roster Begin and requires five seats per room')
    if args.venue_concurrent_roster_seconds is not None and (not args.venue_field_evidence or not 1 <= args.venue_concurrent_roster_seconds <= 90):
        p.error('--venue-concurrent-roster-seconds requires --venue-field-evidence and 1..90 seconds')
    if args.check_venue_concurrent_fire and (args.venue_concurrent_roster_seconds is None or args.check_venue_openxr):
        p.error('--check-venue-concurrent-fire requires --venue-concurrent-roster-seconds and all desktop seats')
    if args.check_venue_link_metrics and (not args.venue_field_evidence or args.check_venue_openxr_reconnect or args.check_venue_concurrent_fire):
        p.error('--check-venue-link-metrics requires venue field evidence and the original packaged client connections')
    if args.windows_release_report and (not args.player_package or args.check_venue_concurrent_fire or args.openxr_mock_only):
        p.error('--windows-release-report requires the packaged Windows launchers in the ordinary venue check')
    if args.check_windows_evidence_zip and not (args.windows_release_report and args.venue_field_evidence):
        p.error('--check-windows-evidence-zip requires Windows release and venue field evidence')
    if args.check_venue_field_ui and not args.venue_field_evidence:
        p.error('--check-venue-field-ui requires --venue-field-evidence')
    if args.check_room_readiness and not args.player_package:p.error('--check-room-readiness requires the three-package check')
    if args.check_room_observer and not args.player_package:p.error('--check-room-observer requires the three-package check')
    if args.check_room_participation and (not args.check_room_readiness or args.peer_diagnostics):
        p.error('--check-room-participation requires --check-room-readiness without the one-connection peer diagnostics check')
    if args.check_vr_participation_pause and not args.check_room_participation:
        p.error('--check-vr-participation-pause requires --check-room-participation')
    if args.check_room_clocks and not args.player_package:p.error('--check-room-clocks requires the three-package check')
    if args.check_venue_phase and not args.check_room_clocks:p.error('--check-venue-phase requires --check-room-clocks')
    if args.check_venue_begin and not args.player_package:p.error('--check-venue-begin requires the three-package check')
    if args.check_live_room_navigation and (venue_only or args.openxr_mock_only or not args.check_venue_begin
                                           or not args.player_package or not shutil.which('node')):
        p.error('--check-live-room-navigation requires the two-topology three-package check with --check-venue-begin and Node.js')
    if args.check_venue_launcher and (not all((args.prepare_independent_set, args.check_venue_begin, args.check_venue_end))
                                     or any((args.check_lan_preflight, args.check_layout_preview, args.field_evidence,
                                             args.venue_field_evidence, args.observe_closure_ui))):
        p.error('--check-venue-launcher requires --prepare-independent-set --check-venue-begin --check-venue-end; '
                'individual launcher report workflows must be checked separately')
    if args.check_venue_plan_ui and (not args.check_venue_launcher or not shutil.which('node')):
        p.error('--check-venue-plan-ui requires --check-venue-launcher and Node.js with Playwright Chromium')
    if args.check_venue_udp_readiness and not (args.check_venue_launcher and args.check_venue_preview):
        p.error('--check-venue-udp-readiness requires --check-venue-launcher and --check-venue-preview')
    if args.check_venue_receipt_retry and (not args.check_venue_plan_ui or args.venue_management_https):
        p.error('--check-venue-receipt-retry requires --check-venue-plan-ui and its own plain loopback management target')
    if args.check_venue_launch_review and not args.check_venue_receipt_retry:
        p.error('--check-venue-launch-review requires --check-venue-receipt-retry')
    if args.check_venue_relay_readback and (not args.check_venue_plan_ui or not shutil.which('dotnet')):
        p.error('--check-venue-relay-readback requires --check-venue-plan-ui and the built .NET relay tools')
    if args.check_venue_preview and not args.check_venue_launcher:
        p.error('--check-venue-preview requires --check-venue-launcher')
    if args.venue_management_https and not (args.check_venue_launcher and args.game_address and shutil.which('pwsh')):
        p.error('--venue-management-https requires --check-venue-launcher, a local --game-address and PowerShell 7')
    if args.check_venue_endpoint_batch and not args.check_venue_launcher:
        p.error('--check-venue-endpoint-batch requires --check-venue-launcher')
    if args.check_venue_ticket_freshness and (not args.check_venue_launcher or not shutil.which('node')):
        p.error('--check-venue-ticket-freshness requires --check-venue-launcher and Node.js with Playwright Chromium')
    if args.check_venue_ticket_recovery and not args.check_venue_ticket_freshness:
        p.error('--check-venue-ticket-recovery requires --check-venue-ticket-freshness')
    if args.check_linked_room_enemies and (not args.player_package or args.check_room_combat or not shutil.which('node')):
        p.error('--check-linked-room-enemies requires the player package, Node.js and a separate run from --check-room-combat')
    if args.check_venue_tracking_gate and not args.check_venue_begin:p.error('--check-venue-tracking-gate requires --check-venue-begin')
    if args.check_venue_participation_gate and not (args.check_venue_begin and args.player_package):
        p.error('--check-venue-participation-gate requires --check-venue-begin and all native player seats')
    if args.check_venue_end and (not args.player_package or args.observe_closure_ui):
        p.error('--check-venue-end requires the three-package check and its own End path')
    if args.check_venue_reports and (not args.check_venue_end or not args.check_room_reports):
        p.error('--check-venue-reports requires --check-venue-end and --check-room-reports')
    if args.check_venue_replay_ui and not args.check_venue_end:
        p.error('--check-venue-replay-ui requires --check-venue-end')
    if args.check_venue_replay_alignment and not (args.check_venue_replay_ui and args.check_venue_participation_gate):
        p.error('--check-venue-replay-alignment requires --check-venue-replay-ui and --check-venue-participation-gate')
    if args.check_venue_mission_time and not args.check_venue_replay_ui:
        p.error('--check-venue-mission-time requires --check-venue-replay-ui')
    if args.check_player_room_replay and not (args.check_venue_replay_ui and args.check_room_combat):
        p.error('--check-player-room-replay requires --check-venue-replay-ui and --check-room-combat')
    if args.check_clip_statistics_csv and not args.check_player_room_replay:
        p.error('--check-clip-statistics-csv requires --check-player-room-replay')
    if args.check_venue_history_ui and not (args.check_venue_replay_ui and args.check_venue_reports):
        p.error('--check-venue-history-ui requires --check-venue-replay-ui and --check-venue-reports')
    if args.check_venue_environment and not args.player_package:
        p.error('--check-venue-environment requires the three-package check')
    if args.check_venue_environment_ui and not args.check_venue_environment:
        p.error('--check-venue-environment-ui requires --check-venue-environment')
    if args.check_venue_enemies and not args.check_room_combat:
        p.error('--check-venue-enemies requires --check-room-combat')
    if args.check_venue_enemy_ui and not args.check_venue_enemies:
        p.error('--check-venue-enemy-ui requires --check-venue-enemies')
    if args.check_venue_setting_downloads and not (args.venue_field_evidence and args.check_venue_environment_ui and args.check_venue_enemy_ui):
        p.error('--check-venue-setting-downloads requires --venue-field-evidence and both setting UI checks')
    if args.check_room_reports and not args.player_package:p.error('--check-room-reports requires the three-package check')
    if args.check_room_combat and not args.check_room_reports:p.error('--check-room-combat requires --check-room-reports')
    if args.check_hardware_feedback and not args.check_room_combat:p.error('--check-hardware-feedback requires --check-room-combat')
    openxr_hardware=bool(args.openxr_mock_only and args.hardware_simulator_package)
    if args.hardware_simulator_package and not (args.check_hardware_feedback or openxr_hardware):
        p.error('--hardware-simulator-package requires --check-hardware-feedback or --openxr-mock-only')
    if args.prepare_independent_set and not args.player_package:p.error('--prepare-independent-set requires the player package')
    if args.check_layout_fine_opening and not args.check_layout_preview:
        p.error('--check-layout-fine-opening requires --check-layout-preview')
    if args.check_independent_room_missions and (not args.prepare_independent_set or args.check_layout_preview or args.check_room_combat):
        p.error('--check-independent-room-missions requires --prepare-independent-set and its own mission fixtures')
    if args.check_independent_room_layouts_ui and (not args.check_independent_room_missions or not shutil.which('node')):
        p.error('--check-independent-room-layouts-ui requires --check-independent-room-missions and Chromium')
    if args.check_linked_archive_plan_ui and (not args.player_package or venue_only or args.openxr_mock_only
            or args.mission_template or args.check_layout_preview or args.check_room_combat or not shutil.which('node')):
        p.error('--check-linked-archive-plan-ui requires the ordinary three-package run and Chromium')
    if args.check_venue_mission_file_ui and not (args.check_independent_room_layouts_ui and args.check_linked_archive_plan_ui):
        p.error('--check-venue-mission-file-ui requires both native browser mission preparation checks')
    if args.mission_template and (not args.prepare_independent_set or venue_only or args.openxr_mock_only
            or args.check_independent_room_missions or args.check_layout_preview or args.check_room_combat):
        p.error('--mission-template requires --prepare-independent-set and the ordinary two-topology check')
    address='127.0.0.1'
    if args.game_address:
        if not any(args.game_address in ipaddress.IPv4Network(net) for net in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):
            p.error('--game-address must be a local private IPv4 address')
        address=str(args.game_address)
        try:free(socket.SOCK_DGRAM,address)
        except OSError:p.error('--game-address must be assigned to this PC')
    folder=args.package.resolve();manifest=package.verify(folder);assert manifest['launcherSourceSha256']==package.digest(ROOT/'tools/WindowsServerLauncher/ServerLauncher.cs')
    player_folder=None
    windows_release_hash=None
    openxr_mock=None
    if args.player_package:
        player_folder=args.player_package.resolve()
        player_package=module('portable_player_package','package-windows-player.py')
        player_manifest=player_package.verify(player_folder)
        if player_manifest['build']['sourceFingerprint']!=manifest['build']['sourceFingerprint']:
            p.error('Player and server packages must share the Unity build source')
        if args.windows_release_report:
            args.windows_release_report=args.windows_release_report.resolve(strict=True)
            release=json.loads(args.windows_release_report.read_text(encoding='utf-8-sig'))
            windows_release_hash=player_package.digest(player_folder/'player-package.json')
            if (release.get('verified') is not True or release.get('scope')!='offline-package-consistency'
                    or release.get('windows',{}).get('playerManifestSha256')!=windows_release_hash):
                p.error('Release report must identify this original Windows player package')
    if args.openxr_mock_only or args.check_venue_openxr:
        unity=ROOT/'clients/unity'
        mock_package_version=read(unity/'Packages/manifest.json')['dependencies']['com.unity.xr.openxr']
        candidates=[path for path in (unity/'Library/PackageCache').glob('com.unity.xr.openxr@*')
                    if (path/'package.json').is_file() and read(path/'package.json')['version']==mock_package_version]
        if len(candidates)!=1:
            p.error('Restore the project-pinned Unity OpenXR package in the Editor first')
        openxr_mock=candidates[0]/'Runtime/MockRuntime/unity-mock-runtime.json'
        runtime_file=openxr_mock.parent/'windows/x64/mock_runtime.dll'
        expected={'api_version':'1.0','name':'Unity Mock Runtime','library_path':r'.\windows\x64\mock_runtime.dll'}
        if not openxr_mock.is_file() or read(openxr_mock).get('runtime')!=expected or not runtime_file.is_file():
            p.error('The pinned Unity OpenXR package does not contain the expected Windows mock runtime')
    control.package.verify(args.control_package);out=ROOT/'artifacts/server-package-checks'/('run-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False);runtime=args.runtime_root.resolve()/out.name;runtime.mkdir(parents=True,exist_ok=False)
    (ROOT/'artifacts/server-package-checks-latest-path.txt').write_text(str(out),encoding='utf-8');print(json.dumps({'stage':'starting','directory':str(out)}),flush=True)
    env=dict(os.environ);env.update(PATH=str(Path(os.environ['WINDIR'])/'System32'),DOTNET_ROOT=str(runtime/'absent-dotnet'),DOTNET_MULTILEVEL_LOOKUP='0');exe=folder/'Launch-Server.exe';control_exe=args.control_package.resolve()/'Start-Control.exe';data=runtime/'control';checks=[];runners=[];clients=[];cleanup=[];witnesses=[];api=None;api_witness=None;keys=None;sessions=[];rounds=[];observer=None;observer_log=None;observer_out=out/'closure-ui';observer_stop=out/'closure-ui-stop.request';observer_entry=None
    receipt_gates=[]
    venue_control_reports={}
    venue_target = data / 'control-instance.json'
    venue_uri = venue_pin = venue_password = None
    hardware_processes=[]
    reconnect_gates=[]
    if args.hardware_simulator_package:
        hardware=args.hardware_simulator_package.resolve()
        hardware_manifest=module('native_hardware_package','package-hardware-simulator.py').verify(hardware)
        if hardware_manifest['mode']!='OfflineAndLiveSimulation':p.error('Use a live hardware simulator package')
        dotnet=shutil.which('dotnet')
        if not dotnet:p.error('The hardware simulator requires .NET 10')
        mock_env={key:value for key,value in os.environ.items() if not key.lower().startswith('operatorkeys__') and key.lower() not in
            ('operatorkeyfile','playerticketsigningkey','controlpipetoken','vr_command_room_key')}
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    def stage(name,**extra):save('stage.json',{'stage':name,**extra});print(json.dumps({'stage':name,**extra}),flush=True)
    def check(ok,label):
        if not ok:raise AssertionError(label)
        checks.append(label);print('PASS: '+label,flush=True)
    def wait(fn,seconds,label):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            value=fn()
            if value:return value
            time.sleep(.1)
        raise RuntimeError('Timeout: '+label)
    def request(path,body=None,role='Master',method=None,expected=200,admission=None,raw_response=False,request_id=None,
                content_type=None):
        h={'Authorization':'Bearer '+keys[role]};h.update({'Content-Type':'application/json'} if body is not None else {})
        if admission:h['If-Match-Admission']=admission
        if request_id:h['Idempotency-Key']=request_id
        if isinstance(body,bytes):h['Content-Type']=content_type or 'application/octet-stream'
        req=urllib.request.Request(uri+path,data=body if isinstance(body,bytes) or body is None else json.dumps(body).encode(),headers=h,method=method)
        try:
            with urllib.request.urlopen(req,timeout=5) as r:code=r.status;raw=r.read();headers=r.headers
        except urllib.error.HTTPError as e:code=e.code;raw=e.read();headers=e.headers
        if code!=expected:raise RuntimeError(path+' HTTP '+str(code))
        if raw_response:return raw,headers
        if path.endswith('/report.csv'):return raw.decode('utf-8-sig')
        return json.loads(raw) if raw else None
    def command(session,action):return request('/api/sessions/'+session+'/commands',{'commandId':str(uuid.uuid4()),'action':action})
    def config(session,port=None,**extra):return dict({'role':'Server','managementApiUrl':uri,'gameServerKey':keys['GameServer'],'sessionId':session,'address':address,'listenAddress':address,'port':port or free(socket.SOCK_DGRAM,address)},**extra)
    def call(label,options,good=False,report=None):
        result=out/(label+'.json') if report is None else report
        child=subprocess.run([str(exe),*map(str,options),'--report',str(result)],env=env,cwd=out,timeout=45)
        check(child.returncode==(0 if good else 1),label+' original exit')
        if report is None:
            value=read(result);check(value['complete']==good,label+' complete flag')
        return result
    def rejected(label,value,**options):
        file=runtime/(label+'.json');file.write_text(json.dumps(value),encoding='utf-8');work=runtime/(label+'-work');ready=out/(label+'-ready.json')
        call(label,['--run',file,'--work',work,'--seconds',options.get('seconds',60),'--ready-report',ready,*options.get('extra',())]);check(not work.exists() and not ready.exists(),label+' creates no native world')
    def save_mission(label, *, auto_attack=False, enemy_count=1, experience='VR', props=None):
        if props is None:
            props=[{'assetId':'sandbag','position':{'x':x,'y':0,'z':-1},'yawDegrees':0}
                   for x in (-5,-3,-1,3,5)] if args.check_layout_preview else []
            if args.check_layout_fine_opening:
                props=[{'assetId':'barrel' if x==-1.4 else 'sandbag','position':{'x':x,'y':0,'z':-1},'yawDegrees':0}
                       for x in (-4.75,-2.75,-1.4,.75,2.75,4.75)]
                props.extend([
                    {'assetId':'sandbag','position':{'x':4,'y':0,'z':2},'yawDegrees':45},
                    {'assetId':'barrel','position':{'x':-2,'y':0,'z':2},'yawDegrees':-30},
                ])
        return request('/api/missions',{'name':'Portable '+label,'briefing':'Owned PC package fixture','durationSeconds':600,'environment':{'mode':experience,'weather':'Clear','timeOfDay':'Day','lightning':False},'enemies':{'count':enemy_count,'behavior':'Hold','autoAttack':auto_attack},'props':props},expected=201)
    def create(rooms,label, **options):
        mission=save_mission(label,**options)
        state=request('/api/sessions',{'missionId':mission['id'],'mode':'Linked' if len(rooms)==5 else 'Independent','roomIds':rooms},expected=201);sessions.append(state['id']);return state

    def verify_template_world(entry, mission, running, source='imported template', evidence='template'):
        info=request(f"/api/sessions/{entry['sessionId']}/world")
        definition=mission['definition']; environment=definition['environment']; enemies=definition['enemies']
        header=info['header']; packet=running['packet']; frame=packet['frame']
        expected=[]
        for room in header['roomIds']:
            for prop in definition['props']:
                feet=prop['position']
                expected.append((room,prop['assetId'],feet['x']+(room-3)*14,feet['y'],feet['z'],prop['yawDegrees']))
        actual=[(prop['roomId'],prop['kind'].lower(),prop['feet']['x'],prop['feet']['y'],prop['feet']['z'],prop['yaw'])
                for prop in header['props']]
        def matches(left,right):
            return left[:2]==right[:2] and all(abs(a-b)<.0001 for a,b in zip(left[2:],right[2:]))
        check(header['missionDurationSeconds']==definition['durationSeconds'] and packet['weather']==environment['weather']
              and packet['lightning']==environment['lightning'] and frame['night']==(environment['timeOfDay']=='Night')
              and frame['behavior']==enemies['behavior'] and frame['autoAttack']==enemies['autoAttack']
              and len(frame['enemies'])==enemies['count'] and len(actual)==len(expected)
              and all(matches(left,right) for left,right in zip(actual,expected)),
              entry['label']+' native duration, environment, enemies and cover match the '+source)
        save(entry['label']+'-'+evidence+'-world.json',{'missionId':mission['id'],'header':header,'runningSequence':packet['sequence']})

    def prepare_linked_archive(rooms):
        definition = {'name': 'Portable archived Linked mission', 'briefing': 'Original five-room briefing', 'durationSeconds': 420,
                      'environment': {'mode': 'VR', 'weather': 'Rain', 'timeOfDay': 'Night', 'lightning': False},
                      'enemies': {'count': 5, 'behavior': 'Hold', 'autoAttack': False},
                      'props': [{'assetId': 'barrel', 'position': {'x': 2, 'y': 0, 'z': 1}, 'yawDegrees': 45}]}
        mission = request('/api/missions', definition, expected=201)
        original = request('/api/sessions', {'missionId': mission['id'], 'mode': 'Linked', 'roomIds': rooms}, expected=201)
        targets = request('/api/venue/phase')['end']
        assert [row['sessionId'] for row in targets] == [original['id']]
        batch = request('/api/venue/phase', {'action': 'End', 'targets': targets}, request_id=str(uuid.uuid4()))
        head = request(f'/api/missions/{mission["id"]}/revisions', dict(definition, durationSeconds=600, props=[]),
                       expected=201, request_id=str(uuid.uuid4()))
        output = out/'native-linked-archive-plan.json'
        driver = ROOT/'tests/browser/server-plan-browser.cjs'
        completed = subprocess.run([shutil.which('node'), str(driver)], cwd=driver.parent,
                                   input=json.dumps({'base': uri, 'token': keys['Master'], 'output': str(output),
                                                     'useMissionFile': args.check_venue_mission_file_ui,
                                                     'linkedArchive': {'batchId': batch['requestId'], 'sessionId': original['id'], 'mission': mission}}),
                                   capture_output=True, encoding='utf-8', timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        check(completed.returncode == 0 and output.is_file(), 'shipped console restores the historical Linked batch: '
              + completed.stderr.replace(keys['Master'], '[redacted]')[-600:])
        observed = read(output)
        if args.check_venue_mission_file_ui:
            check(observed['filePlan'] == {'schemaVersion': 1, 'mode': 'Linked',
                                          'rooms': [{'roomId': room, 'missionId': mission['id']} for room in rooms]},
                  'fresh console reopens the saved Linked mission file with all five original assignments')
            check(read(out/'native-linked-mission-file-review.json') == {'mode': 'Linked',
                  'rooms': [{'roomId': room, 'missionId': mission['id'], 'layout': 'valid'} for room in rooms]},
                  'fresh console previews each original Linked assignment and layout before loading')
        prepared = observed['prepared']
        check(prepared['id'] != original['id'] and prepared['mode'] == 'Linked' and prepared['roomIds'] == rooms
              and prepared['mission'] == mission and prepared['mission']['id'] != head['id']
              and request('/api/sessions/'+original['id'])['state'] == 'Ended'
              and request('/api/venue/closure/'+batch['requestId']+'/linked-plan') == observed['original'],
              'new Linked session uses the archived mission while the original batch remains intact')
        sessions.append(prepared['id'])
        return prepared

    def verify_lan_preflight(value, label):
        powershell = Path(os.environ['WINDIR']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        script = [str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                  '-File', str(ROOT/'scripts/check-lan-udp.ps1')]
        options = {'cwd': out, 'creationflags': subprocess.CREATE_NO_WINDOW}
        with tempfile.TemporaryDirectory(prefix='udp-key-', dir=runtime) as directory:
            key = str(Path(directory)/'probe.key')
            subprocess.run(script + ['-NewKey', '-KeyFile', key], capture_output=True, check=True, timeout=10, **options)
            common = ['-KeyFile', key, '-LocalAddress', value['address'], '-PeerAddress', value['address'],
                      '-Port', str(value['port']), '-Count', '3']
            log_path = out/(label+'-lan-listener.ndjson')
            with log_path.open('xb') as log:
                listener = subprocess.Popen(script + ['-Mode', 'Listen', '-Seconds', '15', *common],
                                            stdout=log, stderr=subprocess.STDOUT, **options)
                try:
                    def listening():
                        if listener.poll() is not None: raise RuntimeError('UDP preflight listener exited before its bind')
                        text = log_path.read_text(encoding='utf-8')
                        return json.loads(text.splitlines()[0]) if '\n' in text else None
                    ready = wait(listening, 10, label+' UDP preflight bind')
                    if ready != {'version': 1, 'stage': 'listening', 'localAddress': value['address'],
                                 'peerAddress': value['address'], 'port': value['port']}:
                        raise RuntimeError('UDP preflight reported another endpoint')
                    probe = subprocess.run(script + ['-Mode', 'Probe', *common], capture_output=True, check=True,
                                           encoding='utf-8', timeout=10, **options)
                    if listener.wait(timeout=17) != 0: raise RuntimeError('UDP preflight listener did not finish')
                finally:
                    if listener.poll() is None: listener.kill(); listener.wait(timeout=10)
            reply = json.loads(probe.stdout)
            final = json.loads(log_path.read_text(encoding='utf-8').splitlines()[-1])
            probe_path = out/(label+'-lan-probe.json')
            probe_path.write_text(probe.stdout, encoding='utf-8')
            pair = json.loads(subprocess.check_output(script + ['-ListenerReport', str(log_path), '-ProbeReport', str(probe_path)],
                                                      encoding='utf-8', timeout=10, **options))
        check(all(item['complete'] and item['port'] == value['port'] and item['matched'] == item['requested'] == 3
                  and item['scope'] == 'authenticated-udp-only' for item in (reply, final))
              and [sample['sample'] for sample in reply['samples']] == [1, 2, 3]
              and all(sample['roundTripMs'] >= 0 for sample in reply['samples']),
              label+' Windows PowerShell UDP preflight exchanged all three authenticated samples and exited')
        check(pair['complete'] is True and pair['stage'] == 'pair-verified' and pair['port'] == value['port'] and pair['matched'] == 3
              and pair['exchangeSha256'] == reply['exchangeSha256'] == final['exchangeSha256'],
              label+' original listener and probe reports match the same authenticated exchange')
        return {'listener': final, 'probe': reply, 'pair': pair}

    def venue_udp_readiness(label, topology, states, values, plan_path, preview):
        endpoints = [{'roomIds': state['roomIds'], 'address': value['address'], 'port': value['port']}
                     for state, value in zip(states, values, strict=True)]
        sources = [{'roomId': room, 'seat': seat, 'address': address}
                   for room in range(1, 6) for seat in range(1, players_per_room + 1)]
        network = out / (label + '-udp-network.json')
        network.write_text(json.dumps({'version': 1, 'mode': topology, 'endpoints': endpoints, 'sources': sources}), encoding='utf-8')
        pairs = []
        for value, endpoint in zip(values, endpoints, strict=True):
            suffix = label + '-rooms-' + '-'.join(map(str, endpoint['roomIds']))
            verify_lan_preflight(value, suffix)
            pairs.append({'listener': suffix + '-lan-listener.ndjson', 'probe': suffix + '-lan-probe.json'})
        manifest = out / (label + '-udp-pairs.json')
        manifest.write_text(json.dumps({'version': 1, 'pairs': pairs}), encoding='utf-8')

        def run(preview_path, suffix):
            report = out / (label + suffix + '.json')
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/check-venue-udp-preflight.py'),
                '--network-plan', str(network), '--pairs', str(manifest), '--launcher-preview', str(preview_path),
                '--output', str(report)], capture_output=True, encoding='utf-8', timeout=75)
            return result, read(report)

        changed = read(plan_path)
        last = next(row for row in changed['servers'] if row['roomIds'] == endpoints[-1]['roomIds'])
        original_ports = {item['port'] for item in endpoints}
        while last['port'] in original_ports:
            last['port'] = free(socket.SOCK_DGRAM, address)
        wrong_plan = runtime / (label + '-udp-wrong-port-plan.json')
        wrong_plan.write_text(json.dumps(changed), encoding='utf-8')
        wrong = call(label + '-udp-wrong-port-preview', ['--venue-check', wrong_plan], good=True)
        result, rejected = run(wrong, '-udp-rejected')
        check(result.returncode == 1 and not rejected['complete'] and rejected['verifiedSources'] == len(values)
              and not rejected['launcherPreview']['complete']
              and rejected['launcherPreview']['groups'][-1] == {'roomIds': endpoints[-1]['roomIds'], 'issues': ['port-mismatch']},
              label + ' original UDP reports cannot pass with a changed last launcher port')
        result, readiness = run(preview, '-udp-readiness')
        check(result.returncode == 0 and readiness['complete'] and readiness['verifiedSources'] == len(values)
              and readiness['launcherPreview']['sha256'] == hashlib.sha256(preview.read_bytes()).hexdigest()
              and all(not group['issues'] for group in readiness['launcherPreview']['groups']),
              label + ' readiness matches every original launcher preview binding and preserves its digest')
        return pairs

    def launch(state,label, *, listen_address=None, verify_layout=True):
        value=config(state['id'], listenAddress=listen_address or address);file=runtime/(label+'.json');file.write_text(json.dumps(value),encoding='utf-8');ready=out/(label+'-ready.json');report=out/(label+'-final.json');work=runtime/(label+'-work')
        preflight = verify_lan_preflight(value, label) if args.check_lan_preflight and label in ('room-1', 'room-2', 'room-3', 'room-4', 'room-5', 'linked') else None
        diagnostics=args.peer_diagnostics and (label=='linked' or (args.venue_field_evidence and label in {f'room-{i}' for i in range(1,6)}))
        options=['--peer-diagnostics','on'] if diagnostics else []
        child=subprocess.Popen([str(exe),'--run',str(file),'--work',str(work),'--seconds','600','--ready-report',str(ready),'--report',str(report),*options],cwd=out,env=env);entry={'process':child,'readyPath':ready,'reportPath':report,'work':work,'config':value,'label':label,'sessionId':state['id'],'witness':None,'peerDiagnostics':diagnostics};runners.append(entry)
        def is_ready():
            if child.poll() is not None:raise RuntimeError('Server launcher exited before ready '+label)
            return read(ready) if ready.exists() else None
        info=wait(is_ready,100,label+' ready')
        return confirm_launch(entry,state,info,preflight,verify_layout)
    def confirm_launch(entry,state,info,preflight=None,verify_layout=True):
        label,value,diagnostics=entry['label'],entry['config'],entry['peerDiagnostics']
        w=control.ChildWitness(info['childPid']);entry['witness']=w;witnesses.append(w);entry['ready']=info
        check(info['peerDiagnosticsEnabled'] is diagnostics, label+' ready report records the explicit diagnostics choice')
        if args.check_layout_preview and verify_layout:entry['layoutSession']=state
        endpoint=request('/api/sessions/'+state['id']+'/connection-endpoint');check(info['streamId']==endpoint['streamId'] and info['port']==endpoint['port'] and endpoint['address']==address,label+' original endpoint / child')
        binding = info['udpBinding']
        observed = datetime.fromisoformat(binding['observedAtUtc'])
        check(binding['processId'] == info['childPid'] and binding['address'] == value['listenAddress'] and binding['port'] == value['port']
              and observed <= datetime.fromisoformat(endpoint['createdAtUtc']), label + ' owned binding observed before endpoint publication')
        netstat = Path(os.environ['WINDIR']) / 'System32/netstat.exe'
        rows = subprocess.check_output([str(netstat), '-ano', '-p', 'udp'], cwd=out, timeout=10, encoding='ascii', errors='ignore').splitlines()
        local = f"{binding['address']}:{binding['port']}"
        pid = str(binding['processId'])
        check(any(len(parts) >= 4 and parts[0] == 'UDP' and parts[1] == local and parts[-1] == pid
                  for parts in map(str.split, rows)), label + ' independent Windows UDP owner check')
        if preflight:
            check((binding['address'], binding['port']) == (preflight['listener']['localAddress'], preflight['listener']['port']),
                  label+' original Unity child owns the exact endpoint released by the UDP preflight')
            save(label+'-lan-preflight.json', dict(preflight, gameBinding=binding, scope='same-host'))
        return entry
    def browser_launch_review(report, expected, label):
        driver=ROOT/'tests/browser/venue-launch-review-browser.cjs'
        output=out/(label+'-browser-review.json')
        completed=subprocess.run([shutil.which('node'),str(driver)],cwd=driver.parent,
            input=json.dumps({'base':uri,'token':keys['Master'],'reportPath':str(report),'expected':expected,'output':str(output)}),
            text=True,encoding='utf-8',capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        diagnostic=completed.stderr
        for key in keys.values():diagnostic=diagnostic.replace(key,'[redacted]')
        check(completed.returncode==0 and output.is_file(),label+' shipped Chromium reviews the original launcher file: '+diagnostic[-600:])
        return read(output)

    def launch_venue(states, linked, *, unlocked_mr=False, label=None):
        topology='Linked' if linked else 'Independent'
        label=label or ('unlocked-mr-venue' if unlocked_mr else topology.lower()+'-venue')
        plan_file=runtime/(label+'.json')
        work=runtime/(label+'-work')
        ready=out/(label+'-ready.json')
        report=out/(label+'-final.json')
        receipt_gate=None
        values=[]
        ports=set()
        for state in states:
            value=config(state['id'])
            while value['port'] in ports:
                value=config(state['id'])
            ports.add(value['port']);values.append(value)
        plan={'version':1,'controlInstance':str(venue_target),'topology':topology,'address':address,'listenAddress':address,
              'servers':[{'roomIds':state['roomIds'],'sessionId':state['id'],'port':value['port']} for state,value in zip(states,values,strict=True)]}
        def args_for(plan_file,work,ready):
            return ['--venue-run',plan_file,'--work',work,'--seconds','600','--ready-report',ready]
        if unlocked_mr:
            plan_file.write_text(json.dumps(plan),encoding='utf-8')
            if args.check_venue_preview:
                blocked=call('preview-unlocked-mr',['--venue-check',plan_file])
                check('校正鎖定' in read(blocked)['error'], 'The shared venue preview rejects an unlocked Linked MR plan')
            call(label,args_for(plan_file,work,ready),report=report)
            check('校正鎖定' in read(report)['error'] and not work.exists() and not ready.exists()
                  and request('/api/sessions/'+states[0]['id'])['combatStream'] is None,
                  'unlocked Linked MR venue cannot start or publish a game source')
            return []
        if not linked:
            if venue_pin:
                valid_profile = read(venue_target)
                for label_suffix, changes in [('wrong-pin', {'managementCertificateSha256': '0' * 64}),
                                              ('plaintext', {'managementApiUrl': uri}),
                                              ('wrong-role', {'gameServerKey': keys['Room1']})]:
                    case = 'https-profile-' + label_suffix
                    private_dir = runtime / case
                    private_dir.mkdir()
                    profile = private_dir / 'control-instance.json'
                    profile.write_text(json.dumps(dict(valid_profile, **changes)), encoding='utf-8')
                    rejected_plan = runtime / (case + '.json')
                    rejected_plan.write_text(json.dumps(dict(plan, controlInstance=str(profile))), encoding='utf-8')
                    empty_work, empty_ready = runtime / (case + '-work'), out / (case + '-ready.json')
                    call(case, args_for(rejected_plan, empty_work, empty_ready))
                    check(not empty_work.exists() and not empty_ready.exists()
                          and all(request('/api/sessions/' + row['id']) == row for row in states),
                          case + ' leaves all five original sessions untouched before native launch')
            stale=runtime/'venue-wrong-room.json'
            wrong=list(plan['servers']);wrong[0]={**wrong[0],'sessionId':wrong[1]['sessionId']}
            stale.write_text(json.dumps(dict(plan,servers=wrong)),encoding='utf-8')
            empty_work=runtime/'venue-rejected-work'
            empty_ready=out/'venue-rejected-ready.json'
            call('venue-wrong-room',args_for(stale,empty_work,empty_ready))
            if args.check_venue_preview:
                wrong_preview=call('preview-wrong-room',['--venue-check',stale])
                check('原場次與房間不符' in read(wrong_preview)['error'], 'The shared venue preview rejects a mismatched room assignment')
            plan_file.write_text(json.dumps(plan),encoding='utf-8')
            if args.check_venue_preview:
                legacy=read(call('preview-legacy-venue',['--venue-check',plan_file],good=True))
                check(legacy['topology']=='Independent'
                      and [(row['sessionId'],row['roomIds'],row['port']) for row in legacy['servers']]
                      ==[(row['sessionId'],row['roomIds'],row['port']) for row in plan['servers']]
                      and all('sessionSequence' not in row for row in legacy['servers']),
                      'legacy v1 plan retains its original successful preview and report shape')
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as occupied:
                occupied.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
                occupied.bind((address,values[-1]['port']))
                call('venue-occupied-port',args_for(plan_file,empty_work,empty_ready))
                if args.check_venue_preview:
                    busy_preview=call('preview-occupied-port',['--venue-check',plan_file])
                    check(f'房間 5 的 UDP 埠 {values[-1]["port"]}' in read(busy_preview)['error'],
                          'The shared venue preview identifies the unavailable original fifth-room port')
            check(not empty_work.exists() and not empty_ready.exists()
                  and all(request('/api/sessions/'+row['id'])['combatStream'] is None for row in states),
                  'wrong room assignment or occupied fifth UDP port rejects the entire venue before any server starts')
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CreateMutexW.argtypes=(ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p)
            kernel.CreateMutexW.restype=ctypes.c_void_p
            kernel.CloseHandle.argtypes=(ctypes.c_void_p,)
            kernel.ReleaseMutex.argtypes=(ctypes.c_void_p,)
            lock_name='Local\\VRCommand.Server.'+hashlib.sha256(f"{venue_uri or uri}/{states[-1]['id']}".encode()).hexdigest()
            ctypes.set_last_error(0)
            lease=kernel.CreateMutexW(None,True,lock_name)
            owns_lease=bool(lease) and ctypes.get_last_error()!=183
            try:
                check(owns_lease,'fixture reserves only the original fifth session launch lease')
                locked_work=runtime/'venue-session-locked'
                locked_report=call('venue-session-locked',args_for(plan_file,locked_work,empty_ready))
                locked=read(locked_report)
                check(locked['status']=='venue-incomplete' and not locked['readyPublished'] and not empty_ready.exists()
                      and not list(locked_work.iterdir()) and len(locked['servers'])==5
                      and all(row['result']['childPid'] is None and row['result']['cleanupCompleted'] for row in locked['servers'])
                      and all(request('/api/sessions/'+row['id'])['combatStream'] is None for row in states),
                      'one occupied session lease cancels all venue starts before any child or source is created')
            finally:
                if lease:
                    if owns_lease:
                        kernel.ReleaseMutex(lease)
                    kernel.CloseHandle(lease)
        if args.check_venue_plan_ui:
            driver=ROOT/'tests/browser/server-plan-browser.cjs'
            def download_plan(suffix):
                file=runtime/(label+suffix+'.json')
                completed=subprocess.run([shutil.which('node'),str(driver)],cwd=driver.parent,
                    input=json.dumps({'base':uri,'token':keys['Master'],'plan':plan,'output':str(file)}),
                    text=True,encoding='utf-8',capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
                diagnostic=completed.stderr
                for key in keys.values():diagnostic=diagnostic.replace(key,'[redacted]')
                check(completed.returncode==0 and read(file)==plan,label+suffix+' downloads exact session and mission revisions: '+diagnostic[-600:])
                return file
            def refresh_plan():
                plan['version']=4
                plan['servers']=[{**row,'sessionSequence':state['sequence'],'missionId':state['mission']['id']}
                                 for row,state in zip(plan['servers'],states,strict=True)]
            def advance_revision():
                state=states[-1]
                return request('/api/sessions/'+state['id']+'/commands',{'commandId':str(uuid.uuid4()),
                    'action':'SetEnvironment','expectedSequence':state['sequence'],'environment':state['environment']})['session']

            @contextmanager
            def revision_fixture(suffix, fault):
                catalog_reads=[]
                batch_requests=[]
                batch_path='/api/venue/combat-streams'
                class RevisionFixture(BaseHTTPRequestHandler):
                    def log_message(self, *args):pass
                    def authorized(self):
                        if self.headers.get('Authorization')=='Bearer '+keys['GameServer']:return True
                        self.send_error(403)
                        return False
                    def reply(self,status,body):
                        self.send_response(status)
                        self.send_header('Content-Type','application/json')
                        self.send_header('Content-Length',str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                    def do_GET(self):
                        if not self.authorized():return
                        if self.path=='/api/sessions':
                            if fault=='catalog' and len(catalog_reads)==1:advance_revision()
                            catalog_reads.append(self.path)
                        body,_=request(self.path,role='GameServer',raw_response=True)
                        self.reply(200,body)
                    def do_PUT(self):
                        if not self.authorized():return
                        length=int(self.headers.get('Content-Length','0'))
                        if (fault not in ('revision','unavailable') or self.path!=batch_path or not 0<length<=4096
                                or self.headers.get_content_type()!='application/json'):
                            self.send_error(400);return
                        body=self.rfile.read(length)
                        batch_requests.append((hashlib.sha256(body).hexdigest(),json.loads(body)))
                        if fault=='unavailable':
                            self.reply(503,b'');return
                        if len(batch_requests)!=1:
                            self.reply(409,b'');return
                        advance_revision()
                        rejected,_=request(self.path,body,role='GameServer',method='PUT',expected=409,
                                           raw_response=True,content_type='application/json')
                        self.reply(409,rejected)
                fixture_dir=runtime/(label+suffix+'-instance')
                fixture_dir.mkdir()
                marker=fixture_dir/'control-instance.json'
                shutil.copyfile(data/'operator-keys.json',fixture_dir/'operator-keys.json')
                file=runtime/(label+suffix+'-plan.json')
                with ThreadingHTTPServer(('127.0.0.1',0),RevisionFixture) as fixture:
                    marker.write_text(json.dumps(dict(read(data/'control-instance.json'),port=fixture.server_port)),encoding='utf-8')
                    file.write_text(json.dumps(dict(plan,controlInstance=str(marker))),encoding='utf-8')
                    thread=threading.Thread(target=fixture.serve_forever,daemon=True)
                    thread.start()
                    try:
                        yield file,catalog_reads,batch_requests
                    finally:
                        fixture.shutdown()
                        thread.join()

            refresh_plan()
            old_plan=download_plan('-browser-original')
            empty_work,empty_ready=runtime/(label+'-stale-work'),out/(label+'-stale-ready.json')
            if not linked:
                wrong_plan=runtime/(label+'-wrong-mission.json')
                wrong_plan.write_text(json.dumps(dict(plan,servers=[*plan['servers'][:-1],
                    {**plan['servers'][-1],'missionId':str(uuid.uuid4())}])),encoding='utf-8')
                wrong=read(call(label+'-wrong-mission',['--venue-check',wrong_plan]))
                check('房間 5' in wrong['error'] and '任務版本已變更' in wrong['error'],
                      'Guarded preview rejects a wrong mission at the original sequence')

                gate_work,gate_ready=runtime/(label+'-gate-work'),out/(label+'-gate-ready.json')
                with revision_fixture('-gate',fault='catalog') as (gate_plan,catalog_reads,_):
                    blocked=read(call(label+'-gate-stale',args_for(gate_plan,gate_work,gate_ready)))
                check(len(catalog_reads)==2 and '房間 5' in blocked['error'] and '場次序號' in blocked['error']
                      and not gate_ready.exists() and not list(gate_work.iterdir()),
                      'A real fifth-room edit at the final launch gate stops every worker before writing a native config')
                states[-1]=request('/api/sessions/'+states[-1]['id'])
                refresh_plan()
                download_plan('-browser-before-batch')
            source_work,source_ready=runtime/(label+'-source-work'),out/(label+'-source-ready.json')
            with revision_fixture('-source',fault='revision') as (source_plan,catalog_reads,batch_requests):
                blocked=read(call(label+'-source-stale',args_for(source_plan,source_work,source_ready)))
            check(len(catalog_reads)==2 and len(batch_requests)==1 and blocked['sourceAttachment']=='rejected'
                  and not blocked['sourceAttachmentRetried']
                  and 'HTTP 409' in blocked['sourceAttachmentError'] and not source_ready.exists()
                  and blocked['endpointPublication']=='not-attempted' and not blocked['readyPublished'],
                  label+' original launcher observes rejection before any venue readiness or endpoint announcement')
            batch=batch_requests[0][1]
            check(batch['topology']==topology and batch['launchId']==blocked['venueLaunchId']
                  and [(row['sessionId'],row['expectedSequence']) for row in batch['servers']]
                  ==[(state['id'],state['sequence']) for state in states],
                  label+' late request reached the API with every exact original candidate and revision')
            for entry,candidate,state in zip(blocked['servers'],batch['servers'],states,strict=True):
                result=entry['result']
                folder=source_work/('linked' if linked else f"room-{state['roomIds'][0]:02}")
                boot_log=(folder/'server.log').read_text(encoding='utf-8',errors='replace')
                check(result['sessionId']==state['id'] and result['childPid'] and result['childExited'] and result['cleanupCompleted']
                      and result['udpBinding'] is None and 'VR_NETWORK_STARTED' not in boot_log
                      and f"VR_VENUE_STREAM_CANDIDATE stream={candidate['streamId']}" in boot_log,
                      label+f" rooms {state['roomIds']} prepared the original journal but exited without opening UDP")
                request('/api/sessions/'+state['id']+'/connection-endpoint',expected=404)
            check(all(request('/api/sessions/'+state['id'])==state for state in states[:-1]),
                  label+' batch rejection leaves every unchanged room at its exact original unbound state')
            updated=request('/api/sessions/'+states[-1]['id'])
            check(updated['id']==states[-1]['id'] and updated['sequence']==states[-1]['sequence']+1
                  and updated['state']=='Preparing' and updated['combatStream'] is None,
                  label+' original session remains launchable with a newer configuration revision')
            states[-1]=updated
            stale_preview=read(call(label+'-stale-preview',['--venue-check',old_plan]))
            stale_run=read(call(label+'-stale-run',args_for(old_plan,empty_work,empty_ready)))
            check(all('場次序號' in result['error'] and '重新讀取並下載' in result['error'] for result in (stale_preview,stale_run))
                  and not empty_work.exists() and not empty_ready.exists()
                  and all(request('/api/sessions/'+state['id'])==state for state in states),
                  label+' stale downloaded plan cannot start a child, bind a source or alter any room')
            refresh_plan()
            if args.check_venue_receipt_retry and label in ('independent-venue','linked-venue'):
                if not linked:
                    outage_work,outage_ready=runtime/(label+'-outage-work'),out/(label+'-outage-ready.json')
                    with revision_fixture('-outage',fault='unavailable') as (outage_plan,_,attempts):
                        outage=read(call(label+'-receipt-unavailable',args_for(outage_plan,outage_work,outage_ready)))
                    check(len(attempts)==2 and attempts[0][0]==attempts[1][0] and outage['sourceAttachmentRetried']
                          and outage['sourceAttachment']=='unconfirmed' and 'HTTP 503' in outage['sourceAttachmentError']
                          and outage['endpointPublication']=='not-attempted' and not outage_ready.exists()
                          and len(outage['servers'])==5
                          and all(row['result']['childExited'] and row['result']['cleanupCompleted'] for row in outage['servers'])
                          and all(request('/api/sessions/'+state['id'])==state for state in states),
                          'Two unavailable replies stop all five original children after exactly one byte-identical retry')
                    if args.check_venue_launch_review:
                        observed=browser_launch_review(out/(label+'-receipt-unavailable.json'),
                            [{'sessionId':state['id'],'roomIds':state['roomIds'],'phase':'Preparing','sourceState':'unbound',
                              'endpointState':'not-checked'} for state in states],label+'-unbound')
                        check(observed['launchId']==outage['venueLaunchId']
                              and all(request('/api/sessions/'+state['id'])==state for state in states),
                              'Original unbound launch review leaves all five management histories untouched')
                gate_class=module('venue_receipt_fault_gate','venue_http_gate.py').VenueReceiptGate
                receipt_gate=gate_class(uri,[state['id'] for state in states]).start()
                receipt_gates.append(receipt_gate)
                private=runtime/(label+'-receipt-instance')
                private.mkdir()
                marker=private/'control-instance.json'
                shutil.copyfile(data/'operator-keys.json',private/'operator-keys.json')
                marker.write_text(json.dumps(dict(read(data/'control-instance.json'),port=receipt_gate.server.server_port)),encoding='utf-8')
                plan['controlInstance']=str(marker)
            plan_file=download_plan('-browser-plan')
            if not linked and args.check_venue_preview:
                previous=runtime/(label+'-previous-plan.json')
                previous.write_text(json.dumps(dict(plan,version=2)),encoding='utf-8')
                result=read(call(label+'-v2-preview',['--venue-check',previous],good=True))
                check([row['sessionSequence'] for row in result['servers']]==[state['sequence'] for state in states],
                      'Existing v2 plans still preview the exact revisions with the guarded packages')
        else:
            plan_file.write_text(json.dumps(dict(plan,servers=list(reversed(plan['servers'])))),encoding='utf-8')
        udp_pairs = []
        if args.check_venue_preview:
            preview=call(label+'-preview',['--venue-check',plan_file],good=True)
            actual=read(preview)
            expected=[{**plan_row,'missionId':state['mission']['id'],'missionName':state['mission']['definition']['name'],
                       'experienceMode':state['environment']['mode'],'address':address,'listenAddress':address}
                      for plan_row,state in zip(plan['servers'],states,strict=True)]
            check(actual=={'schemaVersion':1,'status':'venue-checked','complete':True,'topology':topology,
                           'instanceId':read(data/'control-instance.json')['instanceId'],'servers':expected}
                  and not work.exists() and not ready.exists()
                  and all(request('/api/sessions/'+row['id'])==row for row in states),
                  label+' shared preview lists exact original rooms, missions and UDP without modifying any session or publishing readiness')
            if args.check_venue_udp_readiness:
                udp_pairs = venue_udp_readiness(label, topology, states, values, plan_file, preview)
        if venue_pin:
            listed = read(call(label + '-https-catalog', ['--catalog', venue_target], good=True))
            check(listed['instanceId'] == read(venue_target)['instanceId']
                  and [(row['id'], row['roomIds']) for row in listed['sessions']] == [(row['id'], row['roomIds']) for row in states],
                  label + ' pinned HTTPS catalog returns the exact original venue rooms')
        extra=['--peer-diagnostics','on'] if args.peer_diagnostics else []
        process=subprocess.Popen([str(exe),*map(str,args_for(plan_file,work,ready)),'--report',str(report),*extra],cwd=out,env=env)
        entries=[]
        for index,(state,value) in enumerate(zip(states,values,strict=True)):
            name='linked' if linked else f"room-{state['roomIds'][0]:02}"
            entry_label=('linked' if label=='linked-venue' else label) if linked else f'room-{index+1}'
            entry={'process':process,'readyPath':ready,'reportPath':report,'work':work/name,'config':value,'label':entry_label,
                   'sessionId':state['id'],'witness':None,'peerDiagnostics':args.peer_diagnostics,'venueIndex':index}
            runners.append(entry);entries.append(entry)
        def is_ready():
            if process.poll() is not None:raise RuntimeError('Venue launcher exited before all sources were ready')
            return read(ready) if ready.exists() else None
        witness=wait(is_ready,120,label+' ready')
        check(witness['status']=='venue-ready' and witness['topology']==topology and witness['instanceId']==read(data/'control-instance.json')['instanceId']
              and [(row['roomIds'],row['ready']['sessionId'],row['ready']['port']) for row in witness['servers']]
                  ==[(state['roomIds'],state['id'],value['port']) for state,value in zip(states,values,strict=True)]
              and len({row['ready']['childPid'] for row in witness['servers']})==len(states)
              and all(Path(row['ready']['workDirectory'])==entry['work'] for entry,row in zip(entries,witness['servers'],strict=True)),
              label+' confirms the exact game processes, sorted original rooms and UDP bindings')
        for entry,state,row in zip(entries,states,witness['servers'],strict=True):
            confirm_launch(entry,state,row['ready'])
        if udp_pairs:
            checks = []
            for state, pair, row in zip(states, udp_pairs, witness['servers'], strict=True):
                binding = row['ready']['udpBinding']
                summary, _ = field.verify_udp_preflight((out / pair['listener'], out / pair['probe']),
                                                         binding, {ipaddress.IPv4Address(address)})
                checks.append({'roomIds': state['roomIds'], 'sessionId': state['id'], 'binding': binding, 'pair': summary})
            save(label + '-udp-game-bindings.json', checks)
            check(len(checks) == len(values), label + ' each original pair re-verifies against the actual Unity bind time and port')
        if args.check_venue_plan_ui:
            sources=[request('/api/sessions/'+state['id'])['combatStream'] for state in states]
            launch_ids={source['venueLaunchId'] for source in sources}
            check(len(launch_ids)==1 and uuid.UUID(launch_ids.pop()).int!=0
                  and [source['expectedSequence'] for source in sources]==[state['sequence'] for state in states],
                  label+' every original Unity source is durably bound to the same launch ID and reviewed sequences')
        if receipt_gate:
            receipts=receipt_gate.receipt_snapshot()
            for route,attempts in receipts.items():
                check(len(attempts)==2 and [row['upstreamStatus'] for row in attempts]==[200,200]
                      and [row['deliveredStatus'] for row in attempts]==[502,200]
                      and len({row['requestSha256'] for row in attempts})==1
                      and len({row['receiptSha256'] for row in attempts})==1,
                      label+' confirms original committed '+route+' after one byte-identical retry and matching receipt')
            save(label+'-receipt-gate.json',receipts)
            for entry in entries:entry['receiptRetried']=True
        if venue_pin:
            generated = [read(entry['work'] / 'server-config.json') for entry in entries]
            check(all(value['managementApiUrl'] == venue_uri and value['managementCertificateSha256'] == venue_pin
                      and value['gameServerKey'] == keys['GameServer'] and value['sessionId'] == state['id']
                      for value, state in zip(generated, states, strict=True)),
                  label + ' passes the original HTTPS target and pin to each native process')
        if args.check_venue_endpoint_batch:
            endpoint_route='/api/venue/connection-endpoints'
            originals=[request('/api/sessions/'+state['id']+'/connection-endpoint') for state in states]
            targets=[{'sessionId':row['sessionId'],'endpoint':{key:row[key] for key in ('version','streamId','address','port')}}
                     for row in reversed(originals)]
            batch={'version':1,'topology':topology,'servers':targets}
            request(endpoint_route,batch,'Room1',method='PUT',expected=403)
            request(endpoint_route,dict(batch,servers=targets[:-1]),'GameServer',method='PUT',expected=400)
            changed=list(targets)
            changed[0]=dict(changed[0],endpoint=dict(changed[0]['endpoint'],streamId=str(uuid.uuid4())))
            request(endpoint_route,dict(batch,servers=changed),'GameServer',method='PUT',expected=409)
            repeated=request(endpoint_route,batch,'GameServer',method='PUT')
            check(repeated=={'version':1,'topology':topology,'servers':originals}
                  and len({row['createdAtUtc'] for row in originals})==1,
                  label+' whole-batch retry returns the exact sorted, simultaneously committed endpoints')
            save(label+'-endpoint-batch.json',repeated)
        return entries

    def review_lost_endpoint():
        state=create(list(range(1,6)),'launch review after both endpoint replies are lost')
        session_id=state['id']
        session_path='/api/sessions/'+session_id
        target=config(session_id)
        gate_class=module('venue_review_fault_gate','venue_http_gate.py').VenueReceiptGate
        gate=gate_class(uri,[session_id],endpoint_losses=2).start()
        receipt_gates.append(gate)
        private=runtime/'lost-endpoint-instance'
        private.mkdir()
        marker=private/'control-instance.json'
        shutil.copyfile(data/'operator-keys.json',private/'operator-keys.json')
        marker.write_text(json.dumps(dict(read(data/'control-instance.json'),port=gate.server.server_port)),encoding='utf-8')
        plan=runtime/'lost-endpoint-plan.json'
        plan.write_text(json.dumps({'version':4,'controlInstance':str(marker),'topology':'Linked','address':address,
            'listenAddress':'0.0.0.0','servers':[{'roomIds':state['roomIds'],'sessionId':session_id,'sessionSequence':state['sequence'],
                                               'missionId':state['mission']['id'],'port':target['port']}]}),encoding='utf-8')
        work=runtime/'lost-endpoint-work'
        ready=out/'lost-endpoint-ready.json'
        file=call('lost-endpoint-launch',['--venue-run',plan,'--work',work,'--seconds','60','--ready-report',ready])
        result=read(file)
        receipts=gate.receipt_snapshot()[gate.endpoint_route]
        child=result['servers'][0]['result']
        check(len(receipts)==2 and all(row['upstreamStatus']==200 and row['deliveredStatus']==502 for row in receipts)
              and len({row['requestSha256'] for row in receipts})==len({row['receiptSha256'] for row in receipts})==1
              and result['sourceAttachment']=='confirmed' and result['endpointPublication']=='unconfirmed'
              and result['endpointPublicationRetried'] and child['childExited'] and child['cleanupCompleted'] and not ready.exists(),
              'The original Linked launcher stops after both successful endpoint receipts are lost')
        before=request(session_path)
        endpoint=request(session_path+'/connection-endpoint')
        row={'sessionId':session_id,'roomIds':state['roomIds'],'streamId':child['streamId'],
             'udp':{'bindAddress':child['udpBinding']['address'],'port':child['udpBinding']['port']}}
        inquiry={'version':1,'instanceId':result['instanceId'],'launchId':result['venueLaunchId'],'topology':'Linked','servers':[row]}
        def stale_source():
            value=request('/api/venue/server-launch-review',inquiry)
            return value if value['servers'][0]['recentSource'] is False else None
        wait(stale_source,15,'original stopped source ages out')
        observed=browser_launch_review(file,[{'sessionId':session_id,'roomIds':state['roomIds'],'phase':'Preparing',
            'sourceState':'original-source','streamId':endpoint['streamId'],'endpointState':'published','endpointAddress':address,
            'endpointPort':endpoint['port'],'addressMatched':None,'recentSource':False}],'lost-endpoint')
        wrong={**row,'udp':{'bindAddress':'0.0.0.0','port':1024 if endpoint['port']!=1024 else 1025}}
        mismatch=request('/api/venue/server-launch-review',{**inquiry,'servers':[wrong]})
        check(observed['launchId']==result['venueLaunchId'] and child['udpBinding']['address']=='0.0.0.0'
              and mismatch['servers'][0]['endpointState']=='endpoint-mismatch'
              and request(session_path)==before and request(session_path+'/connection-endpoint')==endpoint,
              'Launch review checks the original endpoint, keeps wildcard address distinct, and writes no management state')
        command(session_id,'End')

    def reject_last_venue_endpoint():
        states=[create([room],f'venue endpoint rollback room {room}') for room in range(1,6)]
        ids=[state['id'] for state in states]
        ports=[]
        while len(ports)<5:
            port=free(socket.SOCK_DGRAM,address)
            if port not in ports:ports.append(port)
        plan=runtime/'venue-endpoint-rollback.json'
        plan.write_text(json.dumps({'version':1,'controlInstance':str(venue_target),'topology':'Independent',
            'address':address,'listenAddress':address,'servers':[{'roomIds':state['roomIds'],'sessionId':state['id'],'port':port}
                for state,port in zip(states,ports,strict=True)]}),encoding='utf-8')
        work=runtime/'venue-endpoint-rollback-work'
        ready=out/'venue-endpoint-rollback-ready.json'
        report=out/'venue-endpoint-rollback-final.json'
        database=(data/'sessions/worlds.db').resolve(strict=True)
        with closing(sqlite3.connect(database.as_uri()+'?mode=rw',uri=True,timeout=10)) as db, db:
            db.execute(f"""CREATE TRIGGER fixture_reject_fifth_endpoint BEFORE INSERT ON connection_endpoints
                WHEN NEW.session = '{uuid.UUID(ids[-1])}' BEGIN SELECT RAISE(ABORT, 'fixture endpoint rejection'); END""")
        try:
            with subprocess.Popen([str(exe),'--venue-run',str(plan),'--work',str(work),'--seconds','60',
                '--ready-report',str(ready),'--report',str(report)],cwd=out,env=env) as process:
                try: code=process.wait(timeout=120)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=15);raise
            value=read(report)
            rows=[row['result'] for row in value['servers']]
            check(code==1 and value['status']=='venue-incomplete' and not value['complete'] and not value['readyPublished']
                  and value['endpointPublication']=='unconfirmed' and 'HTTP 500' in value['publicationError'] and not ready.exists(),
                  'A real last-room SQLite insert rejection prevents publication and a successful venue report')
            check([row['sessionId'] for row in rows]==ids and len({row['childPid'] for row in rows})==5
                  and all(row['childPid']>0 and row['childExited'] and row['cleanupCompleted'] and not row['complete']
                          and row['udpBinding']['processId']==row['childPid'] for row in rows),
                  'All five original native processes and UDP bindings existed, then the launcher stopped its own children')
            for row in rows:
                route='/api/sessions/'+row['sessionId']
                request(route+'/connection-endpoint',expected=404)
                current=request(route)
                check(current['state']=='Preparing' and current['combatStream']['streamId']==row['streamId']
                      and request(route+'/world')['header']['streamId']==row['streamId'],
                      'Rolled-back room preserves the original Preparing source with no advertised endpoint')
            check(all('endpoint' not in room for room in request('/api/rooms/readiness')['rooms']),
                  'The control-room overview advertises none of the five rejected endpoints')
            for session in ids:command(session,'End')
        finally:
            with closing(sqlite3.connect(database.as_uri()+'?mode=rw',uri=True,timeout=10)) as db, db:
                db.execute('DROP TRIGGER fixture_reject_fifth_endpoint')
    def player(entry,room):
        state=request('/api/sessions/'+entry['sessionId']+'/players',{'playerId':str(uuid.uuid4()),'roomId':room,'name':'Portable server room '+str(room),'headset':'Quest3'},role='Room'+str(room));person=next(x for x in state['players'] if x['roomId']==room)
        invitation=request('/api/sessions/'+state['id']+'/players/'+person['id']+'/join-ticket',{},role='Room'+str(room),admission=person['admissionId']);file=runtime/(entry['label']+'-client-'+str(room)+'.json');file.write_text(json.dumps({'role':'Client','address':address,'port':entry['ready']['port'],'joinTicket':invitation['ticket']}),encoding='utf-8');log=runtime/(file.stem+'.log')
        child=subprocess.Popen([str(folder/'Runtime/VrCommand.exe'),'-batchmode','-nographics','-job-worker-count','2','-logFile',str(log),'--vr-config',str(file)],cwd=runtime,env=env,creationflags=subprocess.CREATE_NO_WINDOW);client={'process':child,'log':log,'player':person,'sessionId':state['id']};clients.append(client);return client
    def prepare_room_roster(entry,room,count=5):
        path='/api/sessions/'+entry['sessionId']
        role='Room'+str(room)
        for seat in range(1,count+1):
            headset = 'ViveXr' if args.check_quest_vr_partial_map and seat in (2, 4) else 'Quest3'
            state=request(path+'/players',{'playerId':str(uuid.uuid4()),'roomId':room,
                'name':f'Portable room {room} seat {seat}','headset':headset},role=role)
        return sorted((p for p in state['players'] if p['roomId']==room),key=lambda p:p['seat'])

    def verify_stale_ticket_source():
        state=create(list(range(1,6)), 'managed ticket-source interruption')
        route='/api/sessions/'+state['id']
        entry,=launch_venue([state],True,label='stale-ticket-venue')
        people={room:prepare_room_roster(entry,room) for room in range(1,6)}
        def live_preview():
            preview=request('/api/vr-deployment/venue')
            return preview if preview['ready'] else None
        live=wait(live_preview,12,'current managed ticket source')
        endpoint=request(route+'/connection-endpoint')
        before=request(route+'/world')
        room_tickets=lambda room:[{'playerId':person['id'],'admissionId':person['admissionId']} for person in people[room]]
        venue_body={'topology':'Linked','rooms':[{'roomId':room,'sessionId':state['id'],
                    'streamId':endpoint['streamId'],'players':room_tickets(room)} for room in range(1,6)]}
        room_body={'address':endpoint['address'],'port':endpoint['port'],'players':room_tickets(1)}
        first=people[1][0]
        player_path=route+'/players/'+first['id']+'/join-ticket'
        bundle_path=route+'/rooms/1/join-ticket-bundle'
        venue_path='/api/vr-deployment/venue-bundle'
        original=request(player_path,{},'Room1',admission=first['admissionId'])
        room_zip,_=request(bundle_path,room_body,'Room1',raw_response=True)
        venue_zip,_=request(venue_path,venue_body,raw_response=True)
        with zipfile.ZipFile(io.BytesIO(room_zip)) as archive:
            assert len(archive.namelist())==5 and archive.testzip() is None
        with zipfile.ZipFile(io.BytesIO(venue_zip)) as archive:
            assert len(archive.namelist())==6 and archive.testzip() is None
        check(all(row['problem'] is None for row in live['rooms'])
              and all(row['ticketSourceLive'] for row in request('/api/rooms/readiness')['rooms']),
              'Live managed native source issues one player ticket, one room ZIP and all five rooms')
        def blocked():
            preview=request('/api/vr-deployment/venue')
            return preview if not preview['ready'] and all(row['problem']=='vr-venue-endpoint-stale' for row in preview['rooms']) else None
        if args.check_venue_ticket_recovery:
            opened=out/'ticket-recovery-browser-open.request'
            paused=out/'ticket-recovery-browser-blocked.request'
            descriptor=runtime/'ticket-recovery-private.json'
            downloaded=runtime/'ticket-recovery-venue.zip'
            output=out/'ticket-recovery-browser.json'
            descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'mode':'Linked',
                'recovery':{'ready':str(opened),'blocked':str(paused)}}),encoding='utf-8')
            driver=ROOT/'tests/browser/check-vr-venue-tickets-native.cjs'
            with (out/'ticket-recovery-browser.log').open('xb') as log:
                browser=subprocess.Popen([shutil.which('node'),str(driver),str(descriptor),str(downloaded),str(output)],
                    stdout=log,stderr=subprocess.STDOUT)
                try:
                    def marker(path):
                        if browser.poll() is not None:raise RuntimeError('Original recovery browser exited early')
                        return path.is_file()
                    wait(lambda:marker(opened),25,'live preview opens in the original Chromium')
                    with hold_owned_unity_threads(entry['witness'],entry['ready']['childPid']) as thread_count:
                        held=wait(blocked,12,'the held native source expires')
                        held_world=request(route+'/world')
                        check(request(venue_path,venue_body,expected=409)['code']=='vr-venue-endpoint-stale',
                              'Temporary native hold blocks the original venue request')
                        wait(lambda:marker(paused),12,'original Chromium observes the same preview blocked')
                    restored=wait(live_preview,18,'the same native source resumes publication')
                    resumed_world=request(route+'/world')
                    check(restored['rooms']==live['rooms'] and resumed_world['header']==held_world['header']
                          and resumed_world['acceptedSequence']>held_world['acceptedSequence']
                          and entry['witness'].kernel.WaitForSingleObject(entry['witness'].handle,0)==258
                          and request(route+'/connection-endpoint')==endpoint,
                          'Resumed original Unity handle advances the same stream without changing endpoints or admissions')
                    check(browser.wait(timeout=35)==0 and read(output)['recoveredSamePreview'] and downloaded.is_file(),
                          'One existing Chromium preview automatically reopens the same original venue and downloads its tickets')
                    with zipfile.ZipFile(downloaded) as archive:
                        check(archive.testzip() is None and len(archive.namelist())==6,'Recovered browser download contains all five original rooms')
                    save('ticket-recovery-native.json',{'threadCount':thread_count,'held':held,'heldWorld':held_world,
                        'restored':restored,'resumedWorld':resumed_world})
                finally:
                    if browser.poll() is None:browser.terminate();browser.wait(timeout=10)
        entry['process'].kill();entry['process'].wait(timeout=10)
        handle=entry['witness']
        check(handle.kernel.WaitForSingleObject(handle.handle,15000)==0,'Managed source crash stops the exact original Unity process')
        handle.close();entry['witness']=None
        stale=wait(blocked,12,'managed capture freshness expires after the original source stops')
        check(request(player_path,{},'Room1',admission=first['admissionId'],expected=409)['code']=='ticket-source-unavailable'
              and request(bundle_path,room_body,'Room1',expected=409)['code']=='ticket-source-unavailable'
              and request(venue_path,venue_body,expected=409)['code']=='vr-venue-endpoint-stale',
              'Stale managed source rejects fresh individual, room and venue tickets')
        cards=request('/api/rooms/readiness')['rooms']
        world_after=request(route+'/world')
        check(all(row['endpoint']==endpoint and row['ticketSourceLive'] is False for row in cards)
              and request(route+'/connection-endpoint')==endpoint
              and world_after['header']==before['header'] and world_after['acceptedSequence']>=before['acceptedSequence']
              and request('/api/player-tickets/validate',{'ticket':original['ticket'],'sessionId':state['id'],
                  'protocolVersion':2},'GameServer')['admissionId']==first['admissionId'],
              'Original endpoint, saved world and already issued admission remain readable while issuance is blocked')
        if args.check_windows_venue_staging:
            original_zip = runtime/'stale-ticket-windows.zip'
            original_zip.write_bytes(venue_zip)
            seat_map = runtime/'stale-ticket-windows-map.json'
            seat_map.write_text(json.dumps({'version': 1, 'seats': [{'roomId': 1, 'seat': 2, 'station': 'PC-A'}]}),
                                encoding='utf-8')
            delivery = runtime/'stale-ticket-windows-delivery'
            result = subprocess.run([shutil.which('pwsh'), '-NoProfile', '-File', str(ROOT/'scripts/deploy-quest.ps1'),
                '-VenueBundle', str(original_zip), '-ManagementApi', uri, '-WindowsSeatMap', str(seat_map),
                '-WindowsOutputDirectory', str(delivery)], env={**os.environ, 'VR_COMMAND_MASTER_KEY': keys['Master']},
                capture_output=True, encoding='utf-8', timeout=25)
            check(result.returncode == 1 and 'Room 1 seat 2: source-stale' in result.stderr
                  and not result.stdout.strip() and not delivery.exists() and not list(runtime.glob('.vr-windows-*')),
                  'Stale original native source blocks Windows export of the already issued VIVE seat')
        descriptor=runtime/'stale-ticket-browser-private.json'
        output=out/'stale-ticket-browser.json'
        descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'mode':'Linked','expectStale':True,
            'expectedEndpoints':[{'roomId':room,'address':endpoint['address'],'port':endpoint['port']} for room in range(1,6)]}),encoding='utf-8')
        no_zip=runtime/'stale-ticket-must-not-download.zip'
        driver=ROOT/'tests/browser/check-vr-venue-tickets-native.cjs'
        with (out/'stale-ticket-browser.log').open('xb') as log:
            subprocess.run([shutil.which('node'),str(driver),str(descriptor),str(no_zip),str(output)],
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=45)
        check(read(output)['blocked'] and read(output)['verifiedRoomEndpoints']==5 and not no_zip.exists(),
              'Shipped Chromium shows the stale source on all five cards and disables the venue download')
        save('stale-ticket-native.json',{'live':live,'stale':stale,'cards':cards,'world':world_after})
        command(state['id'],'End')
    def room_players(entry,room,people=None,raw=None,*,windows_files=None):
        path='/api/sessions/'+entry['sessionId']
        role='Room'+str(room)
        if people is None: people=prepare_room_roster(entry,room,players_per_room)
        names=[f'room-{room:02}-seat-{seat:02}.json' for seat in range(1,len(people)+1)]
        destination={'address':address,'port':entry['ready']['port']}
        if raw is None:
            raw,headers=request(path+f'/rooms/{room}/join-ticket-bundle',
                dict(destination,players=[{'playerId':p['id'],'admissionId':p['admissionId']} for p in people]),
                role=role,raw_response=True)
            check(headers.get_content_type()=='application/zip' and headers['Cache-Control']=='no-store',
                entry['label']+f' room {room} no-store ticket download')
        directory=runtime/(entry['label']+f'-bundle-{room}')
        directory.mkdir()
        (directory/'download.zip').write_bytes(raw)
        prepared=[]
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            check(archive.namelist()==names and [p['seat'] for p in people]==list(range(len(people))),
                entry['label']+f' room {room} exact {len(people)} seats')
            for name,person in zip(names,people,strict=True):
                content=archive.read(name)
                value=json.loads(content)
                if value!={'role':'Client',**destination,'joinTicket':value.get('joinTicket')} or not value['joinTicket']:
                    raise ValueError('Player connection file differs from the advertised endpoint')
                file = (windows_files or {}).get((room, person['seat'] + 1))
                if file is None:
                    file = directory/name
                    file.write_bytes(content)
                elif file.read_bytes() != content:
                    raise ValueError('Windows staging changed the original connection file')
                prepared.append((person,file))
        launched=[]
        for person,file in prepared:
            mock=None
            if args.check_venue_openxr and (room,person['seat'])==(5,1):
                tracking_loss=runtime/(entry['label']+'-openxr-loss.request')
                mock=openxr_environment(entry['label']+'-openxr-runtime.json',tracking_loss)
                entry['openxrLossMarker']=tracking_loss
                entry['openxrPlayerId']=person['id']
                if args.check_venue_openxr_reconnect:
                    controls = {}
                    for name in ('reconnect', 'trigger'):
                        command_file = runtime / (entry['label'] + '-openxr-' + name + '.request')
                        ack_file = command_file.with_suffix('.ack')
                        command_file.write_text('0', encoding='ascii')
                        controls[name] = (command_file, ack_file)
                        mock['VR_COMMAND_OPENXR_' + name.upper() + '_COMMAND'] = str(command_file)
                        mock['VR_COMMAND_OPENXR_' + name.upper() + '_ACK'] = str(ack_file)
                    udp = module('venue_reconnect_udp', 'udp_gate.py')
                    gate = udp.LoopbackGate(entry['ready']['port'], lambda: False, local_address=address).start()
                    reconnect_gates.append(gate)
                    original_file = file
                    content = read(file)
                    file = file.with_stem(file.stem + '-relay')
                    file.write_text(json.dumps(dict(content, port=gate.port)), encoding='ascii')
                    entry['openxrReconnect'] = {'gate':gate, 'controls':controls, 'originalFile':original_file,
                                                'originalHash':package.digest(original_file)}
            launched.append(packaged_player(entry,person,file,mock=mock))
        return launched

    def room_endpoint_descriptor(preview):
        if not args.check_room_endpoints: return {}
        rows = request('/api/rooms/readiness')['rooms']
        endpoints = {row['roomId']: row['endpoint'] for row in preview['rooms']}
        check({row['roomId']: row['endpoint'] for row in rows} == endpoints
              and all([(row['roomId'], row['endpoint']) for row in request('/api/rooms/readiness', role=f'Room{room}')['rooms']]
                      == [(room, endpoint)] for room, endpoint in endpoints.items()),
              'master and room desks receive only their original published UDP endpoints')
        return {'expectedEndpoints': [{'roomId': room, 'address': endpoint['address'], 'port': endpoint['port']}
                                      for room, endpoint in endpoints.items()]}

    def venue_ticket_players(staged, linked):
        mode = 'Linked' if linked else 'Independent'
        label = mode.lower()
        preview = request('/api/vr-deployment/venue')
        check(preview['ready'] and preview['topology'] == mode
              and all(row['roomId'] == room and row['sessionId'] == entry['sessionId']
                      and (row['endpoint']['address'], row['endpoint']['port'], row['endpoint']['streamId'])
                      == (address, entry['ready']['port'], entry['ready']['streamId'])
                      and [seat['admissionId'] for seat in row['seats']] == [person['admissionId'] for person in people]
                      for row, (entry, room, people) in zip(preview['rooms'], staged, strict=True)),
              mode+' venue previews all current admissions on their original native UDP endpoints')
        node = shutil.which('node')
        if not node: raise RuntimeError('Node is required for the shipped venue ticket test')
        descriptor = runtime / (label+'-venue-tickets-private.json')
        archive_path = runtime / (label+'-vr-venue-connections.zip')
        output = out / (label+'-vr-venue-tickets-ui.json')
        descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'mode':mode,**room_endpoint_descriptor(preview)}),encoding='utf-8')
        with (out/(label+'-vr-venue-tickets-ui.log')).open('xb') as log:
            subprocess.run([node, str(ROOT/'tests/browser/check-vr-venue-tickets-native.cjs'), str(descriptor),
                            str(archive_path), str(output)], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=65)
        if args.check_room_endpoints:
            check(read(output)['verifiedRoomEndpoints'] == 5, mode+' shipped room cards show five original UDP endpoints')
        files = []
        with zipfile.ZipFile(archive_path) as archive:
            manifest = json.loads(archive.read('venue.json'))
            expected = [{'roomId':room,'sessionId':entry['sessionId'],'address':address,'port':entry['ready']['port'],
                         'ticketsZip':f'room-{room:02}-connections.zip',
                         'seats':[{'seat':person['seat']+1,'name':person['name']} for person in people]}
                        for entry,room,people in staged]
            check(read(output)['complete'] and manifest == {'version':1,'mode':'VR','topology':mode,'rooms':expected}
                  and archive.namelist() == ['venue.json', *[row['ticketsZip'] for row in expected]]
                  and archive.testzip() is None, mode+' shipped browser ZIP includes the five original rooms and no other files')
            files = [archive.read(row['ticketsZip']) for row in expected]
        if args.check_vr_seat_files:
            before = request('/api/sessions')
            verified = []
            for (entry, room, people), raw in zip(staged, files, strict=True):
                with zipfile.ZipFile(io.BytesIO(raw)) as seats:
                    for person in people:
                        seat = person['seat']
                        file = seats.read(f'room-{room:02}-seat-{seat+1:02}.json')
                        route = f"/api/sessions/{entry['sessionId']}/rooms/{room}/players/{person['id']}/vr-connection-check"
                        reply, headers = request(route, {'connectionFile': base64.b64encode(file).decode()},
                                                 role=f'Room{room}', admission=person['admissionId'], raw_response=True)
                        result = json.loads(reply)
                        assert result['status'] == 'matched' and (result['roomId'], result['seat']) == (room, seat)
                        assert (result['address'], result['port']) == (address, entry['ready']['port'])
                        assert result['expiresAtUtc'] and headers['Cache-Control'] == 'no-store'
                        if room == 1 and seat == 0:
                            altered = dict(json.loads(file), port=1024 if result['port'] != 1024 else 1025)
                            mismatch = request(route, {'connectionFile': base64.b64encode(json.dumps(altered).encode()).decode()},
                                               role='Room1', admission=person['admissionId'])
                            check(mismatch['status'] == 'endpoint-mismatch' and mismatch['port'] == result['port'],
                                  mode+' native seat file check diagnoses a modified port')
                        verified.append(result)
            check(len(verified) == 25 and request('/api/sessions') == before,
                  mode+' exact original 25 VR seat files match their current live native endpoints without changing the roster')
            save(f'{label}-vr-seat-file-checks.json', verified)
        windows_files = {}
        if args.check_quest_vr_deploy or args.check_quest_vr_partial_map:
            before = request('/api/sessions')
            pwsh = shutil.which('pwsh')
            if not pwsh: raise RuntimeError('PowerShell is required for the Quest deployment check')
            deploy = [pwsh, '-NoProfile', '-File', str(ROOT/'scripts/deploy-quest.ps1'),
                      '-VenueBundle', str(archive_path), '-ManagementApi', uri]
            environment = {**os.environ, 'VR_COMMAND_MASTER_KEY': keys['Master']}
            with tempfile.TemporaryDirectory(prefix='quest-vr-', dir=runtime) as scratch:
                destination = Path(scratch).resolve()
                if destination.parent != runtime: raise RuntimeError('Invalid owned deployment scratch directory')
                sample = '1' if args.check_quest_vr_partial_map else '2'
                seat = json.loads(subprocess.check_output([*deploy, '-RoomId', '4', '-Seat', sample, '-CheckOnly'],
                    env=environment, timeout=25, encoding='utf-8', cwd=destination))
                check(seat['roomId']==4 and seat['seat']==int(sample) and seat['mode']=='VR' and seat['headset']=='Quest3'
                      and seat['managementVerified'] and seat['alignmentSha256'] is None and not list(destination.iterdir()),
                      mode+' Quest tool checks the original VR seat using the live game endpoint without ADB')
                save(f'vr-venue-{label}-quest-seat.json', seat)
                verify_mapped_quest(deploy, destination, environment, archive_path.read_bytes(), mode, partial=args.check_quest_vr_partial_map)
            if args.check_windows_venue_staging:
                mapped = [{'roomId': room, 'seat': person['seat'] + 1,
                           'station': f"R{room}-S{person['seat'] + 1}"}
                          for _, room, people in staged for person in people if person['headset'] == 'ViveXr']
                seat_map = runtime / f'{label}-windows-map.json'
                seat_map.write_text(json.dumps({'version': 1, 'seats': mapped[::-1]}), encoding='utf-8')
                staged_path = runtime / f'{label}-windows'
                command = [*deploy, '-WindowsSeatMap', str(seat_map), '-WindowsOutputDirectory', str(staged_path)]
                report = json.loads(subprocess.check_output(command, env=environment, timeout=25, encoding='utf-8'))
                expected_rows = [{**row, 'file': f"pc-{row['station']}-room-{row['roomId']:02}-seat-{row['seat']:02}.json",
                                  'endpoint': f"{address}:{staged[row['roomId'] - 1][0]['ready']['port']}"} for row in mapped]
                check(report['topology'] == mode and report['managementVerified'] and report['liveSourceVerified'] and len(mapped) == 10
                      and [{k: v for k, v in row.items() if k != 'expiresAtUtc'} for row in report['seats']] == expected_rows
                      and {file.name for file in staged_path.iterdir()} == {row['file'] for row in expected_rows},
                      mode+' stages exactly the ten live-verified VIVE XR seats')
                windows_files = {(row['roomId'], row['seat']): staged_path / row['file'] for row in expected_rows}
                save(f'vr-venue-{label}-windows-staging.json', report)
            check(request('/api/sessions') == before, mode+' deployment checks do not change the original venue roster')
        launched = [client for (entry, room, people), raw in zip(staged, files, strict=True)
                    for client in room_players(entry, room, people, raw, windows_files=windows_files)]
        if windows_files:
            check({Path(client['configPath']) for client in launched if client['player']['headset'] == 'ViveXr'}
                  == set(windows_files.values()), mode+' Windows launchers consumed the original staged files')
        return launched

    def packaged_player(entry,person,file, *, mock=None):
        log=file.with_suffix('.log')
        if args.check_venue_concurrent_fire:
            exercise=file.with_suffix('.exercise')
            child=subprocess.Popen([str(player_folder/'VrCommand.exe'), '-batchmode', '-nographics',
                '-job-worker-count', '2', '-logFile', str(log), '--vr-config', str(file),
                '--vr-desktop-exercise', str(exercise)], cwd=runtime, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
            client={'process':child,'log':log,'player':person,'sessionId':entry['sessionId'],
                    'configPath':file,'nativePid':child.pid,'witness':None}
            clients.append(client)
            client['witness']=control.ChildWitness(child.pid)
            return client
        report=file.with_suffix('.launcher.json')
        metrics=file.with_suffix('.link.json') if args.check_venue_link_metrics else None
        flags=['--headless'] if mock is None else ['--openxr']
        if metrics is not None:
            flags += ['--link-metrics',str(metrics)]
        if args.windows_release_report:
            flags += ['--release-report',str(args.windows_release_report)]
        archive=file.with_suffix('.evidence.zip') if args.check_windows_evidence_zip else None
        if archive is not None:
            flags += ['--evidence-zip',str(archive)]
        environment=env if mock is None else {**env,**mock}
        child=subprocess.Popen([str(player_folder/'Launch-Player.exe'),'--config',str(file),'--launch',
            *flags,'--wait','--log',str(log),'--report',str(report)],cwd=runtime,env=environment)
        client={'process':child,'log':log,'player':person,'sessionId':entry['sessionId'],
            'launcherReport':report,'witness':None,'configPath':file}
        if metrics is not None:
            client['linkMetrics']=metrics
        if archive is not None:
            client['evidenceZip']=archive
        clients.append(client)
        def started():
            if child.poll() is not None:raise RuntimeError('Player launcher exited before admission')
            return read(report) if report.exists() else None
        info=wait(started,30,'owned player launcher')
        if info['status']!='started':raise RuntimeError('Player launcher did not report a live child')
        client['witness']=control.ChildWitness(info['processId'],allow_terminate=True)
        client['nativePid']=info['processId']
        if info.get('playerManifestSha256')!=windows_release_hash:
            raise RuntimeError('Player launcher did not report the expected release manifest')
        return client
    def stop_player(client):
        child=client['process']
        report=client.get('launcherReport')
        if report:
            witness=client['witness']
            if witness is None and child.poll() is None:
                info=wait(lambda:read(report) if report.exists() else None,10,'player cleanup ownership')
                if info['status']=='started':
                    witness=control.ChildWitness(info['processId'],allow_terminate=True)
                    client['witness']=witness
                    client['nativePid']=info['processId']
            if witness:
                witness.terminate()
                witness.wait()
                child.wait(timeout=15)
                status=read(report)
                if 'linkMetrics' in client:
                    status.pop('linkMetrics',None)
                release_log_hash=status.pop('playerLogSha256',None)
                if windows_release_hash and 'final' in client and (release_log_hash is not None or 'linkMetrics' not in client):
                    if release_log_hash!=control.sha(client['log']):
                        raise RuntimeError('Player launcher exit does not identify the original release log')
                if status.pop('playerManifestSha256',None)!=windows_release_hash:
                    raise RuntimeError('Player launcher exit differs from its original release manifest')
                allowed_codes=(0,1) if 'evidenceZip' in client and 'final' not in client else (0,)
                if child.returncode not in allowed_codes or status!={'status':'exited','processId':client['nativePid'],'exitCode':0}:
                    raise RuntimeError('Launcher did not confirm original player exit')
                witness.close()
                client['witness']=None
                if 'evidenceZip' in client and 'final' in client:
                    with zipfile.ZipFile(client['evidenceZip']) as bundle:
                        originals = {'launch-report.json': report, 'player.log': client['log']}
                        if 'linkMetrics' in client:
                            originals['link-metrics.json'] = client['linkMetrics']
                        check(sorted(bundle.namelist()) == sorted(originals)
                              and all(bundle.read(name) == path.read_bytes() for name, path in originals.items()),
                              'player ZIP contains the exact original log, exited report and requested evidence')
            elif not report.exists() or read(report)['status'] not in ('exited','rejected'):
                raise RuntimeError('Native player cleanup unknown')
        elif child.poll() is None:
            child.terminate()
        child.wait(timeout=15)
        if not report and client.get('witness'):
            client['witness'].close()
            client['witness']=None
    def verify_delivery(entry,owners):
        manifest_entry = None
        world_journal = None
        combat_journal = None
        server=(entry['work']/'server.log').read_text(encoding='utf-8',errors='replace')
        acks=[int(value) for value in re.findall(r'VR_SERVER_DEBRIEF_ACK id=(\d+)',server)]
        check(len(acks)==len(owners) and set(acks)=={c['connection'] for c in owners}
            and 'VR_SERVER_DEBRIEF_TIMEOUT ' not in server,entry['label']+' exact original server ACKs')
        if args.peer_diagnostics:
            peers=re.findall(r'^VR_SERVER_PEER id=(\d+) endpoint=(\S+)$',server,re.M)
            check('VR_SERVER_PEER_LIMIT' not in server,entry['label']+' no peer log overflow')
            if entry['peerDiagnostics']:
                expected_peers={int(connection) for client in owners for connection in client.get('reconnectIds', [client['connection']])}
                check(len(peers)==len(expected_peers) and {int(connection) for connection,_ in peers}==expected_peers,
                    entry['label']+' exact UDP peer history for the original player processes')
                session_path='/api/sessions/'+entry['sessionId']
                session_raw,_=request(session_path,raw_response=True)
                endpoint_raw,_=request(session_path+'/connection-endpoint',raw_response=True)
                (out/(entry['label']+'-session.json')).write_bytes(session_raw)
                (out/(entry['label']+'-endpoint.json')).write_bytes(endpoint_raw)
                session,endpoint=field.read_json(session_raw),field.read_json(endpoint_raw)
                statistics=field.read_json(field.content(out/(entry['label']+'-statistics.json')))
                if args.field_evidence:
                    route=session_path+'/field-evidence.zip'
                    raw,headers=request(route,raw_response=True)
                    check(headers.get_content_type()=='application/zip' and headers['Cache-Control']=='no-store'
                          and f'vr-command-field-v1-{entry["sessionId"]}.zip' in headers['Content-Disposition'],
                          entry['label']+' management ZIP headers and original session filename')
                    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                        check(archive.namelist()==['session.json','statistics.json','endpoint.json'] and archive.testzip() is None,
                              entry['label']+' management ZIP contains exactly three JSON records')
                        exported=[field.read_json(archive.read(name)) for name in archive.namelist()]
                    check(exported==[session,statistics,endpoint],entry['label']+' management ZIP matches the original sealed API data')
                    request(route,role='Room1',expected=403)
                    check(True,entry['label']+' room controller denied the full evidence ZIP')
                    evidence_zip=out/(entry['label']+'-field-evidence.zip')
                    evidence_zip.write_bytes(raw)
                    session,statistics,endpoint=exported
                    world_journal = entry['work']/'telemetry'/(entry['sessionId']+'.worldlog')
                    combat_journal = entry['work']/'telemetry'/(entry['sessionId']+'.journal')
                    manifest_entry={'evidenceZip':str(evidence_zip),'launcherReport':str(entry['reportPath']),
                        'serverLog':str(entry['work']/'server.log'),'worldJournal':str(world_journal),
                        'combatJournal':str(combat_journal),
                        'players':[{'address':address,'log':str(c['log']),
                                    **({'launcherReport':str(c['launcherReport'])} if windows_release_hash or 'linkMetrics' in c else {}),
                                    **({'linkMetrics':str(c['linkMetrics'])} if 'linkMetrics' in c else {})} for c in owners]}
                preflight = (out/(entry['label']+'-lan-listener.ndjson'), out/(entry['label']+'-lan-probe.json')) if args.check_lan_preflight else None
                if manifest_entry is not None and preflight is not None:
                    manifest_entry['udpSourcePreflights'] = [dict(zip(('listener', 'probe'), map(str, preflight), strict=True))]
                ip=ipaddress.IPv4Address(address)
                result=field.verify('same-host',{ip},read(entry['reportPath']),session,statistics,endpoint,server,
                    [(ip,field.content(c['log'])) for c in owners], world_journal=world_journal,
                    combat_journal=combat_journal,
                    udp_source_preflights=[preflight] if preflight is not None else None,
                    verify_player_sources=args.check_venue_openxr and not args.check_venue_openxr_reconnect and world_journal is not None,
                    verify_reconnect_history=args.check_venue_openxr_reconnect)
                save(entry['label']+'-field-results.json',result)
                check(result['serverAcknowledgements']==len(acks),entry['label']+' field report matches same-PC endpoints and sealed player results')
                if world_journal is not None:
                    check(result['worldJournal']['frames']==result['worldSequence'] and result['worldJournal']['runningFrames']>0,
                          entry['label']+' field report verifies the original closed world journal')
                    check(result['combatJournal']['events']==result['combatSequence']
                          and result['combatJournal']['players']==len(owners),
                          entry['label']+' original combat journal reproduces each sealed player result')
                if preflight is not None:
                    coverage = result['udpSourcePreflight']
                    check(coverage['observedSourceAddresses']==coverage['verifiedSourceAddresses']==1
                          and [pair['samples'] for pair in coverage['pairs']]==[3],
                          entry['label']+' field report binds the original UDP preflight to the server endpoint and accepted player sources')
            else:
                check('VR_SERVER_PEER' not in server,entry['label']+' default does not record UDP peers')
        raw,headers=request('/api/sessions/'+entry['sessionId']+'/report.csv',raw_response=True)
        rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline='')))
        results={c['player']['id']:c['final'] for c in owners}
        check(headers.get_content_type()=='text/csv' and raw.startswith(b'\xef\xbb\xbf')
            and len(rows)==len(owners) and {r['playerId'] for r in rows}==set(results),
            entry['label']+' exact CSV roster')
        fields=('playerId','origin','sessionId','streamId')
        numbers=('throughSequence','finalStreamSequence','ammoUsed','shotsHit','kills',
            'damageTaken','hitsReceived','accuracyPercent','health')
        for row in rows:
            final=results[row['playerId']]
            if row['rowType']!='Player' or row['reportVersion']!='1' or int(row['playerRoomId'])!=final['roomId'] \
                or any(row[k]!=final[k] for k in fields) or any(Decimal(row[k])!=Decimal(str(final[k])) for k in numbers):
                raise ValueError('CSV row differs from the original sealed player result')
        (out/(entry['label']+'-report.csv')).write_bytes(raw)
        if args.check_debrief_receipts:
            route='/api/sessions/'+entry['sessionId']+'/world?includeDebriefReceipts=true'
            snapshot=request(route)['debriefReceipts']
            boundaries=('streamId','throughSequence','finalStreamSequence','worldSequence')
            check({row['playerId'] for row in snapshot['players']}==set(results)
                  and len(snapshot['players'])==len(results)
                  and all(row['acknowledged'] and row['admissionId']==results[row['playerId']]['admissionId']
                          and row['roomId']==results[row['playerId']]['roomId']
                          and all(snapshot[key]==results[row['playerId']][key] for key in boundaries)
                          for row in snapshot['players']),entry['label']+' management receipts match original native results and both seals')
            for room in sorted({row['roomId'] for row in snapshot['players']}):
                scoped=request(route,role=f'Room{room}')['debriefReceipts']
                check(scoped=={**snapshot,'players':[row for row in snapshot['players'] if row['roomId']==room]},
                      entry['label']+f' room {room} reads only its original admissions and receipts')
            save(entry['label']+'-debrief-receipts.json',snapshot)
        if args.check_room_reports and entry['label']=='linked':
            session_path='/api/sessions/'+entry['sessionId']
            prefix='vr-command-report-v1-'+entry['sessionId']
            expected_files={prefix+'.csv':raw}
            for room in range(1,6):
                scoped,scoped_headers=request(session_path+f'/rooms/{room}/report.csv',
                    role=f'Room{room}',raw_response=True)
                scoped_rows=list(csv.DictReader(io.StringIO(scoped.decode('utf-8-sig'),newline='')))
                expected=[dict(row,reportRoomId=str(room)) for row in rows if row['playerRoomId']==str(room)]
                check(len(expected)==players_per_room and scoped_rows==expected and scoped_headers['Cache-Control']=='no-store'
                    and f'-room-{room:02}.csv' in scoped_headers['Content-Disposition'],
                    f'room {room} CSV matches its {players_per_room} original sealed Linked player rows')
                (out/f'linked-scoped-room-{room:02}.csv').write_bytes(scoped)
                expected_files[f'{prefix}-room-{room:02}.csv']=scoped
            request(session_path+'/rooms/2/report.csv',role='Room1',expected=403)
            reports,headers=request(session_path+'/reports.zip',raw_response=True)
            check(headers.get_content_type()=='application/zip' and headers['Cache-Control']=='no-store'
                  and f'vr-command-reports-v1-{entry["sessionId"]}.zip' in headers['Content-Disposition'],
                  'Linked battle ZIP headers and original session filename')
            with zipfile.ZipFile(io.BytesIO(reports)) as archive:
                check(archive.namelist()==list(expected_files) and archive.testzip() is None
                      and all(archive.read(name)==content for name,content in expected_files.items()),
                      f'Linked battle ZIP matches the exact six CSVs from the original {venue_players} player results')
            request(session_path+'/reports.zip',role='Room1',expected=403)
            (out/'linked-reports.zip').write_bytes(reports)
        save(entry['label']+'-delivery.json',{'serverAcknowledgedConnections':acks,
            'players':[{'playerId':c['player']['id'],'admissionId':c['player']['admissionId'],
                'roomId':c['player']['roomId'],'seat':c['player']['seat'],'connectionId':c['connection'],
                'nativePid':c['nativePid'],'launcherPid':c['process'].pid if c.get('launcherReport') else None} for c in owners]})
        check(True,entry['label']+' CSV rows match sealed player results')
        return manifest_entry

    def preserve_venue_control_report(mode, action, receipt):
        if not args.venue_field_evidence:
            return
        raw, _ = request('/api/venue/phase', raw_response=True)
        key = 'latestEnvironment' if action == 'SetEnvironment' else 'latestEnemies'
        batch = field.read_json(raw)[key]
        check(batch['requestId'] == receipt['requestId']
              and {row['sessionId']: row['appliedAtSequence'] for row in batch['sessions']}
              == {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']},
              mode + ' phase report preserves the original ' + action + ' receipt')
        path = out / (mode + '-phase-' + receipt['requestId'] + '.json')
        path.write_bytes(raw)
        venue_control_reports.setdefault(mode, []).append({'action': action, 'phaseReport': str(path)})

    def verify_venue_field_evidence(mode, closed, entries):
        label = mode.lower()
        route = '/api/venue/closure/' + closed['requestId']
        raw, headers = request(route, raw_response=True)
        check(field.read_json(raw)['batch'] == closed and headers['Cache-Control'] == 'no-store',
              label + ' field evidence reads the exact sealed closure by original batch ID')
        closure_file = out / (label + '-field-closure.json')
        closure_file.write_bytes(raw)
        bundle_route = route + '/field-evidence.zip'
        bundle, headers = request(bundle_route, raw_response=True)
        request(bundle_route, role='Room1', expected=403)
        check(headers['Cache-Control'] == 'no-store' and headers.get_content_type() == 'application/zip'
              and f'vr-command-venue-field-v1-{closed["requestId"]}.zip' in headers['Content-Disposition'],
              label + ' field bundle uses the original batch filename and Master scope')
        names = ['linked.zip'] if mode == 'Linked' else [f'room-{room:02}.zip' for room in range(1, 6)]
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            check(archive.namelist() == ['closure.json', *names] and archive.testzip() is None
                  and field.read_json(archive.read('closure.json')) == field.read_json(raw)
                  and all(archive.read(name) == Path(entry['evidenceZip']).read_bytes() for name, entry in zip(names, entries)),
                  label + ' field bundle contains the original closure and exact individual ZIP bytes')
        bundle_file = out / (label + '-venue-field-evidence.zip')
        bundle_file.write_bytes(bundle)
        manifest_path = runtime / (label + '-field-manifest.json')
        common = {'version': 1, 'mode': mode, 'topology': 'same-host', 'serverIps': [address],
                  **({'expectedPlayersPerRoom': players_per_room} if players_per_room != 5 else {}),
                  **({'verifyPlayerSources': True} if args.check_venue_openxr and not args.check_venue_openxr_reconnect else {}),
                  **({'verifyReconnectHistory': True} if args.check_venue_openxr_reconnect else {})}
        if label in venue_control_reports:
            common['venueControlBatches'] = venue_control_reports[label]
        debrief_file = None
        if args.check_debrief_receipts:
            debrief_route = route + '/debrief-receipts.json'
            snapshot, headers = request(debrief_route, raw_response=True)
            request(debrief_route, role='Room1', expected=403)
            check(headers['Cache-Control'] == 'no-store' and headers.get_content_type() == 'application/json'
                  and f'vr-command-venue-debrief-receipts-v1-{closed["requestId"]}.json' in headers['Content-Disposition'],
                  label + ' receipt export uses the original batch filename and Master scope')
            debrief_file = out / (label + '-venue-debrief-export.json')
            debrief_file.write_bytes(snapshot)
            common['venueDebriefReceipts'] = str(debrief_file)
            original_receipts = {row['sessionId']: row for row in json.loads(snapshot)['sessions']}
            seat_views = []
            seat_reports = []
            for row in closed['sessions']:
                session = request('/api/sessions/' + row['sessionId'])
                original = original_receipts[session['id']]
                acknowledged = {player['admissionId'] for player in original['players'] if player['acknowledged']}
                for room in row['roomIds']:
                    detail_route = f'{route}/rooms/{room}/debrief-receipts'
                    raw_detail, detail_headers = request(detail_route, raw_response=True)
                    request(detail_route, role=f'Room{room}', expected=403)
                    detail = json.loads(raw_detail)
                    roster = sorted((player for player in session['players'] if player['roomId'] == room),
                                    key=lambda player: player['seat'])
                    expected = {'version': 1, 'requestId': closed['requestId'], 'roomId': room,
                                **{key: value for key, value in original.items() if key != 'players'},
                                'players': [{'seat': player['seat'] + 1, 'name': player['name'],
                                             'acknowledged': player['admissionId'] in acknowledged} for player in roster]}
                    check(detail == expected and detail_headers['Cache-Control'] == 'no-store'
                          and len(detail['players']) == players_per_room and all(player['acknowledged'] for player in detail['players']),
                          f'{label} room {room} seat detail matches the original sealed roster and native receipts')
                    scored_route = detail_route + '?includeScores=true&includePlayerIds=true'
                    scored, score_headers = request(scored_route, raw_response=True)
                    request(scored_route, role=f'Room{room}', expected=403)
                    scores = []
                    for player in roster:
                        seat = player['seat'] + 1
                        seat_route = f'{route}/rooms/{room}/seats/{seat}/report.csv'
                        csv_bytes, csv_headers = request(seat_route, raw_response=True)
                        direct, _ = request(f'/api/sessions/{session["id"]}/players/{player["id"]}/report.csv', raw_response=True)
                        name = f'vr-command-report-v1-{session["id"]}-player-{player["id"]}.csv'
                        check(csv_bytes == direct and csv_headers['Cache-Control'] == 'no-store'
                              and csv_headers.get_content_type() == 'text/csv' and name in csv_headers['Content-Disposition'],
                              f'{label} room {room} seat {seat} CSV exactly matches its original sealed personal report')
                        csv_row, = csv.DictReader(io.StringIO(csv_bytes.decode('utf-8-sig'), newline=''))
                        scores.append({key: int(csv_row[key]) for key in ('ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken', 'health')}
                                      | {'accuracyPercent': float(csv_row['accuracyPercent'])})
                        seat_reports.append({'roomId': room, 'seat': seat, 'filename': name,
                                             'sha256': hashlib.sha256(csv_bytes).hexdigest()})
                    view = json.loads(scored)
                    check(view == {**expected, 'players': [dict(seat, score=score, playerId=player['id'])
                          for seat, score, player in zip(expected['players'], scores, roster, strict=True)]}
                          and score_headers['Cache-Control'] == 'no-store',
                          f'{label} room {room} seat scores match all seven metrics of the original sealed personal CSVs')
                    seat_views.append(view)
            batch_view, batch_headers = request(route + '/debrief-seats', raw_response=True)
            request(route + '/debrief-seats', role='Room1', expected=403)
            combined_seats = json.loads(batch_view)
            check(batch_headers['Cache-Control'] == 'no-store'
                  and combined_seats == {'version': 1, 'requestId': closed['requestId'],
                      'rooms': sorted(seat_views, key=lambda room: room['roomId'])},
                  label + ' whole-venue seat list exactly matches every original scoped receipt and score')
            save(label + '-venue-debrief-all.json', combined_seats)
            seats_file = out / (label + '-venue-debrief-seats.json')
            save(seats_file.name, seat_views)
            seat_reports_file = out / (label + '-venue-debrief-csv.json')
            save(seat_reports_file.name, seat_reports)
        if args.windows_release_report:
            common['venueReleaseReport']=str(args.windows_release_report)
        if args.check_venue_participation_gate:
            common['verifyParticipationBegin'] = True
        concurrent_seconds = args.venue_concurrent_roster_seconds
        if concurrent_seconds is not None:
            common['minimumConcurrentMilliseconds'] = concurrent_seconds * 1000
        if args.check_venue_concurrent_fire:
            common['requireConcurrentFire'] = True
        evidence = dict(common, venueBundle=str(bundle_file),
                        sessions=[{key: value for key, value in entry.items() if key not in ('evidenceZip', 'players')}
                                  for entry in reversed(entries)],
                        windowsPlayers=[player for entry in reversed(entries) for player in reversed(entry['players'])])
        split = dict(common, closure=str(closure_file), sessions=entries)

        def run(manifest, *options):
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            return subprocess.run([sys.executable, str(ROOT / 'scripts/verify-field-results.py'),
                                   '--venue-manifest', str(manifest_path), *options], capture_output=True, encoding='utf-8', timeout=45)

        result = run(evidence)
        if result.returncode:
            raise RuntimeError('Native venue field evidence rejected: ' + result.stderr.strip())
        summary = json.loads(result.stdout)
        original = run(split)
        check(original.returncode == 0 and json.loads(original.stdout) == summary,
              label + ' untouched venue ZIP and unordered Windows logs match the original split field summary')
        if args.check_windows_evidence_zip:
            bundled = dict(evidence, windowsPlayers=[{'address': player['address'],
                'evidenceZip': str(Path(player['log']).with_suffix('.evidence.zip'))} for player in evidence['windowsPlayers']])
            zipped = run(bundled)
            check(zipped.returncode == 0 and json.loads(zipped.stdout) == summary,
                  label + ' original Windows player ZIPs match the exact loose-file field report')
            (runtime / (label + '-player-archives-manifest.json')).write_text(json.dumps(bundled), encoding='utf-8')
            if args.check_venue_link_metrics:
                inbox = runtime / (label + '-windows-inbox')
                inbox.mkdir()
                for index, player in enumerate(bundled['windowsPlayers'], 1):
                    shutil.copyfile(player['evidenceZip'], inbox / f'returned-{index:02}.zip')
                received = dict(evidence, windowsEvidenceDirectory=str(inbox))
                del received['windowsPlayers']
                inspected = run(received, '--inspect-windows-inbox')
                check(inspected.returncode == 0 and json.loads(inspected.stdout)['receivedWindowsSeats'] == venue_players,
                      label + ' measured player ZIP inbox recognizes every original acknowledged seat')
                inbox_result = run(received)
                check(inbox_result.returncode == 0 and json.loads(inbox_result.stdout) == summary,
                      label + ' measured player ZIP inbox matches the complete loose-file report without sidecars')
                save(label + '-measured-windows-inbox.json', json.loads(inspected.stdout))
                (runtime / (label + '-measured-inbox-manifest.json')).write_text(json.dumps(received), encoding='utf-8')
        check(summary['consistent'] and summary['mode'] == mode and summary['players'] == summary['serverAcknowledgements'] == venue_players
              and summary['rooms'] == [{'roomId': room, 'players': players_per_room, 'playersOutsideDeclaredServer': 0} for room in range(1, 6)]
              and not summary['physicalHostsVerified'] and not summary['networkCapacityAccepted'],
              label + f' field evidence matches all {venue_players} original sealed admissions and UDP peers')
        if players_per_room != 5:
            check(summary['expectedPlayersPerRoom'] == players_per_room, label + ' field report preserves the explicit stage size')
            full_manifest = dict(evidence)
            del full_manifest['expectedPlayersPerRoom']
            wrong_stage = run(full_manifest)
            check(wrong_stage.returncode == 1 and not wrong_stage.stdout and 'player log count' in wrong_stage.stderr,
                  label + ' sealed staged roster cannot pass default full-venue verification')
        if label in venue_control_reports:
            batches = summary['venueControlBatches']
            check([batch['action'] for batch in batches] == [row['action'] for row in venue_control_reports[label]]
                  and all(batch['sessionsVerified'] == len(entries) for batch in batches)
                  and all(len(row['worldJournal']['venueControlFrames']) == len(batches) for row in summary['sessions']),
                  label + ' original journals contain an exact Running witness for every venue control batch')
        if debrief_file is not None:
            check(summary['venueDebriefReceipts'] == {'sha256': control.sha(debrief_file), 'sessions': len(entries),
                                                    'acknowledgedPlayers': venue_players},
                  label + ' field evidence matches every stored receipt to original native acknowledgements')
            modified = field.read_json(debrief_file.read_bytes())
            modified['sessions'][0]['players'][0]['acknowledged'] = False
            incomplete = out / (label + '-venue-debrief-unconfirmed.json')
            save(incomplete.name, modified)
            rejected_receipts = run(dict(evidence, venueDebriefReceipts=str(incomplete)))
            check(rejected_receipts.returncode == 1 and not rejected_receipts.stdout
                  and 'missing or unconfirmed' in rejected_receipts.stderr,
                  label + ' unconfirmed management receipt fails even with complete original native logs')
        check(summary['worldJournalsVerified'] == len(entries)
              and all(row['worldJournal']['frames'] == row['worldSequence'] and row['worldJournal']['runningFrames'] > 0
                      for row in summary['sessions']), label + ' field evidence verifies every original closed world journal')
        check(summary['combatJournalsVerified'] == len(entries)
              and all(row['combatJournal']['events'] == row['combatSequence']
                      and row['combatJournal']['players'] == players_per_room * len(row['roomIds']) for row in summary['sessions']),
              label + f' original combat journals reproduce the sealed scores of all {venue_players} seats')
        if args.windows_release_report:
            expected_seats=[{'roomId':room,'seat':seat} for room in range(1,6) for seat in range(1,players_per_room+1)]
            check(summary['venueRelease']=={'reportSha256':control.sha(args.windows_release_report),
                    'windows':{'playerManifestSha256':windows_release_hash,'seatsVerified':venue_players}}
                  and [seat for session in summary['sessions'] for seat in session['windowsReleaseSeats']]==expected_seats,
                  label+f' field release identifies the original {venue_players} acknowledged Windows seats')
            swapped=[dict(player) for player in evidence['windowsPlayers']]
            swapped[0]['launcherReport'],swapped[1]['launcherReport']=swapped[1]['launcherReport'],swapped[0]['launcherReport']
            rejected=run(dict(evidence,windowsPlayers=swapped))
            check(rejected.returncode==1 and 'original' in rejected.stderr and 'log' in rejected.stderr,
                  label+' rejects an authentic launcher report from another seat of the same release')
        if args.check_venue_link_metrics:
            links = [row for session in summary['sessions'] for row in session['windowsLinkMetrics']]
            check(summary['windowsLinkMetricsVerified']==len(links)==venue_players and all(
                row['attempts']==row['replies']+row['timeouts']+row['interrupted']==30 and row['replies']>0 for row in links),
                label+f' {venue_players} packaged client link reports match the original acknowledged connections and keep every outcome')
            swapped = [dict(player) for player in evidence['windowsPlayers']]
            swapped[0]['linkMetrics'],swapped[1]['linkMetrics'] = swapped[1]['linkMetrics'],swapped[0]['linkMetrics']
            rejected = run(dict(evidence, windowsPlayers=swapped))
            check(rejected.returncode==1 and 'original link and player log bytes' in rejected.stderr,
                  label+' rejects swapping two authentic original link reports')
        if args.check_venue_participation_gate:
            proofs=read(out/(label+'-full-participation-begin.json'))
            receipt=read(out/(label+'-venue-begin.json'))['receipt']
            check(summary['participationBegin']=={'requestId':receipt['requestId'], 'sessions':len(entries),
                  'participants':venue_players, 'trackedPlayers':0, 'simulatedPlayers':venue_players},
                  label+f' untouched field ZIP verifies the original {venue_players}-seat simulated Begin')
            archived={tuple(row['roomIds']):row for row in closed['sessions']}
            for report in summary['sessions']:
                row=archived[tuple(report['roomIds'])]; witness=row['participationBegin']; expected=proofs[row['sessionId']]
                proof=report['worldJournal']['participationBegin']
                assert witness=={'requestId':receipt['requestId'], 'appliedAtSequence':expected['appliedAtSequence'],
                                'frame':expected['witness']} and 'trackingBegin' not in row
                assert proof['preparingFrame']==expected['witness']['worldSequence'] and proof['firstRunningFrame']>proof['preparingFrame']
            check(True,label+' offline frame proofs match the original live Begin receipts and sealed source')
            wrong_policy=run(dict(evidence,verifyParticipationBegin=False,verifyTrackingBegin=True))
            check(wrong_policy.returncode==1 and not wrong_policy.stdout and 'missing an original guarded Begin witness' in wrong_policy.stderr,
                  label+' original participation archive cannot pass as a tracking-only Begin')
        # Exercise the missing terminal seal using a new copy of one original file.
        first = evidence['sessions'][0]
        original_journal = Path(first['combatJournal']).read_bytes()
        assert original_journal[-37:-32] == b'\x01\x00\x00\x00\x05'
        unsealed = out / (label + '-field-combat-without-seal.journal')
        unsealed.write_bytes(original_journal[:-37])
        rejected = run(dict(evidence, sessions=[dict(first, combatJournal=str(unsealed)), *evidence['sessions'][1:]]))
        check(rejected.returncode == 1 and not rejected.stdout and 'combat journal seal' in rejected.stderr,
              label + ' field evidence rejects an original combat prefix without its terminal seal')
        if concurrent_seconds is not None:
            coverage = summary['concurrentRoster']
            check(coverage['players'] == venue_players and coverage['longestMilliseconds'] >= concurrent_seconds * 1000,
                  label + f' original closed world journals verify the continuous concurrent {venue_players}-seat window')
            if args.check_venue_concurrent_fire:
                check(coverage['playersWithConfirmedFire'] == venue_players,
                      label + f' original world and combat journals verify fire from all {venue_players} seats inside one shared window')
            tracked = run(dict(evidence, requireTrackedRoster=True))
            check(tracked.returncode == 1 and not tracked.stdout and 'original Quest or non-mock Windows OpenXR' in tracked.stderr,
                  label + ' continuous desktop roster cannot satisfy the tracked-only evidence gate')
        if args.check_venue_openxr_reconnect:
            check(summary['reconnectHistory']=={'observedConnections':26,'retiredConnections':1,
                  'reconnectedSeats':[{'roomId':5,'seat':2,'retiredConnections':1}]},
                  label+' field evidence verifies the released connection and its exact original seat')
            witness=read(out/(label+'-venue-openxr-reconnect.json'))
            old_connection=witness['connections'][0]
            session_id=witness['renewed']['readiness']['sessionId']
            target=next(row for row in evidence['sessions'] if read(Path(row['launcherReport']))['sessionId']==session_id)
            server=Path(target['serverLog']).read_bytes()
            release=f'VR_SERVER_CLIENT_LEFT id={old_connection}\n'.encode('ascii')
            if release not in server:
                release=release.replace(b'\n',b'\r\n')
            assert server.count(release)==1
            missing_release=out/(label+'-field-server-without-release.log')
            missing_release.write_bytes(server.replace(release,b'',1))
            missing=run(dict(evidence,sessions=[dict(row,serverLog=str(missing_release)) if row is target else row
                                               for row in evidence['sessions']]))
            check(missing.returncode==1 and not missing.stdout and 'Missing server release' in missing.stderr,
                  label+' original venue closure cannot pass without the superseded transport release')
        elif args.check_venue_openxr:
            sources={(row['roomId'],row['seat']):row['source'] for session in summary['sessions'] for row in session['playerSources']}
            check(sources=={(room,seat):'windows-openxr-mock-tracked' if (room,seat)==(5,2) else 'windows-desktop-simulated'
                           for room in range(1,6) for seat in range(1,6)},
                  label+' closed field evidence identifies the exact mock OpenXR seat and all 24 desktop peers')
        if args.check_lan_preflight:
            check(summary['udpSourcePreflightsVerified'] == len(entries)
                  and all(row['udpSourcePreflight']['verifiedSourceAddresses'] == 1 for row in summary['sessions']),
                  label + ' original paired UDP reports cover all acknowledged source addresses at every sealed game endpoint')
        save(label + '-venue-field-results.json', summary)
        rejected = run(dict(evidence, topology='direct-lan'))
        check(rejected.returncode == 1 and not rejected.stdout and 'outside the declared server addresses' in rejected.stderr,
              label + ' field evidence rejects relabeling the same-PC peers as direct LAN')
        manifest_path.write_text(json.dumps(evidence), encoding='utf-8')
        return {'batchId': closed['requestId'], 'zip': str(bundle_file), 'route': bundle_route,
                **({'debrief': str(debrief_file), 'debriefSeats': str(seats_file), 'debriefSeatReports': str(seat_reports_file)}
                   if debrief_file is not None else {})}

    def verify_venue_field_ui(mode, current, earlier):
        node = shutil.which('node')
        if not node: raise RuntimeError('Node is required for the shipped field bundle check')
        cases = [dict(current, archived=False)]
        if earlier: cases.append(dict(earlier, archived=True))
        descriptor = runtime / (mode + '-field-browser-private.json')
        output = out / (mode + '-venue-field-ui.json')
        descriptor.write_text(json.dumps({'base': uri, 'masterKey': keys['Master'], 'mode': mode,
                                          'sessions': [], 'fieldEvidence': cases}), encoding='utf-8')
        with (out / (mode + '-venue-field-ui.log')).open('xb') as log:
            subprocess.run([node, str(ROOT/'tests/browser/check-venue-replay-native.cjs'), str(descriptor), str(output)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=75)
        result = read(output)
        check(result['complete'] and result['fieldEvidence'] == [case['batchId'] for case in cases],
              mode + ' shipped console downloads exact field bundles for the selected original batches')
        if args.check_debrief_receipts:
            check(result['receiptExports'] == [case['batchId'] for case in cases],
                  mode + ' shipped console downloads exact receipt exports for the selected original batches')
            expected = [{'batchId': case['batchId'], 'rooms': [
                {'roomId': room['roomId'], 'sessionId': room['sessionId'], 'seats': len(room['players'])}
                for room in read(Path(case['debriefSeats']))]} for case in cases]
            check(result['debriefSeats'] == expected,
                  mode + ' shipped console opens every original room and filters confirmed native seats')
            check(result['debriefAll'] == [{'batchId': case['batchId'], 'seats': sum(room['seats'] for room in case['rooms'])}
                                          for case in expected],
                  mode + ' shipped console lists every original native seat together and starts with no unconfirmed rows')
            csv_checks = [{'batchId': case['batchId'], **next(row for row in reversed(read(Path(case['debriefSeatReports'])))
                           if row['roomId'] == 5)} for case in cases]
            check(result['debriefCsv'] == csv_checks, mode + ' shipped console downloads the exact original personal seat CSV')
            replays = []
            for case in cases:
                room = next(row for row in read(Path(case['debriefSeats'])) if row['roomId'] == 5)
                player = room['players'][-1]
                pages, cursor = [], 0
                while True:
                    events = request(f'/api/sessions/{room["sessionId"]}/world/event-frames?afterFrame={cursor}'
                                     f'&throughFrame={room["worldSequence"]}&roomId=5&playerId={player["playerId"]}')
                    next_cursor = events.get('nextAfterFrame')
                    pages.append({**{key: events[key] for key in ('afterFrame', 'scannedThroughFrame', 'frames')},
                                  'nextAfterFrame': next_cursor})
                    if events['frames'] or next_cursor is None:
                        break
                    assert next_cursor == events['scannedThroughFrame'] and cursor < next_cursor < room['worldSequence']
                    cursor = next_cursor
                assert not args.check_room_combat or pages[-1]['frames']
                replays.append({'batchId': case['batchId'], 'sessionId': room['sessionId'], 'roomId': 5,
                                'playerId': player['playerId'], 'streamId': room['streamId'],
                                'throughFrame': room['worldSequence'], 'pages': pages})
            check(result['debriefReplay'] == replays,
                  mode + ' shipped console opens each original room five seat replay and its exact event frames')
    def verify_live_room_navigation(entries, clients, linked):
        topology = 'Linked' if linked else 'Independent'
        rooms = []
        for entry in entries:
            sid = entry['sessionId']
            minimum = (entry['combatWindow']['disabledSequence'] if args.check_room_combat else
                       read(out/(entry['label']+'-running.json'))['acceptedBeginSequence'])
            for room_id in request('/api/sessions/'+sid)['roomIds']:
                players = [client['player']['id'] for client in clients
                           if client['sessionId'] == sid and client['player']['roomId'] == room_id]
                assert len(players) == players_per_room
                rooms.append({'roomId': room_id, 'sessionId': sid, 'streamId': entry['ready']['streamId'],
                              'minimumSequence': minimum, 'playerIds': players})
        descriptor = runtime/(topology.lower()+'-live-rooms-private.json')
        descriptor.write_text(json.dumps({'base': uri, 'masterKey': keys['Master'], 'topology': topology,
            'rooms': sorted(rooms, key=lambda room: room['roomId']), 'requireDamage': args.check_room_combat}), encoding='utf-8')
        browser_out = out/(topology.lower()+'-live-rooms')
        try:
            with (out/(topology.lower()+'-live-rooms-browser.log')).open('xb') as log:
                subprocess.run([shutil.which('node'), str(ROOT/'tests/browser/check-live-rooms-native.cjs'),
                                str(descriptor), str(browser_out)], cwd=ROOT/'tests/browser', stdout=log,
                               stderr=subprocess.STDOUT, check=True, timeout=85)
        finally:
            descriptor.unlink()
        observed = read(browser_out/'checks.json')
        check(observed['complete'] and observed['topology'] == topology and observed['scopedWatches'] == 5
              and observed['retiredWatches'] == 4 and [sample['roomId'] for sample in observed['samples']] == [1,4,2,5,3],
              topology+' shipped console switches all five original live rooms and retires the previous streams')
        if args.check_room_combat:
            reviews = observed['liveEventReviews']
            check([row['roomId'] for row in reviews] == [3,1,4,2,5]
                  and all(row['matchCount'] > 0 and row['eventFrame'] < row['visibleTail'] < row['returnedSequence'] for row in reviews),
                  topology+' shipped console pauses at the latest original room damage events and returns to each live source')
        return observed['samples']

    def verify_venue_reports(entries, receipt, linked):
        mode = 'linked' if linked else 'independent'
        key = receipt['requestId']
        route = f'/api/venue/closure/{key}/reports.zip'
        raw, headers = request(route, raw_response=True)
        check(headers.get_content_type() == 'application/zip' and headers['Cache-Control'] == 'no-store'
              and f'vr-command-venue-reports-v1-{key}.zip' in headers['Content-Disposition'],
              f'{mode} batch ZIP uses the original End request and no-store')
        request(route, role='Room1', expected=403)
        expected = {}
        manifest_sessions = []
        sequences = {item['sessionId']: item['appliedAtSequence'] for item in receipt['sessions']}
        for entry in entries:
            sid = entry['sessionId']
            session_path = '/api/sessions/' + sid
            rooms = request(session_path)['roomIds']
            prefix = f'vr-command-report-v1-{sid}'
            files = []
            if linked:
                name = prefix + '.csv'
                expected[name] = (out/(entry['label']+'-report.csv')).read_bytes()
                files.append({'roomId': None, 'name': name})
            for room in rooms:
                name = f'{prefix}-room-{room:02}.csv'
                expected[name], _ = request(session_path+f'/rooms/{room}/report.csv', raw_response=True)
                files.append({'roomId': room, 'name': name})
                scoped = list(csv.DictReader(io.StringIO(expected[name].decode('utf-8-sig'), newline='')))
                original = (out/(entry['label']+'-report.csv')).read_text(encoding='utf-8-sig')
                original_rows = list(csv.DictReader(io.StringIO(original)))
                check(scoped == [dict(row, reportRoomId=str(room)) for row in original_rows if row['playerRoomId'] == str(room)]
                      and len(scoped) == players_per_room,
                      f'{mode} batch room {room} preserves its {players_per_room} sealed native rows')
            manifest_sessions.append({'sessionId': sid, 'roomIds': rooms, 'appliedAtSequence': sequences[sid],
                'throughSequence': entry['sealed']['statistics']['throughSequence'], 'files': files})
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            manifest = json.loads(archive.read('manifest.json'))
            check(archive.namelist() == ['manifest.json', *expected] and archive.testzip() is None
                  and all(archive.read(name) == value for name, value in expected.items())
                  and manifest['schemaVersion'] == 1 and manifest['requestId'] == key and manifest['sessions'] == manifest_sessions,
                  f'{mode} batch ZIP matches the original session manifest and exact scoped CSV bytes')
        (out/f'{mode}-venue-reports.zip').write_bytes(raw)
        return route, raw

    def verify_venue_replay_ui(entries, closed, linked, earlier=None):
        mode = 'linked' if linked else 'independent'
        sources = {entry['sessionId']: entry['sealed']['world'] for entry in entries}
        rows = closed['sessions']
        check(all(row['replay'] == {'streamId': sources[row['sessionId']]['header']['streamId'],
                                   'throughSequence': sources[row['sessionId']]['acceptedSequence']} for row in rows),
              f'{mode} closure exposes the original native stream and replay boundary')
        node = shutil.which('node')
        if not node:
            raise RuntimeError('Node is required for the shipped replay console check')
        descriptor = runtime / f'{mode}-venue-replay-private.json'
        output = out / f'{mode}-venue-replay-ui.json'
        def totals(players):
            fields = ('ammoUsed', 'shotsHit', 'kills', 'hitsReceived', 'damageTaken')
            counts = {key: sum(player[key] for player in players) for key in fields}
            accuracy = round(Decimal(100 * counts['shotsHit']) / counts['ammoUsed'], 2) if counts['ammoUsed'] else 0
            return {'players': len(players), **counts, 'accuracyPercent': float(accuracy)}

        players = {entry['sessionId']: entry['sealed']['statistics']['players'] for entry in entries}
        scores = {'requestId': closed['requestId'], 'rooms': [
            {'roomId': room, 'sessionId': row['sessionId'],
             'totals': totals([player for player in players[row['sessionId']] if player['roomId'] == room])}
            for row in rows for room in row['roomIds']],
            'total': totals([player for roster in players.values() for player in roster])}
        config = {'base': uri, 'masterKey': keys['Master'], 'mode': mode, 'sessions': rows, 'scores': scores}
        if args.check_debrief_receipts:
            config['debriefReceipts'] = {'requestId': closed['requestId'], 'rooms': [
                {'sessionId': room['sessionId'], 'roomId': room['roomId'], 'rosterCount': room['totals']['players'],
                 'confirmedCount': room['totals']['players']} for room in scores['rooms']]}
        if args.check_venue_replay_alignment:
            config['alignReplay'] = closed['requestId']
        if args.check_venue_mission_time:
            config['missionTime'] = {'requestId': closed['requestId']}
            if not linked:
                target = entries[1]
                config['missionTime'].update(targetSessionId=target['sessionId'], targetRoom=2,
                    targetTimeline=[[row['packet']['sequence'], row['packet']['frame']['tick']] for row in read(out/'room-2-replay.json')])
        scoped = linked and args.check_player_room_replay
        if scoped:
            config['roomReplaySource'] = str(out/'linked-replay.json')
            config['roomReviewKey'] = keys['Room3']
            if args.check_clip_statistics_csv:
                config['checkClipStatisticsCsv'] = True
        if earlier:
            config['history'] = {'batch': earlier, 'zip': str(out/'independent-venue-reports.zip')}
        descriptor.write_text(json.dumps(config), encoding='utf-8')
        with (out/f'{mode}-venue-replay-ui.log').open('xb') as log:
            subprocess.run([node, str(ROOT/'tests/browser/check-venue-replay-native.cjs'), str(descriptor), str(output)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=75)
        result = read(output)
        check(result['scores'] == scores and scores['total']['players'] == venue_players,
              f'{mode} shipped console renders exact room and batch totals from all {venue_players} original sealed statistics')
        if args.check_debrief_receipts:
            check(result['debriefReceipts'] == config['debriefReceipts'],
                  f'{mode} shipped console renders the five original room receipt counts')
        check(result['complete'] and [item['sessionId'] for item in result['results']] == [row['sessionId'] for row in rows]
              and all(item['throughSequence'] == sources[item['sessionId']]['acceptedSequence'] for item in result['results']),
              f'{mode} shipped console opens every original sealed native replay')
        if args.check_venue_participation_gate:
            check(result['participation']==[{'sessionId':row['sessionId'],
                  'room':str(row['roomIds'][0]) if len(row['roomIds'])==1 else 'all',
                  'sequence':row['participationBegin']['frame']['worldSequence'],
                  'next':row['participationBegin']['frame']['worldSequence']+1,
                  'simulatedPlayers':5*len(row['roomIds'])} for row in rows],
                  f'{mode} shipped console reopens every original participation Begin frame and its neighbor')
        if args.check_venue_replay_alignment:
            alignment = result['alignment']
            check(alignment == {'hidden': True} if linked else alignment['requestId'] == closed['requestId']
                  and alignment['fromSessionId'] == rows[0]['sessionId'] and alignment['toSessionId'] == rows[1]['sessionId']
                  and 0 <= alignment['millisecondsBeforeAnchor'] <= 500,
                  f'{mode} shipped console scopes UTC replay alignment to separate original room recordings')
        if args.check_venue_mission_time:
            mission_match = result['missionTime']
            check(mission_match == {'hidden': True} if linked else mission_match['requestId'] == closed['requestId']
                  and mission_match['fromSessionId'] == rows[0]['sessionId'] and mission_match['toSessionId'] == rows[1]['sessionId']
                  and 0 <= mission_match['fromTick'] - mission_match['frameTick'] <= 10,
                  f'{mode} shipped console scopes mission tick alignment to the exact original room frames')
        first = result['results'][0]
        interval = first['interval']
        check(0 < interval['start'] < interval['end'] == interval['reached'] < first['throughSequence'],
              f'{mode} shipped console stops at the exact marked interval in the original sealed native replay')
        clips_path = f"/api/sessions/{first['sessionId']}/world/clips"
        shared = request(clips_path, role=f"Room{rows[0]['roomIds'][0]}")
        clip = next(clip for clip in shared['clips'] if clip['id'] == interval['clipId'])
        check(shared == request(clips_path) and len(shared['clips']) == (2 if scoped else 1)
              and shared['sessionId'] == first['sessionId'] and shared['streamId'] == sources[first['sessionId']]['header']['streamId']
              and (clip['id'], clip['startFrame'], clip['endFrame'], clip['endMilliseconds'])
              == (interval['clipId'], interval['start'], interval['end'], interval['elapsedMilliseconds']),
              f'{mode} original native replay clip is shared with the authorized room')
        check(interval['playerReplay'] == {'start': interval['start'], 'end': interval['end'],
              'originalPackets': interval['end'] - interval['start'] + 1, 'apiRequests': 0},
              f'{mode} unauthenticated player plays the exact exported native frames locally')
        if scoped:
            room = result['roomReplay']
            check(room['roomId'] == 3 and 0 < room['start'] < room['end'] <= first['throughSequence']
                  and room['retainedEvents'] > 0 and room['omittedEvents'] > 0 and room['props'] == 1 and room['apiRequests'] == 0,
                  'linked shipped room export retains original timing and room 3 combat, excluding the other four rooms')
            damage = room['latestDamage']
            check(1 <= damage['frame'] < first['throughSequence'] and damage['matches'] > 0 and damage['managementWrites'] == 0,
                  'linked room 3 controller opens its latest original damage frame without management writes')
            check(damage['contextStart']['sequence'] <= damage['frame'] <= damage['contextEnd']['sequence']
                  and 1 <= damage['contextEnd']['sequence'] - damage['contextStart']['sequence'] <= 299
                  and 0 <= damage['contextEnd']['elapsedMilliseconds'] - damage['contextStart']['elapsedMilliseconds'] <= 10000,
                  'linked room 3 controller marks and plays the original saved context around that damage')
            report = damage['clipStatistics']
            check(report['sessionId'] == first['sessionId'] and report['streamId'] == sources[first['sessionId']]['header']['streamId']
                  and (report['fromFrame'], report['throughFrame'], report['roomId']) ==
                      (damage['contextStart']['sequence'], damage['contextEnd']['sequence'], 3)
                  and len(report['players']) == 1 and report['players'][0]['hitsReceived'] >= damage['matches']
                  and report['players'][0]['damageTaken'] > 0 and report['players'][0]['accuracyPercent'] is None,
                  'linked room 3 clip statistics match the original native hits and damage for one player')
            if args.check_clip_statistics_csv:
                raw = (out/'linked-room-03-clip-statistics.csv').read_bytes()
                row, = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
                original, = report['players']
                check(raw.startswith(b'\xef\xbb\xbf') and damage['clipCsv'] is True
                      and (row['sessionId'], row['streamId'], row['reportRoomId'], row['reportPlayerId'], row['playerId'])
                          == (report['sessionId'], report['streamId'], '3', original['playerId'], original['playerId'])
                      and (int(row['fromFrame']), int(row['throughFrame'])) == (report['fromFrame'], report['throughFrame'])
                      and all(int(row[key]) == original[key] for key in ('ammoUsed','shotsHit','matchedShots','kills','hitsReceived','damageTaken'))
                      and row['accuracyPercent'] == '',
                      'linked room 3 downloads the original personal clip CSV with actual damage and an undefined hit rate')
        if earlier:
            older = earlier['sessions'][2]
            history = result['history']
            check(history['requestId'] == earlier['requestId'] and history['zipMatched']
                  and history['sessionId'] == older['sessionId'] and history['room'] == '3'
                  and history['throughSequence'] == older['replay']['throughSequence'],
                  'shipped history reopens the older original native replay and byte-identical ZIP after the Linked batch')
            if args.check_venue_participation_gate:
                sequence=older['participationBegin']['frame']['worldSequence']
                check(history['participation']=={'sessionId':older['sessionId'], 'room':'3', 'sequence':sequence,
                      'next':sequence+1, 'simulatedPlayers':5},
                      'shipped history reopens the original room 3 participation frame after room reuse')

    def observe(entry,expected,begin=None, *, record=True):
        metadata=request('/api/sessions/'+entry['sessionId']+'/world');path='/api/sessions/'+entry['sessionId']+'/world/watch?mode=live';req=urllib.request.Request(uri+path,headers={'Authorization':'Bearer '+keys['Master']})
        with urllib.request.urlopen(req,timeout=5) as response:
            kind=''
            for _ in range(80):
                line=response.readline().decode().strip()
                if line.startswith('event: '):kind=line[7:]
                if kind=='frame' and line.startswith('data: '):
                    frame=json.loads(line[6:]);rows=frame['packet']['frame']['players'];connected={p['id'] for p in rows if p['connected'] and p['rig']['kind']=='Simulated'}
                    packet=frame['packet'];source=datetime.fromisoformat(metadata['header']['captureStartedAtUtc'])+timedelta(milliseconds=packet['elapsedMilliseconds']);age=(datetime.now(timezone.utc)-source).total_seconds()
                    expected_rigs=set(expected)
                    rigs_match=connected==expected_rigs
                    if 'openxrPlayerId' in entry:
                        tracked=entry['openxrPlayerId']
                        rigs_match=connected==expected_rigs-{tracked} and {p['id'] for p in rows
                            if p['connected'] and p['rig']['kind']=='Tracked'}=={tracked}
                    if rigs_match and (begin is None or packet['frame']['phase']=='Running' and packet['frame']['tick']>0 and not packet['suspended'] and packet['observedSequence']>=begin and -1<=age<1.5):
                        if record:save(entry['label']+('-running.json' if begin is not None else '-live.json'),{'metadata':metadata,'frame':frame,'sourceAgeSeconds':age,'acceptedBeginSequence':begin})
                        return frame
                    return None
    def start_hardware_mock(feed):
        frames=[]
        room=feed['room']; sid=feed['session']; label=f'{sid}-room-{room}'
        mock_command=[sys.executable,str(hardware/'mock-device.py')]
        if hardware_manifest['toolVersion'] in ('0.2.5','0.2.6','0.2.11','0.2.12','0.2.13'):mock_command+=['--room',str(room)]
        mock=subprocess.Popen(mock_command,env=mock_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        hardware_processes.append(mock)
        def collect():
            for line in mock.stdout:
                try:frames.append(json.loads(line))
                except ValueError:frames.append({'kind':'invalid'})
        reader=threading.Thread(target=collect,daemon=True);reader.start()
        listening=wait(lambda:next((f for f in frames if f['kind']=='listening'),None),8,'mock '+label+' listening')
        bindings=[{'deviceId':str(uuid.uuid4()),'playerId':player,'admissionId':admission,'seat':seat}
                  for player,(admission,seat) in feed['players'].items()]
        setup={'version':1,'managementUrl':uri,'sessionId':sid,'roomId':room,'mockPort':listening['port'],'seconds':120,'bindings':bindings}
        config=runtime/(label+'-hardware.json')
        gateway_env={**mock_env,'VR_COMMAND_ROOM_KEY':keys[f'Room{room}']}
        simulator=str(hardware/'VrCommand.HardwareSimulator.dll')
        if hardware_manifest['toolVersion'] in ('0.2.3','0.2.4','0.2.5','0.2.6','0.2.11','0.2.12','0.2.13'):
            seat_map=runtime/(label+'-seat-map.json')
            map_value={key:value for key,value in setup.items() if key!='bindings'}
            map_value['devices']=[{'deviceId':b['deviceId'],'seat':b['seat']} for b in bindings]
            seat_map.write_text(json.dumps(map_value),encoding='utf-8')
            result=subprocess.run([dotnet,simulator,'--bind-room',str(seat_map),'--output',str(config)],
                env=gateway_env,capture_output=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
            bound=read(config) if result.returncode==0 else None
            check(bound=={**setup,'version':2,'bindings':sorted(bindings,key=lambda item:item['seat'])},
                  'room '+str(room)+' packaged binding matches the exact original device, seat and admission')
            save(label+'-hardware-binding.json',bound)
        else:
            config.write_text(json.dumps(setup),encoding='utf-8')
        report=out/(label+'-hardware-mock.json')
        gateway=subprocess.Popen([dotnet,simulator,'--live',str(config),'--output',str(report)],
            env=gateway_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        hardware_processes.append(gateway)
        return {'frames':frames,'mock':mock,'reader':reader,'gateway':gateway,'report':report,
                'devices':{b['playerId']:b['deviceId'] for b in bindings}}

    def exercise_room_combat(entries,clients):
        feeds={}
        if args.check_hardware_feedback:
            for client in clients:
                player=client['player'];room=player['roomId'];sid=client['sessionId']
                path=f'/api/sessions/{sid}/rooms/{room}/hardware-feedback'
                feed=feeds.get(path)
                if feed is None:
                    initial=request(path,role=f'Room{room}')
                    assert initial['resetReason']=='attached' and initial['signals']==[] and initial['state']=='Running'
                    feed={'cursor':initial['throughSequence'],'room':room,'session':sid,'stream':initial['streamId'],'players':{},'signals':[]}
                    feeds[path]=feed
                feed['players'][player['id']]=(player['admissionId'],player['seat'])
        if args.hardware_simulator_package:
            for feed in feeds.values():feed['mock']=start_hardware_mock(feed)
            for feed in feeds.values():
                wait(lambda:any(f['kind']=='hello' and f['roomId']==feed['room'] for f in feed['mock']['frames']),8,'mock handshake')

        def read_feedback():
            for path,feed in feeds.items():
                after=feed['cursor']
                page=request(path+f'?after={after}',role=f"Room{feed['room']}")
                assert page['state']=='Running' and page['resetReason'] is None and page['throughSequence']>=after
                assert page['sessionId']==feed['session'] and page['roomId']==feed['room'] and page['streamId']==feed['stream'] and page['combatOrigin']=='Simulation'
                for signal in page['signals']:
                    assert signal['kind']=='PlayerDamaged' and signal['damage']>0 and after<signal['eventSequence']<=page['throughSequence']
                    assert feed['players'][signal['playerId']]==(signal['admissionId'],signal['seat'])
                    feed['signals'].append(signal)
                feed['cursor']=page['throughSequence']

        def attack(entry,enabled):
            identity=str(uuid.uuid4());session=entry['sessionId']
            response=request('/api/sessions/'+session+'/commands',{'commandId':identity,'action':'SetEnemies',
                'enemies':{'count':entry['combatEnemyCount'],'behavior':'Hold','autoAttack':enabled}})
            check(response['commandId']==identity and not response['duplicate'] and response['session']['id']==session
                  and response['session']['enemies']['autoAttack'] is enabled,entry['label']+' original AI '+('enable' if enabled else 'disable')+' accepted')
            return response['appliedAtSequence']

        venue_changes = []
        def venue_attack(behavior, enabled):
            route = '/api/venue/phase'
            expected = {entry['sessionId']: entry['combatEnemyCount'] for entry in entries}
            preview = request(route)['enemies']
            targets = [{field: row[field] for field in ('sessionId', 'phaseSinceSequence', 'enemiesSinceSequence')} for row in preview]
            check({row['sessionId'] for row in targets} == set(expected)
                  and sorted(room for row in preview for room in row['roomIds']) == list(range(1, 6)),
                  'native enemy policy preview covers the original five rooms')
            policy = {'behavior': behavior, 'autoAttack': enabled}
            key = str(uuid.uuid4())
            body = {'action': 'SetEnemies', 'targets': targets, 'enemyPolicy': policy}
            receipt = request(route, body, request_id=key)
            applied = {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}
            def confirmed():
                rows = request('/api/rooms/readiness')['rooms']
                if len(rows) == 5 and all((status := row.get('venueEnemies')) and status['worldSequence']
                    and status['appliedAtSequence'] == applied.get(row['sessionId'])
                    and all(status[field] == value for field, value in policy.items()) for row in rows):
                    return rows
            observed = wait(confirmed, 20, f'{behavior} native enemy policy confirmations')
            check(not receipt['duplicate'] and receipt['requestId'] == key and set(applied) == set(expected)
                  and all(request('/api/sessions/'+sid)['enemies'] == {'count': count, **policy} for sid, count in expected.items()),
                  f'native {behavior} enemy policy confirms all sources and preserves their original targets')
            venue_changes.append({'policy': policy, 'receipt': receipt, 'rooms': observed})
            preserve_venue_control_report('linked' if len(entries) == 1 else 'independent', 'SetEnemies', receipt)
            return applied

        def stopped_attack(entry, owners, enabled, live, entry_feeds, disabled, behavior):
            def stopped():
                value=observe(entry,owners,disabled,record=False)
                return value if value and not value['packet']['frame']['autoAttack'] and value['packet']['frame']['behavior']==behavior else None
            quiet=wait(stopped,12,entry['label']+' original source disables attack')
            entry['combatWindow']={'owners':owners,'enabledSequence':enabled,'disabledSequence':disabled,
                'allDamaged':live,'disabled':quiet}
            save(entry['label']+'-combat-window.json',entry['combatWindow'])
            check(True,entry['label']+' live damage to every original player and observed attack disabled')
            if entry_feeds:entry['hardwareFeedback']=entry_feeds

        started = venue_attack('Hold', True) if args.check_venue_enemies else None
        windows=[]
        for entry in entries:
            owners={c['player']['id']:c['player']['roomId'] for c in clients if c['sessionId']==entry['sessionId']}
            enabled=started[entry['sessionId']] if started is not None else attack(entry,True)
            windows.append((entry,owners,enabled))
        observations = []
        for entry,owners,enabled in windows:
            entry_feeds=[feed for feed in feeds.values() if feed['session']==entry['sessionId']]
            def damaged():
                read_feedback()
                value=observe(entry,owners,enabled,record=False)
                complete=all({signal['playerId'] for signal in feed['signals']}==set(feed['players']) for feed in entry_feeds)
                if args.hardware_simulator_package:
                    complete=complete and all({item['signal']['playerId'] for frame in feed['mock']['frames'] if frame['kind']=='feedback'
                                               for item in frame['signals']}==set(feed['players']) for feed in entry_feeds)
                if complete and value and value['packet']['frame']['autoAttack'] and {p['playerId'] for p in value['statistics'] if p['damageTaken']>0}==set(owners):
                    return value
            live=wait(damaged,35,entry['label']+' damage to every original admission')
            if args.check_venue_enemies:
                observations.append((entry, owners, enabled, live, entry_feeds))
            else:
                stopped_attack(entry, owners, enabled, live, entry_feeds, attack(entry,False), 'Hold')
        if args.check_venue_enemies:
            disabled = venue_attack('Advance', False)
            for entry, owners, enabled, live, entry_feeds in observations:
                stopped_attack(entry, owners, enabled, live, entry_feeds, disabled[entry['sessionId']], 'Advance')
            mode = 'linked' if len(entries) == 1 else 'independent'
            save(mode+'-venue-enemies.json', venue_changes)
            if args.check_venue_enemy_ui:
                verify_setting_batch_ui(mode, 'enemy', 'latestEnemies', venue_changes[-1]['receipt'])

    def verify_setting_batch_ui(mode, kind, key, receipt):
        phase, _ = request('/api/venue/phase', raw_response=True)
        batch = field.read_json(phase)[key]
        revisions = {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}
        check(batch['requestId']==receipt['requestId']
              and {row['sessionId']:row['appliedAtSequence'] for row in batch['sessions']}==revisions,
              f'{mode} latest {kind} batch keeps the original accepted revisions')
        node = shutil.which('node')
        if not node: raise RuntimeError(f'Node is required for the packaged {kind} batch check')
        destination = out/f'{mode}-venue-{kind}-ui'; destination.mkdir()
        with tempfile.TemporaryDirectory(prefix='setting-ui-', dir=runtime) as directory:
            descriptor = Path(directory)/'fixture.json'
            descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'kind':kind,'batch':batch,
                                              'verifyDownload':args.check_venue_setting_downloads}),encoding='utf-8')
            subprocess.run([node,str(ROOT/'tests/browser/check-venue-setting-native.cjs'),str(descriptor),str(destination)],
                           cwd=ROOT/'tests/browser',check=True,timeout=65)
        observed = read(destination/'checks.json')
        check(observed['complete'] and observed['requestId']==batch['requestId'] and len(observed['rooms'])==5,
              f'{mode} packaged console confirms every original {kind} room and opens the native room 4 witness')
        if args.check_venue_setting_downloads:
            filename = f'vr-command-venue-{kind}-{batch["requestId"]}.json'
            downloaded = destination / filename
            check(observed['phaseDownload'] == filename and downloaded.read_bytes() == phase,
                  f'{mode} packaged console {kind} download matches the original phase response byte for byte')
            references = venue_control_reports[mode]
            original = Path(references[-1]['phaseReport'])
            check(original.name == f'{mode}-phase-{batch["requestId"]}.json' and original.read_bytes() == phase,
                  f'{mode} field manifest uses the exact downloaded {kind} batch response')
            references[-1] = {**references[-1], 'phaseReport': str(downloaded)}

    def check_linked_room_enemies(entry):
        session=entry['sessionId']; route=f'/api/sessions/{session}'
        def venue_fences():
            fields=('sessionId','phaseSinceSequence','enemiesSinceSequence','roomEnemiesSinceSequence')
            targets=request('/api/venue/phase')['enemies']
            return [{key:row[key] for key in fields if key in row} for row in targets], targets
        def batch(targets, request_id, expected=200):
            return request('/api/venue/phase',{'action':'SetEnemies','targets':targets,
                'enemyPolicy':{'behavior':'Hold','autoAttack':False}},expected=expected,request_id=request_id)
        def room_browser(role, **options):
            driver=ROOT/'tests/browser/check-room-enemies-native.cjs'
            browser=subprocess.run([shutil.which('node'),str(driver)],cwd=driver.parent,
                input=json.dumps({'base':uri,'token':keys[role],'sessionId':session,**options}),
                text=True,encoding='utf-8',capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
            diagnostic=browser.stderr
            for key in keys.values():diagnostic=diagnostic.replace(key,'[redacted]')
            check(browser.returncode==0,role+' Chromium room enemy check succeeded '+diagnostic[-700:])
            return json.loads(browser.stdout)
        stale,_=venue_fences()
        denied={'commandId':str(uuid.uuid4()),'action':'SetRoomEnemies','roomEnemyPolicy':{'roomId':2,'policy':{'behavior':'Patrol','autoAttack':True}}}
        request(route+'/commands',denied,'Room1',expected=403)
        request(route+'/commands',denied,'GameServer',expected=403)
        applied=room_browser('Room2')
        override={'roomId':2,'behavior':'Patrol','autoAttack':True}
        check(applied['session']['roomEnemyPolicies']==[{**override,'appliedAtSequence':applied['appliedAtSequence']}]
              and applied['session']['enemies']=={'count':5,'behavior':'Hold','autoAttack':False},
              'Room 2 has one original override while shared count and policy remain intact')
        overwritten,targets=venue_fences()
        check(len(targets)==1 and targets[0]['roomEnemiesSinceSequence']==applied['appliedAtSequence']
              and targets[0]['roomEnemyOverrideRoomIds']==[2], 'Master preview identifies the original Room 2 override')
        batch(stale,str(uuid.uuid4()),409)
        check(request(route)['roomEnemyPolicies']==applied['session']['roomEnemyPolicies']
              and room_browser('Master',venuePreview=True)=={'roomsToClear':[2]},
              'A stale batch cannot overwrite the room, and the shipped Master console identifies the room to clear')
        def witnessed():
            info=request(route+'/world')
            frame=request(route+'/world/frames/'+str(info['acceptedSequence']))
            packet=frame['packet']
            if (packet['observedSequence']>=applied['appliedAtSequence'] and packet['frame'].get('roomEnemyPolicies')==[override]
                    and any(row['roomId']==2 and row['damageTaken']>0 for row in frame['statistics'])
                    and all(row['damageTaken']==0 for row in frame['statistics'] if row['roomId']!=2)):
                return frame
        active=wait(witnessed,20,'original native room 2 policy and damage')
        cards=request('/api/rooms/readiness',role='Room2')['rooms']
        check(len(cards)==1 and cards[0]['roomId']==2 and cards[0]['enemies']['setting']['appliedAtSequence']==applied['appliedAtSequence']
              and cards[0]['enemies']['setting']['worldSequence'] is not None and cards[0]['enemies']['inherited'] is False,
              'Room 2 readiness ties its own override to an original saved frame')
        restored=request(route+'/commands',{'commandId':str(uuid.uuid4()),'action':'SetRoomEnemies',
            'roomEnemyPolicy':{'roomId':2,'policy':None}},'Room2')
        def quiet():
            info=request(route+'/world')
            packet=request(route+'/world/frames/'+str(info['acceptedSequence']))['packet']
            if (packet['observedSequence']>=restored['appliedAtSequence'] and packet['frame']['tick']>=active['packet']['frame']['tick']+24
                    and not packet['frame'].get('roomEnemyPolicies') and not any(row['walking'] for row in packet['frame']['enemies'])):
                return packet
        after=wait(quiet,15,'original room 2 returns to the venue policy')
        batch(overwritten,str(uuid.uuid4()),409)
        batch(stale,str(uuid.uuid4()),409)
        fresh,targets=venue_fences()
        check(len(targets)==1 and targets[0]['roomEnemiesSinceSequence']==restored['appliedAtSequence']
              and 'roomEnemyOverrideRoomIds' not in targets[0] and not request(route).get('roomEnemyPolicies'),
              'Both earlier previews are rejected after inheritance, even though the effective policy is the same as before')
        restored_view=room_browser('Room2',restoreSequence=restored['appliedAtSequence'])
        batch_key=str(uuid.uuid4())
        accepted=batch(fresh,batch_key)
        repeated=batch(fresh,batch_key)
        check(accepted['duplicate'] is False and repeated['duplicate'] is True and repeated['sessions']==accepted['sessions']
              and 'roomEnemiesSinceSequence' not in venue_fences()[1][0],
              'Fresh venue preview applies once and retries with its original receipt after clearing the scoped fence')
        entry['roomEnemyWitness']={'applied':applied['appliedAtSequence'],'active':active['packet']['sequence'],
                                    'restored':restored['appliedAtSequence'],'after':after['sequence'],
                                    'roomCard':restored_view,'venueApplied':accepted['sessions'][0]['appliedAtSequence']}
        save('linked-room-enemy-witness.json',entry['roomEnemyWitness'])
    def finish(entry):
        entry['process'].wait(timeout=80);w=entry['witness'];w.wait();w.close();entry['witness']=None
        report=read(entry['reportPath'])
        if 'venueIndex' in entry:
            check(report['complete'] and report['readyPublished'] and report['status']=='venue-sealed-stopped',
                  entry['label']+' original venue process final report is complete')
            if entry.get('receiptRetried'):
                check(report['sourceAttachment']=='confirmed' and report['sourceAttachmentRetried']
                      and report['endpointPublication']=='confirmed' and report['endpointPublicationRetried'],
                      entry['label']+' final report retains both confirmed retry outcomes')
            report=report['servers'][entry['venueIndex']]['result']
            check(report['sessionId']==entry['sessionId'] and report['childPid']==entry['ready']['childPid'],
                  entry['label']+' final venue result identifies the original child')
        check(entry['process'].returncode==0 and report['complete'] and report['cleanupCompleted'] and report['childExited'] and report['playerResultsAcknowledged'] is None,entry['label']+' dual seal / retained36 / original process terminal')
        check(report['udpBinding'] == entry['ready']['udpBinding'], entry['label'] + ' terminal report preserves the startup UDP observation')
        check(report['peerDiagnosticsEnabled'] is entry['peerDiagnostics'], entry['label']+' terminal report preserves the startup diagnostics choice')
        if 'layoutSession' in entry:
            state=entry['layoutSession'];mission=state['mission']
            preview=request('/api/missions/'+mission['id']+'/layout?mode='+state['mode'])
            routes=preview['routePreview']['seats']
            low, high = (-.76,-.55) if args.check_layout_fine_opening else (0,2)
            step = .125 if args.check_layout_fine_opening else None
            check(preview['canStart'] and [row['seat'] for row in routes]==list(range(5)) and all(
                row.get('sampleStep')==step and row['path'] and row['path'][-1]['z']==0
                and any(point['z']==-1 and low<point['x']<high for point in row['path'])
                for row in routes),entry['label']+' saved preview routes through the known opening')
            header=report['finalWorld']['header']
            expected={(room,prop['assetId'].capitalize(),(room-3)*14+prop['position']['x'],prop['position']['y'],prop['position']['z'],prop['yawDegrees'])
                for room in state['roomIds'] for prop in mission['definition']['props']}
            actual={(prop['roomId'],prop['kind'],prop['feet']['x'],prop['feet']['y'],prop['feet']['z'],prop['yaw']) for prop in header['props']}
            check(actual==expected and len(header['props'])==len(expected),entry['label']+' native world preserves every saved cover coordinate and opening')
            save(entry['label']+'-layout-preview.json',preview)
        closed=world.analyze(entry['work']/'telemetry'/(entry['sessionId']+'.worldlog'),expected_session=entry['sessionId']);save(entry['label']+'-journal.json',closed)
        check(closed['complete'] and closed['sealed'] and closed['unacknowledgedFrames']==0 and closed['lastFrame']['worldSequence']==report['finalWorld']['acceptedSequence'],entry['label']+' closed original journal complete / sealed / exact durable tail')
        stats=request('/api/sessions/'+entry['sessionId']+'/statistics');entry['sealed']={'world':report['finalWorld'],'statistics':stats};save(entry['label']+'-statistics.json',stats)
        frames=[];req=urllib.request.Request(uri+'/api/sessions/'+entry['sessionId']+'/world/watch?mode=replay&rate=4',headers={'Authorization':'Bearer '+keys['Master']})
        with urllib.request.urlopen(req,timeout=10) as response:
            kind=''
            for raw in response:
                line=raw.decode().strip()
                if line.startswith('event: '):kind=line[7:]
                elif line.startswith('data: '):
                    value=json.loads(line[6:])
                    if kind=='frame':frames.append(value)
                    if kind=='complete':break
        check(len(frames)==report['finalWorld']['acceptedSequence'] and [x['packet']['sequence'] for x in frames]==list(range(1,len(frames)+1)) and frames[-1]['packet']['frame']['phase']=='Ended',entry['label']+' full API replay through terminal frame')
        save(entry['label']+'-replay.json',frames)
        if args.check_venue_relay_readback and entry['label']=='linked':
            copies=runtime/'linked-relay-copies'
            copies.mkdir()
            session_id=entry['sessionId']
            before=request('/api/sessions/'+session_id)
            originals=entry['work']/'telemetry'
            combat_copy=copies/'combat.journal'
            world_copy=copies/'world.worldlog'
            shutil.copyfile(originals/(session_id+'.journal'),combat_copy)
            shutil.copyfile(originals/(session_id+'.worldlog'),world_copy)
            def relay(tool,arguments):
                dll=ROOT/'tools'/tool/'bin/Release/net10.0'/(tool+'.dll')
                result=subprocess.run([shutil.which('dotnet'),str(dll),*map(str,arguments),'--base-url',uri,
                    '--key-file',str(data/'operator-keys.json')],cwd=ROOT,capture_output=True,encoding='utf-8',timeout=30)
                check(result.returncode==0,tool+' accepts the original guarded source')
                return json.loads(result.stdout)
            combat_result=relay('VrCommand.TelemetryRelay',['--journal',combat_copy])
            world_result=relay('VrCommand.WorldRelay',['--world-journal',world_copy,'--combat-journal',combat_copy])
            check(combat_result['sessionId']==session_id and combat_result['sealedStream']
                  and combat_result['acknowledged']==before['combatStream']['acceptedSequence']
                  and world_result['sessionId']==session_id and world_result['complete'] and world_result['acknowledged']==len(frames)
                  and before['combatStream']['venueLaunchId'] and request('/api/sessions/'+session_id)==before
                  and request('/api/sessions/'+session_id+'/world')==report['finalWorld'],
                  'Both relay tools preserve the original attached batch, sealed boundaries and management state')
            save('linked-relay-readback.json',{'combat':combat_result,'world':world_result})
        if 'roomEnemyWitness' in entry:
            witness=entry['roomEnemyWitness']; route='/api/sessions/'+entry['sessionId']+'/world'
            room_by_player={body['id']:body['roomId'] for body in frames[witness['active']-1]['packet']['frame']['players']}
            shots=[event for value in frames for event in value['packet']['events'] if event['kind']=='EnemyShot']
            check(shots and all(room_by_player[event['playerId']]==2 for event in shots)
                  and all(not any(event['kind']=='EnemyShot' for event in value['packet']['events'])
                          for value in frames if value['packet']['sequence']>witness['after']),
                  'All original enemy shots stay in Room 2 and stop after the recorded restore boundary')
            window=[value['packet'] for value in frames if witness['applied']<=value['packet']['observedSequence']<witness['restored']]
            check(any(enemy['roomId']==2 and enemy['walking'] for packet in window for enemy in packet['frame']['enemies'])
                  and all(not enemy['walking'] for packet in window for enemy in packet['frame']['enemies'] if enemy['roomId']!=2),
                  'Original replay preserves actual patrol only in the overridden room')
            def timeline(room):
                pages=[]; cursor=0
                while cursor is not None:
                    page=request(route+f'/policy-frames?throughFrame={len(frames)}&afterFrame={cursor}&includeEnemyRoster=true&roomId={room}',role=f'Room{room}')
                    assert page['scannedThroughFrame']>cursor and page['roomId']==room
                    pages.append(page)
                    cursor=page['nextAfterFrame']
                assert pages[-1]['scannedThroughFrame']==len(frames)
                return pages
            room2=timeline(2); room1=timeline(1)
            transitions=[row for page in room2 for row in page['frames'] if 'enemies' in row['changes']]
            check(len(transitions)==2 and [(row['policy']['behavior'],row['policy']['autoAttack']) for row in transitions]
                  ==[('Patrol',True),('Hold',False)] and all(row['policy']['behavior']=='Hold' and not row['policy']['autoAttack']
                      for page in room1 for row in page['frames']),
                  'Room 2 timeline finds both original policy transitions while Room 1 retains Hold')
            save('linked-room-enemy-timeline.json',{'room1':room1,'room2':room2})
        if 'venueOpenxr' in entry:
            window=entry['venueOpenxr']
            check(all(frames[packet['sequence']-1]['packet']==packet for packet in window['packets']),
                  entry['label']+' sealed replay preserves all four OpenXR participation checkpoints')
            _,lost,held,_=window['packets']
            expected=set(window['players'])-{entry['openxrPlayerId']}
            check(all({row['id'] for row in value['packet']['frame']['players'] if row['connected']}==expected
                      and value['packet']['frame']['phase']=='Running' for value in frames[lost['sequence']-1:held['sequence']]),
                  entry['label']+' every replay frame of held tracking loss preserves the other admissions')
        if 'poseReviewPackets' in entry:
            check(all(frames[packet['sequence']-1]['packet']==packet for packet in entry['poseReviewPackets']),
                  entry['label']+' the reviewed interruption and returned live packets both match sealed replay')
        if 'venueReconnectWindow' in entry:
            window = entry['venueReconnectWindow']
            first, last = window['first'], window['last']
            start, end = first['sequence'], last['sequence']
            checkpoints = [first, last, *window['outage']]
            check(start < end and all(frames[packet['sequence']-1]['packet'] == packet for packet in checkpoints),
                  entry['label']+' sealed replay preserves the exact UDP reconnect window checkpoints')
            expected = window['peers']
            for value in frames[start-1:end]:
                packet = value['packet']; frame = packet['frame']
                connected = {row['id']:row['rig']['kind'] for row in frame['players'] if row['connected']}
                target = window['target']
                tracked = connected.pop(target, None)
                if (frame['phase'] != 'Running' or packet['suspended'] or connected != expected or
                        (window['outage'] and window['outage'][0]['sequence'] <= packet['sequence'] <= window['outage'][-1]['sequence'] and tracked is not None)):
                    raise AssertionError(entry['label']+' UDP reconnect replay changed an unaffected seat or lost the outage boundary')
            check(True, entry['label']+' all sealed UDP reconnect window frames preserve unaffected admissions')
            save(entry['label']+'-reconnect-window.json', {'firstSequence':start, 'lastSequence':end, 'frames':end-start+1,
                'unaffectedSeats':len(expected), 'affectedPlayerId':window['target'],
                'outageSequences':[packet['sequence'] for packet in window['outage']]})
        if 'combatWindow' in entry:
            window=entry['combatWindow']
            actual={value['packet']['sequence']:value for value in frames}
            check(all(actual.get(window[key]['packet']['sequence'])==window[key] for key in ('allDamaged','disabled')),
                  entry['label']+' exact live damage and attack-disabled checkpoints survive replay')
            proof=reconcile_ai_damage(frames,window['owners'],window['enabledSequence'],window['disabledSequence'])
            stream=request('/api/sessions/'+entry['sessionId'])['combatStream']
            check(frames[-1]['statistics']==stats['players'] and stream['sealed'] and stream['acceptedSequence']==proof['damageEvents'],
                  entry['label']+' every same-room attack, damage event and per-frame statistic agrees with the sealed ledger')
            save(entry['label']+'-combat-reconciliation.json',proof)
        if 'hardwareFeedback' in entry:
            sid=entry['sessionId'];events={};after=0
            while True:
                rows=request(f'/api/sessions/{sid}/events?after={after}&limit=500')
                events.update({event['eventId']:event for event in rows})
                if len(rows)<500:break
                after=rows[-1]['sequence']
            for feed in entry['hardwareFeedback']:
                room=feed['room']
                ended=request(f'/api/sessions/{sid}/rooms/{room}/hardware-feedback?after={feed["cursor"]}',role=f'Room{room}')
                assert ended['state']=='Ended' and ended['resetReason']=='inactive' and ended['signals']==[] and feed['stream']==entry['ready']['streamId']
                for signal in feed['signals']:
                    source=events[signal['eventId']];record=source['payload'];combat=record['report']
                    assert source['sequence']==signal['eventSequence'] and record['streamSequence']==signal['streamSequence']
                    assert record['observedSequence']==signal['observedSequence'] and record['streamId']==entry['ready']['streamId']
                    assert (combat['reportId'],combat['playerId'],combat['kind'],combat['damage'])==(signal['reportId'],signal['playerId'],signal['kind'],signal['damage'])
                check(len({s['eventId'] for s in feed['signals']})==len(feed['signals']),entry['label']+f' room {room} live hardware signals match original accepted combat reports and stop at End')
                if 'mock' in feed:
                    owned=feed.pop('mock'); log,_=owned['gateway'].communicate(timeout=12)
                    assert owned['gateway'].returncode==0 and not any(key in log for key in keys.values())
                    result=read(owned['report'])
                    assert result['complete'] and result['termination']=='ended' and result['physicalDeliveryConfirmed'] is False
                    assert (result['roomId'],result['sessionId'])==(room,sid)
                    acknowledged=[item for attempt in result['attempts'] if attempt['status']=='simulated-acknowledged' for item in attempt['deliveries']]
                    expected_players=feed.get('expectedAcknowledgedPlayers',feed['players'])
                    check(len(acknowledged)==result['acknowledged'] and {item['signal']['playerId'] for item in acknowledged}==set(expected_players),
                          entry['label']+f' room {room} mock confirmed the expected original admissions')
                    for item in acknowledged:
                        signal=item['signal'];player=signal['playerId'];original=events[signal['eventId']]
                        assert (signal['admissionId'],signal['seat'])==feed['players'][player] and item['deviceId']==owned['devices'][player]
                        assert original['sequence']==signal['eventSequence'] and original['payload']['streamId']==feed['stream']
                        assert original['payload']['report']['reportId']==signal['reportId'] and original['payload']['report']['damage']==signal['damage']
                    if 'mockBatch' in feed:
                        batch=feed['mockBatch']
                        check([frame for frame in owned['frames'] if frame['kind']=='feedback']==[batch]
                              and result['attempts']==[{'connectionId':batch['connectionId'],'batchId':batch['batchId'],
                                  'status':'simulated-acknowledged','deliveries':batch['signals']}]
                              and result['acknowledged']==1 and result['dropped']==0,
                              'the single mock device batch is acknowledged exactly once through End')
                    owned['mock'].terminate();owned['mock'].wait(timeout=5);owned['reader'].join(timeout=5)
                    check(not owned['reader'].is_alive(),entry['label']+f' room {room} mock and original gateway are terminal')
            save(entry['label']+'-hardware-feedback.json',entry['hardwareFeedback'])
        rounds.append({'name':entry['label'],'ready':entry['ready'],'report':report,'journal':closed,'replayFrames':len(frames)})
    def openxr_environment(manifest_name, tracking_loss):
        fixture_manifest=runtime/manifest_name
        fixture_manifest.write_text(json.dumps({'file_format_version':'1.0.0','runtime':
            {'api_version':'1.0','name':'VR Command pose fixture','library_path':str(args.openxr_mock_pose_dll.resolve(strict=True))}}),encoding='utf-8')
        return {'XR_RUNTIME_JSON':str(fixture_manifest),'VR_COMMAND_OPENXR_MOCK_DLL':str(runtime_file),
                'VR_COMMAND_OPENXR_TRACKING_LOSS_FILE':str(tracking_loss)}

    def check_openxr_mock():
        nonlocal observer,observer_log
        stage('native-openxr-mock')
        label='openxr-mock'
        pose_dll=args.openxr_mock_pose_dll.resolve(strict=True)
        tracking_loss=runtime/'openxr-tracking-loss.request'
        trigger_command=runtime/'openxr-trigger.request'
        trigger_ack=runtime/'openxr-trigger-ack.txt'
        trigger_command.write_text('0',encoding='ascii')
        mock_environment={**openxr_environment('openxr-pose-runtime.json',tracking_loss),
                          'VR_COMMAND_OPENXR_TRIGGER_COMMAND':str(trigger_command),'VR_COMMAND_OPENXR_TRIGGER_ACK':str(trigger_ack)}
        reconnect_command=runtime/'openxr-reconnect.request'
        reconnect_ack=runtime/'openxr-reconnect-ack.txt'
        if args.check_openxr_reconnect or args.check_openxr_revocation:
            reconnect_command.write_text('0',encoding='ascii')
            mock_environment.update(VR_COMMAND_OPENXR_RECONNECT_COMMAND=str(reconnect_command),
                                    VR_COMMAND_OPENXR_RECONNECT_ACK=str(reconnect_ack))
        entry=launch(create([1],label),label)
        sid=entry['sessionId']
        session='/api/sessions/'+sid
        owners=[]
        for name,headset in (('Desktop peer','Quest3'),('OpenXR mock','ViveXr')):
            identity=str(uuid.uuid4())
            state=request(session+'/players',{'playerId':identity,'roomId':1,'name':name,'headset':headset},role='Room1')
            owners.append(next(row for row in state['players'] if row['id']==identity))
        target={'address':address,'port':entry['ready']['port']}
        raw,_=request(session+'/rooms/1/join-ticket-bundle',
            dict(target,players=[{'playerId':p['id'],'admissionId':p['admissionId']} for p in owners]),role='Room1',raw_response=True)
        (runtime/'openxr-mock-tickets.zip').write_bytes(raw)
        clients_for_room=[]
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for index,owner in enumerate(owners):
                file=runtime/f'openxr-mock-seat-{index+1}.json'
                file.write_bytes(archive.read(f'room-01-seat-{owner["seat"]+1:02}.json'))
                content=read(file)
                check(content=={'role':'Client',**target,'joinTicket':content['joinTicket']} and content['joinTicket'],
                      'original seat connection file '+str(index+1))
                if index==1 and args.check_openxr_reconnect:
                    udp=module('openxr_reconnect_udp','udp_gate.py')
                    gate=udp.LoopbackGate(target['port'],lambda:False).start()
                    reconnect_gates.append(gate)
                    file.write_text(json.dumps(dict(content,port=gate.port)),encoding='ascii')
                clients_for_room.append(packaged_player(entry,owner,file,mock=mock_environment if index==1 else None))
        desktop,tracked=clients_for_room
        def client_log(client):
            if client['process'].poll() is not None:
                raise RuntimeError('An original player exited before End')
            return client['log'].read_text(encoding='utf-8',errors='replace') if client['log'].exists() else ''

        reconnect_states=[]
        def confirm_reconnect_sync(state):
            reconnect_states.append(state+' '+state)
            wait(lambda:reconnect_ack.is_file() and reconnect_ack.read_text(encoding='ascii').splitlines()==reconnect_states,
                 12,'OpenXR right Vive menu sync '+state)

        def set_reconnect(value):
            replace_fixture_file(reconnect_command,value)
            confirm_reconnect_sync(value)

        def tracked_connections():
            return re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$',client_log(tracked),re.M)

        wait(lambda: all('VR_CLIENT_CONNECTED id=' in client_log(c) for c in clients_for_room),35,'both signed OpenXR fixture admissions')
        lines=client_log(tracked).splitlines()
        markers=[line for line in lines if line.startswith(('VR_OPENXR_STARTUP ','VR_NETWORK_STARTED ','VR_CLIENT_CONNECTED '))]
        check(len(markers)==4 and markers[:2]==['VR_OPENXR_STARTUP status=requested','VR_OPENXR_STARTUP status=active']
              and markers[2].startswith('VR_NETWORK_STARTED role=Client started=True ')
              and markers[3].startswith('VR_CLIENT_CONNECTED id=')
              and any('Runtime Name: Unity Mock Runtime' in line for line in lines)
              and 'VR_OPENXR_STARTUP ' not in client_log(desktop),
              'actual packaged mock OpenXR starts before transport and original admission')
        save(label+'-runtime.json',{'packageVersion':mock_package_version,'manifestSha256':package.digest(openxr_mock),
            'runtimeSha256':package.digest(runtime_file),'poseDllSha256':package.digest(pose_dll),'markers':markers})
        tracked_connection_ids=tracked_connections()
        revocation_frames=[]
        expected={owners[0]['id']:(owners[0]['admissionId'],'Simulated'),owners[1]['id']:(owners[1]['admissionId'],'Tracked')}
        latest=None
        def readiness():
            nonlocal latest
            report=request(session+'/readiness')
            latest=report
            actual={row['playerId']:(row['admissionId'],row['rigKind']) for row in report['players'] if row['canParticipate']}
            return report if report['sourceState']=='Fresh' and report['observedSequence']==report['sessionSequence'] and actual==expected else None
        try:
            wait(readiness,25,'exact simulated and tracked accepted admissions')
        finally:
            save(label+'-readiness.json',latest)
        check(True,'management recognizes mock head and hands as tracked, and the separate desktop peer as simulated')
        if args.check_openxr_revocation:
            stage('native-openxr-revocation')
            previous=tracked['player']
            peer_id=desktop['player']['id']
            player_path=session+'/players/'+previous['id']
            old_file=read(tracked['configPath'])
            old_hash=package.digest(tracked['configPath'])
            ticket_route='/api/player-tickets/validate'
            old_ticket={'sessionId':sid,'ticket':old_file['joinTicket'],'protocolVersion':2}
            validation=request(ticket_route,old_ticket,role='GameServer')
            ready_revision=validation['throughSequence']
            check(validation['admissionId']==previous['admissionId'] and validation['playerId']==previous['id'],
                  'the original signed ticket validates before revocation')

            def preparing_checkpoint(revision,owner,connected,after=0):
                report=request(session+'/readiness')
                if report['sourceState']!='Fresh' or report['observedSequence']!=revision or report['sessionSequence']!=revision or report['worldSequence']<=after:
                    return None
                rows={row['playerId']:row for row in report['players']}
                roster_ids={peer_id,owner['id']} if owner else {peer_id}
                if set(rows)!=roster_ids or not rows[peer_id]['canParticipate'] or rows[peer_id]['rigKind']!='Simulated':
                    return None
                expected_rigs={peer_id:'Simulated'}
                if owner:
                    row=rows[owner['id']]
                    if (row['admissionId'],row['seat'],row['roomId'],row['canParticipate'])!=(owner['admissionId'],owner['seat'],owner['roomId'],connected):
                        return None
                    if connected:expected_rigs[owner['id']]='Tracked'
                packet=request(session+'/world/frames/'+str(report['worldSequence']))['packet']
                frame=packet['frame']
                if frame['phase']=='Preparing' and packet['observedSequence']==revision and {
                    row['id']:row['rig']['kind'] for row in frame['players'] if row['connected']}==expected_rigs:
                    return {'packet':packet,'readiness':report}
                return None

            def server_lines():
                return (entry['work']/'server.log').read_text(encoding='utf-8',errors='replace').splitlines()

            ready=wait(lambda:preparing_checkpoint(ready_revision,previous,True),12,'original admission in Preparing')
            confirm_reconnect_sync('0')
            set_reconnect('1')
            request(player_path,method='DELETE',admission=previous['admissionId'],expected=204)
            removed_revision=request(session)['sequence']
            wait(lambda:'VR_CLIENT_DISCONNECTED' in client_log(tracked)
                 and f'VR_SERVER_CLIENT_LEFT id={tracked_connection_ids[0]}' in server_lines(),15,'operator revokes the original native connection')
            removed=wait(lambda:preparing_checkpoint(removed_revision,None,False,ready['packet']['sequence']),12,'original seat removed while peer remains')
            state=request(session+'/players',{'playerId':previous['id'],'roomId':previous['roomId'],
                'name':previous['name'],'headset':previous['headset']},role='Room1')
            replacement=next(row for row in state['players'] if row['id']==previous['id'])
            revision=state['sequence']
            check(removed_revision==ready_revision+1 and revision==removed_revision+1
                  and replacement['admissionId']!=previous['admissionId'] and replacement['seat']==previous['seat'],
                  'the same player and seat receive a different admission after the original is revoked')
            request(player_path,method='DELETE',admission=previous['admissionId'],expected=409)
            rejected=request(ticket_route,old_ticket,role='GameServer',expected=403)
            check(rejected['error']=='Player ticket no longer matches the current admission.' and request(session)['sequence']==revision,
                  'the old signed ticket and the stale operator admission cannot affect the replacement')
            waiting=wait(lambda:preparing_checkpoint(revision,replacement,False,removed['packet']['sequence']+15),12,'replacement remains disconnected with menu held')
            initial_pending=[line for line in server_lines() if line.startswith('VR_SERVER_CLIENT_PENDING id=')]
            check(tracked_connections()==tracked_connection_ids and len(initial_pending)==2,
                  'held menu does not retry when the operator revokes and replaces the seat')
            set_reconnect('0')
            wait(lambda:preparing_checkpoint(revision,replacement,False,waiting['packet']['sequence']+8),12,'release reaches the eligible disconnected player')
            set_reconnect('1')
            wait(lambda:'VR_CLIENT_ADMISSION_REJECTED' in client_log(tracked)
                 and 'VR_SERVER_ADMISSION_REJECTED' in server_lines(),15,'original game server refuses the revoked ticket on a fresh menu press')
            refused=wait(lambda:preparing_checkpoint(revision,replacement,False,waiting['packet']['sequence']),12,'refused ticket never becomes a participating admission')
            pending=[line for line in server_lines() if line.startswith('VR_SERVER_CLIENT_PENDING id=')]
            check(len(pending)==3 and tracked_connections()==tracked_connection_ids
                  and package.digest(tracked['configPath'])==old_hash and server_lines().count('VR_SERVER_ADMISSION_REJECTED')==1,
                  'one old-ticket UDP attempt is refused while the other player remains admitted')
            renewed=request(player_path+'/join-ticket',{},role='Room1',admission=replacement['admissionId'])
            check(renewed['ticket']!=old_file['joinTicket'],'room desk issues a different signed ticket for the replacement admission')
            replace_fixture_file(tracked['configPath'],json.dumps(dict(old_file,joinTicket=renewed['ticket'])))
            cooled=wait(lambda:preparing_checkpoint(revision,replacement,False,refused['packet']['sequence']+24),12,'reconnect cooldown ends with menu held')
            set_reconnect('0')
            released_for_replacement=wait(lambda:preparing_checkpoint(revision,replacement,False,cooled['packet']['sequence']+8),12,'new ticket remains idle after release')
            check(tracked_connections()==tracked_connection_ids and server_lines().count('VR_SERVER_ADMISSION_REJECTED')==1,
                  'refresh and release do not automatically connect with the new ticket')
            set_reconnect('1')
            admitted=wait(lambda:preparing_checkpoint(revision,replacement,True,released_for_replacement['packet']['sequence']),15,
                          'new ticket accepts the replacement in the original process')
            tracked_connection_ids=tracked_connections()
            check(len(set(tracked_connection_ids))==2 and pending[-1].split('=')[-1] not in tracked_connection_ids
                  and tracked['witness'].kernel.WaitForSingleObject(tracked['witness'].handle,0)==258
                  and client_log(tracked).count('VR_OPENXR_STARTUP status=active')==1,
                  'only the new admission restores the tracked rig in the same player process')
            check(client_log(desktop).count('VR_CLIENT_CONNECTED id=')==1 and 'VR_CLIENT_DISCONNECTED' not in client_log(desktop),
                  'roster replacement preserves the desktop peer transport')
            owners[1]=tracked['player']=replacement
            expected[replacement['id']]=(replacement['admissionId'],'Tracked')
            revocation_frames=[row['packet'] for row in (ready,removed,waiting,refused,released_for_replacement,admitted)]
            save(label+'-revocation.json',{'acknowledged':reconnect_states,'connections':tracked_connection_ids,
                'rejectedConnection':pending[-1].split('=')[-1],'ready':ready,'removed':removed,'waiting':waiting,
                'refused':refused,'released':released_for_replacement,'admitted':admitted})
        prior_disconnects=client_log(tracked).count('VR_CLIENT_DISCONNECTED')
        begin=command(sid,'Begin')['appliedAtSequence']
        def running(minimum_tick=1):
            metadata=request(session+'/world')
            packet=request(session+'/world/frames/'+str(metadata['acceptedSequence']))['packet']
            frame=packet['frame']
            rigs={row['id']:row['rig']['kind'] for row in frame['players'] if row['connected']}
            return packet if packet['observedSequence']>=begin and frame['phase']=='Running' and frame['tick']>=minimum_tick and rigs=={key:value[1] for key,value in expected.items()} else None
        packet=wait(running,15,'original Running replay frame with both rig types')
        save(label+'-running-pose.json',packet)
        tracked_pose=next(row for row in packet['frame']['players'] if row['id']==tracked['player']['id'])
        head=tracked_pose['head']
        hands=[tracked_pose['rig']['left'],tracked_pose['rig']['right']]
        check(abs(head['y']-1.65)<.001 and all(
            abs(hand['y']-1.25)<.001 and abs(hand['x']-head['x'])<.001 and abs(hand['z']-head['z']-.4)<.001
            for hand in hands),'accepted head and both hands match the fixture coordinates in the live world')
        tracked_id=tracked['player']['id']
        desktop_id=desktop['player']['id']
        magazine=tracked_pose['magazine']
        original_config_hash=package.digest(tracked['configPath'])
        expected_admissions={(p['id'],p['admissionId'],p['roomId'],p['seat']) for p in owners}
        acknowledged=[]
        feed=None
        if openxr_hardware:
            hardware_route=session+'/rooms/1/hardware-feedback'
            initial=request(hardware_route,role='Room1')
            check(initial['state']=='Running' and initial['resetReason']=='attached' and initial['signals']==[]
                  and initial['streamId']==entry['ready']['streamId'] and initial['runningSinceSequence']==begin,
                  'room hardware reader attaches to the original Running stream with an empty cursor')
            request(hardware_route,role='Room2',expected=403)
            check(True,'another room key cannot read the original hardware route')
            feed={'cursor':initial['throughSequence'],'room':1,'session':sid,'stream':initial['streamId'],
                  'players':{p['id']:(p['admissionId'],p['seat']) for p in owners},'signals':[],
                  'expectedAcknowledgedPlayers':[tracked_id]}
            feed['mock']=start_hardware_mock(feed)
            wait(lambda:any(f['kind']=='hello' and f['roomId']==1 for f in feed['mock']['frames']),8,'OpenXR hardware mock handshake')

        def feedback_page():
            page=request(hardware_route+f'?after={feed["cursor"]}',role='Room1')
            assert page['sessionId']==sid and page['roomId']==1 and page['streamId']==feed['stream']
            assert page['state']=='Running' and page['resetReason'] is None and page['combatOrigin']=='Simulation'
            assert page['runningSinceSequence']==begin and page['throughSequence']>=feed['cursor']
            assert all(feed['cursor']<s['eventSequence']<=page['throughSequence'] for s in page['signals'])
            feed['cursor']=page['throughSequence']
            return page

        def expect_trigger(*states):
            acknowledged.extend(states)
            def synced():
                return trigger_ack.is_file() and trigger_ack.read_text(encoding='ascii').splitlines()==acknowledged
            wait(synced,12,'original OpenXR trigger sync '+states[-1])

        def set_trigger(value,*states):
            replace_fixture_file(trigger_command,value)
            expect_trigger(*states)

        def magazine_at(frame):
            return next(row['magazine'] for row in frame['frame']['players'] if row['id']==tracked_id)
        if args.observe_closure_ui:
            node=shutil.which('node')
            if not node:
                raise RuntimeError('The optional console observation requires Node')
            descriptor=runtime/'openxr-console-private.json'
            end_request=runtime/'openxr-console-end.request'
            descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'sessionId':sid,
                'streamId':entry['ready']['streamId'],'endRequestFile':str(end_request),
                'trackedParticipation':{'roomId':1,'seat':tracked['player']['seat']+1},
                'weaponAmmunition':[{'name':c['player']['name'],'ammoUsed':int(c is tracked)} for c in clients_for_room]}),
                encoding='utf-8')
            observer_log=(out/'openxr-console.log').open('xb')
            observer=subprocess.Popen([node,str(ROOT/'tests/browser/check-closure-native.cjs'),
                '--descriptor',str(descriptor),'--output',str(observer_out),'--stop-file',str(observer_stop)],
                stdout=observer_log,stderr=subprocess.STDOUT,cwd=ROOT/'tests/browser')

        def console_observation(name):
            def observed():
                path=observer_out/name
                if path.is_file():
                    return read(path)
                if observer.poll() is not None:
                    raise RuntimeError('OpenXR console observer exited before '+name)
                return None
            return wait(observed,25,'OpenXR console '+name)

        if args.observe_closure_ui:
            check(console_observation('ready.json')['selectedSessionId']==sid,'shipped console observes the original Running room')
        expect_trigger('0 0')

        def tracking_checkpoint(available, minimum_tick, *, revision=begin):
            report=request(session+'/readiness')
            rows={row['playerId']:row for row in report['players']}
            if (report['sourceState']!='Fresh' or report['observedSequence']!=revision or report['sessionSequence']!=revision
                    or {(row['playerId'],row['admissionId'],row['roomId'],row['seat']) for row in rows.values()}!=expected_admissions):
                return None
            owner=rows[tracked_id]
            if (owner['canParticipate'] is not available or owner['state']!=('Participating' if available else 'PoseUnavailable')
                    or (available and owner['rigKind']!='Tracked')
                    or rows[desktop_id]['rigKind']!='Simulated' or not rows[desktop_id]['canParticipate']):
                return None
            frame=request(session+'/world/frames/'+str(report['worldSequence']))['packet']
            players={row['id']:row for row in frame['frame']['players']}
            if (frame['frame']['phase']!='Running' or frame['frame']['tick']<minimum_tick
                    or players[tracked_id]['connected'] is not available or not players[desktop_id]['connected']):
                return None
            if available:
                pose=players[tracked_id]
                joints=[pose['head'],pose['rig']['left'],pose['rig']['right']]
                if pose['rig']['kind']!='Tracked' or any(abs(new['x']-old['x']-.2)>=.001
                    for new,old in zip(joints,[head,*hands],strict=True)):
                    return None
            rooms=request('/api/rooms/readiness',role='Room1')['rooms']
            if len(rooms)!=1:
                return None
            room=rooms[0]
            if (room['sessionId']!=sid or room['sessionSequence']!=revision or room['sourceState']!='Fresh'
                    or room['simulatedReady']!=1 or room['trackedReady']!=int(available)
                    or room['vrParticipation']['awaitingPose']!=([] if available else [tracked['player']['seat']+1])):
                return None
            return {'packet':frame,'readiness':report,'room':room}

        tracking_loss.touch(exist_ok=False)
        try:
            lost=wait(lambda:tracking_checkpoint(False,packet['frame']['tick']+1),12,'tracked seat loses readiness')
            save(label+'-tracking-lost.json',lost)
            set_trigger('1','1 1')
            held=wait(lambda:tracking_checkpoint(False,lost['packet']['frame']['tick']+14),12,'tracked seat stays unavailable during Running')
            save(label+'-tracking-held.json',held)
            if args.observe_closure_ui:
                alert=console_observation('participation-alert.json')
                check(alert['roomId']==1 and alert['seat']==tracked['player']['seat']+1,'shipped console flags only the original OpenXR seat')
        finally:
            tracking_loss.unlink()
        check(True,'same Running room marks only the original OpenXR seat unavailable during controller tracking loss')
        recovered=wait(lambda:tracking_checkpoint(True,held['packet']['frame']['tick']+1),12,'same tracked seat accepts a new pose after recovery')
        save(label+'-tracking-recovered.json',recovered)
        check(package.digest(tracked['configPath'])==original_config_hash
              and tracked_connections()==tracked_connection_ids
              and client_log(tracked).count('VR_CLIENT_DISCONNECTED')==prior_disconnects
              and tracked['witness'].kernel.WaitForSingleObject(tracked['witness'].handle,0)==258,
              'original OpenXR process and connection recover with the same ticket and newly accepted head and hand positions')
        if args.observe_closure_ui:
            restored=console_observation('participation-recovered.json')
            check(restored['roomId']==1 and restored['seat']==tracked['player']['seat']+1,'shipped console clears the OpenXR tracking alert')
        held_recovered=wait(lambda:running(recovered['packet']['frame']['tick']+14),12,'original rig remains ready with the trigger held')
        check(magazine_at(held_recovered)==magazine,'trigger held through tracking recovery cannot fire')
        set_trigger('0','0 0')
        released=wait(lambda:running(held_recovered['frame']['tick']+14),12,'original ready rig after trigger release')
        check(magazine_at(released)==magazine,'trigger release leaves the original magazine unchanged')
        if feed is not None:
            quiet=feedback_page()
            check(quiet['signals']==[] and feed['mock']['gateway'].poll() is None
                  and not any(frame['kind']=='feedback' for frame in feed['mock']['frames']),
                  'tracking loss, held recovery and trigger release generate no feedback for either bound device')
            save(label+'-hardware-before-tap.json',quiet)
        set_trigger('2','2 1','2 0')
        if feed is not None:
            page=wait(lambda:(value if (value:=feedback_page())['signals'] else None),5,'one original live OpenXR hardware signal')
            check(len(page['signals'])==1,'one live hardware signal follows the new OpenXR tap')
            signal=page['signals'][0]
            check(signal['kind']=='ShotFired' and signal['playerId']==tracked_id and signal['damage']==0
                  and (signal['admissionId'],signal['seat'])==feed['players'][tracked_id] and signal['observedSequence']==begin,
                  'live logical recoil signal belongs to the original tracked admission and seat')
            batch=wait(lambda:next((f for f in feed['mock']['frames'] if f['kind']=='feedback'),None),5,'original mock device feedback batch')
            check(batch['mode']=='simulation' and batch['roomId']==1 and batch['streamId']==feed['stream']
                  and batch['runningSinceSequence']==begin
                  and batch['signals']==[{'deviceId':feed['mock']['devices'][tracked_id],'signal':signal}],
                  'TCP mock device receives the original shot for the tracked device only')
            feed['signals']=page['signals']
            feed['mockBatch']=batch
            entry['hardwareFeedback']=[feed]

        def shot():
            frame=running(released['frame']['tick']+1)
            if frame and magazine_at(frame)<magazine-1:
                raise RuntimeError('One test tap consumed more than one round')
            return frame if frame and magazine_at(frame)==magazine-1 else None

        fired=wait(shot,12,'one accepted shot from the new OpenXR trigger press')
        after_tap=wait(lambda:running(fired['frame']['tick']+14),12,'original world after the single trigger tap')
        check(magazine_at(after_tap)==magazine-1,'one new OpenXR trigger press consumes exactly one round')
        save(label+'-trigger.json',{'acknowledged':acknowledged,'heldAfterRecovery':held_recovered,
                                    'released':released,'fired':fired,'afterTap':after_tap})
        reconnect_frames=[]
        reconnect_ids=[]
        if args.check_openxr_reconnect:
            stage('native-openxr-reconnect')
            reconnect_revision=request(session)['sequence']
            confirm_reconnect_sync('0')
            set_reconnect('1')
            reconnect_ids=tracked_connections()
            check(len(reconnect_ids)==1 and markers[2].endswith('port='+str(gate.port))
                  and gate.counts['upstream']>0 and gate.counts['downstream']>0,
                  'original tracked player passes real NGO UDP through its private relay')
            gate.close()
            gate_report=gate.report()
            check(gate_report['threadStopped'] and gate_report['error'] is None,'owned UDP relay closes before original client disconnect')
            server_log=entry['work']/'server.log'
            wait(lambda:'VR_CLIENT_DISCONNECTED' in client_log(tracked)
                 and f'VR_SERVER_CLIENT_LEFT id={reconnect_ids[0]}' in server_log.read_text(encoding='utf-8',errors='replace').splitlines(),
                 45,'original client and server report the UDP disconnect')
            lost_udp=wait(lambda:tracking_checkpoint(False,after_tap['frame']['tick']+1,revision=reconnect_revision),12,
                          'only original tracked player loses participation after UDP disconnect')
            updated=request(session+'/players/'+tracked_id+'/join-ticket',{},role='Room1',admission=tracked['player']['admissionId'])
            original=read(tracked['configPath'])
            check(updated['ticket']!=original['joinTicket'] and updated['ticket'] and request(session)['sequence']==reconnect_revision,
                  'room desk issues a fresh signed ticket for the original admission without mutating the room')
            replace_fixture_file(tracked['configPath'],json.dumps({'role':'Client',**target,'joinTicket':updated['ticket']}))
            updated_hash=package.digest(tracked['configPath'])
            held_button=wait(lambda:tracking_checkpoint(False,lost_udp['packet']['frame']['tick']+50,revision=reconnect_revision),12,
                        'right Vive menu stays held after eligible disconnect')
            check(tracked_connections()==reconnect_ids and 'VR_CLIENT_ADMISSION_REJECTED' not in client_log(tracked),
                  'held right Vive menu cannot reconnect after the UDP interruption and ticket refresh')
            set_reconnect('0')
            released_button=wait(lambda:tracking_checkpoint(False,held_button['packet']['frame']['tick']+14,revision=reconnect_revision),12,
                            'right Vive menu release without reconnect')
            check(tracked_connections()==reconnect_ids,'right Vive menu release alone does not reconnect')
            set_reconnect('1')
            wait(lambda:len(tracked_connections())==2,15,'new original NGO connection from right Vive menu')
            renewed=wait(lambda:tracking_checkpoint(True,released_button['packet']['frame']['tick']+1,revision=reconnect_revision),15,
                         'original admission recovers its tracked pose through the game UDP endpoint')
            reconnect_ids=tracked_connections()
            prior_pose,next_pose=(next(p for p in frame['frame']['players'] if p['id']==tracked_id)
                                  for frame in (after_tap,renewed['packet']))
            check(len(set(reconnect_ids))==2 and package.digest(tracked['configPath'])==updated_hash
                  and tracked['witness'].kernel.WaitForSingleObject(tracked['witness'].handle,0)==258
                  and client_log(tracked).count('VR_OPENXR_STARTUP status=active')==1
                  and client_log(tracked).count('VR_CLIENT_DISCONNECTED')==1
                  and 'VR_CLIENT_ADMISSION_REJECTED' not in client_log(tracked)
                  and all(prior_pose[key]==next_pose[key] for key in ('health','magazine','reserve')),
                  'new right Vive menu press reloads the ticket in the same tracked player process and preserves combat state')
            tracked_connection_ids=reconnect_ids
            reconnect_frames=[lost_udp['packet'],held_button['packet'],released_button['packet'],renewed['packet']]
            save(label+'-reconnect.json',{'relay':gate_report,'acknowledged':reconnect_states,'connections':reconnect_ids,
                'refreshedConfigSha256':updated_hash,'managementRevision':reconnect_revision,
                'before':after_tap,'lost':lost_udp,'held':held_button,'released':released_button,'renewed':renewed})
        if args.observe_closure_ui:
            ammunition=console_observation('weapon-ammunition.json')
            check({row['name']:row['ammoUsed'] for row in ammunition}
                  == {c['player']['name']:str(int(c is tracked)) for c in clients_for_room},
                  'shipped console shows the exact OpenXR and desktop ammunition counts before End')
            end_request.touch(exist_ok=False)
            check(console_observation('end-receipt.json')['sessionId']==sid,'shipped console ends the original OpenXR room')
        else:
            command(sid,'End')
        finish(entry)
        if args.observe_closure_ui:
            observer.wait(timeout=45)
            ui=read(observer_out/'checks.json')
            check(observer.returncode==0 and ui['complete'] and ui['browserClosed']
                  and ui['acceptedWorldSequence']==entry['sealed']['world']['acceptedSequence'],
                  'shipped console observes the exact OpenXR world seal and closes')
            observer_log.close()
            observer_log=None
            observer=None
        replay=read(out/(label+'-replay.json'))
        checkpoints=[packet,lost['packet'],held['packet'],recovered['packet'],held_recovered,released,fired,after_tap,*reconnect_frames]
        check(all(replay[frame['sequence']-1]['packet']==frame for frame in checkpoints),
              'exact tracked, lost and recovered Running checkpoints survive in the sealed replay')
        held_frames=replay[lost['packet']['sequence']-1:held['packet']['sequence']]
        check(len(held_frames)>1 and all({row['id']:row['connected'] for row in frame['packet']['frame']['players']}
              == {desktop_id:True,tracked_id:False} for frame in held_frames),
              'every saved frame during the held loss preserves desktop participation and OpenXR unavailability')
        if reconnect_frames:
            interrupted=replay[reconnect_frames[0]['sequence']-1:reconnect_frames[2]['sequence']]
            check(len(interrupted)>1 and all({row['id']:row['connected'] for row in frame['packet']['frame']['players']}
                  == {desktop_id:True,tracked_id:False} for frame in interrupted),
                  'sealed replay preserves only the tracked UDP outage through the release of right Vive menu')
        if revocation_frames:
            check(all(replay[frame['sequence']-1]['packet']==frame for frame in revocation_frames),
                  'sealed replay preserves each original admission, revocation, refusal and replacement checkpoint')
            inactive=replay[revocation_frames[1]['sequence']-1:revocation_frames[-2]['sequence']]
            peer_ready_by_revision={}
            for value in inactive:
                saved=value['packet']
                frame=saved['frame']
                connected={row['id'] for row in frame['players'] if row['connected']}
                assert frame['phase']=='Preparing' and not saved['suspended'] and connected<={desktop_id}
                peer_ready_by_revision.setdefault(saved['observedSequence'],[]).append(desktop_id in connected)
            # Preparing rebuilds pose state when the roster changes. Only the prefix before the next valid pose may be empty.
            check(set(peer_ready_by_revision)=={revocation_frames[1]['observedSequence'],revocation_frames[-2]['observedSequence']}
                  and all(any(rows) and all(rows[rows.index(True):]) for rows in peer_ready_by_revision.values()),
                  'sealed replay excludes the old ticket and retains the peer after pose reacquisition in each roster revision')
            result=request('/api/player-tickets/validate',{'sessionId':sid,'ticket':renewed['ticket'],'protocolVersion':2},role='GameServer',expected=403)
            check(result['error']=='Player ticket no longer matches the current admission.',
                  'the replacement ticket also becomes invalid when the original session ends')
        check(all(magazine_at(frame['packet'])==magazine for frame in replay[packet['sequence']-1:released['sequence']]),
              'sealed playback confirms no firing throughout tracking loss, held recovery and release')
        shots=[(frame['packet']['sequence'],event) for frame in replay
               for event in frame['packet']['events'] if event['kind']=='ShotFired']
        check(len(shots)==1 and released['sequence']<shots[0][0]<=fired['sequence']
              and shots[0][1]['playerId']==tracked_id and shots[0][1]['hasRay'],
              'sealed playback contains one ray-bearing shot by the original OpenXR player after the new press')
        if feed is not None:
            event=shots[0][1]
            accepted=next(row for row in request(session+'/events?limit=500') if row['eventId']==signal['eventId'])
            report=accepted['payload']['report']
            check(report['reportId']==signal['reportId']==event['eventId'] and report['shotId']==event['shotId'],
                  'the acknowledged recoil signal matches the original accepted combat report and sealed shot identifiers')
        for client in clients_for_room:
            log=client_log(client)
            finals=[json.loads(line.removeprefix('VR_CLIENT_DEBRIEF_FINAL ')) for line in log.splitlines() if line.startswith('VR_CLIENT_DEBRIEF_FINAL ')]
            connections=re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$',log,re.M)
            expected_connections=tracked_connection_ids if client is tracked else connections[:1]
            check(venue.player_result_phase(log)=='acknowledged' and len(finals)==1 and connections and connections==expected_connections,
                  'original result and terminal disconnect on the last accepted connection')
            debrief.validate_result(finals[0],{'id':sid},client['player'],entry['sealed'])
            check(finals[0]['ammoUsed']==int(client is tracked),'sealed ammunition matches the original player input')
            client.update(final=finals[0],connection=int(connections[-1]))
            save(client['player']['id']+'-result.json',client['final'])
            stop_player(client)
        verify_delivery(entry,clients_for_room)

    def verify_interrupted_replay(entry, client):
        session = '/api/sessions/' + entry['sessionId']
        path = session + '/world'
        saved = request(path)
        state = request(session)
        stats = request(session + '/statistics')
        check(state['state'] == 'Ended' and not state['combatStream']['sealed'] and stats['pendingTelemetry']
              and not saved['complete'] and saved['acceptedSequence'] > 1,
              'interrupted source leaves accepted frames and pending combat after End')
        raw, headers = request(path + '/watch?mode=replay&fromFrame=1&throughFrame=latest&rate=4', role='Room1', raw_response=True)
        messages = []
        for block in raw.decode('utf-8').strip().split('\n\n'):
            kind, data = block.split('\n', maxsplit=1)
            messages.append((kind.removeprefix('event: '), json.loads(data.removeprefix('data: '))))
        frames = [value for kind, value in messages if kind == 'frame']
        tail = saved['acceptedSequence']
        check(headers.get_content_type() == 'text/event-stream' and messages[0] == ('header', saved)
              and messages[-1] == ('saved-end', saved) and all(kind != 'complete' for kind, _ in messages)
              and [frame['packet']['sequence'] for frame in frames] == list(range(1, tail + 1)),
              'interrupted native replay closes at the exact saved boundary without a seal')
        exact = request(path + f'/frames/{tail}', role='Room1')
        check(frames[-1] == exact and exact['packet']['frame']['phase'] == 'Running'
              and any(row['damageTaken'] > 0 for row in exact['statistics']) and request(path) == saved,
              'saved native tail retains exact original damage and statistics')
        request(session + '/report.csv', expected=409)
        request(session + '/rooms/1/report.csv', role='Room1', expected=409)
        stop_player(client)
        check('VR_CLIENT_DEBRIEF_FINAL ' not in client['log'].read_text(encoding='utf-8', errors='replace'),
              'interrupted run gives neither a final operator CSV nor a player final result')
        save('parent-exit-saved-replay.json', {'world': saved, 'combatAcceptedSequence': state['combatStream']['acceptedSequence'],
             'terminalEvent': messages[-1][0], 'frames': frames, 'finalCsvAvailable': False, 'playerFinalReceived': False})
    def verify_quest_tracking(linked, target_status='not-tracked', checkpoint=None):
        mode='linked' if linked else 'independent'
        bundle=runtime/(mode+'-vr-venue-connections.zip')
        full_venue=['-AllHeadsets'] if args.check_quest_vr_partial_map else []
        command_line=[shutil.which('pwsh'),'-NoProfile','-File',str(ROOT/'scripts/deploy-quest.ps1'),
            '-VenueBundle',str(bundle),'-ManagementApi',uri,'-VerifyTrackedSeats','-AdbPath',str(runtime/'absent-adb.exe'),
            *full_venue]
        environment={**os.environ,'VR_COMMAND_MASTER_KEY':keys['Master']}
        tracking=subprocess.run(command_line,env=environment,timeout=25,encoding='utf-8',capture_output=True)
        report=json.loads(tracking.stdout)
        suffix='-'+checkpoint if checkpoint else ''
        save(mode+'-vr-venue-tracked-readiness'+suffix+'.json',report)
        check(tracking.returncode==1 and report['complete'] is False and report['managementVerified'] is True and report.get('sampledAtUtc')
              and [(row['roomId'],row['seat'],row['status'],row['sourceState']) for row in report['seats']]==
                  [(room,seat,target_status if (room,seat)==(5,2) else 'not-tracked','Fresh')
                   for room in range(1,6) for seat in range(1,6)],
              mode+' original venue ZIP reports room 5 seat 2 '+target_status+' and the remaining seats not-tracked')
        if full_venue:
            check(report['scope']=='venue' and [(row['roomId'],row['seat'],row['registeredHeadset']) for row in report['seats']]==
                  [(room,seat,'ViveXr' if seat in (2,4) else 'Quest3') for room in range(1,6) for seat in range(1,6)],
                  mode+' venue tracking includes all original Quest and VIVE admissions')
        if args.check_quest_tracking_wait:
            initial_revision = {row['id']:row['sequence'] for row in request('/api/sessions')}
            waiting = subprocess.run([*command_line, '-WaitForTrackedSeconds', '3'], env=environment, timeout=20,
                                     encoding='utf-8', capture_output=True)
            waited = json.loads(waiting.stdout)
            save(mode+'-vr-venue-tracked-wait.json', waited)
            check(waiting.returncode == 1 and waited['complete'] is False and waited['managementVerified'] is True
                  and waited['wait']['outcome'] == 'timed-out' and waited['wait']['maximumSeconds'] == 3
                  and waited['wait']['samples'] >= 2 and waited['sampledAtUtc'] > report['sampledAtUtc']
                  and len(waited['seats']) == 25 and all(current['worldSequence'] > first['worldSequence']
                      and {key:value for key,value in current.items() if key != 'worldSequence'} ==
                          {key:value for key,value in first.items() if key != 'worldSequence'}
                      for current, first in zip(waited['seats'], report['seats'], strict=True)),
                  mode+' tracked wait returns the latest original sample without treating same-PC simulated poses as tracked')
            check(initial_revision == {row['id']:row['sequence'] for row in request('/api/sessions')},
                  mode+' tracked wait leaves all original management revisions unchanged')
        if checkpoint == 'initial':
            route = '/api/venue/tracked-readiness'
            rooms = [{'roomId': row['id'], 'sessionId': row['sessionId']} for row in request('/api/rooms')]
            body = {'topology': 'Linked' if linked else 'Independent', 'rooms': rooms[::-1]}
            request(route, body, role='Room5', expected=403)
            request(route, body, role='GameServer', expected=403)
            request(route, dict(body, rooms=rooms[:-1]), expected=400)
            wrong = [dict(rooms[0], sessionId=str(uuid.uuid4())), *rooms[1:]] if not linked else [
                dict(room, sessionId=str(uuid.UUID(int=1))) for room in rooms]
            request(route, dict(body, rooms=wrong), expected=409)
            raw, headers = request(route, body, raw_response=True)
            sample = json.loads(raw)
            ids = list(dict.fromkeys(room['sessionId'] for room in rooms))
            check(headers['Cache-Control'] == 'no-store' and sample['topology'] == body['topology']
                  and sample['maxSourceAgeMilliseconds'] == 1500 and sample['version'] == 1
                  and [row['sessionId'] for row in sample['sessions']] == ids
                  and all(row['sampledAtUtc'] == sample['sampledAtUtc'] and row['sourceState'] == 'Fresh'
                          and row['observedSequence'] == row['sessionSequence'] for row in sample['sessions']),
                  mode+' venue sample binds the original sessions to one clock and rejects other roles and sessions')
            for row in sample['sessions']:
                frame = request(f"/api/sessions/{row['sessionId']}/world/frames/{row['worldSequence']}")['packet']
                check(frame['observedSequence'] == row['observedSequence']
                      and {player['id']: player['rig']['kind'] for player in frame['frame']['players']} ==
                          {player['playerId']: player['rigKind'] for player in row['players']},
                      mode+' sampled tracking matches the original stored game frame')
            save(mode+'-venue-tracking-sample.json', sample)

    def verify_venue_openxr(entries,round_clients,linked):
        mode='linked' if linked else 'independent'
        entry=next(item for item in entries if 'openxrPlayerId' in item)
        tracked=entry['openxrPlayerId'];sid=entry['sessionId'];session='/api/sessions/'+sid
        original=next(c for c in round_clients if c['player']['id']==tracked)
        scoped={c['player']['id']:c['player'] for c in round_clients if c['sessionId']==sid}
        sessions_by_room={c['player']['roomId']:c['sessionId'] for c in round_clients}
        begin=read(out/(entry['label']+'-running.json'))['acceptedBeginSequence']
        config_hash=package.digest(original['configPath'])

        def checkpoint(available, minimum_tick, revision=begin):
            rooms=request('/api/rooms/readiness')['rooms']
            if {row['roomId']:row['sessionId'] for row in rooms}!=sessions_by_room or len(rooms)!=5:
                return None
            if any(row['sourceState']!='Fresh' or row['registered']!=5 or row['simulatedReady']!=(4 if row['roomId']==5 else 5)
                   or row['trackedReady']!=int(row['roomId']==5 and available)
                   or row['vrParticipation']['awaitingPose']!=([2] if row['roomId']==5 and not available else []) for row in rooms):
                return None
            if args.check_venue_live_tracking and any(row.get('venueTracking')!={
                'trackedSeats':[2] if row['roomId']==5 and available else [],
                'simulatedSeats':[1,3,4,5] if row['roomId']==5 else [1,2,3,4,5],
                'waitingSeats':[2] if row['roomId']==5 and not available else [], 'eliminatedSeats':[]
            } for row in rooms):
                return None
            report=request(session+'/readiness')
            if report['sourceState']!='Fresh' or report['observedSequence']!=revision or report['sessionSequence']!=revision:
                return None
            expected={(pid,row['admissionId'],row['roomId'],row['seat'],pid!=tracked or available) for pid,row in scoped.items()}
            if {(row['playerId'],row['admissionId'],row['roomId'],row['seat'],row['canParticipate']) for row in report['players']}!=expected:
                return None
            packet=request(session+'/world/frames/'+str(report['worldSequence']))['packet']
            frame=packet['frame']
            rigs={row['id']:row['rig']['kind'] for row in frame['players'] if row['connected']}
            expected_rigs={pid:'Tracked' if pid==tracked else 'Simulated' for pid in scoped if pid!=tracked or available}
            if packet['observedSequence']==revision and frame['phase']=='Running' and frame['tick']>=minimum_tick and rigs==expected_rigs:
                return {'packet':packet,'rooms':rooms,'readiness':report}
            return None

        stage('running-venue-openxr',mode=mode)
        ready=wait(lambda:checkpoint(True,1),20,mode+' original OpenXR venue seat')
        verify_quest_tracking(linked,'tracked-ready','initial')
        marker=entry['openxrLossMarker']
        marker.touch(exist_ok=False)
        try:
            lost=wait(lambda:checkpoint(False,ready['packet']['frame']['tick']+1),15,mode+' original OpenXR loss')
            verify_quest_tracking(linked,'awaiting-tracked-pose','lost')
            held=wait(lambda:checkpoint(False,lost['packet']['frame']['tick']+14),15,mode+' isolated held tracking loss')
            if args.check_venue_pose_review:
                verify_venue_pose_review(entry, original['player'], marker, mode, held['packet']['sequence'])
        finally:
            marker.unlink(missing_ok=True)
        recovered=wait(lambda:checkpoint(True,held['packet']['frame']['tick']+1),15,mode+' original OpenXR recovery')
        verify_quest_tracking(linked,'tracked-ready','recovered')
        if args.check_venue_live_tracking:
            scoped_rooms=request('/api/rooms/readiness',role='Room5')['rooms']
            check(len(scoped_rooms)==1 and scoped_rooms[0]['roomId']==5 and 'venueTracking' not in scoped_rooms[0],
                  mode+' native tracking overview identifies the original lost and recovered seat only for Master')
        packets=[value['packet'] for value in (ready,lost,held,recovered)]
        first,last=(next(row for row in packet['frame']['players'] if row['id']==tracked) for packet in (packets[0],packets[-1]))
        x_offsets=[last['head']['x']-first['head']['x'],*[last['rig'][hand]['x']-first['rig'][hand]['x'] for hand in ('left','right')]]
        log=original['log'].read_text(encoding='utf-8',errors='replace')
        check(all(abs(offset-.2)<.001 for offset in x_offsets) and package.digest(original['configPath'])==config_hash
              and log.count('VR_CLIENT_CONNECTED id=')==1 and 'VR_CLIENT_DISCONNECTED' not in log
              and 'VR_OPENXR_STARTUP status=active' in log and 'Runtime Name: Unity Mock Runtime' in log
              and original['witness'].kernel.WaitForSingleObject(original['witness'].handle,0)==258,
              mode+' only room 5 seat 2 loses tracked readiness and recovers new poses on the original OpenXR connection')
        entry['venueOpenxr']={'packets':packets,'players':list(scoped)}
        save(mode+'-venue-openxr-checkpoints.json',{'ready':ready,'lost':lost,'held':held,'recovered':recovered,
            'mockRuntimeSha256':package.digest(runtime_file),'fixtureSha256':package.digest(args.openxr_mock_pose_dll)})
        if args.check_venue_openxr_reconnect:
            verify_venue_openxr_reconnect(entries, round_clients, entry, original, checkpoint, recovered, mode)

    def verify_venue_pose_review(entry, player, marker, mode, minimum_sequence):
        node = shutil.which('node')
        if not node:
            raise RuntimeError('Node is required for the packaged pose review browser')
        destination = out / (mode + '-pose-review')
        destination.mkdir()
        room, seat = player['roomId'], player['seat'] + 1
        sid, stream = entry['sessionId'], entry['ready']['streamId']
        venue_overview = args.check_venue_live_tracking
        desk = 'Master' if venue_overview else f'Room{room}'
        review_source = 'Master tracking overview' if venue_overview else 'room desk'
        descriptor = runtime / (mode + '-pose-review-private.json')
        descriptor.write_text(json.dumps({'base':uri,'key':keys[desk],'sessionId':sid,'roomId':room,
                                          'seat':seat,'playerId':player['id'],'streamId':stream,'venueOverview':venue_overview}),encoding='utf-8')
        with (destination/'browser.log').open('xb') as log:
            browser = subprocess.Popen([node,str(ROOT/'tests/browser/check-venue-pose-review-native.cjs'),
                                        str(descriptor),str(destination)],stdout=log,stderr=subprocess.STDOUT)
            try:
                def saved_review():
                    if browser.poll() is not None:
                        raise RuntimeError('Pose review browser exited before opening the original snapshot')
                    file = destination/'reviewed.json'
                    return read(file) if file.is_file() else None
                reviewed = wait(saved_review,30,mode+' '+review_source+' opens the original native pose frame')
                marker.unlink()
                check(browser.wait(timeout=30)==0,mode+' '+review_source+' returns from the saved frame to live without writing')
            finally:
                if browser.poll() is None:
                    browser.kill()
                    browser.wait(timeout=10)
        result = read(destination/'checks.json')
        check(result['complete'] and result['venueOverview'] is venue_overview
              and (result['sessionId'],result['streamId'],result['roomId'],result['seat'])==(sid,stream,room,seat)
              and result['after']>result['before']==reviewed['sequence']>=minimum_sequence
              and (result['savedPose'],result['livePose'])==('Unavailable','Tracked'),
              mode+' native browser records the original room and exact interruption and recovery frames')
        route = '/api/sessions/'+sid+'/world/frames/'
        entry['poseReviewPackets'] = [request(route+str(sequence))['packet'] for sequence in (result['before'],result['after'])]

    def verify_venue_openxr_reconnect(entries, round_clients, entry, client, checkpoint, recovered, mode):
        stage('running-venue-openxr-reconnect', mode=mode)
        sid = entry['sessionId']; session = '/api/sessions/'+sid
        person = client['player']; target_id = person['id']
        fixture = entry['openxrReconnect']
        gate = fixture['gate']
        history = {'reconnect':['0 0'], 'trigger':['0 0']}

        def log():
            return client['log'].read_text(encoding='utf-8', errors='replace')

        def connection_ids():
            return re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$', log(), re.M)

        def sync(name, value, *expected):
            command_path, ack_path = fixture['controls'][name]
            if value is not None:
                replace_fixture_file(command_path, value)
            history[name].extend(expected)
            wait(lambda:ack_path.is_file() and ack_path.read_text(encoding='ascii').splitlines()==history[name],
                 12, mode+' OpenXR sync '+name+' '+history[name][-1])

        def pose(value):
            return next(row for row in value['packet']['frame']['players'] if row['id']==target_id)

        def sample_peers(other):
            path = '/api/sessions/'+other['sessionId']
            revision = read(out/(other['label']+'-running.json'))['acceptedBeginSequence']
            expected = {(row['id'],row['admissionId'],row['roomId'],row['seat']) for row in
                        (owner['player'] for owner in round_clients if owner['sessionId']==other['sessionId'])}
            def original():
                report = request(path+'/readiness')
                if report['sourceState'] != 'Fresh' or report['observedSequence'] != revision or report['sessionSequence'] != revision:
                    return None
                actual = {(row['playerId'],row['admissionId'],row['roomId'],row['seat']) for row in report['players']
                          if row['canParticipate'] and row['rigKind']=='Simulated'}
                if actual != expected:
                    return None
                packet = request(path+'/world/frames/'+str(report['worldSequence']))['packet']
                return packet if packet['frame']['phase']=='Running' and not packet['suspended'] else None
            return wait(original, 15, other['label']+' original peers during venue reconnect')

        sync('reconnect', None)
        sync('trigger', None)
        magazine = pose(recovered)['magazine']
        sync('trigger', '2', '2 1', '2 0')
        def fired_once():
            revision = request(session)['sequence']
            if revision <= recovered['readiness']['sessionSequence']:
                return None
            value = checkpoint(True, recovered['packet']['frame']['tick']+1, revision)
            if value and pose(value)['magazine']==magazine-1:
                return value
        before = wait(fired_once, 15, mode+' original tracked seat fires one round before outage')
        revision = before['readiness']['sessionSequence']
        sync('reconnect', '1', '1 1')
        old_ids = connection_ids()
        first_other = {other['sessionId']:sample_peers(other) for other in entries if other is not entry}
        check(len(old_ids)==1 and gate.counts['upstream']>0 and gate.counts['downstream']>0,
              mode+' only the original tracked player used the owned same-host UDP relay')
        gate.close()
        relay = gate.report()
        check(relay['threadStopped'] and relay['error'] is None, mode+' tracked relay closed cleanly')
        server_log = entry['work']/'server.log'
        wait(lambda:'VR_CLIENT_DISCONNECTED' in log() and
             f'VR_SERVER_CLIENT_LEFT id={old_ids[0]}' in server_log.read_text(encoding='utf-8',errors='replace').splitlines(),
             45, mode+' actual client and server UDP disconnect')
        lost = wait(lambda:checkpoint(False,before['packet']['frame']['tick']+1,revision), 15, mode+' original tracked seat loses readiness after disconnect')
        signed = request(session+'/players/'+target_id+'/join-ticket',{},role='Room5',admission=person['admissionId'])
        original_config = read(fixture['originalFile'])
        check(signed['ticket'] and signed['ticket']!=original_config['joinTicket'] and request(session)['sequence']==revision,
              mode+' room desk reissues the original admission without changing the roster')
        replace_fixture_file(client['configPath'],json.dumps(dict(original_config,joinTicket=signed['ticket'])))
        held = wait(lambda:checkpoint(False,lost['packet']['frame']['tick']+50,revision), 15, mode+' held menu cannot reconnect')
        check(connection_ids()==old_ids and 'VR_CLIENT_ADMISSION_REJECTED' not in log(), mode+' held menu leaves only the original connection in the log')
        sync('reconnect', '0', '0 0')
        released = wait(lambda:checkpoint(False,held['packet']['frame']['tick']+14,revision), 15, mode+' released menu cannot reconnect')
        check(connection_ids()==old_ids, mode+' menu release does not start a connection')
        sync('reconnect', '1', '1 1')
        wait(lambda:len(connection_ids())==2, 20, mode+' new original transport after explicit menu press')
        renewed = wait(lambda:checkpoint(True,released['packet']['frame']['tick']+1,revision), 20, mode+' same original admission restores tracked readiness')
        new_ids = connection_ids()
        check(new_ids[:1]==old_ids and len(set(new_ids))==2 and client['process'].poll() is None
              and client['witness'].kernel.WaitForSingleObject(client['witness'].handle,0)==258
              and log().count('VR_OPENXR_STARTUP status=active')==log().count('VR_CLIENT_DISCONNECTED')==1
              and 'VR_CLIENT_ADMISSION_REJECTED' not in log() and package.digest(fixture['originalFile'])==fixture['originalHash']
              and all(pose(before)[key]==pose(renewed)[key] for key in ('health','magazine','reserve')),
              mode+' original tracked player process recovers without resetting spent ammunition, health or reserve')
        client['reconnectIds'] = new_ids
        for other in entries:
            tracked = other is entry
            other['venueReconnectWindow'] = {
                'first':before['packet'] if tracked else first_other[other['sessionId']],
                'last':renewed['packet'] if tracked else sample_peers(other),
                'outage':[item['packet'] for item in (lost,held,released)] if tracked else [],
                'target':target_id if tracked else None,
                'peers':{owner['player']['id']:'Simulated' for owner in round_clients
                         if owner['sessionId']==other['sessionId'] and owner is not client}}
        save(mode+'-venue-openxr-reconnect.json',{'roomId':person['roomId'],'seat':person['seat']+1,
            'admissionId':person['admissionId'],'originalNativePid':client['nativePid'], 'connections':new_ids,
            'relay':relay, 'managementRevision':revision, 'synchronizedInput':history,
            'before':before, 'lost':lost, 'held':held, 'released':released, 'renewed':renewed})

    def verify_room_readiness(round_clients,linked):
        expected={client['player']['roomId']:client['sessionId'] for client in round_clients}
        def all_ready():
            summary=request('/api/rooms/readiness')
            rows=summary['rooms']
            if summary['version']!=1 or len(rows)!=5 or {row['roomId']:row['sessionId'] for row in rows}!=expected:
                return None
            return summary if all(row['sourceState']=='Fresh' and row['registered']==players_per_room and
                row['trackedReady']==int(args.check_venue_openxr and row['roomId']==5)
                and row['simulatedReady']==players_per_room-row['trackedReady'] for row in rows) else None
        save(('linked' if linked else 'independent')+'-room-readiness.json',wait(all_ready,20,'five fresh room aggregates'))
        check(True,('Linked' if linked else 'Independent')+f' has five fresh {players_per_room}/{players_per_room} room counts with expected rig types')
        room=request('/api/rooms/readiness',role='Room1')
        check(room['version']==1 and len(room['rooms'])==1 and room['rooms'][0]['roomId']==1
            and room['rooms'][0]['sessionId']==expected[1],'room operator only receives its own active room aggregate')
    def verify_room_participation(entries, round_clients, linked):
        mode = 'Linked' if linked else 'Independent'
        room, seat = 4, 3
        index = next(i for i, client in enumerate(round_clients)
                     if (client['player']['roomId'], client['player']['seat'] + 1) == (room, seat))
        original = round_clients[index]
        entry = next(item for item in entries if item['sessionId'] == original['sessionId'])
        connections = re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$', original['log'].read_text(encoding='utf-8'), re.M)
        if len(connections) != 1: raise RuntimeError('Expected one original connection for the target seat')
        initial = original['configPath'].read_bytes()
        expected = {client['player']['roomId']:client['sessionId'] for client in round_clients}

        def snapshot(missing):
            rows = request('/api/rooms/readiness')['rooms']
            if {row['roomId']:row['sessionId'] for row in rows} != expected: return None
            return rows if all(row['sourceState'] == 'Fresh' and row['registered'] == 5 and row['trackedReady'] == 0
                and row['simulatedReady'] == (4 if missing and row['roomId'] == room else 5)
                and row.get('vrParticipation') == {'awaitingAdmission': [], 'awaitingPose': [seat] if missing and row['roomId'] == room else [], 'eliminated': []}
                for row in rows) else None

        before = wait(lambda:snapshot(False), 15, mode+' original 25 VR seats')
        stop_player(original)
        missing = wait(lambda:snapshot(True), 20, mode+' only room 4 seat 3 missing its pose')
        check(True, mode+' loss identifies the exact original VR seat while the other 24 remain participating')
        scoped = request('/api/rooms/readiness', role='Room4')['rooms']
        check(len(scoped) == 1 and scoped[0]['roomId'] == room and scoped[0]['vrParticipation']['awaitingPose'] == [seat],
              mode+' only the affected room details are visible to its room controller')
        if args.observe_closure_ui and not linked:
            alert = wait(lambda:read(observer_out/'participation-alert.json') if (observer_out/'participation-alert.json').is_file() else None,
                         10, 'actual console highlights only the missing VR seat')
            check(alert['roomId'] == room and alert['seat'] == seat, 'shipped console identifies the affected native VR seat')
        pause = None
        if args.check_vr_participation_pause:
            sid = entry['sessionId']
            role = 'Master' if linked else 'Room4'
            node = shutil.which('node')
            if not node: raise RuntimeError('Node is required for the shipped VR pause console check')
            def transition(action):
                label = f'{mode.lower()}-vr-{action.lower()}'
                descriptor = runtime/(label+'-private.json')
                descriptor.write_text(json.dumps({'base':uri,'key':keys[role],'sessionId':sid,
                    'roomId':room,'seat':seat,'linked':linked,'action':action}),encoding='utf-8')
                evidence = out/(label+'-ui.json')
                with (out/(label+'-ui.log')).open('xb') as log:
                    subprocess.run([node, str(ROOT/'tests/browser/check-vr-participation-pause-native.cjs'),
                        str(descriptor), str(evidence)], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=50)
                return read(evidence)
            pause = transition('Pause')
            sequence = pause['appliedAtSequence']
            def observed_pause():
                rows = request('/api/rooms/readiness')['rooms']
                affected = [row for row in rows if row['sessionId'] == sid]
                if len(affected) == (5 if linked else 1) and all(
                    row.get('vrPause',{}).get('triggerRoomId') == room and row['vrPause']['appliedAtSequence'] == sequence
                    and row['vrPause']['worldSequence'] and row['sourceState'] == 'Fresh' for row in affected):
                    return affected
            pause['appliedRooms'] = wait(observed_pause, 20, mode+' original VR pause source confirmation')
            check(pause['sessionId'] == sid and pause['roomId'] == room and request('/api/sessions/'+sid)['state'] == 'Paused'
                  and all(request('/api/sessions/'+other)['state'] == 'Running' for other in set(expected.values())-{sid}),
                  mode+' room card pauses exactly the affected scope and the original source confirms it')
            rejected = request('/api/sessions/'+sid+'/commands', {'commandId':str(uuid.uuid4()),'action':'Resume'},
                               role=role, expected=409)
            check(rejected['code'] == 'vr-participation-resume-not-ready' and request('/api/sessions/'+sid)['state'] == 'Paused',
                  mode+' direct Resume is denied while the original native seat is missing')
        server_log = entry['work']/'server.log'
        wait(lambda:f'VR_SERVER_CLIENT_LEFT id={connections[0]}\n' in server_log.read_text(encoding='utf-8'), 50,
             mode+' original UDP transport release')
        config = original['configPath'].with_stem(original['configPath'].stem+'-reconnected')
        with config.open('xb') as stream: stream.write(initial)
        recovered = packaged_player(entry, original['player'], config)
        round_clients[index] = recovered
        if pause is not None:
            wait(lambda: recovered['log'].is_file() and 'VR_CLIENT_CONNECTED id=' in recovered['log'].read_text(encoding='utf-8'),
                 25, mode+' original VR seat reconnects while paused')
            resume = transition('Resume')
            check(resume['sessionId'] == sid and resume['roomId'] == room and request('/api/sessions/'+sid)['state'] == 'Running'
                  and resume['appliedAtSequence'] > pause['appliedAtSequence'],
                  mode+' operator resumes the exact original session from the recovered room card')
            pause['resume'] = resume
        after = wait(lambda:snapshot(False), 30, mode+' original admission restores all five room counts')
        new_connections = re.findall(r'^VR_CLIENT_CONNECTED id=(\d+)$', recovered['log'].read_text(encoding='utf-8'), re.M)
        check(len(new_connections) == 1 and new_connections != connections and recovered['nativePid'] != original['nativePid']
              and original['configPath'].read_bytes() == initial, mode+' replacement process uses the same original admission and clears the alert')
        if args.observe_closure_ui and not linked:
            recovered_ui = wait(lambda:read(observer_out/'participation-recovered.json') if (observer_out/'participation-recovered.json').is_file() else None,
                                10, 'actual console clears the original VR alert')
            check(recovered_ui['rooms'] == [1,2,3,4,5], 'shipped console clears the seat warning and restores all five actual room counts')
        save(mode.lower()+'-room-participation.json', {'before':before,'missing':missing,'after':after,
             'roomId':room,'seat':seat,'oldConnectionId':connections[0],'newConnectionId':new_connections[0],
             **({'pause':pause} if pause is not None else {})})
    def verify_venue_environment(entries, linked):
        route = '/api/venue/phase'
        mode = 'linked' if linked else 'independent'
        sessions = {entry['sessionId'] for entry in entries}
        evidence = []
        for weather, time_of_day, lightning in [('Storm', 'Night', True), ('Clear', 'Day', False)]:
            preview = request(route)['environment']
            targets = [{key: row[key] for key in ('sessionId', 'phaseSinceSequence', 'environmentSinceSequence')} for row in preview]
            check({row['sessionId'] for row in targets} == sessions
                  and sorted(room for row in preview for room in row['roomIds']) == list(range(1, 6)),
                  f'{mode} {weather} environment preview covers the original five rooms')
            climate = {'weather': weather, 'timeOfDay': time_of_day, 'lightning': lightning}
            body = {'action': 'SetEnvironment', 'targets': targets, 'environment': climate}
            key = str(uuid.uuid4())
            receipt = request(route, body, request_id=key)
            applied = {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}
            def observed():
                rows = request('/api/rooms/readiness')['rooms']
                if len(rows) == 5 and all((status := row.get('venueEnvironment')) and status['worldSequence']
                   and status['appliedAtSequence'] == applied.get(row['sessionId'])
                   and all(status[field] == value for field, value in climate.items()) for row in rows):
                    return rows
            confirmed = wait(observed, 20, f'{mode} {weather} native environment confirmations')
            frames = {}
            for row in confirmed:
                sid = row['sessionId']
                if sid in frames:
                    continue
                sequence = row['venueEnvironment']['worldSequence']
                frames[sid] = request(f'/api/sessions/{sid}/world/frames/{sequence}')['packet']
            check(not receipt['duplicate'] and receipt['requestId'] == key and set(frames) == sessions
                  and all(packet['observedSequence'] >= applied[sid] and packet['weather'] == weather and packet['lightning'] == lightning
                          and packet['frame']['night'] == (time_of_day == 'Night') and packet['frame']['phase'] == 'Running'
                          for sid, packet in frames.items()),
                  f'{mode} {weather} original accepted frames record all three values and their receipt sequence')
            evidence.append({'receipt': receipt, 'rooms': confirmed, 'frames': frames})
            preserve_venue_control_report(mode, 'SetEnvironment', receipt)
        save(mode+'-venue-environment.json', evidence)
        if args.check_venue_environment_ui:
            verify_setting_batch_ui(mode, 'environment', 'latestEnvironment', evidence[-1]['receipt'])
        if not linked:
            room_routes = [f"/api/sessions/{entry['sessionId']}" for entry in entries]
            path = room_routes[0]
            loaded = [request(room + '/overview') for room in room_routes]
            original = loaded[0]
            climate = dict(original['session']['environment'], weather='Storm', timeOfDay='Night', lightning=True)
            enemies = dict(original['session']['enemies'], behavior='Patrol', autoAttack=False)
            changes = [
                {'commandId': str(uuid.uuid4()), 'action': 'SetEnvironment', 'environment': climate,
                 'expectedSettingSequence': original['settingRevisions']['environment']},
                {'commandId': str(uuid.uuid4()), 'action': 'SetEnemies', 'enemies': enemies,
                 'expectedSettingSequence': original['settingRevisions']['enemies']},
            ]
            receipts = [request(path + '/commands', change) for change in changes]
            check(receipts[1]['appliedAtSequence'] == receipts[0]['appliedAtSequence'] + 1
                  and receipts[1]['session']['environment'] == climate and receipts[1]['session']['enemies'] == enemies,
                  'two direct setting drafts from the same overview apply through the native management service')
            def observed_direct():
                sequence = request(path + '/world')['acceptedSequence']
                packet = request(f'{path}/world/frames/{sequence}')['packet']
                frame = packet['frame']
                if (packet['observedSequence'] >= receipts[1]['appliedAtSequence'] and packet['weather'] == 'Storm'
                    and packet['lightning'] and frame['night'] and frame['phase'] == 'Running'
                    and any(enemy['walking'] for enemy in frame['enemies'])):
                    return packet
            direct = wait(observed_direct, 20, 'native direct environment and enemy setting witness')
            check(all(request(room + '/overview')['settingRevisions'] == prior['settingRevisions']
                      for room, prior in zip(room_routes[1:], loaded[1:])),
                  'direct settings reach an original game frame while the other independent rooms retain their revisions')
            save('independent-direct-settings.json', {'changes': changes, 'receipts': receipts, 'frame': direct})

    def verify_room_clocks(entries, linked):
        mode = 'linked' if linked else 'independent'
        expected = {room: entries[0 if linked else room-1]['sessionId'] for room in range(1, 6)}
        def snapshot(phase, after=None, minimum=None):
            response = request('/api/rooms/readiness')
            rows = response['rooms']
            if [(row['roomId'], row['sessionId']) for row in rows] != list(expected.items()): return None
            for row in rows:
                room = row['roomId']; clock = row.get('clock')
                if not clock or row['sourceState'] != 'Fresh' or clock['phase'] != (phase if linked or room == 1 else 'Running') \
                    or clock['durationSeconds'] != 600 or clock['remainingSeconds'] != max(0, 600-clock['elapsedSeconds']) \
                    or clock['autoEnd'] != (linked or room == 1): return None
                if after and (linked or room == 1) and row['sessionSequence'] < after: return None
            if linked and any(row['clock'] != rows[0]['clock'] for row in rows): return None
            if minimum and rows[minimum[0]-1]['clock']['elapsedSeconds'] <= minimum[1]: return None
            return rows
        running = wait(lambda: snapshot('Running'), 15, mode+' five native room clocks')
        check(True, mode+' original active clocks publish per-room policy and one identical value for a linked source')
        own = request('/api/rooms/readiness', role='Room2')['rooms']
        check(len(own) == 1 and own[0]['roomId'] == 2 and own[0]['sessionId'] == expected[2], mode+' Room2 receives only its scoped clock row')
        pause = command(expected[1], 'Pause')['appliedAtSequence']
        first = wait(lambda: snapshot('Paused', pause), 15, mode+' accepted native paused clock')
        if linked:
            time.sleep(1.1)
            frozen = wait(lambda: snapshot('Paused', pause), 15, mode+' linked clock remains paused')
        else:
            frozen = wait(lambda: snapshot('Paused', pause, (2, first[1]['clock']['elapsedSeconds'])), 15, 'another independent room advances')
        check(frozen[0]['clock'] == first[0]['clock'], mode+' original pause retains exactly the accepted activity time')
        resume = command(expected[1], 'Resume')['appliedAtSequence']
        resumed = wait(lambda: snapshot('Running', resume, (1, first[0]['clock']['elapsedSeconds'])), 15, mode+' resume advances original clock')
        check(True, mode+' accepts a new running clock after the original Resume')
        save(mode+'-room-clocks.json', {'running':running, 'paused':first, 'frozen':frozen, 'resumed':resumed})
    def verify_venue_phase(entries, linked):
        mode = 'linked' if linked else 'independent'
        room_two = None if linked else entries[1]['sessionId']
        mock_feeds = [feed for entry in entries for feed in entry.get('hardwareFeedback', []) if 'mock' in feed]
        verify_mock_resume = mock_feeds and hardware_manifest['toolVersion'] == '0.2.6'
        def handshakes(feed):
            return [frame['connectionId'] for frame in feed['mock']['frames'] if frame['kind']=='hello']
        if room_two: command(room_two, 'Pause')
        route = '/api/venue/phase'
        def submit(action):
            targets = request(route)[action.lower()]
            wanted = {entry['sessionId'] for entry in entries if entry['sessionId'] != room_two}
            assert {row['sessionId'] for row in targets} == wanted
            body = {'action': action, 'targets': [{key: row[key] for key in ('sessionId', 'phaseSinceSequence')} for row in targets]}
            key = str(uuid.uuid4())
            receipt = request(route, body, request_id=key)
            assert not receipt['duplicate'] and receipt['requestId'] == key and receipt['action'] == action
            assert {row['sessionId'] for row in receipt['sessions']} == wanted
            return body, key, receipt
        def observe_phase(phase, receipt, previous=None):
            rows = request('/api/rooms/readiness')['rooms']
            applied = {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}
            if len(rows) != 5: return None
            for row in rows:
                clock = row.get('clock'); manual = row['sessionId'] == room_two
                if not clock or clock['phase'] != ('Paused' if manual else phase): return None
                if not manual and (row['sessionId'] not in applied or row['sessionSequence'] < applied[row['sessionId']]): return None
                status = row.get('venuePhase')
                if manual and status is not None: return None
                if not manual and (not status or status['action'] != receipt['action'] or status['appliedAtSequence'] != applied[row['sessionId']]
                    or not status['worldSequence'] or status['readyToResume'] != (phase == 'Paused')): return None
                if previous:
                    before = previous[row['roomId']-1]['clock']['elapsedSeconds']
                    if manual and clock['elapsedSeconds'] != before or not manual and clock['elapsedSeconds'] <= before: return None
            return rows
        body, key, pause = submit('Pause')
        paused = wait(lambda: observe_phase('Paused', pause), 15, mode+' all original paused sources observe venue command')
        check(True, mode+' venue Pause reaches all targeted native sources with one management receipt')
        _, _, resume = submit('Resume')
        resumed = wait(lambda: observe_phase('Running', resume, paused), 15, mode+' venue Resume advances only targeted native sources')
        check(True, mode+' venue Resume advances the target clocks and preserves a manual pause when present')
        retry = request(route, body, request_id=key)
        check(retry['duplicate'] and retry['sessions'] == pause['sessions'] and request(route)['resume'] == [],
              mode+' late venue Pause retry keeps the original receipt without pausing again')
        save(mode+'-venue-phase.json', {'pause': pause, 'paused': paused, 'resume': resume, 'resumed': resumed, 'pauseRetry': retry})
        if verify_mock_resume and room_two:
            manual = next(feed for feed in mock_feeds if feed['session']==room_two)
            check(len(handshakes(manual))==1, 'independent room 2 stays on hold while the other four rooms resume')
        if room_two: command(room_two, 'Resume')
        if verify_mock_resume:
            resumed_connections = {}
            for feed in mock_feeds:
                ids = wait(lambda: (current if len(current := handshakes(feed)) >= 2 else None), 8,
                           mode+f' room {feed["room"]} resumed mock handshake')
                check(len(ids)==len(set(ids))==2, mode+f' room {feed["room"]} resumes on exactly one fresh mock connection')
                resumed_connections[feed['room']] = ids
            save(mode+'-venue-hardware-connections.json',resumed_connections)
    def verify_mr_alignment_archive(entry, files):
        sid = entry['sessionId']
        terminal = request('/api/sessions/'+sid)
        report = read(entry['reportPath'])
        if 'venueIndex' in entry:
            report = report['servers'][entry['venueIndex']]['result']
        header = report['finalWorld']['header']
        supplied = {room: files[room] for room in terminal['roomIds']}
        proofs = field.verify_room_alignments(terminal, header, supplied)
        check(terminal['state'] == 'Ended' and proofs == [{'roomId': room, 'sha256': package.digest(path)}
              for room, path in sorted(supplied.items())], entry['label']+' sealed MR source matches the exact locked room exports')
        room = terminal['roomIds'][0]
        other = next(path for number, path in files.items() if number != room)
        try:
            field.verify_room_alignments(terminal, header, dict(supplied) | {room: other})
        except field.EvidenceError as error:
            check('bytes differ' in str(error), entry['label']+' archive rejects an original export from another room')
        else:
            raise RuntimeError('MR archive unexpectedly accepted another room export')
        journal = entry['work']/'telemetry'/(sid+'.worldlog')
        try:
            field.verify_world_journal(journal, report['finalWorld'], report['finalCombatStream']['acceptedSequence'], terminal['sequence'], None)
        except field.EvidenceError as error:
            check('active play' in str(error) and read(out/(entry['label']+'-journal.json'))['runningFrames'] == 0,
                  entry['label']+' Preparing-only archive still cannot satisfy played field evidence')
        else:
            raise RuntimeError('MR Preparing-only archive unexpectedly satisfied the played-session gate')
        save(entry['label']+'-alignment-archive.json', {'rooms': proofs, 'scope': 'Native MR Preparing seal and original export locks',
              'playedFieldEvidenceAccepted': False})

    def save_room_alignment_exports(files):
        paths = {room: out/f'room-{room:02}-locked-alignment.json' for room in files}
        for room, path in paths.items():
            path.write_bytes(files[room])
        return paths

    def recover_mr_venue_source(entry, rooms, alignments):
        node = shutil.which('node')
        if not node: raise RuntimeError('Node is required for the native MR browser check')
        route = '/api/sessions/' + entry['sessionId']
        endpoint = request(route + '/connection-endpoint')
        body = {'topology': 'Linked', 'rooms': rooms}
        signed = out/'mr-source-signed.request'
        blocked = out/'mr-source-blocked.request'
        descriptor = runtime/'mr-source-private.json'
        bundle = runtime/'mr-source-recovered.zip'
        output = out/'mr-source-browser.json'
        descriptor.write_text(json.dumps({'base': uri, 'masterKey': keys['Master'], 'signed': str(signed), 'blocked': str(blocked),
            'files': [str(alignments[room]) for room in range(1, 6)], 'endpoint': f'{endpoint["address"]}:{endpoint["port"]}'}), encoding='utf-8')
        def readiness(live):
            rows = request('/api/rooms/readiness')['rooms']
            return rows if len(rows) == 5 and all(row.get('ticketSourceLive') is live and row.get('endpoint') == endpoint for row in rows) else None
        driver = ROOT/'tests/browser/check-mr-venue-source-native.cjs'
        with (out/'mr-source-browser.log').open('xb') as log:
            browser = subprocess.Popen([node, str(driver), str(descriptor), str(bundle), str(output)], stdout=log, stderr=subprocess.STDOUT)
            try:
                def marker(path):
                    if browser.poll() is not None: raise RuntimeError('Original MR browser exited early')
                    return path.is_file()
                wait(lambda: marker(signed), 25, 'one original Chromium request receives its signed MR ZIP')
                with hold_owned_unity_threads(entry['witness'], entry['ready']['childPid']) as thread_count:
                    stale = wait(lambda: readiness(False), 12, 'managed MR source expires')
                    held_world = request(route+'/world')
                    rejection = request('/api/mr-deployment/venue-bundle', body, expected=409)
                    check(rejection['code'] == 'venue-endpoint-stale' and rejection['roomId'] == 1,
                          'New MR issuance refuses the same held native publisher')
                    wait(lambda: marker(blocked), 12, 'Chromium discards the original signed ZIP and keeps the five files')
                restored = wait(lambda: readiness(True), 18, 'same MR source resumes publishing')
                resumed_world = request(route+'/world')
                check(resumed_world['header'] == held_world['header'] and resumed_world['acceptedSequence'] > held_world['acceptedSequence']
                      and request(route+'/connection-endpoint') == endpoint
                      and entry['witness'].kernel.WaitForSingleObject(entry['witness'].handle, 0) == 258,
                      'The original MR Unity handle advances the same world and published endpoint')
                check(browser.wait(timeout=35) == 0 and read(output)['restoredFiveFiles'] and bundle.is_file(),
                      'Same browser panel retains five calibration files, suppresses the held ZIP and exports only on a new click')
                save('mr-source-native.json', {'threadCount': thread_count, 'heldReadiness': stale, 'restoredReadiness': restored,
                    'heldWorld': held_world, 'resumedWorld': resumed_world, 'rejection': rejection})
                return bundle.read_bytes()
            finally:
                if browser.poll() is None: browser.terminate(); browser.wait(timeout=10)

    def check_mr_venue_bundle():
        pwsh = shutil.which('pwsh')
        if not pwsh: raise RuntimeError('PowerShell is required for Quest venue preflight')
        room_ids = list(range(1, 6))
        markers = [{'room': {'x': x, 'z': z}, 'tracking': {'x': x, 'z': z}} for x, z in [(-2, -2), (2, -2), (-2, 2)]]
        files = {room: json.dumps(request('/api/room-alignment', {'roomId': room, 'markers': markers})).encode() for room in room_ids}
        hashes = {room: hashlib.sha256(data).hexdigest() for room, data in files.items()}
        alignment_exports = save_room_alignment_exports(files)
        for mode in ('Linked', 'Independent'):
            stage('native-mr-venue-bundle', mode=mode)
            if mode == 'Linked':
                states = [create(room_ids, 'MR venue linked', experience='MR')]
            else:
                mission = save_mission('MR venue independent', experience='MR')
                states = request('/api/sessions/independent-set', {'missionId': mission['id']}, expected=201, request_id=str(uuid.uuid4()))['sessions']
                sessions.extend(state['id'] for state in states)
            entries, rooms = [], []
            managed = args.check_mr_venue_source_recovery and mode == 'Linked'
            for state in states:
                sid = state['id']; route = '/api/sessions/' + sid
                pins = {f'room{room}': hashes[room] for room in state['roomIds']}
                request(route + '/commands', {'commandId': str(uuid.uuid4()), 'action': 'SetRoomAlignment', 'roomAlignment': pins})
                for room in state['roomIds']:
                    for seat in range(1, 6):
                        state = request(route + '/players', {'playerId': str(uuid.uuid4()), 'roomId': room, 'name': f'MR venue {room}/{seat}', 'headset': 'Quest3'})
                    rooms.append({'roomId': room, 'sessionId': sid, 'alignmentFile': base64.b64encode(files[room]).decode(),
                        'players': [{'playerId': row['id'], 'admissionId': row['admissionId']} for row in state['players'] if row['roomId'] == room]})
                if managed: entries.extend(launch_venue([state], True, label='mr-venue-source-linked'))
                else: entries.append(launch(state, f'mr-venue-{mode.lower()}-{state["roomIds"][0]}'))
            before = request('/api/sessions')
            if managed:
                raw = recover_mr_venue_source(entries[0], rooms, alignment_exports)
            else:
                raw, headers = request('/api/mr-deployment/venue-bundle', {'topology': mode, 'rooms': rooms}, raw_response=True)
                check(headers['Cache-Control'] == 'no-store' and headers.get_content_type() == 'application/zip', mode + ' native endpoint export is a non-cacheable ZIP')
            with tempfile.TemporaryDirectory(prefix='deployment-', dir=runtime) as scratch:
                destination = Path(scratch).resolve()
                if destination.parent != runtime: raise RuntimeError('Invalid owned deployment scratch directory')
                expected = {'venue.json', *(f'room-{room:02}-{suffix}' for room in room_ids for suffix in ('alignment.json', 'connections.zip'))}
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    assert len(archive.namelist()) == len(expected) and set(archive.namelist()) == expected
                    manifest_rooms = json.loads(archive.read('venue.json'))['rooms']
                    assert [(row['roomId'], row['sessionId']) for row in manifest_rooms] == [(row['roomId'], row['sessionId']) for row in rooms]
                    assert all(archive.read(f'room-{room:02}-alignment.json') == files[room] for room in room_ids)
                bundle = destination / 'quest-mr-venue.zip'
                bundle.write_bytes(raw)
                deploy = [pwsh, '-NoProfile', '-File', str(ROOT/'scripts/deploy-quest.ps1'), '-VenueBundle', str(bundle), '-ManagementApi', uri]
                environment = {**os.environ, 'VR_COMMAND_MASTER_KEY': keys['Master']}
                report = json.loads(subprocess.check_output(deploy, env=environment, timeout=25, encoding='utf-8', cwd=destination))
                seat = json.loads(subprocess.check_output([*deploy, '-RoomId', '4', '-Seat', '2', '-CheckOnly'],
                    env=environment, timeout=25, encoding='utf-8', cwd=destination))
                assert list(destination.iterdir()) == [bundle]
                if args.check_mapped_quest:
                    verify_mapped_quest(deploy, destination, environment, raw, mode, files, hashes)
                    subset = destination / 'partial'
                    subset.mkdir()
                    verify_mapped_quest(deploy, subset, environment, raw, mode, files, hashes, partial=True)
                if managed and args.check_mr_venue_write_gate:
                    boundary = destination / 'write-boundary'
                    boundary.mkdir()
                    verify_mr_venue_write_gate(entries[0], deploy, boundary, environment, raw, rooms)
            endpoints = {entry['sessionId']: f'{address}:{entry["ready"]["port"]}' for entry in entries}
            check(report['managementVerified'] and report['alignmentPinsVerified'] and report['topology'] == mode and report['seats'] == 25
                and [(row['roomId'], row['seats'], row['endpoint'], row['alignmentSha256']) for row in report['rooms']] == [
                    (room['roomId'], 5, endpoints[room['sessionId']], hashes[room['roomId']]) for room in rooms]
                and request('/api/sessions') == before,
                mode + ' actual Quest preflight verifies 25 signed files, original calibration and owned UDP endpoints without writing session events')
            save(f'mr-venue-{mode.lower()}-deployment.json', report)
            check(seat['roomId'] == 4 and seat['seat'] == 2 and seat['mode'] == 'MR' and seat['managementVerified']
                and seat['alignmentPinsVerified'] and seat['alignmentSha256'] == hashes[4],
                mode + ' direct ZIP preflight selects the original room 4 seat 2 without extraction or ADB')
            save(f'mr-venue-{mode.lower()}-seat.json', seat)
            for entry in entries: command(entry['sessionId'], 'End')
            for entry in entries:
                finish(entry)
                verify_mr_alignment_archive(entry, alignment_exports)

    def verify_mr_venue_write_gate(entry, deploy, destination, environment, raw, rooms):
        route = '/api/mr-deployment/venue-check'
        proof = {'topology': 'Linked', 'rooms': []}
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for room in rooms:
                room_id = room['roomId']
                with zipfile.ZipFile(io.BytesIO(archive.read(f'room-{room_id:02}-connections.zip'))) as tickets:
                    connections = [base64.b64encode(tickets.read(f'room-{room_id:02}-seat-{seat:02}.json')).decode()
                                   for seat in range(1, 6)]
                proof['rooms'].append({'roomId': room_id, 'sessionId': room['sessionId'],
                    'alignmentFile': room['alignmentFile'], 'connectionFiles': connections})
        strict = dict(proof, requireLiveSource=True)
        initial = request(route, strict)
        check(initial['allMatched'] and initial['liveSourceVerified'] and len(initial['seats']) == 25,
              'Strict MR check binds the signed 25-seat bundle to its current managed publisher')
        tampered = json.loads(json.dumps(strict))
        first_config = json.loads(base64.b64decode(proof['rooms'][0]['connectionFiles'][0]))
        tampered['rooms'][0]['connectionFiles'][0] = base64.b64encode(json.dumps(dict(first_config, port=1024 if first_config['port'] != 1024 else 1025)).encode()).decode()
        mismatch = request(route, tampered)
        check(not mismatch['liveSourceVerified'] and [(row['roomId'], row['seat'], row['status']) for row in mismatch['seats'] if row['status'] != 'matched']
              == [(1, 0, 'endpoint-mismatch')], 'Strict MR check rejects a changed UDP port with the original valid ticket')
        selected = [{'roomId': room, 'seat': 1, 'serial': f'fixture-{(room - 1) * 5 + 1:02}'} for room in (1, 3, 5)]
        mapping = destination / 'device-map.json'
        mapping.write_text(json.dumps({'version': 1, 'seats': selected}), encoding='utf-8')
        mapped = [*deploy, '-DeviceMap', str(mapping), '-AllowPartialMap', '-DeployMappedSeats', '-ExpectedVersionCode', '61',
                  '-AdbPath', str(ROOT/'tests/fixtures/mock-quest-fleet.ps1')]
        fixture_env = {**environment, 'VR_QUEST_FLEET_FIXTURE': str(destination), 'VR_QUEST_FLEET_FAULTS': ''}
        held_env = {**fixture_env, 'VR_QUEST_FLEET_HOLD_AFTER_LAUNCH': selected[0]['serial']}
        resume = destination/'continue.request'
        session_route = '/api/sessions/' + entry['sessionId']
        with subprocess.Popen(mapped, env=held_env, cwd=destination, text=True, encoding='utf-8', stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as cli:
            try:
                def first_launched():
                    if cli.poll() is not None: raise RuntimeError('Mapped Quest CLI exited before the first original mock launch')
                    return (destination/'first-launch.request').is_file()
                wait(first_launched, 25, 'first original Quest mock launch reaches the fixture boundary')
                with hold_owned_unity_threads(entry['witness'], entry['ready']['childPid']):
                    wait(lambda: all(row.get('ticketSourceLive') is False for row in request('/api/rooms/readiness')['rooms']),
                         12, 'original MR source goes stale between mapped seats')
                    held_world = request(session_route + '/world')
                    held_receipt = request(route, strict)
                    readonly = request(route, proof)
                    check(held_receipt['liveSourceVerified'] is False and not held_receipt['allMatched']
                          and {row['status'] for row in held_receipt['seats']} == {'source-stale'}
                          and readonly['allMatched'] and 'liveSourceVerified' not in readonly,
                          'Held source blocks strict deployment while original read-only signature check remains available')
                    resume.touch(exist_ok=False)
                    stdout, _ = cli.communicate(timeout=15)
                    interrupted = json.loads(stdout)
                    check(cli.returncode == 1 and not interrupted['complete'] and interrupted['managementVerified']
                          and [row['status'] for row in interrupted['devices']] == ['launch-requested', 'venue-check-failed', 'not-attempted']
                          and interrupted['devices'][1]['failedStep'] == 'verify-live-venue'
                          and {path.name for path in destination.glob('fixture-*')} == {selected[0]['serial']},
                          'MR deployment preserves the first mock write and performs no writes on the blocked or pending device')
            finally:
                if cli.poll() is None: cli.kill(); cli.communicate(timeout=10)
        before = (destination / selected[0]['serial'] / 'vr-connection.json').read_bytes()
        adb_log = destination/'adb.log'
        old_commands = adb_log.read_text(encoding='utf-8').splitlines()
        mapping.write_text(json.dumps({'version': 1, 'seats': selected[1:]}), encoding='utf-8')
        restored = wait(lambda: (receipt if (receipt := request(route, strict))['liveSourceVerified'] else None),
                        18, 'original MR publisher restores strict venue verification')
        resumed = request(session_route + '/world')
        retried = json.loads(subprocess.check_output(mapped, env=fixture_env, cwd=destination, encoding='utf-8', timeout=45))
        new_commands = adb_log.read_text(encoding='utf-8').splitlines()[len(old_commands):]
        check(restored == initial and resumed['header'] == held_world['header'] and resumed['acceptedSequence'] > held_world['acceptedSequence']
              and retried['complete'] and retried['mappedSeats'] == 2 and all(row['status'] == 'launch-requested' for row in retried['devices'])
              and {line.split()[1] for line in new_commands if line.startswith('-s ')} == {row['serial'] for row in selected[1:]}
              and before == (destination / selected[0]['serial'] / 'vr-connection.json').read_bytes(),
              'The same native publisher recovers and an explicit retry deploys only the two remaining mock devices')
        save('mr-venue-write-gate.json', {'interrupted': interrupted, 'retried': retried, 'heldSequence': held_world['acceptedSequence'],
            'resumedSequence': resumed['acceptedSequence'], 'staleSeats': len(held_receipt['seats'])})

        staging = destination/'staging-boundary'
        staging.mkdir()
        staging_map = staging/'device-map.json'
        staging_map.write_text(json.dumps({'version': 1, 'seats': selected}), encoding='utf-8')
        stage_command = [str(staging_map) if option == str(mapping) else option for option in mapped]
        second_device = staging/selected[1]['serial']
        second_device.mkdir()
        active_config = second_device/'vr-connection.json'
        original = b'Original mock active connection\n'
        active_config.write_bytes(original)
        stage_env = {**fixture_env, 'VR_QUEST_FLEET_FIXTURE': str(staging)}
        staged_env = {**stage_env, 'VR_QUEST_FLEET_HOLD_AFTER_STAGE': selected[1]['serial']}
        with subprocess.Popen(stage_command, env=staged_env, cwd=staging, text=True, encoding='utf-8',
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as cli:
            try:
                def staged_connection():
                    if cli.poll() is not None: raise RuntimeError('Mapped Quest CLI exited before the staged hash check')
                    return (staging/'connection-staged.request').is_file()
                wait(staged_connection, 25, 'the second Quest mock stages and hashes the original connection file')
                staged_file, = second_device.glob('vr-connection-*.tmp')
                staged_hash = hashlib.sha256(staged_file.read_bytes()).hexdigest()
                assert staged_hash == (staging/'connection-staged.request').read_text(encoding='utf-8')
                with hold_owned_unity_threads(entry['witness'], entry['ready']['childPid']):
                    wait(lambda: all(row.get('ticketSourceLive') is False for row in request('/api/rooms/readiness')['rooms']),
                         12, 'original MR source goes stale after the staged file was hashed')
                    stale_world = request(session_route + '/world')
                    stale = request(route, strict)
                    assert stale['liveSourceVerified'] is False and {row['status'] for row in stale['seats']} == {'source-stale'}
                    (staging/'continue.request').touch(exist_ok=False)
                    stdout, _ = cli.communicate(timeout=15)
                    blocked = json.loads(stdout)
                    commands = (staging/'adb.log').read_text(encoding='utf-8').splitlines()
                    affected = [line for line in commands if line.startswith('-s '+selected[1]['serial']+' ')]
                    check(cli.returncode == 1 and not blocked['complete'] and blocked['managementVerified']
                          and [row['status'] for row in blocked['devices']] == ['launch-requested', 'venue-check-failed', 'not-attempted']
                          and blocked['devices'][1]['failedStep'] == 'verify-live-venue-before-stop'
                          and active_config.read_bytes() == original and not staged_file.exists()
                          and any(' shell rm -f ' in line and staged_file.name in line for line in affected)
                          and not any(' shell am force-stop ' in line or ' shell monkey ' in line
                                      or (' shell mv ' in line and line.endswith('/vr-connection.json')) for line in affected)
                          and not (staging/selected[2]['serial']).exists(),
                          'After staging, a stale original MR source discards the second mock temporary file without stopping its app')
            finally:
                if cli.poll() is None: cli.kill(); cli.communicate(timeout=10)
        previous = staging/'interrupted.json'
        previous.write_bytes(stdout.encode('utf-8'))
        first_connection = staging/selected[0]['serial']/'vr-connection.json'
        first_bytes = first_connection.read_bytes()
        wait(lambda: request(route, strict)['liveSourceVerified'], 18, 'the original MR publisher recovers after staging interruption')
        recovered_world = request(session_route + '/world')
        resumed_cli = subprocess.run([*stage_command, '-RetryIncomplete', str(previous)], env=stage_env, cwd=staging,
                                     encoding='utf-8', capture_output=True, timeout=45)
        resumed = json.loads(resumed_cli.stdout)
        new_commands = (staging/'adb.log').read_text(encoding='utf-8').splitlines()[len(commands):]
        check(resumed_cli.returncode == 0 and resumed['complete'] and all(row['status'] == 'launch-requested' for row in resumed['devices'])
              and resumed['previousDeploymentSha256'] == hashlib.sha256(previous.read_bytes()).hexdigest()
              and recovered_world['header'] == stale_world['header'] and recovered_world['acceptedSequence'] > stale_world['acceptedSequence']
              and first_connection.read_bytes() == first_bytes and active_config.read_bytes() != original
              and {line.split()[1] for line in new_commands if line.startswith('-s ')} == {row['serial'] for row in selected[1:]},
              'The same MR publisher recovers and the original report retries only the blocked and unattempted mock devices')
        save('mr-venue-activation-gate.json', {'blocked': blocked, 'retried': resumed, 'stagedSha256': staged_hash,
            'originalActiveSha256': hashlib.sha256(original).hexdigest(), 'heldSequence': stale_world['acceptedSequence'],
            'resumedSequence': recovered_world['acceptedSequence'], 'staleSeats': len(stale['seats'])})
    def check_mixed_venue_bundle():
        stage('native-mixed-venue-bundle')
        markers = [{'room': {'x': x, 'z': z}, 'tracking': {'x': x, 'z': z}} for x, z in [(-2, -2), (2, -2), (-2, 2)]]
        files = {room: b'\xef\xbb\xbf' + json.dumps(request('/api/room-alignment', {'roomId': room, 'markers': markers})).encode() + b'\r\n'
                 for room in (2, 4)}
        hashes = {room: hashlib.sha256(raw).hexdigest() for room, raw in files.items()}
        alignment_exports = save_room_alignment_exports(files)
        endpoint = '/api/mixed-deployment/venue'
        staged = []
        for room in range(1, 6):
            mode = 'MR' if room in files else 'VR'
            state = create([room], f'Mixed venue {room}', experience=mode)
            route = '/api/sessions/' + state['id']
            if room in files:
                request(route + '/commands', {'commandId': str(uuid.uuid4()), 'action': 'SetRoomAlignment',
                                              'roomAlignment': {f'room{room}': hashes[room]}})
            for seat in range(1, 6):
                headset = 'ViveXr' if room == 1 and seat == 2 else 'Quest3'
                state = request(route + '/players', {'playerId': str(uuid.uuid4()), 'roomId': room,
                                'name': f'Mixed venue {room}/{seat}', 'headset': headset})
            staged.append((state, launch(state, f'mixed-room-{room}')))
        before = request('/api/sessions')
        preview_raw, headers = request(endpoint, raw_response=True)
        preview = json.loads(preview_raw)
        check(preview['ready'] and headers['Cache-Control'] == 'no-store'
              and all((row['roomId'], row['sessionId'], row['mode'], row.get('alignmentSha256')) ==
                      (room, state['id'], state['environment']['mode'], hashes.get(room))
                      and (row['endpoint']['address'], row['endpoint']['port'], row['endpoint']['streamId']) ==
                      (address, entry['ready']['port'], entry['ready']['streamId'])
                      and [(seat['number'], seat['playerId'], seat['admissionId']) for seat in row['seats']] ==
                      [(seat['seat']+1, seat['id'], seat['admissionId']) for seat in state['players']]
                      for room, (row, (state, entry)) in enumerate(zip(preview['rooms'], staged, strict=True), 1)),
              'mixed preview binds all 25 current admissions, modes, original streams and locked MR hashes')
        bundle_rooms = [{'roomId': row['roomId'], 'sessionId': row['sessionId'], 'mode': row['mode'],
                         'streamId': row['endpoint']['streamId'],
                         'players': [{key: seat[key] for key in ('playerId', 'admissionId')} for seat in row['seats']],
                         **({'alignmentFile': base64.b64encode(files[row['roomId']]).decode()} if row['roomId'] in files else {})}
                        for row in preview['rooms']]
        request(endpoint, role='Room1', expected=403)
        request(endpoint+'-bundle', {'rooms': bundle_rooms}, role='Room1', expected=403)
        wrong_hash = [dict(row, alignmentFile=base64.b64encode(files[2] + b'\n').decode()) if row['roomId'] == 2 else row for row in bundle_rooms]
        wrong_stream = [dict(row, streamId=str(uuid.uuid4())) if row['roomId'] == 5 else row for row in bundle_rooms]
        check(request(endpoint+'-bundle', {'rooms': wrong_hash}, expected=409)['code'] == 'venue-alignment-mismatch'
              and request(endpoint+'-bundle', {'rooms': wrong_stream}, expected=409)['code'] == 'venue-source-changed',
              'mixed issuance rejects changed alignment bytes or a stale native stream')
        node, pwsh = shutil.which('node'), shutil.which('pwsh')
        if not node or not pwsh: raise RuntimeError('Node and PowerShell are required for the mixed ZIP check')
        with tempfile.TemporaryDirectory(prefix='mixed-', dir=runtime) as scratch:
            destination = Path(scratch).resolve()
            paths = {}
            for room, original in files.items():
                path = destination/f'original-{room}.json'
                path.write_bytes(original)
                paths[room] = str(path)
            descriptor, bundle = destination/'descriptor.json', destination/'vr-mr-venue-deployment.zip'
            descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'mode':'Mixed','alignments':paths,
                                              **room_endpoint_descriptor(preview)}),encoding='utf-8')
            with (out/'mixed-venue-browser.log').open('xb') as log:
                subprocess.run([node, str(ROOT/'tests/browser/check-vr-venue-tickets-native.cjs'), str(descriptor), str(bundle),
                                str(out/'mixed-venue-browser.json')], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=65)
            check(read(out/'mixed-venue-browser.json')['complete'], 'shipped browser uploads only the two MR files and downloads the mixed ZIP')
            if args.check_room_endpoints:
                check(read(out/'mixed-venue-browser.json')['verifiedRoomEndpoints'] == 5, 'mixed shipped room cards show five original UDP endpoints')
            raw = bundle.read_bytes()
            live = {'topology': 'Independent', 'rooms': []}
            expected = {'venue.json'}
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                manifest = json.loads(archive.read('venue.json'))
                assert (manifest['version'], manifest['mode'], manifest['topology']) == (2, 'Mixed', 'Independent')
                for row, source in zip(manifest['rooms'], preview['rooms'], strict=True):
                    room = row['roomId']
                    assert row == {'roomId': source['roomId'], 'sessionId': source['sessionId'], 'mode': source['mode'],
                                   'address': address, 'port': source['endpoint']['port'], 'ticketsZip': f'room-{room:02}-connections.zip',
                                   **({'alignmentFile': f'room-{room:02}-alignment.json'} if room in files else {})}
                    expected.add(row['ticketsZip'])
                    wanted = {key: row[key] for key in ('roomId', 'sessionId', 'mode')}
                    if room in files:
                        expected.add(row['alignmentFile'])
                        assert archive.read(row['alignmentFile']) == files[room]
                        wanted['alignmentFile'] = base64.b64encode(files[room]).decode()
                    with zipfile.ZipFile(io.BytesIO(archive.read(row['ticketsZip']))) as inner:
                        names = [f'room-{room:02}-seat-{seat:02}.json' for seat in range(1, 6)]
                        assert sorted(inner.namelist()) == names
                        wanted['connectionFiles'] = [base64.b64encode(inner.read(name)).decode() for name in names]
                    live['rooms'].append(wanted)
                assert sorted(archive.namelist()) == sorted(expected)
            check(True, 'mixed ZIP contains five original room ticket bundles and exactly two unchanged MR alignment files')
            request(endpoint+'-check', live, role='Room1', expected=403)
            accepted = request(endpoint+'-check', live)
            check(accepted['allMatched'] and [(row['roomId'], row['seat'], row['status'], row['headset']) for row in accepted['seats']] ==
                  [(room, seat, 'matched', 'ViveXr' if (room, seat) == (1, 1) else 'Quest3')
                   for room in range(1, 6) for seat in range(5)], 'mixed live check validates all 25 signatures and current headset assignments')
            for room_id in (1, 2):
                room = live['rooms'][room_id-1]
                first = room['connectionFiles'][0]
                changed = json.loads(base64.b64decode(first))
                changed['port'] = 7777 if changed['port'] != 7777 else 7778
                room['connectionFiles'][0] = base64.b64encode(json.dumps(changed).encode()).decode()
                rejected_check = request(endpoint+'-check', live)
                room['connectionFiles'][0] = first
                check(not rejected_check['allMatched'] and [(row['roomId'], row['seat'], row['status']) for row in rejected_check['seats']
                      if row['status'] != 'matched'] == [(room_id, 0, 'endpoint-mismatch')],
                      f'mixed live check rejects a changed {room["mode"]} destination')
            deploy = [pwsh, '-NoProfile', '-File', str(ROOT/'scripts/deploy-quest.ps1'), '-VenueBundle', str(bundle), '-ManagementApi', uri]
            environment = {**os.environ, 'VR_COMMAND_MASTER_KEY': keys['Master']}
            report = json.loads(subprocess.check_output(deploy, env=environment, timeout=25, encoding='utf-8', cwd=destination))
            check(report['mode'] == 'Mixed' and report['managementVerified'] and report['alignmentPinsVerified']
                  and report['seats'] == 25 and [row['mode'] for row in report['rooms']] == ['VR','MR','VR','MR','VR'],
                  'Quest CLI confirms the whole mixed ZIP against the packaged API before selecting seats')
            save('mixed-venue-deployment.json', report)
            if args.check_windows_venue_staging:
                seat_map = destination / 'windows-seat-map.json'
                delivery = destination / 'windows-delivery'
                stage_windows = [*deploy, '-WindowsSeatMap', str(seat_map), '-WindowsOutputDirectory', str(delivery)]
                for room, seat, message in ((2, 1, 'belongs to an MR room'), (1, 1, 'not assigned to VIVE XR')):
                    seat_map.write_text(json.dumps({'version': 1, 'seats': [{'roomId': room, 'seat': seat, 'station': 'PC-A'}]}), encoding='utf-8')
                    denied = subprocess.run(stage_windows, env=environment, timeout=25, encoding='utf-8', capture_output=True)
                    check(denied.returncode != 0 and message in denied.stderr and not delivery.exists(),
                          f'Mixed Windows staging refuses room {room} seat {seat} without publishing files')
                seat_map.write_text(json.dumps({'version': 1, 'seats': [{'roomId': 1, 'seat': 2, 'station': 'PC-A'}]}), encoding='utf-8')
                windows = json.loads(subprocess.check_output(stage_windows, env=environment, timeout=25, encoding='utf-8'))
                file = delivery / 'pc-PC-A-room-01-seat-02.json'
                check(windows['managementVerified'] and windows['liveSourceVerified']
                      and windows['topology'] == 'Independent' and len(windows['seats']) == 1
                      and windows['seats'][0]['file'] == file.name and list(delivery.iterdir()) == [file]
                      and file.read_bytes() == base64.b64decode(live['rooms'][0]['connectionFiles'][1]),
                      'Mixed Windows staging preserves only the original signed VR seat')
                save('mixed-venue-windows-staging.json', windows)
            tracking = subprocess.run([*deploy, '-VerifyTrackedSeats', '-AdbPath', str(destination/'absent-adb.exe')],
                env=environment, timeout=25, encoding='utf-8', cwd=destination, capture_output=True)
            tracked = json.loads(tracking.stdout)
            save('mixed-venue-tracked-readiness.json', tracked)
            quest_seats = [(row['roomId'], row['seat'] + 1) for row in accepted['seats'] if row['headset'] == 'Quest3']
            check(tracking.returncode == 1 and tracked['complete'] is False and tracked['managementVerified'] is True
                  and [(row['roomId'], row['seat'], row['status'], row['sourceState']) for row in tracked['seats']] ==
                      [(room, seat, 'awaiting-tracked-pose', 'Fresh') for room, seat in quest_seats],
                  'mixed Quest tracking check distinguishes 24 untracked Quest seats from one VIVE seat')
            tracking = subprocess.run([*deploy, '-VerifyTrackedSeats', '-AllHeadsets', '-AdbPath', str(destination/'absent-adb.exe')],
                env=environment, timeout=25, encoding='utf-8', cwd=destination, capture_output=True)
            tracked = json.loads(tracking.stdout)
            save('mixed-all-headset-readiness.json', tracked)
            check(tracking.returncode == 1 and tracked['complete'] is False and tracked['managementVerified'] is True and tracked['scope'] == 'venue'
                  and [(row['roomId'], row['seat'], row['registeredHeadset'], row['status'], row['sourceState']) for row in tracked['seats']] ==
                      [(row['roomId'], row['seat'] + 1, row['headset'], 'awaiting-tracked-pose', 'Fresh') for row in accepted['seats']],
                  'mixed VR and MR venue tracking checks all 25 original admissions without ADB')
            for room_id, mode in ((1, 'VR'), (2, 'MR')):
                seat = json.loads(subprocess.check_output([*deploy, '-RoomId', str(room_id), '-Seat', '1', '-CheckOnly'],
                                  env=environment, timeout=25, encoding='utf-8', cwd=destination))
                check(seat['roomId'] == room_id and seat['seat'] == 1 and seat['mode'] == mode and seat['managementVerified']
                      and seat.get('alignmentSha256') == hashes.get(room_id), f'single-seat mixed preflight uses the {mode} room settings')
                save(f'mixed-venue-seat-{room_id}.json', seat)
            verify_mapped_quest(deploy, destination, environment, raw, 'Independent', files, hashes, partial=True, mixed=True)
        check(request('/api/sessions') == before, 'mixed issuance, online verification and mock ADB leave management sessions unchanged')
        for state, _ in staged: command(state['id'], 'End')
        for state, entry in staged:
            finish(entry)
            if state['environment']['mode'] == 'MR':
                verify_mr_alignment_archive(entry, alignment_exports)
    def verify_mapped_quest(deploy, destination, environment, raw, mode, files=None, hashes=None, *, partial=False, mixed=False):
        is_vr = files is None
        rows = [{'roomId': room, 'seat': seat, 'serial': f'fixture-{(room-1)*5+seat:02}'} for room in range(1, 6) for seat in range(1, 6)]
        if partial:
            rows = [row for row in rows if row['seat'] == {1:1, 2:3, 3:5, 4:1, 5:3}[row['roomId']]]
        mapping = destination / 'device-map.json'
        mapping.write_text(json.dumps({'version': 1, 'seats': rows[::-1]}), encoding='utf-8')
        mapped = [*deploy, '-DeviceMap', str(mapping), '-ExpectedVersionCode', '61', '-AdbPath', str(ROOT/'tests/fixtures/mock-quest-fleet.ps1')]
        environment = {**environment, 'VR_QUEST_FLEET_FIXTURE': str(destination), 'VR_QUEST_FLEET_FAULTS': ''}
        if partial:
            mapped.append('-AllowPartialMap')
        if partial and is_vr:
            mapping.write_text(json.dumps({'version': 1, 'seats': [*rows, {'roomId': 2, 'seat': 2, 'serial': 'fixture-07'}]}), encoding='utf-8')
            refused = subprocess.run([*mapped, '-DeployMappedSeats'], env=environment, timeout=45, encoding='utf-8',
                                     cwd=destination, capture_output=True)
            if not refused.stdout.strip():
                locked = 'Another Quest deployment is running' in refused.stderr
                save(f'vr-venue-{mode.lower()}-partial-rejection-no-report.json',
                     {'exitCode': refused.returncode, 'deploymentMutexBusy': locked})
                raise RuntimeError(f'{mode} Quest deployment did not emit a report (exit {refused.returncode}, mutex busy: {locked})')
            result = json.loads(refused.stdout)
            check(refused.returncode == 1 and result['complete'] is False and result['managementVerified'] is True
                  and result['mappedSeats'] == 6 and not any(destination.glob('fixture-*'))
                  and [row for row in result['devices'] if row['status'] != 'ready'] ==
                      [{'roomId': 2, 'seat': 2, 'status': 'seat-headset-mismatch', 'versionCode': 61}],
                  mode + ' a live VIVE assignment blocks all requested Quest writes')
            save(f'vr-venue-{mode.lower()}-partial-rejection.json', result)
            (destination/'adb.log').unlink()
            mapping.write_text(json.dumps({'version': 1, 'seats': rows[::-1]}), encoding='utf-8')
        if partial:
            environment['VR_QUEST_FLEET_FAULTS'] = json.dumps({'fixture-07': 'offline', 'fixture-25': 'wrong-model'})
        count = len(rows)
        def invoke(flag):
            return json.loads(subprocess.check_output([*mapped, flag], env=environment, timeout=45, encoding='utf-8', cwd=destination))
        preview = invoke('-CheckOnly')
        check(preview['complete'] and preview['managementVerified'] and preview['phase'] == 'preflight'
              and (preview.get('mode') == 'VR' if is_vr else preview.get('alignmentPinsVerified') is True)
              and (not mixed or preview.get('mode') == 'Mixed')
              and [row['status'] for row in preview['devices']] == ['ready']*count
              and (not partial or (preview['mappedSeats'], preview['unmappedSeats']) == (count, 25-count))
              and not any(destination.glob('fixture-*')), mode + f' mapped preflight confirms {count} mocked devices with no configuration writes')
        (destination/'adb.log').unlink()
        applied = invoke('-DeployMappedSeats')
        check(applied['complete'] and applied['managementVerified'] and applied['phase'] == 'deployment'
              and (applied.get('mode') == 'VR' if is_vr else applied.get('alignmentPinsVerified') is True)
              and (not mixed or applied.get('mode') == 'Mixed')
              and (not partial or (applied['mappedSeats'], applied['unmappedSeats']) == (count, 25-count))
              and applied['devices'] == [{'roomId': row['roomId'], 'seat': row['seat'], 'status': 'launch-requested',
                                          'versionCode': 61, 'filesVerified': True} for row in rows],
              mode + f' mapped deployment submits launch for exactly the {count} requested mock devices')
        with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
            for row in rows:
                room, seat = row['roomId'], row['seat']; remote = destination / row['serial']
                with zipfile.ZipFile(io.BytesIO(bundle.read(f'room-{room:02}-connections.zip'))) as tickets:
                    config = json.loads(tickets.read(f'room-{room:02}-seat-{seat:02}.json'))
                names = {'vr-connection.json'}
                if files is not None and room in files:
                    config.update(questPassthrough=True, requestMixedReality=True)
                    alignment = f'vr-room-alignment-{hashes[room]}.json'
                    assert (remote/alignment).read_bytes() == files[room]
                    names.add(alignment)
                assert read(remote/'vr-connection.json') == config
                assert {item.name for item in remote.iterdir()} == names
        commands = (destination/'adb.log').read_text(encoding='utf-8').splitlines()
        targeted = {line.split()[1] for line in commands if line.startswith('-s ')}
        mr_count = sum(files is not None and row['roomId'] in files for row in rows)
        check(len(commands) == 1 + count * 11 + mr_count * 4 and sum(' shell monkey ' in line for line in commands) == count
              and sum(line.endswith(' shell getprop ro.serialno') for line in commands) == 2 * count
              and sum(' shell sha256sum ' in line for line in commands) == 2 * (count + mr_count)
              and targeted == {row['serial'] for row in rows}
              and all(' install ' not in line and 'unmapped-device' not in line for line in commands),
              mode + f' all {count} mapped original signed configs verify device identity and the expected mode files without APK installs')
        for row in rows:
            seat_commands = [line for line in commands if line.startswith(f'-s {row["serial"]} ')]
            staged = next(i for i, line in enumerate(seat_commands)
                          if ' shell sha256sum ' in line and '/vr-connection-' in line and line.endswith('.tmp'))
            stop = next(i for i, line in enumerate(seat_commands) if ' shell am force-stop ' in line)
            active = next(i for i, line in enumerate(seat_commands) if ' shell mv ' in line and line.endswith('/vr-connection.json'))
            verified = next(i for i, line in enumerate(seat_commands)
                            if ' shell sha256sum ' in line and line.endswith('/vr-connection.json'))
            launch = next(i for i, line in enumerate(seat_commands) if ' shell monkey ' in line)
            assert staged < stop < active < verified < launch, f'Unexpected Quest activation order for room {row["roomId"]} seat {row["seat"]}'
            if files is not None and row['roomId'] in files:
                pin = f'/vr-room-alignment-{hashes[row["roomId"]]}.json'
                aligned = next(i for i, line in enumerate(seat_commands) if ' shell sha256sum ' in line and line.endswith(pin))
                assert aligned < stop, f'Quest MR pin was not verified before stopping room {row["roomId"]} seat {row["seat"]}'
        check(True, mode + f' all {count} devices verify staged files before stop and verify active config before launch')
        prefix = 'mixed' if mixed else 'vr' if is_vr else 'mr'
        kind = 'partial' if partial else 'mapped'
        save(f'{prefix}-venue-{mode.lower()}-{kind}-preflight.json', preview)
        save(f'{prefix}-venue-{mode.lower()}-{kind}-deployment.json', applied)
        if not (mixed or args.check_quest_deployment_retry):
            return

        recovery = destination / 'recovery'
        recovery.mkdir()
        first, failed, *pending = rows
        log = recovery / 'adb.log'
        recovery_env = {**environment, 'VR_QUEST_FLEET_FIXTURE': str(recovery),
                        'VR_QUEST_FLEET_FAULTS': json.dumps({failed['serial']: 'config-active-changed'})}
        interrupted = subprocess.run([*mapped, '-DeployMappedSeats'], env=recovery_env, timeout=45,
                                     cwd=destination, capture_output=True)
        failed_report = json.loads(interrupted.stdout)
        check(interrupted.returncode == 1 and not failed_report['complete'] and failed_report['managementVerified']
              and [device['status'] for device in failed_report['devices']] ==
              ['launch-requested', 'file-verification-failed', *(['not-attempted'] * len(pending))]
              and [device.get('failedStep') for device in failed_report['devices']] ==
              [None, 'verify-active-connection', *([None] * len(pending))]
              and sum(' shell monkey ' in line for line in log.read_text(encoding='utf-8').splitlines()) == 1
              and not any((recovery / row['serial']).exists() for row in pending),
              mode + ' deployment identifies an active-file verification failure after the first successful seat')
        previous = recovery / first['serial'] / 'vr-connection.json'
        previous_bytes = previous.read_bytes()
        retry_rows = [failed, *pending]
        map_bytes = mapping.read_bytes()
        report_file = recovery / 'interrupted-deployment.json'
        report_file.write_bytes(interrupted.stdout)
        (recovery / 'interrupted-adb.log').write_bytes(log.read_bytes())
        log.unlink()
        recovery_env['VR_QUEST_FLEET_FAULTS'] = ''
        retry_bytes = subprocess.check_output([*mapped, '-DeployMappedSeats', '-RetryIncomplete', str(report_file)],
                                              env=recovery_env, timeout=45, cwd=destination)
        retried = json.loads(retry_bytes)
        retry_commands = log.read_text(encoding='utf-8').splitlines()
        check(retried['complete'] and retried['managementVerified']
              and (not partial or retried['mappedSeats'] == len(rows))
              and retried['devices'][0] == failed_report['devices'][0]
              and retried['retry'] == failed_report['retry']
              and retried['previousDeploymentSha256'] == control.sha(report_file)
              and mapping.read_bytes() == map_bytes
              and [(device['roomId'], device['seat'], device['status'], device.get('filesVerified')) for device in retried['devices']]
              == [(row['roomId'], row['seat'], 'launch-requested', True) for row in rows]
              and {line.split()[1] for line in retry_commands if line.startswith('-s ')} == {row['serial'] for row in retry_rows}
              and previous.read_bytes() == previous_bytes
              and all((recovery / row['serial'] / 'vr-connection.json').read_bytes() ==
                      (destination / row['serial'] / 'vr-connection.json').read_bytes() for row in retry_rows),
              mode + ' retry touches only failed and pending seats with the original signed bundle and map')
        recovery_prefix = 'mixed-venue' if mixed else f'vr-venue-{mode.lower()}'
        for phase, raw in (('interrupted', interrupted.stdout), ('retried', retry_bytes)):
            with (out / f'{recovery_prefix}-{phase}-deployment.json').open('xb') as saved:
                saved.write(raw)
    try:
        management_port=venue_browser_port() if args.check_venue_plan_ui else free()
        subprocess.run([str(control_exe),'--init',str(data),'--port',str(management_port),'--report',str(out/'control-init.json')],env=env,check=True,timeout=30);keys=read(data/'operator-keys.json')['OperatorKeys'];marker=read(data/'control-instance.json');uri='http://127.0.0.1:'+str(marker['port'])
        control_env = env
        if args.venue_management_https:
            port = free(address=address)
            while port == marker['port']:
                port = free(address=address)
            venue_uri = f'https://{address}:{port}'
            venue_password = uuid.uuid4().hex + uuid.uuid4().hex
            control_env = dict(env, VR_COMMAND_CONTROL_PFX_PASSWORD=venue_password)
            (data / 'control-https.json').write_text(json.dumps({'schemaVersion': 1, 'bindAddress': address, 'port': port}), encoding='utf-8')
            subprocess.run([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-File',
                            str(ROOT / 'tools/WindowsControlLauncher/Tests/New-HttpsFixture.ps1'),
                            '-Directory', str(data), '-Address', address], env=control_env, timeout=30, check=True)
            venue_pin = control.sha(data / 'leaf.cer')
            venue_target = runtime / 'game-host-profile' / 'control-instance.json'
            venue_target.parent.mkdir()
            venue_target.write_text(json.dumps({'schemaVersion': 1, 'kind': 'VrCommand-RemoteGameServer',
                                                'instanceId': marker['instanceId'], 'managementApiUrl': venue_uri,
                                                'managementCertificateSha256': venue_pin, 'gameServerKey': keys['GameServer']}), encoding='utf-8')
        api_ready=out/'control-ready.json';api_stop=out/'control-stop.request';api=subprocess.Popen([str(control_exe),'--run',str(data),'--seconds','1800','--ready-report',str(api_ready),'--stop-file',str(api_stop),'--report',str(out/'control-final.json')],env=control_env,cwd=out)
        info=wait(lambda:read(api_ready) if api_ready.exists() else None,40,'control startup');api_witness=control.ChildWitness(info['childPid']);check(info['status']=='ready','packaged control API without SDK on PATH');call('verify',['--verify','package'],True)
        if venue_pin:
            check(info['httpsBinding'] == venue_uri and info['uri'] == uri, 'isolated management API publishes separate pinned HTTPS and loopback HTTP bindings')
        if args.check_room_readiness:request('/api/rooms/readiness',role='GameServer',expected=403)
        seed=create([1],'preflight');base=config(seed['id'])
        for name,change in [('master',{'gameServerKey':keys['Master']}),('room-key',{'gameServerKey':keys['Room1']}),('client-role',{'role':'Client'}),('host-role',{'role':'Host'}),('ambiguous-ip',{'address':'127.1'}),('wildcard-advertise',{'address':'0.0.0.0'}),('multicast',{'address':'224.0.0.1'}),('overflow-port',{'port':4294975073}),('extra-key',{'masterKey':'never-pass-to-unity'}),('url-userinfo',{'managementApiUrl':uri.replace('http://','http://user@')})]:rejected(name,dict(base,**change))
        rejected('short-timeout',base,seconds=59)
        if args.peer_diagnostics:rejected('invalid-peer-diagnostics',base,extra=['--peer-diagnostics','off'])
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as occupied:
            occupied.bind((address,0));rejected('occupied-udp',dict(base,port=occupied.getsockname()[1]))
            request('/api/sessions/' + seed['id'] + '/connection-endpoint', expected=404)
            check(request('/api/sessions/' + seed['id'])['combatStream'] is None,
                  'occupied UDP preflight leaves the management session and endpoint unbound')
        command(seed['id'],'End');rejected('ended-session',base)
        # Run both topologies with separate native processes and fresh admissions.
        archived_batch_report = None
        earlier_field_archive = None
        earlier_closure = None
        imported_mission = None
        if args.mission_template:
            with args.mission_template.open('rb') as source:
                raw = source.read(512*1024+1)
            template = request('/api/mission-templates/check-file',raw,method='POST')
            check(template==json.loads(raw) and template['definition']['environment']['mode']=='VR',
                  'destination management verifies the exact exported VR template')
            imported_mission=request('/api/missions',template['definition'],expected=201,request_id=str(uuid.uuid4()))
            check(imported_mission['definition']==template['definition'],'destination management explicitly saves the template as a new mission')
            save('imported-mission.json',imported_mission)
        if args.openxr_mock_only:
            check_openxr_mock()
        if args.check_venue_launcher:
            unlocked=create(list(range(1,6)),'unlocked venue alignment',experience='MR')
            launch_venue([unlocked],True,unlocked_mr=True)
            command(unlocked['id'],'End')
        for linked in ([] if venue_only or args.openxr_mock_only else [False,True]):
            entries=[];round_clients=[];staged=[]
            batch=None
            if args.prepare_independent_set and not linked:
                if args.check_independent_room_missions:
                    missions=[]
                    for room, weather in enumerate(('Clear','Rain','Fog','Storm','Rain'),1):
                        definition={'name':f'Portable distinct room {room}','briefing':f'Only room {room}', 'durationSeconds':180+30*room,
                            'environment':{'mode':'VR','weather':weather,'timeOfDay':'Night' if room%2 else 'Day','lightning':weather=='Storm'},
                            'enemies':{'count':room+1,'behavior':('Hold','Patrol','Advance')[(room-1)%3],'autoAttack':False},
                            'props':[{'assetId':'barrel','position':{'x':2*room-6,'y':0,'z':2},'yawDegrees':15*room}]}
                        missions.append(request('/api/missions',definition,expected=201))
                    body={'rooms':[{'roomId':room,'missionId':mission['id']} for room,mission in enumerate(missions,1)]}
                else:
                    mission=imported_mission or save_mission('five independently prepared rooms',enemy_count=5 if args.check_room_combat else 1)
                    missions=[mission]*5
                    body={'missionId':mission['id']}
                route='/api/sessions/independent-set'
                if args.check_independent_room_layouts_ui:
                    output = out / 'native-independent-room-layouts.json'
                    driver = ROOT / 'tests/browser/server-plan-browser.cjs'
                    invalid = save_mission('overlapping independent room layout', props=[
                        {'assetId': asset, 'position': {'x': 0, 'y': 0, 'z': 2}, 'yawDegrees': 0}
                        for asset in ('sandbag', 'barrel')])
                    completed = subprocess.run([shutil.which('node'), str(driver)], cwd=driver.parent,
                        input=json.dumps({'base': uri, 'token': keys['Master'], 'missions': missions,
                                          'invalidMission': invalid['id'], 'output': str(output),
                                          'useMissionFile': args.check_venue_mission_file_ui}),
                        capture_output=True, encoding='utf-8', timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
                    check(completed.returncode == 0 and output.is_file(), 'shipped browser reviews and submits all five original room layouts: '
                          + completed.stderr.replace(keys['Master'], '[redacted]')[-600:])
                    observed = read(output)
                    if args.check_venue_mission_file_ui:
                        check(observed['filePlan'] == {'schemaVersion': 1, 'mode': 'IndependentSet', **body},
                              'fresh console reopens the saved independent mission file with the five original assignments')
                        check(read(out/'native-independent-mission-file-review.json') == {'mode': 'IndependentSet',
                              'rooms': [dict(room, layout='valid') for room in body['rooms']]},
                              'fresh console previews each original independent assignment and layout before loading')
                    check(observed['rejection'] == {'roomId': 4, 'invalidProps': [0, 1],
                          'marked': [{'roomId': room, 'indices': [0, 1]} for room in (4, 5)]},
                          'the exact creation rejection marks the two shared invalid props before the browser submits corrected assignments')
                    check([{'roomId': row['roomId'], 'missionId': row['missionId']} for row in observed['previews']] == body['rooms'],
                          'all five native preparation targets match the exact browser previews')
                    key, prepared = observed['requestId'], observed['prepared']
                else:
                    key = str(uuid.uuid4())
                    prepared = request(route, body, expected=201, request_id=key)
                batch=prepared['sessions']
                sessions.extend(state['id'] for state in batch)
                retry=request(route,body,request_id=key)
                check(not prepared['duplicate'] and retry['duplicate'] and retry['sessions']==batch
                      and [state['roomIds'] for state in batch]==[[room] for room in range(1,6)]
                      and all(state['mission']==mission and state['mode']=='Independent' and state['state']=='Preparing' for state,mission in zip(batch,missions)),
                      'one real management request prepares all five native independent sessions and its retry returns the same IDs')
                save('independent-preparation-receipt.json',prepared)
            if args.check_venue_launcher and not linked:
                venue_entries=launch_venue(batch,False)
            for rooms in ([[1,2,3,4,5]] if linked else [[r] for r in range(1,6)]):
                enemy_count=5*len(rooms) if args.check_room_combat else (5 if linked and args.check_linked_room_enemies else 1)
                if batch is not None:
                    state=batch[rooms[0]-1]
                elif imported_mission:
                    state=request('/api/sessions',{'missionId':imported_mission['id'],'mode':'Linked','roomIds':rooms},expected=201)
                    sessions.append(state['id'])
                elif linked and args.check_linked_archive_plan_ui:
                    state=prepare_linked_archive(rooms)
                else:
                    room_replay_props = [{'assetId':'barrel','position':{'x':4.5,'y':0,'z':4.5},'yawDegrees':0}]
                    state=create(rooms,'linked' if linked else 'independent',enemy_count=enemy_count,
                                 props=room_replay_props if linked and (args.check_player_room_replay or args.check_room_observer) else None)
                if args.check_venue_launcher:
                    entry=launch_venue([state],True)[0] if linked else venue_entries[rooms[0]-1]
                else:
                    entry=launch(state,('linked' if linked else 'room-'+str(rooms[0])))
                entries.append(entry)
                if args.check_room_clocks and (linked or rooms == [1]):
                    request('/api/sessions/'+state['id']+'/commands', {'commandId':str(uuid.uuid4()),'action':'SetMissionClock','missionClock':{'autoEnd':True}})
                entry['combatEnemyCount']=enemy_count
                if not linked and rooms==[1]:rejected('bound-preparing',config(state['id']))
                for room in rooms:
                    if args.check_vr_venue_tickets: staged.append((entry, room, prepare_room_roster(entry, room)))
                    else: round_clients.extend(room_players(entry,room) if player_folder else [player(entry,room)])
            if args.check_vr_venue_tickets: round_clients=venue_ticket_players(staged,linked)
            owner_ids={entry['sessionId']:[c['player']['id'] for c in round_clients if c['sessionId']==entry['sessionId']] for entry in entries}
            if args.check_venue_begin:
                route='/api/venue/phase'
                preview=request(route)['begin']
                targets=[{key:row[key] for key in ('sessionId','phaseSinceSequence','sessionSequence')} for row in preview]
                check({row['sessionId'] for row in targets}==set(owner_ids)
                      and sorted(room for row in preview for room in row['roomIds'])==list(range(1,6)),
                      'native Begin preview covers exactly the original five rooms')
                expected={row['sessionId']:row['sessionSequence'] for row in targets}
                def begin_when_ready():
                    rows=request('/api/rooms/readiness')['rooms']
                    if len(rows)==5 and all(row['venueBeginReady'] and row['sessionSequence']==expected.get(row['sessionId']) for row in rows):
                        return rows
                preparing=wait(begin_when_ready,60,'five fresh original Preparing room aggregates')
                body={'action':'Begin','targets':targets};key=str(uuid.uuid4())
                if args.check_venue_tracking_gate:
                    denied=request(route,{**body,'requireFullTracking':True},request_id=str(uuid.uuid4()),expected=409)
                    unchanged=request(route)['begin']
                    check(all(row['registered']==players_per_room and row['trackedReady']<5 for row in preparing)
                          and denied['code']=='venue-begin-not-ready' and denied['roomIds']==list(range(1,6))
                          and unchanged==preview, 'full tracking Begin refuses the native simulated roster without advancing any room')
                    save(('linked' if linked else 'independent')+'-full-tracking-denied.json',denied)
                if players_per_room != 5:
                    denied=request(route,{**body,'requireFullParticipation':True},request_id=str(uuid.uuid4()),expected=409)
                    check(denied['code']=='venue-begin-not-ready' and denied['roomIds']==list(range(1,6))
                          and request(route)['begin']==preview,
                          'full-roster Begin refuses the pilot without advancing any room')
                    save(('linked' if linked else 'independent')+'-full-participation-denied.json',denied)
                if args.check_venue_participation_gate:
                    body['requireFullParticipation']=True
                receipt=request(route,body,request_id=key)
                applied={row['sessionId']:row['appliedAtSequence'] for row in receipt['sessions']}
                check(not receipt['duplicate'] and applied=={sid:sequence+1 for sid,sequence in expected.items()},
                      'one native Begin reaches exactly the previewed session revisions')
                if args.check_venue_participation_gate:
                    proofs={}
                    for entry in entries:
                        sid=entry['sessionId']; seq=applied[sid]
                        event,=request(f'/api/sessions/{sid}/events?after={seq-1}&limit=1')
                        witness=event['venue']['participationFrame']
                        packet=request(f'/api/sessions/{sid}/world/frames/{witness["worldSequence"]}')['packet']
                        check(event['sequence']==seq and event['venue']['requireFullParticipation']
                              and witness['streamId']==entry['ready']['streamId'] and packet['sequence']==witness['worldSequence']
                              and packet['observedSequence']==seq-1 and packet['elapsedMilliseconds']==witness['elapsedMilliseconds']
                              and packet['frame']['phase']=='Preparing' and not packet['suspended']
                              and {p['id'] for p in packet['frame']['players']}==set(owner_ids[sid])
                              and all(p['connected'] and p['health']==100 and p['rig']['kind']=='Simulated' for p in packet['frame']['players']),
                              entry['label']+' participation gate retains the exact original Preparing pose for every native admission')
                        proofs[sid]={'appliedAtSequence':seq,'witness':witness,'packet':packet}
                    save(('linked' if linked else 'independent')+'-full-participation-begin.json',proofs)
            for entry in entries:
                sid=entry['sessionId'];ids=owner_ids[sid]
                if args.check_venue_begin:
                    sequence=applied[sid]
                else:
                    wait(lambda:observe(entry,ids),60,entry['label']+' original player rigs')
                    sequence=command(sid,'Begin')['session']['sequence']
                running=wait(lambda:observe(entry,ids,sequence),20,entry['label']+' original Begin applied')
                if imported_mission:
                    verify_template_world(entry,imported_mission,running)
                if linked and args.check_linked_archive_plan_ui:
                    verify_template_world(entry,state['mission'],running,source='archived Linked mission',evidence='archive-plan')
                if args.check_independent_room_missions and not linked:
                    room=entries.index(entry)+1
                    mission=missions[room-1]
                    definition=mission['definition']; environment=definition['environment']; enemies=definition['enemies']
                    info=request(f'/api/sessions/{sid}/world')
                    packet=running['packet']; frame=packet['frame']; props=info['header']['props']
                    check(info['header']['roomIds']==[room] and info['header']['missionDurationSeconds']==definition['durationSeconds']
                          and packet['weather']==environment['weather'] and packet['lightning']==environment['lightning']
                          and frame['night']==(environment['timeOfDay']=='Night') and frame['behavior']==enemies['behavior']
                          and frame['autoAttack']==enemies['autoAttack'] and len(frame['enemies'])==enemies['count']
                          and all(enemy['roomId']==room for enemy in frame['enemies']) and len(props)==1
                          and (props[0]['roomId'],props[0]['kind'],props[0]['feet'],props[0]['yaw']) ==
                              (room,'Barrel',{'x':(room-3)*14+2*room-6,'y':0,'z':2},15*room),
                          entry['label']+' native duration, environment, enemies and cover match its own saved mission')
                    save(entry['label']+'-assigned-mission.json',{'mission':mission,'worldHeader':info['header'],'runningSequence':packet['sequence']})
            if args.check_venue_begin:
                def observed_begin():
                    rows=request('/api/rooms/readiness')['rooms']
                    if len(rows)==5 and all((phase:=row.get('venuePhase')) and phase['action']=='Begin'
                       and phase['appliedAtSequence']==applied.get(row['sessionId']) and phase['worldSequence'] for row in rows):
                        return rows
                observed=wait(observed_begin,20,'five fresh Running confirmations of original Begin')
                retry=request(route,body,request_id=key)
                check(retry['duplicate'] and retry['sessions']==receipt['sessions'],
                      'the late native Begin retry returns the same original receipt')
                if args.check_venue_participation_gate:
                    check(receipt['requireFullParticipation'] is retry['requireFullParticipation'] is True,
                          'native retry keeps the 25-seat policy of the original accepted request')
                save(('linked' if linked else 'independent')+'-venue-begin.json',
                     {'preview':preview,'preparing':preparing,'receipt':receipt,'observed':observed,'retry':retry})
            if args.observe_closure_ui and not linked:
                observer_entry=entries[0];descriptor=runtime/'closure-ui-private.json'
                descriptor.write_text(json.dumps({'base':uri,'masterKey':keys['Master'],'sessionId':observer_entry['sessionId'],
                    'streamId':observer_entry['ready']['streamId'],'endRequestFile':str(out/'closure-end.request'),
                    'roomReadiness':args.check_room_readiness,'roomParticipation':args.check_room_participation,
                    'battleOverview':args.check_room_combat,
                    'debriefReceiptCount':len([client for client in round_clients if client['sessionId']==observer_entry['sessionId']])
                        if args.check_debrief_receipts else None}),encoding='utf-8')
                observer_log=(runtime/'closure-ui.log').open('xb')
                node=shutil.which('node')
                if not node:raise RuntimeError('Test observer requires installed Node; shipped launchers do not')
                observer=subprocess.Popen([node,str(ROOT/'tests/browser/check-closure-native.cjs'),'--descriptor',str(descriptor),'--output',str(observer_out),'--stop-file',str(observer_stop)],stdout=observer_log,stderr=subprocess.STDOUT,cwd=ROOT/'tests/browser')
                def watching():
                    if observer.poll() is not None:raise RuntimeError('Archive UI observer exited before watching')
                    return read(observer_out/'ready.json') if (observer_out/'ready.json').exists() else None
                ready_ui=wait(watching,45,'actual Running console observer');check(ready_ui['selectedSessionId']==observer_entry['sessionId'],'shipped console watches original native Running session')
                if args.check_room_readiness:
                    check(ready_ui['roomReadiness']==[1,2,3,4,5],'shipped console shows all five actual native room counts')
            stage('running-linked' if linked else 'running-five-independent')
            time.sleep(3)
            if player_folder:
                for entry in entries:
                    owners=[c for c in round_clients if c['sessionId']==entry['sessionId']]
                    rooms_by_player={c['player']['id']:c['player']['roomId'] for c in owners}
                    accepted=read(out/(entry['label']+'-running.json'))['acceptedBeginSequence']
                    frame=wait(lambda:observe(entry,rooms_by_player,accepted),20,entry['label']+' live room roster')
                    players=frame['packet']['frame']['players']
                    check(len(players)==len(owners) and {p['id']:p['roomId'] for p in players}==rooms_by_player,
                        entry['label']+' exact connected room roster')
                check(len({c['nativePid'] for c in round_clients})==venue_players and all(
                    c['process'].poll() is None and c['witness'].kernel.WaitForSingleObject(c['witness'].handle,0)==258
                    for c in round_clients),f'{venue_players} simultaneous owned native players '+('Linked' if linked else 'Independent'))
                if windows_release_hash:
                    check(all(read(c['launcherReport'])['playerManifestSha256']==windows_release_hash for c in round_clients),
                          ('Linked' if linked else 'Independent')+f' original {venue_players} player processes all use the released Windows package')
            if args.check_venue_link_metrics:
                stage('collecting-player-link-metrics',mode='Linked' if linked else 'Independent')
                wait(lambda:all(c['linkMetrics'].is_file() for c in round_clients),55,'all original packaged client link reports')
            if args.check_venue_openxr:verify_venue_openxr(entries,round_clients,linked)
            elif args.check_quest_vr_deploy or args.check_quest_vr_partial_map:verify_quest_tracking(linked)
            if args.check_room_readiness:verify_room_readiness(round_clients,linked)
            if args.check_room_observer and linked:
                node = shutil.which('node')
                if not node: raise RuntimeError('Node is required to observe the shipped console')
                descriptor = runtime/'room-observer-private.json'
                descriptor.write_text(json.dumps({'base':uri,'roomKey':keys['Room4'],'sessionId':entries[0]['sessionId'],
                    'players':[{key:client['player'][key] for key in ('id','roomId','name')} for client in round_clients]}), encoding='utf-8')
                browser_out = out/'room-observer'
                subprocess.run([node, str(ROOT/'tests/browser/check-room-observer-native.cjs'), str(descriptor), str(browser_out)],
                               cwd=ROOT/'tests/browser', check=True, timeout=70)
                observed = read(browser_out/'checks.json')
                check(observed['complete'] and observed['players']==25 and observed['sessionId']==entries[0]['sessionId']
                      and len(observed['checks'])==9 and observed['recent']['roomId']==observed['reconnect']['roomId']==2
                      and observed['rowFollow']['roomId']==4 and observed['rowFollow']['withoutNewStream'] is True
                      and observed['rowFollow']['activatedAt']>=observed['rowFollow']['focusedAt']+3
                      and observed['recent']['resumedFrame']>observed['recent']['tail']
                      and observed['reconnect']['recoveredFrame']>observed['reconnect']['disconnectedFrame']
                      and observed['roomOnly']['roomId']==4 and observed['roomOnly']['scopedPlayers']==5
                      and observed['roomOnly']['roomRecovered']>observed['roomOnly']['roomFrame'],
                      'shipped console preserves both shared 25-player observation and the explicit five-player room stream')
            if args.check_room_participation:verify_room_participation(entries,round_clients,linked)
            if args.check_room_clocks:verify_room_clocks(entries,linked)
            if args.check_venue_environment:verify_venue_environment(entries,linked)
            if args.check_room_combat:
                stage('running-native-ai-combat',mode='Linked' if linked else 'Independent')
                exercise_room_combat(entries,round_clients)
            live_samples = []
            if args.check_live_room_navigation:
                stage('checking-live-room-navigation',mode='Linked' if linked else 'Independent')
                live_samples = verify_live_room_navigation(entries,round_clients,linked)
            if args.check_linked_room_enemies and linked:check_linked_room_enemies(entries[0])
            if args.check_venue_phase:verify_venue_phase(entries,linked)
            if args.venue_concurrent_roster_seconds is not None:
                stage('observing-concurrent-roster', mode='Linked' if linked else 'Independent',
                      requiredSeconds=args.venue_concurrent_roster_seconds)
                time.sleep(args.venue_concurrent_roster_seconds + 3)
            if args.check_venue_end:
                route = '/api/venue/phase'
                preview = request(route)['end']
                targets = [{field: row[field] for field in ('sessionId', 'phaseSinceSequence')} for row in preview]
                check({row['sessionId'] for row in targets} == set(owner_ids)
                      and sorted(room for row in preview for room in row['roomIds']) == list(range(1, 6)),
                      'native End preview covers exactly the original five rooms')
                body = {'action': 'End', 'targets': targets}
                key = str(uuid.uuid4())
                receipt = request(route, body, request_id=key)
                applied = {row['sessionId']: row['appliedAtSequence'] for row in receipt['sessions']}
                initial = request('/api/venue/closure')['batch']
                check(not receipt['duplicate'] and receipt['requestId'] == key and set(applied) == set(owner_ids)
                      and initial['requestId'] == key
                      and {row['sessionId']: row['appliedAtSequence'] for row in initial['sessions']} == applied,
                      'the native End receipt and closure overview identify the same original sessions')
            else:
                for entry in entries:
                    if args.observe_closure_ui and not linked and entry is observer_entry:(out/'closure-end.request').write_text('request one normal UI End',encoding='utf-8')
                    else:command(entry['sessionId'],'End')
            for entry in entries:finish(entry)
            for sample in live_samples:
                world_sid, observed_room, frame_sequence = (sample[field] for field in ('sessionId','roomId','sequence'))
                world_route = f'/api/sessions/{world_sid}/world'
                archived = request(world_route+f'?observerRoomId={observed_room}')
                check(archived['complete'] and archived['header']['streamId'] == sample['streamId']
                      and request(world_route+f'/frames/{frame_sequence}?observerRoomId={observed_room}') == sample['frame'],
                      f'{world_sid} room {observed_room} frame {frame_sequence} remains exact after native sealing')
            if args.check_venue_end:
                closed = request('/api/venue/closure')['batch']
                retry = request(route, body, request_id=key)
                check(closed['requestId'] == key
                      and {row['sessionId']: row['appliedAtSequence'] for row in closed['sessions']} == applied
                      and sorted(room for row in closed['sessions'] for room in row['roomIds']) == list(range(1, 6))
                      and all(row['combat'] == row['world'] == 'Sealed' for row in closed['sessions']),
                      'the native closure overview confirms both original archive seals for every room')
                check(retry['duplicate'] and retry['sessions'] == receipt['sessions'],
                      'the late native End retry preserves the original batch after sealing')
                save(('linked' if linked else 'independent')+'-venue-end.json',
                     {'preview': preview, 'receipt': receipt, 'initial': initial, 'closed': closed, 'retry': retry})
                if args.check_venue_replay_ui:
                    verify_venue_replay_ui(entries, closed, linked, earlier_closure if args.check_venue_history_ui else None)
                    earlier_closure = closed
            if args.observe_closure_ui and not linked:
                observer.wait(timeout=70);observer_log.close();observer_log=None;ui=read(observer_out/'checks.json');native=read(observer_entry['reportPath'])
                check(observer.returncode==0 and ui['complete'] and ui['browserClosed'],'actual archive UI observer and browser completed / terminal')
                check(ui['sessionId']==observer_entry['sessionId'] and ui['streamId']==native['streamId'] and ui['acceptedWorldSequence']==native['finalWorld']['acceptedSequence'],'shipped UI archive matches exact original native final world boundary')
                if args.check_room_combat:
                    overview=read(observer_out/'archive-battle-overview.json')
                    stats=observer_entry['sealed']['statistics']
                    check(overview['sessionId']==observer_entry['sessionId'] and overview['statistics']==stats
                          and overview['lastEventSequence']==stats['throughSequence'] and len(overview['displayedRows'])==5
                          and all(row['damageTaken']>0 for row in stats['players']),
                          'shipped battle table and latest event match the five original sealed native combat rows')
            for client in round_clients:
                text=client['log'].read_text(encoding='utf-8',errors='replace');check(venue.player_result_phase(text)=='acknowledged','original player result / disconnect '+client['player']['id']);finals=[json.loads(line.split('VR_CLIENT_DEBRIEF_FINAL ',1)[1]) for line in text.splitlines() if 'VR_CLIENT_DEBRIEF_FINAL ' in line];check(len(finals)==1,'one original final result '+client['player']['id']);final=finals[0];entry=next(e for e in entries if e['sessionId']==client['sessionId']);debrief.validate_result(final,{'id':entry['sessionId']},client['player'],entry['sealed']);check(True,'original admission / exact final seals / stats '+client['player']['id']);save(client['player']['id']+'-result.json',final)
                if player_folder:
                    connections=re.findall(r'VR_CLIENT_CONNECTED id=(\d+)',text)
                    if client.get('reconnectIds'):
                        check(connections==client['reconnectIds'] and final['ammoUsed']==1,
                              entry['label']+' original tracked player seals one shot on its new connection')
                    elif len(connections)!=1:
                        raise RuntimeError('Player did not have one original native connection')
                    client['connection']=int(connections[-1])
                    client['final']=final
                else:
                    report_csv=request('/api/sessions/'+client['sessionId']+'/report.csv')
                    (out/(client['player']['id']+'.csv')).write_text(report_csv,encoding='utf-8')
                stop_player(client)
                if player_folder:
                    method = 'player launcher' if client.get('launcherReport') else 'native exercise fixture'
                    check(True,method+' confirmed original child exit '+client['player']['id'])
            if player_folder:
                evidence_entries = [verify_delivery(entry,[c for c in round_clients if c['sessionId']==entry['sessionId']])
                                    for entry in entries]
                if args.venue_field_evidence:
                    mode = 'Linked' if linked else 'Independent'
                    field_archive = verify_venue_field_evidence(mode, closed, evidence_entries)
                    if earlier_field_archive:
                        check(request(earlier_field_archive['route'], raw_response=True)[0] == Path(earlier_field_archive['zip']).read_bytes(),
                              'The original independent field bundle is byte-identical after the newer Linked batch')
                    if args.check_venue_field_ui:
                        verify_venue_field_ui(mode.lower(), field_archive, earlier_field_archive)
                    earlier_field_archive = field_archive
            if args.check_venue_reports:
                current_batch_report = verify_venue_reports(entries, receipt, linked)
                if archived_batch_report:
                    old_route, old_zip = archived_batch_report
                    check(request(old_route, raw_response=True)[0] == old_zip,
                          'The original independent ZIP is byte-identical after the newer Linked batch')
                archived_batch_report = current_batch_report
        if args.mr_venue_bundle_only: check_mr_venue_bundle()
        if args.mixed_venue_bundle_only: check_mixed_venue_bundle()
        if args.check_managed_mr:
            state=create([1],'managed-mr',experience='MR')
            session='/api/sessions/'+state['id']
            unpinned_file=runtime/'mr-unpinned.json';unpinned_log=runtime/'mr-unpinned.log'
            telemetry=runtime/'mr-unpinned-telemetry'
            unpinned_file.write_text(json.dumps(config(state['id'],telemetryOrigin='GameServer',telemetryDirectory=str(telemetry))),encoding='utf-8')
            child=subprocess.Popen([str(folder/'Runtime/VrCommand.exe'),'-batchmode','-nographics','-job-worker-count','2',
                '-logFile',str(unpinned_log),'--vr-config',str(unpinned_file)],cwd=runtime,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                wait(lambda: unpinned_log.exists() and 'MR REQUIRES PINNED ROOM ALIGNMENT FILES' in unpinned_log.read_text(encoding='utf-8',errors='replace'),30,'MR startup refuses missing pins')
                check('VR_NETWORK_STARTED' not in unpinned_log.read_text(encoding='utf-8',errors='replace')
                      and not telemetry.exists() and request(session)==state,'unpinned MR server does not start networking, attach, or write telemetry')
            finally:
                if child.poll() is None: child.terminate()
                child.wait(timeout=15)
            markers=[{'room':{'x':x,'z':z},'tracking':{'x':x,'z':z}} for x,z in [(-2,-2),(2,-2),(-2,2)]]
            alignment=request('/api/room-alignment',{'roomId':1,'markers':markers})
            alignment_file=out/'managed-mr-room-1-alignment.json';alignment_file.write_text(json.dumps(alignment)+'\n',encoding='utf-8')
            pin={'commandId':str(uuid.uuid4()),'action':'SetRoomAlignment','expectedSequence':state['sequence'],
                 'roomAlignment':{'room1':package.digest(alignment_file)}}
            pinned=request(session+'/commands',pin)
            check(pinned['session']['roomAlignment']['room1']==pin['roomAlignment']['room1']
                  and request(session+'/commands',pin)['duplicate'],'real control service pins the original checked room export before launch')
            mr=launch(pinned['session'],'managed-mr')
            check(read(mr['work']/'server-config.json')['telemetryOrigin']=='GameServer','actual launcher selects GameServer telemetry for MR')
            session='/api/sessions/'+mr['sessionId'];client=player(mr,1)
            server_log=mr['work']/'server.log'
            wait(lambda: 'VR_SERVER_ADMISSION_REJECTED' in server_log.read_text(encoding='utf-8',errors='replace'),30,'MR desktop admission rejection')
            check('VR_SERVER_ADMISSION_APPROVED' not in server_log.read_text(encoding='utf-8',errors='replace'),'ordinary desktop ticket was rejected by the original MR game server')
            stop_player(client)
            request(session+'/commands',{'commandId':str(uuid.uuid4()),'action':'Begin'},expected=409)
            check(request(session)['state']=='Preparing','MR Begin remains Preparing after the missing tracked roster rejection')
            receipt=request(session+'/commands',{'commandId':str(uuid.uuid4()),'action':'SetEnvironment',
                'environment':{'mode':'MR','weather':'Storm','timeOfDay':'Night','lightning':True}})
            def mr_weather():
                metadata=request(session+'/world')
                if metadata['acceptedSequence']==0:return None
                frame=request(session+'/world/frames/'+str(metadata['acceptedSequence']))['packet']
                if frame['observedSequence']>=receipt['session']['sequence']:
                    return metadata,frame
            metadata,frame=wait(mr_weather,20,'original MR environment applied')
            check(metadata['header']['origin']=='GameServer' and metadata['header']['calibration']=='quest-room-mr-v1'
                  and frame['weather']=='Storm' and frame['frame']['night'] and frame['lightning'] and frame['frame']['phase']=='Preparing'
                  and not any(p['connected'] for p in frame['frame']['players']),'real MR source records its profile and operator weather without a connected desktop')
            command(mr['sessionId'],'End');finish(mr)
        if args.check_live_reinforcement:
            props=[{'assetId':'sandbag','position':{'x':x,'y':0,'z':z},'yawDegrees':0} for z in (2,4) for x in (-3,-1,1,3)]
            entry=launch(create([1],'live-reinforcement',props=props),'live-reinforcement',verify_layout=False)
            session='/api/sessions/'+entry['sessionId']
            client=player(entry,1); roster=[client['player']['id']]
            wait(lambda: observe(entry,roster),60,'reinforcement original player')
            begun=command(entry['sessionId'],'Begin')
            original=wait(lambda: observe(entry,roster,begun['appliedAtSequence']),20,'reinforcement Running source')['packet']
            body={'commandId':str(uuid.uuid4()),'action':'SetEnemies','expectedSequence':begun['appliedAtSequence'],
                  'enemies':{'count':85,'behavior':'Hold','autoAttack':False}}
            denied=request(session+'/commands',body,expected=400)
            check(denied['code']=='enemy-capacity-exceeded' and denied['maxCount']==84
                  and request(session)['sequence']==begun['appliedAtSequence'],'Running reinforcement beyond the layout capacity is rejected before mutation')
            body['enemies']['count']=84
            added=request(session+'/commands',body)
            def applied(receipt,phase,count):
                meta=request(session+'/world')
                packet=request(session+'/world/frames/'+str(meta['acceptedSequence']))['packet']
                if (packet['observedSequence']>=receipt['appliedAtSequence'] and packet['frame']['phase']==phase
                        and len(packet['frame']['enemies'])==count):
                    return meta,packet
            metadata,reinforced=wait(lambda: applied(added,'Running',84),20,'original server spawns the accepted count')
            original_id=original['frame']['enemies'][0]['id']
            check(metadata['header']['reinforcementVersion']==1 and reinforced['frame']['enemies'][0]['id']==original_id
                  and all(enemy['roomId']==1 for enemy in reinforced['frame']['enemies']),'recorded native reinforcement preserves the existing enemy and room allocation')
            reduced=request(session+'/commands',{'commandId':str(uuid.uuid4()),'action':'SetEnemies',
                            'enemies':{'count':1,'behavior':'Hold','autoAttack':False}})
            paused=command(entry['sessionId'],'Pause')
            _,after=wait(lambda: applied(paused,'Paused',1),20,'reduced target and Pause apply together')
            check(after['observedSequence']>=reduced['appliedAtSequence'] and after['frame']['enemies'][0]['id']==original_id,
                  'operator can remove the new enemies and pause with the original enemy retained')
            save('live-reinforcement-controls.json',{'denied':denied,'added':added,'reinforced':reinforced,'reduced':reduced,'paused':paused,'after':after})
            command(entry['sessionId'],'End');finish(entry)
            replay=[value['packet'] for value in read(out/'live-reinforcement-replay.json')]
            timeline=f"{session}/world/policy-frames?throughFrame={replay[-1]['sequence']}"
            scoped=timeline+'&includeEnemyRoster=true&roomId=1'
            legacy=request(timeline)
            roster=request(scoped,role='Room1')
            expected_roster=[]
            previous_ids=None
            for packet in replay:
                enemies=packet['frame']['enemies']
                ids={enemy['id'] for enemy in enemies}
                if previous_ids is not None and ids!=previous_ids:
                    expected_roster.append((packet['sequence'],{'enemyIds':sorted(ids),'alive':sum(enemy['health']>0 for enemy in enemies),
                                                               'added':len(ids-previous_ids),'removed':len(previous_ids-ids)}))
                previous_ids=ids
            actual_roster=[(row['frameSequence'],row['enemyRoster']) for row in roster['frames'] if 'enemy-roster' in row['changes']]
            save('live-reinforcement-roster.json',roster)
            check(roster['nextAfterFrame'] is None and roster['roomId']==1 and roster['includeEnemyRoster']
                  and roster['scannedThroughFrame']==replay[-1]['sequence'] and actual_roster==expected_roster,
                  'saved enemy-roster timeline exactly matches every original membership change, including replacements')
            changes=[(sequence,row) for sequence,row in actual_roster if original['sequence']<sequence<=after['sequence']]
            check(sum(row['added'] for _,row in changes)==83 and sum(row['removed'] for _,row in changes)==83
                  and all(original_id in row['enemyIds'] for _,row in changes),
                  'the witnessed running command window adds and removes 83 enemies and retains the original enemy')
            legacy_sequences={row['frameSequence'] for row in legacy['frames']}
            first_change=next(sequence for sequence,row in changes if row['added']>0)
            suffix=request(scoped+f'&afterFrame={first_change-1}',role='Room1')
            check(first_change not in legacy_sequences and 'includeEnemyRoster' not in legacy
                  and all('enemyRoster' not in row for row in legacy['frames'])
                  and suffix['frames'][0]==next(row for row in roster['frames'] if row['frameSequence']==first_change),
                  'an unchanged strategy still indexes reinforcement using the actual predecessor across cursors')
            request(scoped,role='Room2',expected=403)
            text=client['log'].read_text(encoding='utf-8',errors='replace')
            check(venue.player_result_phase(text)=='acknowledged','reinforcement player confirms its sealed result')
            finals=[json.loads(line.split('VR_CLIENT_DEBRIEF_FINAL ',1)[1]) for line in text.splitlines() if 'VR_CLIENT_DEBRIEF_FINAL ' in line]
            check(len(finals)==1,'reinforcement player receives one original final result')
            debrief.validate_result(finals[0],{'id':entry['sessionId']},client['player'],entry['sealed'])
            save(client['player']['id']+'-result.json',finals[0])
            stop_player(client)
        if args.check_venue_endpoint_batch:
            reject_last_venue_endpoint()
        if args.check_venue_launch_review:
            review_lost_endpoint()
        if args.check_venue_ticket_freshness:
            verify_stale_ticket_source()
        # A killed launcher must close its already-assigned Job and stop the exact owned native handle.
        crash=launch(create([1],'parent-exit',auto_attack=args.check_interrupted_replay),'parent-exit',listen_address='0.0.0.0')
        if args.check_interrupted_replay:
            crash_client = player(crash, 1)
            roster = [crash_client['player']['id']]
            wait(lambda: observe(crash, roster), 60, 'interrupted round original player')
            begun = command(crash['sessionId'], 'Begin')['session']['sequence']
            def damaged():
                frame = observe(crash, roster, begun)
                return frame and any(row['damageTaken'] > 0 for row in frame['statistics'])
            wait(damaged, 20, 'original player damaged before the owned server exits')
            check(True, 'interrupted native round records original player damage before the crash')
        crash['process'].kill();crash['process'].wait(timeout=10);w=crash['witness'];check(w.kernel.WaitForSingleObject(w.handle,15000)==0,'parent death stops original job child');w.close();crash['witness']=None;check(not crash['reportPath'].exists(),'killed parent cannot publish success');command(crash['sessionId'],'End')
        if args.check_interrupted_replay:
            verify_interrupted_replay(crash, crash_client)
        check(all(x['state']=='Ended' for x in request('/api/sessions?includeEnded=true')),'no active management sessions')
        if args.check_room_endpoints:
            room_rows=request('/api/rooms/readiness')['rooms']
            check(len(room_rows) == 5 and all(row['sessionId'] is None and 'endpoint' not in row for row in room_rows),
                  'ended native sources leave no endpoint in the five current room rows')
        save('evidence.json',{'rounds':rounds,'scope':('One packaged graphical Unity mock OpenXR client and one desktop peer on the same host.' if args.openxr_mock_only else
            'One graphical Unity mock OpenXR client and 24 desktop peers in each same-host venue topology.' if args.check_venue_openxr else
            'Five Windows VR/MR Preparing endpoints and 25 signed files from the console mixed ZIP.' if args.mixed_venue_bundle_only else
            'Real Windows MR Preparing endpoints and 25 signed files per topology.' if args.mr_venue_bundle_only else
            f'Three portable packages, five Independent rooms then Linked, {venue_players} simultaneous same-PC Simulation clients per topology.'
            if player_folder else 'Two portable packages, five Independent rooms then Linked, five same-PC Simulation clients per topology.'),
            'managedMrPreparing':args.check_managed_mr,
            'roomCombat':args.check_room_combat,
            'roomParticipation':args.check_room_participation,
            'roomObserver':args.check_room_observer,
            'roomClocks':args.check_room_clocks,
            'venuePhase':args.check_venue_phase,
            'venueBegin':args.check_venue_begin,
            'venueEnd':args.check_venue_end,
            'venueReports':args.check_venue_reports,
            'venueReplayUi':args.check_venue_replay_ui,
            'venueReplayAlignment':args.check_venue_replay_alignment,
            'venueHistoryUi':args.check_venue_history_ui,
            'venueFieldEvidence':args.venue_field_evidence,
            **({'expectedPlayersPerRoom': players_per_room} if players_per_room != 5 else {}),
            'venueFieldUi':args.check_venue_field_ui,
            'lanPreflight':args.check_lan_preflight,
            'vrVenueTickets':args.check_vr_venue_tickets,
            'questVrDeploy':args.check_quest_vr_deploy,
            'questDeploymentRetry':args.check_quest_deployment_retry,
            'questTrackingWait':args.check_quest_tracking_wait,
            'questVrPartialMap':args.check_quest_vr_partial_map,
            'venueOpenxr':args.check_venue_openxr,
            'venuePoseReview':args.check_venue_pose_review,
            'venueOpenxrReconnect':args.check_venue_openxr_reconnect,
            'openxrReconnect':args.check_openxr_reconnect,
            'openxrRevocation':args.check_openxr_revocation,
            'venueEnvironment':args.check_venue_environment,
            'venueEnvironmentUi':args.check_venue_environment_ui,
            'venueEnemies':args.check_venue_enemies,
            'hardwareFeedback':args.check_hardware_feedback or openxr_hardware,
            'hardwareMockPackage':hardware_manifest['toolVersion'] if args.hardware_simulator_package else None,
            'preparedIndependentSet':args.prepare_independent_set,
            'independentRoomMissions':args.check_independent_room_missions,
            'importedMissionTemplate':imported_mission['id'] if imported_mission else None,
            'sourceFingerprint':manifest['build']['sourceFingerprint'],'gameAddress':address,
            **({'windowsReleaseManifestSha256':windows_release_hash} if windows_release_hash else {})})
    except BaseException as error:stage('failed',errorType=type(error).__name__);raise
    finally:
        for gate in reconnect_gates:
            try:gate.close()
            except Exception as e:cleanup.append({'kind':'openxr-reconnect-udp','errorType':type(e).__name__})
        if observer:
            try:
                if observer.poll() is None:observer_stop.write_text('stop owned observer',encoding='utf-8');observer.wait(timeout=20)
                observed=read(observer_out/'checks.json')
                if not observed['browserClosed']:raise RuntimeError('Observer browser cleanup unknown')
                if observer_log:observer_log.close();observer_log=None
            except Exception as e:cleanup.append({'kind':'observer','errorType':type(e).__name__})
        for client in clients:
            try:
                stop_player(client)
            except Exception as e:cleanup.append({'kind':'client','errorType':type(e).__name__})
        for entry in runners:
            try:
                if entry['process'].poll() is None:entry['process'].kill()
                entry['process'].wait(timeout=15)
                w=entry['witness']
                if w:
                    if w.kernel.WaitForSingleObject(w.handle,15000)!=0:raise RuntimeError('Native child still live')
                    w.close();entry['witness']=None
            except Exception as e:cleanup.append({'kind':entry['label'],'errorType':type(e).__name__})
        for process in hardware_processes:
            try:
                if process.poll() is None:process.terminate()
                process.wait(timeout=10)
            except Exception as e:cleanup.append({'kind':'hardware-mock','errorType':type(e).__name__})
        for gate in receipt_gates:
            try:gate.close()
            except Exception as e:cleanup.append({'kind':'venue-receipt-gate','errorType':type(e).__name__})
        try:
            if api and api.poll() is None:api_stop.write_text('stop own API',encoding='utf-8');api.wait(timeout=50)
            if api_witness:api_witness.wait();api_witness.close()
        except Exception as e:cleanup.append({'kind':'api','errorType':type(e).__name__})
        remaining={'errors':cleanup,'remainingRunners':[e['label'] for e in runners if e['process'].poll() is None],
                   'remainingClients':[c['player']['id'] for c in clients if c['process'].poll() is None],'apiRemaining':api is not None and api.poll() is None}
        if args.hardware_simulator_package:remaining['remainingHardware']=[process.pid for process in hardware_processes if process.poll() is None]
        if args.check_openxr_reconnect or args.check_venue_openxr_reconnect:
            remaining['remainingReconnectRelays']=sum(gate.thread.is_alive() for gate in reconnect_gates)
        if receipt_gates:remaining['remainingReceiptGates']=sum(gate.thread.is_alive() for gate in receipt_gates)
        save('cleanup.json',remaining)
        if cleanup:raise RuntimeError('Cleanup not confirmed; do not snapshot live runtime')
        venue.snapshot_runtime(runtime,out/'runtime-snapshot')
    for file in out.glob('*.json'):
        text=file.read_text(encoding='utf-8')
        if keys and any(k in text for k in keys.values()):raise RuntimeError('Public metadata contains a key')
        if venue_password and venue_password in text:raise RuntimeError('Public metadata contains the test certificate password')
    save('checks.json',{'complete':True,'checks':len(checks),'findings':checks,'runtimeDirectory':str(runtime),
        'packageDirectory':str(folder),'playerPackageDirectory':str(player_folder) if player_folder else None,
        'scope':('Same-machine tracked rig from Unity mock OpenXR and a simulated desktop peer, no physical headset.' if args.openxr_mock_only else
                 'Five Independent rooms then Linked, one Unity mock OpenXR rig and 24 desktop peers per topology, same host.' if args.check_venue_openxr else
                 'Same-machine VR/MR servers in Preparing and mock ADB with no headset client.' if args.mixed_venue_bundle_only else
                 'Same-machine native MR servers in Preparing with no headset client.' if args.mr_venue_bundle_only else
                 'Same-machine VR simulation and a separate MR Preparing admission and seal check.' if args.check_managed_mr else 'Same-machine Simulation only.')
                + (' Venue game processes use pinned HTTPS and WSS on the same Windows PC.' if venue_pin else '')
                +' The separate parent-death case intentionally leaves the world unsealed.'})
    print(json.dumps({'complete':True,'checks':len(checks),'directory':str(out)}))
if __name__=='__main__':main()
