"""Fixed v20 metadata and public-probe guards. Imports perform no device I/O."""
import hashlib
import http.client
import json
import math
from pathlib import Path, PurePosixPath
import subprocess
import time


HERE = Path(__file__).resolve().parent
ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP_SHA = 'd24b0d0007e2aa2b417f459891c7f39f168502a58374334ceab69e31af5881dd'
MAPPING_SHA = 'a7141992428e47d49ef80828ce9a0b33df6bffe32b613343ba01f937f68fdafc'
SPEC_SHA = 'cd67e77691b415d8133015911806c98aaf328feed44945e492c8b0cd421099c7'
CONFIG_SHA = '5518b6705083eb9e2fae7e19a47c003182995fe8660cbc6031860c9905da9786'
BOOT = 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
WAV = Path('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/models/paraformer/test_wavs/0.wav')
FRONTEND_MODELS = Path('/home/root/aura-board-owner-candidate-20261030/frontend-b3d06b653876469d/models')
FFT_DEPS = Path('/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451/deps')
ASR_DEPS = Path('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps')
PACKAGE_FILES = {'run_frontend_abba.py', 'frontend_v20_common.py', 'public_frontend_budget.py',
    'compare_frontend_abba.py', 'allocation_public_probe.py', 'board_audio_runtime_probe.py',
    'source_mapping.v20.json', 'spec.v20.json'}


class Refused(RuntimeError):
    pass


def need(value, code):
    if not value:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_pinned(path, expected=None, maximum=16 * 1024 * 1024):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink()
         and path.is_file() and path.stat().st_size <= maximum, 'REGULAR_FILE_REQUIRED')
    raw = path.read_bytes()
    need(len(raw) <= maximum and (expected is None or sha(raw) == expected), 'SOURCE_PIN_CHANGED')
    return raw


def baseline():
    mapping = json.loads(read_pinned(HERE / 'source_mapping.v20.json', MAPPING_SHA))
    spec = json.loads(read_pinned(HERE / 'spec.v20.json', SPEC_SHA))
    need(mapping['startup_sha256'] == spec['startup_sha256'] == STARTUP_SHA
         and mapping['boot_id'] == spec['boot_id'] == BOOT and mapping['root'] == ROOT.as_posix()
         and mapping['component_pins'] == spec['component_sha256']
         and len(mapping['component_pins']) == spec['component_pins'] == 380
         and mapping['configuration_sha256'] == spec['configuration_sha256'] == CONFIG_SHA
         and mapping['source_manifest_sha256'] == spec['source_manifest_sha256']
         and mapping['current_publication_committed'] is True
         and mapping['saved_listening_preference'] == {'version': 1, 'enabled': False}
         and spec['expected_final_listening_enabled'] is False, 'FIXED_V20_BASELINE_REQUIRED')
    return mapping


def package(expected):
    manifest = json.loads(read_pinned(HERE / 'PACKAGE_MANIFEST.json', expected, 262144))
    need(set(manifest['files']) == PACKAGE_FILES, 'EXACT_PACKAGE_FILES_REQUIRED')
    for name, row in manifest['files'].items():
        raw = read_pinned(HERE / name, row['sha256'], 1024 * 1024)
        need(len(raw) == row['bytes'], 'PACKAGE_SIZE_CHANGED')
    return baseline()


def metadata(port, route):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        connection.request('GET', route)
        response = connection.getresponse()
        raw = response.read(1048577)
        need(response.status == 200 and len(raw) <= 1048576, 'METADATA_UNAVAILABLE')
        return json.loads(raw)
    finally:
        connection.close()


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def process_identity(pid):
    need(type(pid) is int and pid > 0, 'PROCESS_IDENTIFIER_REQUIRED')
    path = Path('/proc') / str(pid)
    fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
    need(fields[0] not in ('Z', 'X'), 'PROCESS_NOT_LIVE')
    raw = (path / 'cmdline').read_bytes()
    need(0 < len(raw) <= 1048576, 'PROCESS_METADATA_BOUND')
    return dict(pid=pid, birth_ticks=int(fields[19]), command_sha256=sha(raw))


def process_parent(pid):
    fields = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
    return int(fields[1])


