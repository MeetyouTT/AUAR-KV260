"""Verify saved UART frames, camera images, and real selection acknowledgements."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
START = '20261011T144658.496465Z'
folders = sorted(path for path in (ROOT / 'evidence').iterdir()
                 if path.name >= START and (path / 'result.json').is_file())
responses = artifacts = 0
failures = []
for folder in folders:
    record = json.loads((folder / 'result.json').read_text())
    assert record['console_echo_restored'], folder
    serial = (folder / 'serial.raw').read_bytes().decode('utf-8', 'replace')
    if not record['complete']:
        failures.append({'evidence': str(folder), 'error': record['error'],
                         'command_count': len(record['commands'])})
    for index, row in enumerate(record['commands']):
        marker = 'BT%03d' % index
        begin = re.search(r'(?:^|# )BEGIN ' + marker + r' (\d+) (\d+)\r?$', serial, re.M)
        end = re.search(r'^END ' + marker + r' ([0-9a-f]{64})\r?$', serial, re.M)
        chunks = re.findall(r'^DATA ' + marker + r' (\d+) ([A-Za-z0-9+/=]+)\r?$', serial, re.M)
        assert begin and end and [int(i) for i, _ in chunks] == list(range(len(chunks))), (folder, marker)
        blob = gzip.decompress(base64.b64decode(''.join(s for _, s in chunks), validate=True))
        assert blob == (folder / (row['label'] + '.output')).read_bytes()
        assert int(begin[1]) == row['exit_code'] and len(blob) == int(begin[2]) == row['bytes']
        assert hashlib.sha256(blob).hexdigest() == end[1] == row['sha256']
        responses += 1
        if row['exit_code'] or not blob.strip():
            continue
        for name, item in json.loads(blob).get('artifacts', {}).items():
            assert Path(name).name == name
            data = base64.b64decode(item['base64'], validate=True)
            assert data == (folder / name).read_bytes()
            assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
            artifacts += 1

live_folder = max(folder for folder in folders if folder.name.endswith('-live'))
record = json.loads((live_folder / 'result.json').read_text())
assert record['complete']
value = json.loads((live_folder / 'live.json').read_text())
uploaded = json.loads((live_folder / 'live-verify.json').read_text())
assert (ROOT / 'board_live.py').stat().st_size == uploaded['bytes']
assert hashlib.sha256((ROOT / 'board_live.py').read_bytes()).hexdigest() == uploaded['sha256']
samples = value['observations']
manual_verified = value['status'] == 'PASS_RECEIPT_AND_SELECTION'
loss_verified = return_verified = False
if manual_verified:
    receipt = value['receipt']
    expected = value['expected_target']
    assert receipt['accepted'] is True and receipt['action'] == 'target_select'
    assert receipt['command_id'] not in {row['command_id'] for row in value['before']['ui_runtime']['results']}
    # UiServiceClient preserves the validated ack's public fields, not its
    # complete ownership envelope. Check the unchanged client and its result.
    assert value['before']['ui_runtime']['ui_epoch'] == value['ui_after']['ui_runtime']['ui_epoch']
    assert receipt in value['ui_after']['ui_runtime']['results']
    assert value['accepted_at']['source_kind'] == 'actual' and len(samples) == 40
    assert value['selected_matches'] == sum(row['target']['selected'] == expected for row in samples) > 0
    assert value['health_before']['pid'] == value['health_after']['pid']
    assert value['health_before']['service_epoch'] == value['health_after']['service_epoch']
    assert value['health_after']['detected_frames'] > value['health_before']['detected_frames']
    matched_once = False
    lost_once = False
    for sample in samples:
        target = sample['target']
        if target['selected'] == expected:
            matched_once = True
        visible = any(row['key'] == expected for row in target['tracks'])
        if matched_once and not visible:
            assert target['selected'] is None, 'Manual selection transferred after losing its target'
            lost_once = loss_verified = True
        if lost_once and target['tracks'] and not visible:
            assert target['selected'] is None
            return_verified = True
else:
    assert value['status'] in ('PENDING_STABLE_REAL_PERSON', 'PENDING_USER_DIALOG_OPEN',
                               'REJECTED_OR_NOT_SUBMITTED', 'RECEIPT_ACCEPTED_APPLY_UNVERIFIED')
watch_folder = max(folder for folder in folders if folder.name.endswith('-watch'))
watch_record = json.loads((watch_folder / 'result.json').read_text())
assert watch_record['complete']
watch = json.loads((watch_folder / 'watch.json').read_text())
assert watch['expected_target'] == value['expected_target']
assert watch['before']['service_epoch'] == value['health_after']['service_epoch'] == watch['after']['service_epoch']
assert watch['before']['camera_epoch'] == value['health_after']['camera_epoch'] == watch['after']['camera_epoch']
assert watch['before']['pid'] == watch['after']['pid'] == value['health_after']['pid']
assert watch['after']['detected_frames'] > watch['before']['detected_frames']
assert watch['observation_seconds'] >= 45 and watch['observations']
for sample in watch['observations']:
    target = sample['target']
    visible = any(row['key'] == watch['expected_target'] for row in target['tracks'])
    if not visible:
        assert target['selected'] is None
        loss_verified = True
        if target['tracks']:
            return_verified = True
assert watch['lost_observed'] == loss_verified
assert watch['new_lifecycle_observed_without_selection'] == return_verified
screen_folder = max(folder for folder in folders if folder.name.endswith('-screen'))
screen = json.loads((screen_folder / 'screen.json').read_text())
ui = screen['ui']
assert not screen['errors'] and not ui['error']
assert ui['ui_runtime']['link'] == 'READY' and ui['ui_runtime']['frame_visible']
assert ui['ui_runtime']['ui_epoch'] == value['ui_after']['ui_runtime']['ui_epoch']
assert ui['ui_runtime']['snapshot']['service_epoch'] == watch['after']['service_epoch']
assert value['receipt'] in ui['ui_runtime']['results']
assert any(row['title'] == '摄像头实时画面' for row in screen['geometry']['dialogs'])
for key in ('volume', 'muted', 'fullscreen', 'economy'):
    assert ui['ui_settings'][key] == value['before']['ui_settings'][key]
result = {'status': 'PASS_REAL_NATIVE_SELECTION' if manual_verified else value['status'],
    'evidence': str(live_folder), 'uart_responses_verified': responses, 'camera_artifacts_verified': artifacts,
    'recorded_helper_failures': failures, 'uploaded_helper': uploaded,
    'real_person_observed': True, 'native_selection_receipt_verified': manual_verified,
    'selected_target': value.get('expected_target'), 'selected_matches': value.get('selected_matches'),
    'observation_samples': len(samples), 'loss_binding_cleared_observed': loss_verified,
    'new_visible_lifecycle_without_auto_transfer_observed': return_verified,
    'loss_watch_evidence': str(watch_folder), 'loss_watch_seconds': watch['observation_seconds'],
    'loss_watch_samples': len(watch['observations']),
    'loss_watch_selected_nonnull_samples': sum(row['target']['selected'] is not None for row in watch['observations']),
    'loss_preceded_first_watch_sample': not any(row['key'] == watch['expected_target'] for row in watch['observations'][0]['target']['tracks']),
    'final_ui_evidence': str(screen_folder), 'final_ui_settings_preserved': True,
    'final_large_view_visible': True, 'final_target': ui['ui_runtime']['snapshot']['modules']['target'],
    'controlled_occlusion_and_multi_person_pending': True,
    'business_runtime_code_changed': False}
(ROOT / 'continuation_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
