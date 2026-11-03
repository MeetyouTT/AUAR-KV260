"""Build a small local JPEG A/B/A trial package from already saved evidence."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
INTEGRATION = REPAIR.parent
SNAPSHOT = REPAIR / 'progress_followup_20261031/v21_camera_metadata_1793506766766332400.json'
SNAPSHOT_SHA = '3ccef2829ef9fbbece73c7408855ab2a461c9eaa78692cd19a23676c0ef13964'
EXECUTOR = INTEGRATION / 'resume_camera_budget/serial_trial.py'
EXECUTOR_SHA = '1e8aeee2a94b4fce674f2468ce48c77fbb88ef99bd9cb1ab66dd3bf20a0327f6'
READBACK_HELPER = INTEGRATION / 'resume_camera_pin/rebuild_same_boot_readback.py'
FROZEN_CAMERA = REPAIR / 'jpeg_demand_actual_camera_candidate_v20/after/board/vision/ui_camera_service.py'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def load(path):
    return json.loads(path.read_bytes())


def exact_file(path, raw):
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('Existing package artifact differs')
        return
    with path.open('xb') as stream:
        stream.write(raw)


def make():
    raw = SNAPSHOT.read_bytes()
    if sha(raw) != SNAPSHOT_SHA or sha(EXECUTOR.read_bytes()) != EXECUTOR_SHA:
        raise ValueError('Saved camera evidence or reviewed executor changed')
    snapshot = json.loads(raw)['result']
    spec = importlib.util.spec_from_file_location('jpeg_entry_builder', HERE / 'candidate/entry.py')
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    if sha(FROZEN_CAMERA.read_bytes()) != entry.CAMERA_AFTER:
        raise ValueError('Frozen JPEG source changed')
    readback = snapshot['readback']
    if (readback['board_boot_id'] != 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
            or readback['camera_pid'] != 1335 or readback['camera_start_ticks'] != '2344'
            or snapshot['owners'] != snapshot['final_owners']
            or snapshot['private_database_read'] is not False
            or snapshot['production_modified'] is not False):
        raise ValueError('Exact stable saved owner evidence required')
    pins = {}

    def add(name, value):
        if name in pins and pins[name] != value:
            raise ValueError('Inherited pin conflict')
        pins[name] = value

    historical = load(INTEGRATION / 'resume_camera_budget/candidate/candidate-manifest.json')
    for name, value in historical['inherited_pins'].items():
        add(name, value)
    for name, value in readback['source_sha256'].items():
        add(name, value)
    for name, row in snapshot['metadata'].items():
        add(name, row['sha256'])
        fields = row['fields']
        for group in ('pins', 'files'):
            for child, value in fields.get(group, {}).items():
                add(child, value)
        for child, value in fields.get('source_pins', {}).items():
            path = PurePosixPath(child)
            add(str(path if path.is_absolute() else PurePosixPath(entry.OPS) / path), value)
    chain = load(REPAIR / 'jpeg_demand_actual_camera_candidate_v20/CALL_CHAIN_REVIEW.json')
    for row in chain['readback_sources']:
        add(row['path'], row['sha256'])
    parent = REPAIR / 'jpeg_demand_review_v20/actual_camera_source_9d714/3_native_entry_pan_face_v5.py'
    for node in ast.parse(parent.read_bytes()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            group = node.targets[0].id
            if group in ('APP_PINS', 'SHADOW_PINS'):
                prefix = entry.SOURCE_ROOT if group == 'APP_PINS' else entry.OPS + '/pan-face-edge-v5'
                for name, value in ast.literal_eval(node.value).items():
                    add(str(PurePosixPath(prefix) / name), value)
    add(entry.SOURCE_ROOT + '/board/identity/calibration_http.py',
        '42159f8b5a37c8bd0a86628df035d959cfd8ce8558b3433bf6b7b9fd01cfb621')
    entry.inherited_subset(pins, entry.REQUIRED)
    manifest = {
        'schema': 'aura-jpeg-demand-candidate-1',
        'candidate_sources': {
            'entry.py': sha((HERE / 'candidate/entry.py').read_bytes()),
            'ui_camera_service.py': entry.CAMERA_AFTER,
        },
        'inherited_pins': pins,
        'policy': entry.POLICY,
    }
    exact_file(HERE / 'candidate/ui_camera_service.py', FROZEN_CAMERA.read_bytes())
    exact_file(HERE / 'candidate/candidate-manifest.json', encoded(manifest))
    exact_file(HERE / 'serial_trial.py', EXECUTOR.read_bytes())
    exact_file(HERE / 'rebuild_same_boot_readback.py', READBACK_HELPER.read_bytes())
    manifest_sha = sha(encoded(manifest))
    stage = '/home/root/aura-board-owner-candidate-20261030/jpeg-trial-' + manifest_sha[:16]
    result = {
        'status': 'LOCAL_PACKAGE_PREPARED_ACTUAL_STATIC_VERIFY_AND_ROOT_REVIEW_REQUIRED',
        'manifest_sha256': manifest_sha,
        'executor_sha256': EXECUTOR_SHA,
        'readback_helper_sha256': sha(READBACK_HELPER.read_bytes()),
        'baseline_snapshot_sha256': SNAPSHOT_SHA,
        'baseline_readback_path': '/home/root/aura-board-owner-candidate-20261030/private-pin-bebd3e7d-1335-20261031/face_gallery_readback.local.json',
        'baseline_readback_sha256': 'c7300d1cf8b2f6c9dae7bd953ada0c55997d3a8d623703df35ff43e0f0d33df4',
        'baseline_owner': {k: readback[k] for k in ('board_boot_id', 'camera_pid', 'camera_start_ticks', 'camera_cmdline_sha256')},
        'staging_root': stage,
        'candidate_dir': stage + '/candidate',
        'journal': stage + '/journal/state.json',
        'inherited_pins': len(pins),
        'candidate_sources': manifest['candidate_sources'],
        'source_of_remaining_pin_checks': 'Original parent source literals and historical exact artifacts. Root must run candidate --verify-only before stopping any owner.',
        'default_final_camera_source': entry.CAMERA_BEFORE,
        'permanent_B_adoption_supported': False,
        'device_actions_executed': False,
    }
    exact_file(HERE / 'PACKAGE_PLAN.json', encoded(result))
    return result


if __name__ == '__main__':
    print(json.dumps(make(), ensure_ascii=True))
