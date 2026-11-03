"""Independently verify this continuation's UART records and camera artifacts."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
folder = Path(sys.argv[1]).resolve()
assert folder.parent == ROOT / 'evidence'
record = json.loads((folder / 'result.json').read_text())
assert record['complete'] and record['phase'] == 'target' and record['console_echo_restored']
serial = (folder / 'serial.raw').read_bytes().decode('utf-8', 'replace')
responses = []
for index, row in enumerate(record['commands']):
    marker = 'BT%03d' % index
    # Raw UART concatenates each prompt with the following BEGIN line.
    begin = re.search(r'(?:^|# )BEGIN ' + marker + r' (\d+) (\d+)\r?$', serial, re.M)
    end = re.search(r'^END ' + marker + r' ([0-9a-f]{64})\r?$', serial, re.M)
    chunks = re.findall(r'^DATA ' + marker + r' (\d+) ([A-Za-z0-9+/=]+)\r?$', serial, re.M)
    assert begin and end and [int(i) for i, _ in chunks] == list(range(len(chunks))), marker
    raw = gzip.decompress(base64.b64decode(''.join(s for _, s in chunks), validate=True))
    assert raw == (folder / (row['label'] + '.output')).read_bytes()
    assert int(begin[1]) == row['exit_code'] == 0
    assert len(raw) == int(begin[2]) == row['bytes']
    assert hashlib.sha256(raw).hexdigest() == end[1] == row['sha256']
    responses.append({'label': row['label'], 'bytes': len(raw), 'sha256': row['sha256']})
uploaded = json.loads((folder / 'target-verify.output').read_text())
helper = ROOT / 'board_target.py'
assert helper.stat().st_size == uploaded['bytes']
assert hashlib.sha256(helper.read_bytes()).hexdigest() == uploaded['sha256']
value = json.loads((folder / 'target.output').read_text())
artifacts = {}
for name, artifact in value['artifacts'].items():
    assert Path(name).name == name
    data = base64.b64decode(artifact['base64'], validate=True)
    assert data == (folder / name).read_bytes()
    assert len(data) == artifact['bytes'] and hashlib.sha256(data).hexdigest() == artifact['sha256']
    artifacts[name] = {key: artifact[key] for key in ('bytes', 'sha256')}
before, after = value['before'], value['after']
assert before['pid'] == after['pid'] and before['service_epoch'] == after['service_epoch']
assert before['camera_epoch'] == after['camera_epoch']
assert after['capture_frames'] > before['capture_frames']
assert after['detected_frames'] > before['detected_frames']
assert value['settings_preserved']
samples = value['observations']
assert samples and all(samples[i]['sequence'] <= samples[i + 1]['sequence'] for i in range(len(samples) - 1))
manual_verified = False
if value['status'] == 'PASS':
    native = value['native']
    assert value['positive_observed'] and native['positive_observed'] and native['native_target_chooser']
    assert native['selected_snapshot']['source_kind'] == 'actual'
    selected = native['selected_snapshot']['modules']['target']['selected']
    assert selected and any(track['key'] == selected for track in native['selected_snapshot']['modules']['target']['tracks'])
    assert native['selection_matches_samples'] == sum(row['selected'] == selected for row in native['observations'])
    assert 'real-track.jpg' in artifacts
    manual_verified = any(row.get('action') == 'target_select' and row.get('accepted') is True
                          for row in value['ui_after']['ui_runtime']['results'])
else:
    assert value['status'] in ('PENDING_REAL_PERSON', 'PENDING_PERSON_LEFT_BEFORE_SELECTION', 'NATIVE_SELECTION_FAILED')
report = {'status': 'PASS_REAL_TARGET_SELECTION' if manual_verified else
                  'PASS_EVIDENCE_MANUAL_SELECTION_UNVERIFIED' if value['status'] == 'PASS' else value['status'],
    'helper_reported_status': value['status'],
    'evidence': str(folder), 'response_count': len(responses), 'responses': responses,
    'helper': uploaded, 'artifacts': artifacts, 'camera_pid_preserved': after['pid'],
    'settings_preserved': value['settings_preserved'], 'positive_observed': value['positive_observed'],
    'observation_seconds': value['observation_seconds'], 'sample_count': len(samples),
    'detected_frames_delta': after['detected_frames'] - before['detected_frames'],
    'capture_frames_delta': after['capture_frames'] - before['capture_frames'],
    'native_target_selection_verified': manual_verified}
(folder / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False))
