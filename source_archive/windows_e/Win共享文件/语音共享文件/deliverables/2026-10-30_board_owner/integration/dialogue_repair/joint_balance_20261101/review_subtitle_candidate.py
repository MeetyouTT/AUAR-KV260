"""Independent local source review; no runtime imports or device access."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUB = HERE / 'subtitle_repair'
REL = 'tools/production_memory_presentation.py'
BEFORE = '984d3ca24067bf5129e9ce3b0054f32cced717b6b8824eab347476bef2f9e502'
AFTER = 'de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def functions(data):
    tree = ast.parse(data.decode('utf-8'))
    result = {}
    for item in tree.body:
        if isinstance(item, ast.FunctionDef):
            result[item.name] = ast.dump(item, include_attributes=False)
        elif isinstance(item, ast.ClassDef):
            for method in item.body:
                if isinstance(method, ast.FunctionDef):
                    result[item.name + '.' + method.name] = ast.dump(method, include_attributes=False)
    return result


before, after = [(SUB / part / REL).read_bytes() for part in ('before', 'after')]
assert digest(before) == BEFORE
assert digest(after) == AFTER
left, right = functions(before), functions(after)
assert set(left) == set(right)
changed = sorted(name for name in left if left[name] != right[name])
assert changed == ['PresentationLifecycle.__init__', 'PresentationLifecycle.channel',
                   'PresentationLifecycle.invalidate', 'bind_presentation']
unchanged_hot_paths = ['_clean', 'PresentationLifecycle._projection',
    'PresentationLifecycle.project', 'PresentationLifecycle._purge_public_copies',
    'PresentationLifecycle.repaint', 'attach_presentation', 'project_presentation',
    'save_production_evidence']
assert all(left[name] == right[name] for name in unchanged_hot_paths)

pins = json.loads((SUB / 'SOURCE_PINS.json').read_text(encoding='utf-8'))
manifest_data = Path(pins['current_manifest_source']).read_bytes()
assert digest(manifest_data) == pins['current_manifest_sha256']
manifest = json.loads(manifest_data)
assert len(manifest['component_pins']) == 380
assert manifest['component_pins'][REL] == BEFORE
for component, pin in pins['files'].items():
    data = Path(pin['source']).read_bytes()
    assert digest(data) == pin['sha256'] == manifest['component_pins'][component]
    assert len(data) == pin['bytes']

tests = json.loads((SUB / 'TEST_RESULT.json').read_text(encoding='utf-8'))
assert tests['passed'] and tests['tests'] == 18
assert tests['before_sha256'] == BEFORE and tests['after_sha256'] == AFTER
proof = dict(schema='aura-root-local-subtitle-source-review-1',
    decision='ACCEPT_FROZEN_SINGLE_SOURCE_FOR_OPERATOR_ARM_CHECK_AND_PUBLICATION',
    before_sha256=BEFORE, after_sha256=AFTER,
    base_manifest_sha256=digest(manifest_data), base_component_count=380,
    pinned_support_sources_verified=len(pins['files']),
    changed_functions=changed, unchanged_hot_paths=unchanged_hot_paths,
    public_regressions=tests['tests'], public_test_result_sha256=digest((SUB/'TEST_RESULT.json').read_bytes()),
    manual_review=['Submit retains jobs.condition RLock across original call and permit registration.',
      'Only matching current waiting owner receives one owner/epoch permit after exactly one invalidation.',
      'Concurrent additional invalidation prevents permit; later invalidation clears it.',
      'Channel still derives hard deadline from original requested_at, never receipt time.',
      'Original submit exceptions and returned object propagate; public metadata projection is unchanged.'],
    scope='Current pinned concrete 380-component production; not arbitrary replacement jobs implementations.',
    device_model_private_data_access=False, arm_tests_or_live_subtitles_accepted_here=False)
(HERE / 'ROOT_SUBTITLE_REVIEW.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(proof, ensure_ascii=False))
