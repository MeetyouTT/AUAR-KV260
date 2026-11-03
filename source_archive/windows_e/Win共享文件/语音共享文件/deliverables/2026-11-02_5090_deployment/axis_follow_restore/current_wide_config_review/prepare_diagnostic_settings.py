"""Prepare a local input-diagnostics-only settings file from verified metadata."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AXIS = HERE.parent
config = json.loads((HERE / 'CURRENT_AXIS_CONFIG_READONLY.json').read_text(encoding='utf-8'))['board_result']
contract = json.loads((HERE / 'FACE_DIAGNOSTIC_CONTRACT_READONLY.json').read_text(encoding='utf-8'))['board_result']
assert contract['filtered_current_packet'] == {'board_boot_id': config['boot_id'],
    'frame_width': 640, 'frame_height': 480, 'mirror_horizontal': True, 'source_kind': 'actual'}
assert config['zone_sha256'] == '91a6334660928591ce695a404a4e43dcc17fe9c932b68e6189d074893f5febac'
settings = dict(config['zone'])
settings.update(board_boot_id=config['boot_id'], updated_mono_ms=contract['board_monotonic_ms'],
    geometry_reused_from=config['zone_path'], geometry_reused_sha256=config['zone_sha256'],
    diagnostic_only=True,
    scope='existing input diagnostics only; no actuator or physical-reference authority',
    current_camera_metadata_verified_utc=contract['utc'],
    current_camera_owner=contract['camera_owner'],
    geometry_basis='same pinned production controls and original user-selected zone; current motion metadata confirms 640x480 mirrored source; GUI not yet restarted',
    actual_current_screen_measurement_performed=False,
    physical_reference_verified=False,
    direction_verified_for_current_boot=False)
zone_source = AXIS / 'original_sources/e31fc0ee824f__face_zone.py'
raw = zone_source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'e31fc0ee824f8c89413f47a4618a6bbc6c31e794bcba55783e63782d03d03feb'
tree = ast.parse(raw.decode('utf-8'))
assert all(isinstance(node, (ast.Expr, ast.Import, ast.FunctionDef)) for node in tree.body)
space = {}
exec(compile(raw, str(zone_source), 'exec'), space)
mapped = space['camera_zone'](settings, config['boot_id'])
assert mapped['left_ratio'] == .1 and abs(mapped['right_ratio'] - .8064720153808593) < 1e-12
output = HERE / 'face-zone-input-diagnostics-903c.json'
with output.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(settings, stream, ensure_ascii=False, indent=2, sort_keys=True)
    stream.write('\n')
receipt = {'settings_file': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
           'camera_zone_mapping': mapped, 'local_original_pure_parser_executed': True,
           'board_settings_written': False, 'diagnostic_executed': False,
           'physical_reference_or_direction_claimed': False}
with (HERE / 'DIAGNOSTIC_SETTINGS.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(receipt, ensure_ascii=True))
