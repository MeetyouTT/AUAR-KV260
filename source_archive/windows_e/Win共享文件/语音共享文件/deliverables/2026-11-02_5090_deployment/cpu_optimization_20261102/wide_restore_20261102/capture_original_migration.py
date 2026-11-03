"""Read the existing pinned original operator migration, without executing it."""
import hashlib
import json
import os
from pathlib import Path
import time

ns = {'__name__': 'reviewed_stop_helper'}
exec(compile(STOP_SOURCE, '<original-stop-helper>', 'exec'), ns)
e = FRESH['normal_stop_expected']
ns['checked'](e)
regular, digest, require = ns['regular'], ns['digest'], ns['require']
c = e['source_closure']; root = ns['OPERATOR']
manifest = json.loads(ns['pinned'](c['native_operator_manifest']))
fixed = {str(root / 'native_entry_operator.py'): '0576a388e2c17174b4102665602aa42fbf078a3f016bdfb641c269571ce13943',
         str(root / 'identity_recovery.py'): '64831498d8497c2087b3bb1543367e8cc1917ca131694000884f2d58e60990f7'}
require(c['native_operator_manifest']['sha256'] == '74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad', 'Original operator manifest differs')
for path, sha in fixed.items():
    require(manifest['files'].get(path) == sha and digest(regular(path)) == sha, 'Original migration source differs')
settings_path = root / 'settings.json'; settings_raw = regular(settings_path)
require(manifest['files'].get(str(settings_path)) == digest(settings_raw), 'Original settings not in pinned operator closure')
settings = json.loads(settings_raw)
run = json.loads(ns['pinned'](c['owner_run_config'])); native = run['native_execution']
require(native['source_unit_sha256'] == '29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
        and native['library_sha256'] == 'c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656'
        and native['library'] == settings['old_library'] and native['library_sha256'] == settings['old_library_sha256']
        and native['source_unit_sha256'] == settings['predecessor_unit_sha256']
        and settings['unit_sha256'] == ns['NATIVE_UNIT'] and settings['library_sha256'] == ns['NATIVE_LIBRARY']
        and settings['library'] == str(root / 'libaura_native_operator.so'), 'Actual original migration tuple differs')
health = ns['get']('/health'); handoff = health['dpu_schedule']['protection_handoff']
audit_path = root / ('recovery-audit-' + str(GRANT['camera_owner']['pid']) + '.json')
require(handoff['operator_recovery_audit'] == str(audit_path) and handoff['native_abi_compatible_migration'] is True
        and handoff['native_unit_sha256'] == ns['NATIVE_UNIT'], 'Actual original handoff migration differs')
audit_raw = regular(audit_path, 1048576); audit = json.loads(audit_raw)
require(audit['audit_path'] == str(audit_path) and audit['request'] == settings
        and audit['artificial_counter_reset'] is False and audit['mechanical_actions'] == 0
        and audit['checkpoint_sha256'] == native['seed']['sha256']
        and audit['checkpoint_unit_sha256'] == handoff['predecessor_unit_sha256']
        and audit['checkpoint_unit_sha256'] in (settings['predecessor_unit_sha256'], settings['unit_sha256'])
        and audit['exact_seed_before_operator_request']['boot_id'] == GRANT['boot_id'], 'Existing original audit/config linkage differs')
owner = ns['owner'](GRANT['camera_owner']); require(owner == GRANT['camera_owner'], 'Migration observation owner changed')
maps = Path('/proc', str(owner['pid']), 'maps').read_text()
require(settings['library'] in maps, 'Reviewed original operator library is not mapped in current camera')
observed_ns = time.monotonic_ns()
proof = dict(schema='aura-original-operator-config-migration-observation-1', boot_id=GRANT['boot_id'],
             source_owner=owner, observed_mono_ns=observed_ns, owner_run_config_pin=c['owner_run_config'],
             native_operator_manifest_pin=c['native_operator_manifest'], native_c_unit_manifest_pin=c['native_c_unit_manifest'],
             native_library_pin=c['native_library'], settings_pin=dict(path=str(settings_path), sha256=digest(settings_raw)),
             original_audit_pin=dict(path=str(audit_path), sha256=digest(audit_raw)),
             original_migration_sources=fixed, mapped_original_operator_library=settings['library'],
             original_live_handoff_migration={k: handoff[k] for k in ('operator_recovery_audit', 'native_abi_compatible_migration',
                 'predecessor_unit_sha256', 'native_unit_sha256')},
             metadata_observation_only=True, original_migration_or_Native_code_executed_by_this_observer=False)
raw = (json.dumps(proof, sort_keys=True, indent=2) + '\n').encode()
target = Path(SESSION) / 'original-operator-migration-proof.json'
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, 'wb') as stream:
    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
parent = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
try: os.fsync(parent)
finally: os.close(parent)
require(ns['owner'](GRANT['camera_owner']) == owner and regular(audit_path, 1048576) == audit_raw
        and regular(settings_path) == settings_raw, 'Original migration inputs changed during observation')
print(json.dumps(dict(status='EXISTING_ORIGINAL_OPERATOR_MIGRATION_METADATA_BOUND',
                     observation_pin=dict(path=str(target), sha256=digest(raw)), observation=proof,
                     actual_settings=settings, original_audit_metadata={k:audit[k] for k in ('status','checkpoint_sha256',
                         'checkpoint_unit_sha256','artificial_counter_reset','mechanical_actions')},
                     original_source_or_config_or_seed_or_marker_modified=False, camera_stop_sent=False), sort_keys=True))
