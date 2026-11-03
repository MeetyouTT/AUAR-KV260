"""Root's local-only review; never import or execute the live diagnostic."""
import ast
import argparse
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE/'memory_probe'
PROJECT = HERE.parents[5]
SPEC = PROJECT/'deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101/package/subtitle_receipt/candidate_spec.json'
EXPECTED = 'cbe23506be5c5a5864814537f8cb0770592803437358d31a8e3a9e072052ae6c'
parser = argparse.ArgumentParser()
parser.add_argument('--seed-hash', default='3611d05a68d1dfc5597b49fad8707f68d264c02c9e3ce1cccfb73c6d09c74736')
args = parser.parse_args()
SEED = args.seed_hash
assert re.fullmatch('[0-9a-f]{64}', SEED)
raw = (PROBE/'read_target_memory_metadata.py').read_bytes()
assert hashlib.sha256(raw).hexdigest() == EXPECTED
tree = ast.parse(raw.decode('utf-8'), feature_version=(3, 9))
values = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in ('SOURCE_PINS', 'EXPECTED_STARTUP', 'APPLICATION_ID'):
            values[node.targets[0].id] = ast.literal_eval(node.value)
spec_raw = SPEC.read_bytes()
assert hashlib.sha256(spec_raw).hexdigest() == '62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177'
spec = json.loads(spec_raw)
assert values['EXPECTED_STARTUP'] == spec['startup_sha256']
assert values['APPLICATION_ID'] == 1096110658
assert all(spec['component_sha256'][key] == val for key, val in values['SOURCE_PINS'].items())
frozen_raw = (PROBE/'FROZEN_HANDOFF_R2.json').read_bytes()
frozen = json.loads(frozen_raw)
for name, pin in frozen['files'].items():
    data = (PROBE/name).read_bytes()
    assert len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['sha256'], name
assert frozen['tests']['tests']==6 and frozen['tests']['passed'] is True
# SELECT expressions are all literal SQL, with every row value supplied by bindings.
sql = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value,str) and n.value.lstrip().upper().startswith('SELECT ')]
for statement in sql:
    assert not re.search(r'\b(text|summary|metadata|value|name)\b', statement, re.I), statement
assert "AND s.summary_id=?" in raw.decode('utf-8')
review = dict(schema='aura-root-target-memory-diagnostic-review-1',
    decision='APPROVED_FOR_EXISTING_DEVICE_OWNER_READ_ONLY_THIS_PUBLIC_TEST',
    probe_sha256=EXPECTED, bytes=len(raw), source_pin_count=len(values['SOURCE_PINS']),
    frozen_handoff_sha256=hashlib.sha256(frozen_raw).hexdigest(), public_tests_passed=6,
    seed_request_hash=SEED, invalid_seed_excluded='57ec56d22463b0d1dfdf35fb4099e55c5f5d351333db9ad56f2d4280cf40d730',
    checks=['Fixed runtime/files and current source pins; two explicit request hashes at most.',
      'Read-only/query-only SQLite with bounded VM time and recent 64 metadata rows only.',
      'Saved conversation scope must match; optional answer scope mismatch rejects event inspection.',
      'No text, summary payload, event metadata, fact value or raw identifiers exported.',
      'Direct compacted summary pointer must match a valid same-revision summary and committed task.',
      'Dependency evidence is conservative association, not proof of final prompt inclusion.'],
    first_allowed_action='One baseline after the valid seed complete ACK and paused microphone.',
    production_change_or_device_access_by_reviewer=False)
output = HERE/('ROOT_MEMORY_PROBE_REVIEW_'+SEED[:16]+'.json')
output.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(review,ensure_ascii=False))