def unit(unit_name):
    raw = subprocess.check_output(['systemctl', 'show', unit_name, '-p', 'MainPID',
                                   '-p', 'ActiveState', '-p', 'SubState'], text=True, timeout=3)
    return dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def paused_metadata(state):
    hands = state.get('handsfree_dialogue', {})
    native = state.get('avatar_display', {})
    business = state.get('board_business', {})
    pan = state.get('manual_pan', {})
    need(state.get('phase') == 'IDLE' and state.get('playing') is False
         and hands.get('enabled') is False and hands.get('state') == 'PAUSED'
         and hands.get('microphone_open') is False and pan.get('automatic_following') is False,
         'SAVED_PAUSE_REQUIRED')
    need(native.get('visible') is True and number(native.get('frames')) is not None
         and native['frames'] > 0, 'VISIBLE_NATIVE_UI_REQUIRED')
    need(business.get('dialogue', {}).get('pending') is False
         and business.get('speaker', {}).get('queued_or_active') == 0, 'BUSINESS_JOB_ACTIVE')
    memory = business.get('memory', {})
    stats = hands.get('diagnostics', {})
    need(all(type(stats.get(name)) is int and stats[name] >= 0 for name in
             ('armed', 'speech_starts', 'submitted')), 'CAPTURE_COUNTERS_REQUIRED')
    need(all(type(memory.get(name)) is int and memory[name] >= 0 for name in
             ('completed', 'discarded')), 'MEMORY_COUNTERS_REQUIRED')
    return dict(native_frames=number(native.get('frames')), native_age_ms=number(native.get('age_ms')),
        memory_completed=number(memory.get('completed')), memory_discarded=number(memory.get('discarded')),
        capture_stats={name: number(stats.get(name)) for name in ('armed', 'speech_starts', 'submitted')},
        listening_paused=True, microphone_open=False, following=False)


def guard(mapping, *, full=True):
    need(boot_id() == BOOT, 'BOARD_BOOT_CHANGED')
    startup = json.loads(read_pinned(ROOT / 'startup/config.json', STARTUP_SHA))
    need(startup['component_sha256'] == mapping['component_pins'], 'COMPONENT_MAP_CHANGED')
    if full:
        for relative, fingerprint in mapping['component_pins'].items():
            path = PurePosixPath(relative)
            need(not path.is_absolute() and '..' not in path.parts and str(path) == relative,
                 'COMPONENT_PATH_REJECTED')
            read_pinned(ROOT / 'runtime/aura' / relative, fingerprint)
        manifest = json.loads(read_pinned(ROOT / 'production_source_manifest.json', mapping['source_manifest_sha256']))
        need(manifest['component_pins'] == mapping['component_pins'], 'SOURCE_MANIFEST_CHANGED')
    config = json.loads(read_pinned(ROOT / 'runtime/aura/config/board_avatar_gtk.json', CONFIG_SHA))
    options = config['board_business']
    need(options['asr_variant'] == 'paraformer_small' and options['asr_threads'] == 3
         and options['asr_directory'] == '/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6',
         'ASR_CONFIGURATION_CHANGED')
    owners = {}
    for role in ('supervisor', 'gtk', 'camera'):
        owners[role] = process_identity(mapping[role]['pid'])
        need(owners[role] == mapping[role], 'PRODUCTION_OWNER_CHANGED')
    need(process_parent(mapping['gtk']['pid']) == mapping['supervisor']['pid'], 'GTK_PARENT_CHANGED')
    for unit_name, role in (('aura-avatar-ui.service', 'supervisor'), ('aura-camera-ui.service', 'camera')):
        value = unit(unit_name)
        need(value == dict(MainPID=str(mapping[role]['pid']), ActiveState='active', SubState='running'),
             'PRODUCTION_SERVICE_CHANGED')
    preference = json.loads(read_pinned(Path('/home/root/.local/share/aura-board-business/listening_preference.json'), maximum=4096))
    need(preference == {'version': 1, 'enabled': False} and preference['enabled'] is False
         and type(preference['version']) is int, 'SAVED_PAUSE_CHANGED')
    result = paused_metadata(metadata(8783, '/api/state'))
    camera = metadata(8790, '/health')
    need(camera.get('pid') == mapping['camera']['pid'], 'CAMERA_HEALTH_OWNER_CHANGED')
    result.update(observed_mono=time.monotonic(), owners=owners,
        camera={name: number(camera.get(name)) for name in ('capture_frames', 'detected_frames',
            'preview_frames', 'capture_age_ms', 'observation_age_ms', 'last_inference_ms')})
    return result


def worker_paths(args):
    expected = dict(source_mapping=HERE / 'source_mapping.v20.json', code_root=ROOT / 'runtime/aura',
        pipeline_helper=HERE / 'allocation_public_probe.py', pump_helper=HERE / 'board_audio_runtime_probe.py',
        wav=WAV, frontend_models=FRONTEND_MODELS, fft_deps=FFT_DEPS, asr_deps=ASR_DEPS)
    need(all(getattr(args, key) == value for key, value in expected.items()), 'EXACT_PUBLIC_INPUT_PATHS_REQUIRED')
    return expected
