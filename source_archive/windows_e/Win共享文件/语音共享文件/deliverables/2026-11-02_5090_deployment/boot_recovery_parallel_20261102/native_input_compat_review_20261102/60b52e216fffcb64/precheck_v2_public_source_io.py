"""Exercise only exact candidate metadata byte readers on pinned original files."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat

tree = ast.parse(CANDIDATE_SOURCE)
names = {'require', 'sha', 'digest', 'pin', 'OriginalPublicSourcePins', 'Snapshot'}
nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
scope = dict(Path=Path, os=os, stat=stat, json=json, hashlib=hashlib)
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<exact-v2-public-source-readers>', 'exec'), scope)
snapshot = scope['Snapshot']()
observation = snapshot.pinned(MIGRATION_OBSERVATION_PIN)
operator = Path(observation['native_operator_manifest_pin']['path']).parent
scope.update(snapshot=snapshot, observation=observation, operator=operator,
             SOURCE_UNIT=observation['native_c_unit_manifest_pin']['sha256'],
             old_library_sha='c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656')
outer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_original_operator_migration')
inner = next(n for n in outer.body if isinstance(n, ast.FunctionDef) and n.name == 'read_bytes')
exec(compile(ast.Module(body=[inner], type_ignores=[]), '<exact-v2-original-source-entry>', 'exec'), scope)
runtime = snapshot.pinned(observation['native_operator_manifest_pin'])
unit = snapshot.pinned(observation['native_c_unit_manifest_pin'])
settings = snapshot.pinned(observation['settings_pin'])
entries = dict(runtime['files'])
entries.update({str(operator / name): checksum for name, checksum in unit['files'].items()})
entries[settings['old_library']] = settings['old_library_sha256']
for path, checksum in entries.items():
    scope['read_bytes'](dict(path=path, sha256=checksum))
snapshot.unchanged()
rejected = []
for label, call in (
    ('original_JSON_pin_still_refuses_Python', lambda: scope['pin'](dict(path=str(operator/'identity_recovery.py'),sha256=runtime['files'][str(operator/'identity_recovery.py')]))),
    ('original_Snapshot_read_still_refuses_DSO', lambda: snapshot.read(operator/'libaura_native_operator.so')),
    ('dedicated_entry_refuses_unknown_path', lambda: scope['read_bytes'](dict(path='/public/not-reviewed.py',sha256='1'*64))),
    ('dedicated_entry_refuses_conflicting_SHA', lambda: scope['read_bytes'](dict(path=settings['library'],sha256='0'*64))),
):
    try: call()
    except ValueError: rejected.append(label)
    else: raise AssertionError('Expected metadata rejection: '+label)
print(json.dumps(dict(status='V2_FIXED_ORIGINAL_PUBLIC_SOURCE_IO_AND_FINAL_STABILITY_PASS',
                     distinct_fixed_files=len(entries), file_extensions=sorted({Path(name).suffix for name in entries}),
                     all_raw_pins_verified=True, original_JSON_and_Snapshot_read_ranges_unchanged=True,
                     dedicated_source_stability_checked_through_Snapshot_unchanged=True,
                     expected_rejections=rejected, full_current_final_reader_executed=False,
                     original_Native_or_models_or_services_or_library_loading=False,
                     source_or_seed_or_marker_or_config_files_written=False),sort_keys=True))
