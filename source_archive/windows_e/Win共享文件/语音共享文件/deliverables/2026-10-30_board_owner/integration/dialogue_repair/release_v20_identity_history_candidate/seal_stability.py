"""Verify actual v20 receipts and live sources before advancing local pointers.

Default mode validates local receipts and generated source only. Device access
and canonical updates require --execute-root-only.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import sys

import stability_common as common


HERE = Path(__file__).resolve().parent
CANONICAL = common.REPAIR.parent / 'production_business_acceptance'
EVIDENCE = HERE / 'identity_history_evidence'


def validate_inputs(spec, ready, installed):
    common.validate_spec(spec)
    if (spec['startup_sha256'] != common.proposed()['startup_sha256']
            or spec['expected_final_listening_enabled'] is not False or spec['component_pins'] != 380):
        raise ValueError('actual_v20_saved_pause_spec_required')
    products = {name: item['sha256'] for name, item in common.approved_sources().items()}
    if (installed.get('status') != 'MINOR_SOURCES_APPLIED_UI_STOPPED'
            or installed.get('spec') != spec or installed.get('source_files') != products
            or installed.get('production_bootstrap_verified') is not True
            or installed.get('profiles_migration_verified') is not True
            or installed.get('gui_configuration_bytes_unchanged') is not True
            or installed.get('private_data_replayed') is not False
            or installed.get('new_source_paths') != sorted(common.NEW_PATHS)):
        raise ValueError('matching_actual_frozen_source_install_receipt_required')
    if set(products) != common.ALLOWED_PATHS:
        raise ValueError('exact_reviewed_source_allowlist_required')
    if (ready.get('status') != 'PRODUCTION_BOARD_BUSINESS_READY' or ready.get('root') != spec['target']
            or ready.get('guard_removed') is not True or ready.get('data_origin') != 'board'
            or ready.get('listening_enabled') is not False or ready.get('listening_state') != 'PAUSED'
            or ready.get('physical_microphone_opened') is not False
            or ready.get('retention_enabled') is not True):
        raise ValueError('actual_ready_with_saved_pause_required')
    if any(type(ready.get(key)) is not int or ready[key] <= 0 for key in ('main_pid', 'gtk_pid')):
        raise ValueError('actual_ready_process_identifiers_required')
    return products


REMOTE = r'''
import hashlib,http.client,json,pathlib,subprocess,time
root=pathlib.Path(SPEC['target']);sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
assert SPEC['startup_sha256']==EXPECTED_STARTUP and SPEC['expected_final_listening_enabled'] is False
startup=(root/'startup/config.json').read_bytes();assert sha(startup)==SPEC['startup_sha256']
pins=json.loads(startup)['component_sha256'];assert pins==SPEC['component_sha256'] and len(pins)==SPEC['component_pins']==380
for rel,pin in pins.items():
 path=root/'runtime/aura'/rel;assert path.resolve()==path and sha(path.read_bytes())==pin
assert set(PRODUCTS)==set(ALLOWED_PRODUCTS)
assert all(pins[rel]==pin for rel,pin in PRODUCTS.items())
manifest_raw=(root/'production_source_manifest.json').read_bytes();assert sha(manifest_raw)==SPEC['source_manifest_sha256']
manifest=json.loads(manifest_raw)
assert manifest['component_pins']==pins and manifest['configuration_sha256']==SPEC['configuration_sha256']
assert sha(pathlib.Path(manifest['configuration_path']).read_bytes())==SPEC['configuration_sha256']
assert sha((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())==SPEC['configuration_sha256']
assert sha(pathlib.Path(SPEC['face_readback']['path']).read_bytes())==SPEC['face_readback']['sha256']
unit=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','ExecMainStatus','-p','NRestarts','-p','DropInPaths'],text=True).splitlines())
assert unit['MainPID']==str(READY['main_pid']) and unit['ActiveState']=='active' and unit['SubState']=='running'
control=json.loads((root.parent/'control-production-v1/state.json').read_bytes())
assert control['phase']=='COMMITTED' and control['guard_removed'] and unit['DropInPaths']==control['final_dropins']
assert control['target_startup_sha256']==SPEC['startup_sha256']

def identity(pid):
 path=pathlib.Path('/proc')/str(pid);fields=(path/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':int(pid),'birth_ticks':int(fields[19]),'command_sha256':sha((path/'cmdline').read_bytes())}

def process_args(pid):
 raw=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes();assert len(raw)<=1048576
 return [part.decode() for part in raw.split(b'\0') if part]

assert process_args(READY['main_pid'])==['/usr/bin/python3','-B',str(root/'startup/launcher.py'),'--config',str(root/'startup/config.json')]
assert process_args(READY['gtk_pid'])[:3]==['/usr/bin/python3','-B',str(root/'runtime/aura/tools/board_avatar_pan.py')]
child_fields=(pathlib.Path('/proc')/str(READY['gtk_pid'])/'stat').read_text().rsplit(')',1)[1].split()
assert int(child_fields[1])==READY['main_pid']
camera=identity(SPEC['camera_owner']['camera_pid'])
assert str(camera['birth_ticks'])==SPEC['camera_owner']['camera_start_ticks'] and camera['command_sha256']==SPEC['camera_owner']['camera_cmdline_sha256']
preference_path=pathlib.Path('/home/root/.local/share/aura-board-business/listening_preference.json')
assert preference_path.resolve()==preference_path
preference_raw=preference_path.read_bytes();assert len(preference_raw)<=4096
preference=json.loads(preference_raw)
assert set(preference)=={'version','enabled'} and type(preference['version']) is int and preference['version']==1
assert preference['enabled'] is False
connection=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
try:
 connection.request('GET','/api/state');response=connection.getresponse();assert response.status==200
 raw=response.read(1048577);assert len(raw)<=1048576;ui=json.loads(raw)
finally:connection.close()
listening=ui.get('handsfree_dialogue',{});display=ui.get('avatar_display',{})
assert listening.get('enabled') is False and listening.get('state')=='PAUSED' and listening.get('microphone_open') is False
assert ui.get('phase')=='IDLE' and ui.get('playing') is False
assert display.get('kind')=='native_yuki_egl' and display.get('visible') is True and display.get('frames',0)>0
print(json.dumps({'status':'IDENTITY_HISTORY_SOURCE_AND_SERVICE_VERIFIED','observed_mono':time.monotonic(),
 'boot_id':SPEC['boot_id'],'root':str(root),'startup_sha256':SPEC['startup_sha256'],
 'source_manifest_sha256':SPEC['source_manifest_sha256'],'configuration_sha256':SPEC['configuration_sha256'],
 'component_pins':pins,'source_files':PRODUCTS,'unit':unit,'supervisor':identity(READY['main_pid']),'gtk':identity(READY['gtk_pid']),
 'camera':camera,'private_data_exported':False,'current_publication_committed':True,
 'saved_listening_preference':preference,'listening':{'enabled':False,'state':'PAUSED','microphone_open':False},
 'phase':'IDLE','playing':False,'native_visible':True,'native_frames':display['frames']}))
'''


def validate_mapping(mapping, spec, ready, products):
    keys = ('startup_sha256', 'source_manifest_sha256', 'configuration_sha256')
    if (mapping.get('status') != 'IDENTITY_HISTORY_SOURCE_AND_SERVICE_VERIFIED'
            or any(mapping.get(key) != spec[key] for key in keys)
            or mapping.get('boot_id') != spec['boot_id']
            or mapping.get('root') != spec['target']
            or mapping.get('component_pins') != spec['component_sha256']
            or len(mapping['component_pins']) != 380 or mapping.get('source_files') != products
            or mapping.get('supervisor', {}).get('pid') != ready['main_pid']
            or mapping.get('gtk', {}).get('pid') != ready['gtk_pid']
            or mapping.get('camera', {}).get('pid') != spec['camera_owner']['camera_pid']
            or str(mapping.get('camera', {}).get('birth_ticks')) != spec['camera_owner']['camera_start_ticks']
            or mapping.get('camera', {}).get('command_sha256') != spec['camera_owner']['camera_cmdline_sha256']
            or mapping.get('current_publication_committed') is not True
            or mapping.get('saved_listening_preference') != {'version': 1, 'enabled': False}
            or mapping.get('saved_listening_preference', {}).get('enabled') is not False
            or type(mapping.get('saved_listening_preference', {}).get('version')) is not int
            or mapping.get('listening') != {'enabled': False, 'state': 'PAUSED', 'microphone_open': False}
            or mapping.get('listening', {}).get('enabled') is not False
            or mapping.get('listening', {}).get('microphone_open') is not False
            or mapping.get('phase') != 'IDLE' or mapping.get('playing') is not False
            or mapping.get('native_visible') is not True):
        raise ValueError('fresh_full_source_and_saved_pause_proof_required')


def exact_file(path, raw):
    if path.exists():
        if path.is_symlink() or path.resolve() != path or path.read_bytes() != raw:
            raise ValueError('existing_seal_file_changed')
        return
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def atomic_file(path, raw):
    temporary = path.with_name(path.name + '.v20-seal-tmp')
    exact_file(temporary, raw)
    os.replace(temporary, path)


def commit_local(raws, mapping, *, evidence=EVIDENCE, canonical=CANONICAL):
    spec, ready, installed = [json.loads(raws[name]) for name in ('spec.json', 'ready.json', 'installed.json')]
    products = validate_inputs(spec, ready, installed)
    validate_mapping(mapping, spec, ready, products)
    desired = {'spec.json': raws['spec.json'], 'actual_ready.json': raws['ready.json']}
    old = {'spec.json': common.pinned(common.PREVIOUS / 'stability_evidence/spec.json', common.BASE_SPEC_SHA),
           'actual_ready.json': common.pinned(common.PREVIOUS / 'stability_evidence/ready.json', common.BASE_READY_SHA)}
    for name in desired:
        path = canonical / name
        if path.is_symlink() or path.read_bytes() not in (old[name], desired[name]):
            raise ValueError('canonical_changed_by_another_publication')
    evidence.mkdir(exist_ok=True)
    for name, raw in raws.items():
        exact_file(evidence / name, raw)
    proof_path = evidence / 'source_mapping.json'
    if proof_path.exists():
        previous = json.loads(proof_path.read_bytes())
        validate_mapping(previous, spec, ready, products)
        if any(previous[key] != mapping[key] for key in ('supervisor', 'gtk', 'camera')):
            raise ValueError('seal_retry_owner_changed')
    else:
        exact_file(proof_path, common.encoded(mapping))
    for name, raw in old.items():
        exact_file(evidence / ('previous_canonical_' + name), raw)
    transaction = {'phase': 'PREPARED', 'spec_sha256': common.sha(desired['spec.json']),
                   'ready_sha256': common.sha(desired['actual_ready.json'])}
    state_path = evidence / 'canonical_update_state.json'
    atomic_file(state_path, common.encoded(transaction))
    # The complete evidence is durable before either current pointer advances.
    # Known old/new pointer combinations permit a safe retry after interruption.
    for name in ('actual_ready.json', 'spec.json'):
        for pointer in desired:
            path = canonical / pointer
            if path.is_symlink() or path.read_bytes() not in (old[pointer], desired[pointer]):
                raise ValueError('canonical_changed_during_evidence_seal')
        if (canonical / name).read_bytes() != desired[name]:
            atomic_file(canonical / name, desired[name])
    transaction['phase'] = 'COMMITTED'
    atomic_file(state_path, common.encoded(transaction))
    return {'status': 'IDENTITY_HISTORY_EVIDENCE_SEALED_CANONICAL_COMMITTED', 'evidence': str(evidence),
            'startup_sha256': spec['startup_sha256'], 'source_manifest_sha256': spec['source_manifest_sha256'],
            'listening_enabled': False, 'current_verification_mono': mapping['observed_mono']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('spec', 'ready', 'installed'):
        parser.add_argument('--' + name, required=True, type=Path)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    raws = {name + '.json': common.pinned(getattr(args, name), getattr(args, name + '_sha256'))
            for name in ('spec', 'ready', 'installed')}
    spec, ready, installed = [json.loads(raws[name]) for name in ('spec.json', 'ready.json', 'installed.json')]
    products = validate_inputs(spec, ready, installed)
    ast.parse(REMOTE, feature_version=(3, 9))
    if not args.execute_root_only:
        print(json.dumps({'status': 'DRY_ACTUAL_RELEASE_RECEIPTS_VALIDATED_NO_SSH_NO_WRITES',
                          'startup_sha256': spec['startup_sha256'], 'remote_sha256': common.sha(REMOTE.encode())}))
        return
    if common.PAYLOAD_FINALIZED is not True:
        raise ValueError('root_final_source_payload_seal_required')
    sys.path.insert(0, str(common.previous_publisher().PROJECT / 'deliverables/2026-10-18_board_dialogue'))
    from board_ssh import ssh
    source = 'SPEC=' + repr(spec) + '\nREADY=' + repr(ready) + '\nPRODUCTS=' + repr(products)
    source += '\nEXPECTED_STARTUP=' + repr(common.proposed()['startup_sha256'])
    source += '\nALLOWED_PRODUCTS=' + repr(sorted(common.ALLOWED_PATHS)) + '\n' + REMOTE
    mapping = json.loads(ssh('python3 -B -', source, timeout=75))
    result = commit_local(raws, mapping)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
