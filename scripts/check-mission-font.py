"""Check immutable unmodified mission-fonts-v1 source / license and real font cmap."""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / 'clients/unity/Assets/VrCommand/Resources/VrCommand/Fonts'
PINS = {'NotoSansCJKtc-Regular.otf': 'dce08bd4fd91aa8aa76ed8fea4b694c2dfb8550f67871e326843212ddbeb88b4',
        'OFL.txt': '6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2',
        'NOTICE.txt': 'de1fa4eb60645113c1f9af1021464af35f166badc951af18b6d6dad0dff8ab43'}
source = json.loads((FONT / 'font-source-v1.json').read_text())
assert source['profile'] == 'mission-fonts-v1' and source['commit'] == 'f8d157532fbfaeda587e826d4cd5b21a49186f7c' and source['files'] == PINS
for name, expected in PINS.items():
    assert hashlib.sha256((FONT / name).read_bytes()).hexdigest() == expected, name
data = (FONT / 'NotoSansCJKtc-Regular.otf').read_bytes(); assert data[:4] == b'OTTO'
count = struct.unpack_from('>H', data, 4)[0]
offset = next(struct.unpack_from('>4sIII', data, 12 + index * 16)[2] for index in range(count) if data[12 + index * 16:16 + index * 16] == b'cmap')
tables = struct.unpack_from('>H', data, offset + 2)[0]
coverage = []
for index in range(tables):
    platform, encoding, relative = struct.unpack_from('>HHI', data, offset + 4 + index * 8)
    start = offset + relative
    if platform in (0, 3) and struct.unpack_from('>H', data, start)[0] == 12:
        groups = struct.unpack_from('>I', data, start + 12)[0]
        coverage.extend(struct.unpack_from('>III', data, start + 16 + group * 12) for group in range(groups))
for value in 'ABC任務防線救援戰術':
    assert any(first <= ord(value) <= last and glyph + ord(value) - first > 0 for first, last, glyph in coverage), value
print('PASS: immutable upstream font / OFL / notice pins; actual Latin and Traditional Chinese glyph mappings')
