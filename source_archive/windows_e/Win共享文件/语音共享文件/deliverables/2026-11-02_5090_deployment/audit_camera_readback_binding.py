"""Audit fresh camera/source/model pins; never opens the identity database."""
import hashlib
import http.client
import json
from pathlib import Path

root = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
startup = json.loads((root / 'startup/config.json').read_bytes())
runtime = Path(startup['runtime'])
path = runtime / 'aura/config/face_gallery_readback.local.json'
config = json.loads(path.read_bytes())
connection = http.client.HTTPConnection('127.0.0.1', 8790, timeout=2)
try:
    connection.request('GET', '/health')
    response = connection.getresponse()
    raw = response.read(1024 * 1024 + 1)
    if response.status != 200 or len(raw) > 1024 * 1024:
        raise RuntimeError('Camera health is not available')
    health = json.loads(raw)
finally:
    connection.close()
pid = health['pid']
process = Path('/proc') / str(pid)
command_hash = hashlib.sha256((process / 'cmdline').read_bytes()).hexdigest()
birth = (process / 'stat').read_text().rsplit(')', 1)[1].split()[19]
source_issues = []
for name, expected in config['source_sha256'].items():
    if Path(name).suffix in ('.sqlite', '.sqlite3', '.db'):
        raise RuntimeError('Unexpected database in source hashes')
    try:
        actual = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    except OSError as error:
        source_issues.append(dict(path=name, issue=type(error).__name__))
        continue
    if actual != expected:
        source_issues.append(dict(path=name, issue='sha256_differs'))
camera_config = json.loads(Path(config['camera_config']).read_bytes())
identity = json.loads(Path(config['identity_config']).read_bytes())
checks = dict(
    camera_command_matches=command_hash == config['camera_cmdline_sha256'],
    source_hashes_match=not source_issues,
    identity_source_matches=camera_config.get('identity') == dict(enabled=True, config=config['identity_config']),
    model_and_private_store_selection_match=(identity.get('database') == config['database'] and identity.get('model_id') == config['model_id']),
    original_int8_backend_matches=(identity.get('feature_backend', {}).get('kind') == 'dpu_sface' and identity['feature_backend'].get('model_sha256') == config['model_sha256']),
    original_ttl_matches=identity.get('result_ttl_ms') == config['result_ttl_ms'],
    original_dimension_matches=config['dimension'] == 128 and config['backend'] == 'DPU_SFACE_INT8',
    camera_identity_ready=health.get('identity', {}).get('ready') is True)
print(json.dumps(dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    pinned_boot_id=config['board_boot_id'], pinned_pid=config['camera_pid'], pinned_birth_ticks=config['camera_start_ticks'],
    actual_camera_pid=pid, actual_camera_birth_ticks=birth, actual_command_sha256=command_hash,
    checks=checks, source_issues=source_issues, source_files_checked=len(config['source_sha256']),
    startup_tracks_readback_config='config/face_gallery_readback.local.json' in startup.get('component_sha256', {}),
    startup_files=sorted(p.name for p in (root / 'startup').iterdir() if p.is_file()),
    configuration_changed=False, database_opened=False, audio_or_motion_requested=False)))
