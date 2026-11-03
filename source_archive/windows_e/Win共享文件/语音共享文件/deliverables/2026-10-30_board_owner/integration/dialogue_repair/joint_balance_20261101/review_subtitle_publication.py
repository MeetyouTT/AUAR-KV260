"""Local frozen-package review only. Never import or execute the publisher."""
import base64
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
JP = PROJECT / 'deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101'
BUNDLE = JP / 'package/subtitle_receipt'
PREVIOUS = JP / 'package/single_projection'
SOURCE = 'tools/production_memory_presentation.py'
BEFORE = '984d3ca24067bf5129e9ce3b0054f32cced717b6b8824eab347476bef2f9e502'
AFTER = 'de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2'
ROOT = '/home/root/aura-board-business-20261030/production-5259eab11e42af13'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raw(name):
    return (BUNDLE / name).read_bytes()


def read(name):
    return json.loads(raw(name))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


manifest_raw = raw('BUNDLE_MANIFEST.json')
bundle_manifest = json.loads(manifest_raw)
previous_manifest_data = (PREVIOUS/'BUNDLE_MANIFEST.json').read_bytes()
assert sha(previous_manifest_data) == '7da0fb13cd0694270ad2c34989f54a65ad9cb529ec7f7be5a6fa000d101af8d7'
for name, expected in json.loads(previous_manifest_data)['files'].items():
    assert sha((PREVIOUS/name).read_bytes()) == expected, name
for name, expected in bundle_manifest['files'].items():
    assert sha(raw(name)) == expected, name
assert sha(raw('base_spec.json')) == '05e9035981fc2771010d92dd046b0af041a9c618e6c0260626aa34380b420d4d'
assert sha(raw('base_startup.json')) == '71c28c2d4a15585a0370790c9be62ab5c1d975d0ac70626613429d355e83bb87'
assert sha(raw('base_manifest.json')) == 'e35ec0e32bb5b4d5c17ce11396753bcb36ad13eb651c9d1c3f57d1d745786020'
assert sha(raw('rollback/production_memory_presentation.py')) == BEFORE
assert sha(raw('payload/production_memory_presentation.py')) == AFTER
assert raw('payload/production_memory_presentation.py') == (HERE/'subtitle_repair/after'/SOURCE).read_bytes()
old, new = read('base_spec.json'), read('candidate_spec.json')
old_start, new_start = read('base_startup.json'), read('candidate_startup.json')
old_manifest, new_manifest = read('base_manifest.json'), read('candidate_manifest.json')
assert len(old['component_sha256']) == len(new['component_sha256']) == 380
assert set(old['component_sha256']) == set(new['component_sha256'])
assert [name for name in old['component_sha256'] if old['component_sha256'][name] != new['component_sha256'][name]] == [SOURCE]
expected_start = copy.deepcopy(old_start)
expected_start['component_sha256'][SOURCE] = AFTER
assert new_start == expected_start
revision = new_manifest['subtitle_submit_receipt']
assert revision['before_sha256'] == BEFORE and revision['after_sha256'] == AFTER
assert revision['parent_spec_sha256'] == sha(raw('base_spec.json'))
assert revision['parent_startup_sha256'] == sha(raw('base_startup.json'))
assert revision['parent_manifest_sha256'] == sha(raw('base_manifest.json'))
expected_manifest = copy.deepcopy(old_manifest)
expected_manifest['component_pins'][SOURCE] = AFTER
expected_manifest['files']['runtime/aura/'+SOURCE] = dict(bytes=len(raw('payload/production_memory_presentation.py')), sha256=AFTER)
expected_manifest['files']['startup/config.json'] = dict(bytes=len(raw('candidate_startup.json')), sha256=sha(raw('candidate_startup.json')))
expected_manifest['subtitle_submit_receipt'] = revision
assert new_manifest == expected_manifest
expected_spec = copy.deepcopy(old)
expected_spec['component_sha256'][SOURCE] = AFTER
expected_spec['release_sources'][SOURCE] = AFTER
expected_spec.update(startup_sha256=sha(raw('candidate_startup.json')),
    source_manifest_sha256=sha(raw('candidate_manifest.json')),
    subtitle_submit_receipt=dict(revision, state='APPLIED'))
