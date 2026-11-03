"""Verify the source-only delta and compose its v19 publication manifest."""
import ast
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
IDENTITY = REPAIR / 'feature_trigger_collaboration/identity_cooperation_v90'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def method_span(source, cls, name):
    tree = ast.parse(source)
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == cls)
    method = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == name)
    lines = source.splitlines(True)
    return ''.join(lines[:method.lineno-1]), ''.join(lines[method.lineno-1:method.end_lineno]), ''.join(lines[method.end_lineno:])


manifest = json.loads((HERE/'SOURCE_MANIFEST.json').read_bytes())
reverse = {}
for relative, entry in manifest['files'].items():
    before = (HERE/'before'/relative).read_bytes()
    after = (HERE/'after'/relative).read_bytes()
    assert hashlib.sha256(before).hexdigest() == entry['before_sha256']
    assert hashlib.sha256(after).hexdigest() == entry['sha256']
    assert sha(Path(entry['before_path'])) == entry['before_sha256']
    text = after.decode('utf-8')
    old = before.decode('utf-8')
    if relative.endswith('/board_business.py'):
        prefix, _, suffix = method_span(text, 'BoardBusinessRuntime', '_submit_speaker_analysis')
        _, method, _ = method_span(old, 'BoardBusinessRuntime', '_submit_speaker_analysis')
        restored = (prefix + method + suffix).replace(
            'from common.board_memory import BoardMemoryStore, BoardMemoryWorker, MemoryBusy',
            'from common.board_memory import BoardMemoryStore, BoardMemoryWorker')
    elif relative.endswith('/board_speaker_business.py'):
        restored = text.replace(
            "'RuntimeError','OSError','ClockUnavailable','MemoryBusy','ScopeDenied',\n"
            "                        'IdempotencyConflict') else",
            "'RuntimeError','OSError','ClockUnavailable') else")
    else:
        prefix, _, suffix = method_span(text, 'BoardMemoryStore', 'append_event')
        _, method, _ = method_span(old, 'BoardMemoryStore', 'append_event')
        restored = prefix + method + suffix
    assert restored.encode('utf-8') == before, relative
    compile(text, str(HERE/'after'/relative), 'exec')
    reverse[relative] = dict(before_sha256=entry['before_sha256'], after_sha256=entry['sha256'],
        reverse_sha256=hashlib.sha256(restored.encode('utf-8')).hexdigest(), byte_exact_reverse=True,
        upstream_frozen_source_matches=True)
write('REVERSIBLE_SOURCE_PROOF.json', dict(schema='aura.reversible-source-delta.v1', files=reverse,
    production_source_files=3, original_frozen_packages_modified=False))

v19_path = REPAIR/'release_v19_stability_candidate/stability_evidence/source_mapping.json'
assert sha(v19_path) == 'ef8db220fde3b70a62ff1ff7cf2e9471a199a6d43b9234a18f8701eff58448f7'
v19 = json.loads(v19_path.read_bytes())
assert v19['startup_sha256'] == 'de7772b898378d2263b0809d18c095a60585a672690371d2f072b2e04c2f574f'
assert len(v19['component_pins']) == 379
five_path = IDENTITY/'COMBINED_M03_SOURCE_MANIFEST.json'
assert sha(five_path) == '52894828fed23021f90ef7434f8143831d483ba655b5d11c9881638b9fce9c6d'
five = json.loads(five_path.read_bytes())
files = {}
for relative in sorted(set(five['files']) | set(manifest['files'])):
    if relative in manifest['files']:
        entry = manifest['files'][relative]
        source = HERE/'after'/relative
    else:
        entry = five['files'][relative]
        source = Path(entry['source'])
    assert sha(source) == entry['sha256']
    files[relative] = dict(source=str(source), before_sha256=v19['component_pins'].get(relative),
        sha256=entry['sha256'], bytes=source.stat().st_size)
    if relative in manifest['files']:
        files[relative]['reviewed_delta_before_sha256'] = manifest['files'][relative]['before_sha256']
assert len(files) == 6
target_pins = dict(v19['component_pins'])
target_pins.update({path: row['sha256'] for path, row in files.items()})
assert len(target_pins) == 380
write('COMBINED_SIX_SOURCE_MANIFEST.json', dict(
    schema='aura.v19-m03-identity-evidence.composed-source.v1', status='LOCAL_REVIEW_ONLY_NOT_DEPLOYED',
    baseline_mapping_path=str(v19_path), baseline_mapping_sha256=sha(v19_path),
    baseline_startup_sha256=v19['startup_sha256'], baseline_boot_id=v19['boot_id'],
    baseline_component_count=379, expected_component_count=380, files=files,
    preserved_v19_pins={name:v19['component_pins'][name]
        for name in ('tools/board_recording.py', 'tools/board_avatar_gtk.py')}))

report_path = HERE/'PUBLIC_REGRESSION_04_v19.xml'
report = ET.fromstring(report_path.read_bytes()).find('testsuite')
assert int(report.attrib['tests']) == 184
assert int(report.attrib['failures']) == int(report.attrib['errors']) == 0
artifacts = {name:sha(HERE/name) for name in (
    'SOURCE_MANIFEST.json', 'CANDIDATE.diff', 'REVERSIBLE_SOURCE_PROOF.json',
    'COMBINED_SIX_SOURCE_MANIFEST.json', 'PUBLIC_REGRESSION_04_v19.xml',
    'test_public_replay.py', 'test_factory_composition.py', 'run_regressions.py', 'build_candidate.py')}
write('HANDOFF.json', dict(schema='aura.speaker-evidence-retry.handoff.v2',
    status='FROZEN_FOR_ROOT_INDEPENDENT_REVIEW', deployed=False,
    incremental_sources=3, composed_sources=6, expected_component_count=380,
    source_files=manifest['files'], artifacts=artifacts,
    public_regression=dict(tests=184, failures=0, errors=0,
        seconds=float(report.attrib['time']), base='v19 exact GTK/recording overlay on 343 verified public Python/config files'),
    confirmed_public_defects=[
        'single_transient_sqlite_busy_loses_speaker_timeline_evidence',
        'sqlite_lock_wait_can_outlive_callback_owner_cancel_or_deadline'],
    production_historical_error_causes='unknown; counters 6/104/103 cannot establish a common cause',
    visual_change_required=False,
    retry=dict(total_attempts=3, waits_seconds=[.025,.05], only='MemoryBusy',
        same_event_id_occurrence_time_and_payload=True, existing_speaker_worker=True),
    guard=dict(optional_keyword='guard', caller_contract='pure callable which raises on invalidation',
        checks=['before_each_attempt','after_BEGIN_IMMEDIATE','after_insert_before_commit'],
        cancellation_exit='existing StaleGeneration; original transaction rollback'),
    excluded_legacy_test='test_board_mode_cannot_bypass_board_kernel_lock_on_windows; previously documented baseline failure',
    collection_gap=dict(artifact='PUBLIC_REGRESSION_02.xml',
        modules=['test_board_memory_review.py','test_board_memory_completion.py'],
        missing_runtime_dependency='common.timeline_conversations',
        unmapped_runtime_fallback_used=False),
    live_device_or_model_or_private_database_access=False))
print(json.dumps(dict(status='SEALED', manifest_sha256=sha(HERE/'SOURCE_MANIFEST.json'),
    combined_manifest_sha256=sha(HERE/'COMBINED_SIX_SOURCE_MANIFEST.json'),
    handoff_sha256=sha(HERE/'HANDOFF.json'), files={p:r['sha256'] for p,r in manifest['files'].items()})))
