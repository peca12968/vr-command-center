"""Package integrity boundaries with fake bytes, not native Unity/GUI evidence."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('test_server_package',ROOT/'scripts/package-windows-server.py');package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)
combat_spec=importlib.util.spec_from_file_location('server_package_combat',ROOT/'scripts/check-server-package.py')
combat=importlib.util.module_from_spec(combat_spec)
combat_spec.loader.exec_module(combat)
class ServerPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name).resolve()
        for name in ['Launch-Server.exe','Runtime/VrCommand.exe','Runtime/UnityPlayer.dll','Runtime/build-receipt.json']:
            f=self.folder/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b'fixture, not a built player')
        self.manifest={'schemaVersion':1,'target':'win-x64','files':[{'path':f.relative_to(self.folder).as_posix(),'bytes':f.stat().st_size,'sha256':package.digest(f)} for f in sorted(self.folder.rglob('*')) if f.is_file()]};self.save()
    def save(self):(self.folder/'server-package.json').write_text(json.dumps(self.manifest),encoding='utf-8')
    def test_changed_runtime_or_missing_file_is_rejected(self):
        package.verify(self.folder);file=self.folder/'Runtime/UnityPlayer.dll';file.write_bytes(b'changed')
        with self.assertRaises(ValueError):package.verify(self.folder)
        file.unlink()
        with self.assertRaises(FileNotFoundError):package.verify(self.folder)
    def test_extra_private_configuration_is_rejected(self):
        (self.folder/'server-config.json').write_text('{"gameServerKey":"fixture"}')
        with self.assertRaises(ValueError):package.verify(self.folder)
    def test_manifest_cannot_escape_or_use_windows_stream_alias(self):
        for name in ['../other','C:/other','/other','Runtime\\other','a//b','a/./b','name:stream']:
            self.manifest['files'][0]['path']=name;self.save()
            with self.subTest(name=name),self.assertRaises(ValueError):package.verify(self.folder)
    def test_case_duplicate_and_missing_required_launcher_reject(self):
        row=dict(self.manifest['files'][0]);self.manifest['files'].append(dict(row,path=row['path'].upper()));self.save()
        with self.assertRaises((ValueError,FileNotFoundError)):package.verify(self.folder)
        self.manifest['files']=[x for x in self.manifest['files'] if x['path'].lower()!='launch-server.exe'];(self.folder/'Launch-Server.exe').unlink();self.save()
        with self.assertRaises(ValueError):package.verify(self.folder)

class RoomCombatChecks(unittest.TestCase):
    def setUp(self):
        self.owners = {'original-player': 3}
        attack = {'tick': 12, 'enemyId': 'original-enemy', 'playerId': 'original-player'}
        self.events = [
            {**attack, 'sequence': 1, 'eventId': 'ray', 'kind': 'EnemyShot',
             'hasRay': True, 'hit': 'Friendly', 'targetId': 'original-player'},
            {**attack, 'sequence': 2, 'eventId': 'damage', 'kind': 'PlayerDamaged', 'damage': 20},
        ]
        self.statistics = [{'playerId': 'original-player', 'roomId': 3, 'hitsReceived': 1,
                            'damageTaken': 20, 'health': 80, 'ammoUsed': 0, 'shotsHit': 0,
                            'kills': 0, 'accuracyPercent': 0}]
        self.packet = {'observedSequence': 4, 'suspended': False, 'throughCombatSequence': 1,
                       'events': self.events,
                       'frame': {'phase': 'Running', 'autoAttack': True,
                                 'enemies': [{'id': 'original-enemy', 'roomId': 3}]}}

    def reconcile(self):
        return combat.reconcile_ai_damage([{'packet': self.packet, 'statistics': self.statistics}], self.owners, 4, 8)

    def test_exact_shot_and_damage_reconcile(self):
        self.assertEqual(self.reconcile(), {'damageEvents': 1, 'players': {
            'original-player': {'roomId': 3, 'hitsReceived': 1, 'damageTaken': 20}}})

    def test_cross_room_enemy_is_rejected(self):
        self.packet['frame']['enemies'][0]['roomId'] = 4
        with self.assertRaisesRegex(ValueError, 'original room'):
            self.reconcile()

    def test_duplicate_report_is_rejected_even_with_a_new_sequence(self):
        self.events[1]['eventId'] = self.events[0]['eventId']
        with self.assertRaisesRegex(ValueError, 'order'):
            self.reconcile()

    def test_damage_after_disable_is_rejected(self):
        self.packet['observedSequence'] = 8
        with self.assertRaisesRegex(ValueError, 'enabled window'):
            self.reconcile()

    def test_damage_and_health_must_match_the_same_snapshot(self):
        self.statistics[0]['health'] = 60
        with self.assertRaisesRegex(ValueError, 'event prefix'):
            self.reconcile()

    def test_result_requires_damage_on_every_original_player(self):
        self.owners['untouched-player'] = 3
        self.statistics.append({**self.statistics[0], 'playerId': 'untouched-player',
                                'hitsReceived': 0, 'damageTaken': 0, 'health': 100})
        with self.assertRaisesRegex(ValueError, 'damage for every original player'):
            self.reconcile()
if __name__=='__main__':unittest.main()