assert new == expected_spec
assert encoded(old) == raw('base_spec.json') and encoded(new) == raw('candidate_spec.json')
for name in ('gui.json', 'publisher_definitions.py', 'camera_binding_runtime.py', 'single_projection_overlay.py'):
    assert raw(name) == (PREVIOUS/name).read_bytes(), name

targets = {
    'production_memory_presentation.py': (ROOT+'/runtime/aura/'+SOURCE, raw('rollback/production_memory_presentation.py'), raw('payload/production_memory_presentation.py')),
    'production-source-manifest.json': (ROOT+'/production_source_manifest.json', raw('base_manifest.json'), raw('candidate_manifest.json')),
    'startup-config.json': (ROOT+'/startup/config.json', raw('base_startup.json'), raw('candidate_startup.json')),
}
parent_transactions = json.loads((PREVIOUS/'forward_plan.json').read_bytes())['parent_transactions']
for direction in ('forward', 'rollback'):
    plan = read(direction+'_plan.json')
    assert set(plan['targets']) == set(targets)
    assert plan['allow_known_mixed_on_first_apply'] is (direction == 'rollback')
    assert plan['changed_source'] == SOURCE
    for name, (path, old_data, new_data) in targets.items():
        before, after = (old_data, new_data) if direction == 'forward' else (new_data, old_data)
        row = plan['targets'][name]
        assert row['path'] == path
        assert row['old_sha256'] == sha(before) and row['new_sha256'] == sha(after)
        assert base64.b64decode(row['new_base64'], validate=True) == after
    assert sha(encoded(plan['transaction'])) == plan['transaction_sha256']
    for key, value in parent_transactions.items():
        assert plan['parent_transactions'][key] == value
    assert plan['parent_transactions']['single_metadata_projection']['spec_sha256'] == sha(raw('base_spec.json'))

previous_runner = (JP/'tools/publish_single_projection.py').read_text(encoding='utf-8')
expected_runner = previous_runner.replace("root=HERE/'package/single_projection'", "root=HERE/'package/subtitle_receipt'", 1)
expected_runner = expected_runner.replace("review['candidate_source_sha256']=='"+BEFORE+"'", "review['candidate_source_sha256']=='"+AFTER+"'", 1)
expected_runner = expected_runner.replace("('single_projection_'+a.direction", "('subtitle_receipt_'+a.direction", 1)
actual_runner = (JP/'tools/publish_subtitle_receipt.py').read_text(encoding='utf-8')
assert actual_runner == expected_runner
preparation = read('PREPARATION.json')
arm_data = Path(preparation['arm_evidence']).read_bytes()
assert sha(arm_data) == preparation['arm_evidence_sha256'] == revision['arm_evidence_sha256']
arm = json.loads(arm_data)
assert arm['result']['status'] == 'PASSED' and arm['result']['candidate_sha256'] == AFTER
review = dict(schema='aura-root-frozen-subtitle-publication-review-1',
    status='APPROVED_FOR_SERIAL_OPERATOR', bundle_manifest_sha256=sha(manifest_raw),
    candidate_source_sha256=AFTER, unchanged_components=379,
    new_spec_sha256=sha(raw('candidate_spec.json')), new_startup_sha256=sha(raw('candidate_startup.json')),
    new_manifest_sha256=sha(raw('candidate_manifest.json')),
    arm_evidence_sha256=sha(arm_data), source_review=str(HERE/'ROOT_SUBTITLE_REVIEW.json'),
    checks=['All frozen file hashes verified.', 'Exactly one source changes within the same 380-component closure.',
      'Complete config, camera binding, original controller, models, memory and presentation hot paths retained.',
      'Forward and known-byte rollback contain exactly source, startup and manifest targets.',
      'Ancestor transactions preserved; publisher differs by exactly three scoped substitutions.',
      'Public ARM receipt passed before publication; no device operation performed by reviewer.'],
    device_access=False, live_caption_acceptance=False)
(HERE/'SERIAL_SUBTITLE_OPERATOR_REVIEW.json').write_text(json.dumps(review, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(review, ensure_ascii=False))
