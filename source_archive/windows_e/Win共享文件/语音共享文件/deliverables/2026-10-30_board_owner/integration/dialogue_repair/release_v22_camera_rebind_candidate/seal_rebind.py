"""Seal actual same-boot rebind evidence before advancing current pointers."""
import argparse
import ast
import json
import os
from pathlib import Path

import rebind_common as common


EVIDENCE = common.HERE / 'camera_rebind_evidence'
CANONICAL = common.REPAIR.parent / 'production_business_acceptance'


def validate_inputs(spec, ready, installed):
    common.validate_spec(spec)
    products = {common.CONFIG_RELATIVE: spec['configuration_sha256']}
    common.need(installed.get('status') == 'CAMERA_OWNER_REBOUND_UI_STOPPED' and installed.get('spec') == spec
                and installed.get('source_files') == products and installed.get('component_pins') == 380
                and installed.get('changed_component_count') == 1 and installed.get('unchanged_component_count') == 379
                and installed.get('production_bootstrap_verified') is True
                and installed.get('profiles_migration_verified') is True
                and installed.get('previous_configuration_preserved') is True
                and installed.get('previous_configuration_path') == common.baseline()['minor_prepared_configuration_path']
                and installed.get('configuration_sha256') == spec['configuration_sha256']
                and installed.get('configuration_path') == spec['minor_prepared_configuration_path']
                and installed.get('private_data_replayed') is False and installed.get('ui_started') is False
                and installed.get('service_stop_or_kill') is False and installed.get('listening_preference_changed') is False
                and common.valid_sha(installed.get('transaction_sha256')), 'matching_rebind_install_receipt_required')
    common.need(ready.get('status') == 'PRODUCTION_BOARD_BUSINESS_READY' and ready.get('root') == spec['target']
                and ready.get('guard_removed') is True and ready.get('data_origin') == 'board'
                and ready.get('listening_enabled') is False and ready.get('listening_state') == 'PAUSED'
                and ready.get('physical_microphone_opened') is False and ready.get('retention_enabled') is True,
                'actual_ready_with_user_pause_required')
    common.need(all(type(ready.get(key)) is int and ready[key] > 1 for key in ('main_pid', 'gtk_pid')),
                'actual_ready_process_ids_required')
    return products


VERIFY_REMOTE = '''
def compact_owner(value):
 return {'pid':value['pid'],'birth_ticks':int(value['birth']),'command_sha256':value['cmdline_sha256']}

boot();root=source();j=journal();u,sup,child=owner(root);v=ready_state()
need(j.get('phase')=='COMMITTED' and j.get('guard_removed') is True
     and j.get('target_startup_sha256')==SPEC['startup_sha256']
     and u['DropInPaths']==j['final_dropins'],'fresh_committed_rebind_required')
need(sup['pid']==READY['main_pid'] and child['pid']==READY['gtk_pid'],'ready_owner_changed')
need(j.get('camera_rebind',{}).get('state')=='APPLIED'
     and j['camera_rebind'].get('transaction_sha256')==INSTALLED['transaction_sha256'], 'completed_transaction_changed')
listening=v.get('handsfree_dialogue',{});display=v.get('avatar_display',{})
need(listening.get('enabled') is False and listening.get('state')=='PAUSED'
     and listening.get('microphone_open') is False and v.get('phase')=='IDLE' and v.get('playing') is False,
     'live_user_pause_required')
need(display.get('kind')=='native_yuki_egl' and display.get('visible') is True and display.get('frames',0)>0,
     'native_visible_required')
camera=c.process(SPEC['camera_owner']['camera_pid'])
need(c.same(camera,p['camera']),'current_restored_camera_required')
first=(compact_owner(sup),compact_owner(child),compact_owner(camera))
source();u2,sup2,child2=owner(root)
need(first==(compact_owner(sup2),compact_owner(child2),compact_owner(c.process(camera['pid'])))
     and journal()==j and u2['DropInPaths']==j['final_dropins'],'owners_or_commit_changed_during_seal')
print(json.dumps({'status':'CAMERA_REBIND_SOURCE_AND_SERVICE_VERIFIED','observed_mono':time.monotonic(),
 'boot_id':SPEC['boot_id'],'root':SPEC['target'],'startup_sha256':SPEC['startup_sha256'],
 'source_manifest_sha256':SPEC['source_manifest_sha256'],'configuration_sha256':SPEC['configuration_sha256'],
 'configuration_path':SPEC['minor_prepared_configuration_path'],'component_pins':SPEC['component_sha256'],
 'source_files':{CONFIG_RELATIVE:SPEC['configuration_sha256']},'supervisor':first[0],'gtk':first[1],'camera':first[2],
 'unit':{key:u2[key] for key in ('MainPID','ActiveState','SubState','DropInPaths')},
 'current_publication_committed':True,'saved_listening_preference':{'version':1,'enabled':False},
 'listening':{'enabled':False,'state':'PAUSED','microphone_open':False},'phase':'IDLE','playing':False,
 'native_visible':True,'native_frames':display['frames'],'private_data_exported':False,
 'camera_rebind_observation_sha256':SPEC['camera_rebind']['binding']['written_proof']['observation_sha256'],
 'transaction_sha256':INSTALLED['transaction_sha256']}))
'''


def build_remote(spec):
    source = common.publisher_remote(spec)
    anchor = "\nboot()\nwith open('/run/aura-production-publisher.lock','a') as lock:"
    common.need(source.count(anchor) == 1, 'unique_frozen_dispatch_anchor_required')
    source = source.split(anchor, 1)[0] + '\n' + VERIFY_REMOTE
    ast.parse(source, feature_version=(3, 9))
    return source


def validate_mapping(mapping, spec, ready, installed):
    products = validate_inputs(spec, ready, installed)
    common.need(mapping.get('status') == 'CAMERA_REBIND_SOURCE_AND_SERVICE_VERIFIED'
                and all(mapping.get(key) == spec[key] for key in
                        ('boot_id', 'startup_sha256', 'source_manifest_sha256', 'configuration_sha256'))
                and mapping.get('root') == spec['target'] and mapping.get('component_pins') == spec['component_sha256']
                and mapping.get('source_files') == products
                and mapping.get('configuration_path') == spec['minor_prepared_configuration_path']
                and mapping.get('supervisor', {}).get('pid') == ready['main_pid']
                and mapping.get('gtk', {}).get('pid') == ready['gtk_pid']
                and mapping.get('camera', {}).get('pid') == spec['camera_owner']['camera_pid']
                and str(mapping.get('camera', {}).get('birth_ticks')) == spec['camera_owner']['camera_start_ticks']
                and mapping.get('camera', {}).get('command_sha256') == spec['camera_owner']['camera_cmdline_sha256']
                and mapping.get('current_publication_committed') is True
                and mapping.get('saved_listening_preference') == {'version': 1, 'enabled': False}
                and type(mapping.get('saved_listening_preference', {}).get('version')) is int
                and mapping.get('saved_listening_preference', {}).get('enabled') is False
                and mapping.get('listening') == {'enabled': False, 'state': 'PAUSED', 'microphone_open': False}
                and mapping.get('listening', {}).get('enabled') is False
                and mapping.get('listening', {}).get('microphone_open') is False
                and mapping.get('phase') == 'IDLE' and mapping.get('playing') is False
                and mapping.get('native_visible') is True and mapping.get('private_data_exported') is False
                and mapping.get('camera_rebind_observation_sha256') == spec['camera_rebind']['binding']['written_proof']['observation_sha256']
                and mapping.get('transaction_sha256') == installed['transaction_sha256'],
                'fresh_complete_rebind_source_and_owner_proof_required')


def exact_file(path, raw):
    if path.exists():
        common.need(not path.is_symlink() and path.resolve() == path and path.read_bytes() == raw,
                    'existing_seal_evidence_changed')
        return
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def atomic_file(path, raw):
    temporary = path.with_name(path.name + '.v22-seal-tmp')
    exact_file(temporary, raw)
    os.replace(temporary, path)


def commit_local(raws, mapping, *, evidence=EVIDENCE, canonical=CANONICAL):
    spec, ready, installed = [json.loads(raws[name]) for name in ('spec.json', 'ready.json', 'installed.json')]
    validate_mapping(mapping, spec, ready, installed)
    old = {'spec.json': common.pinned(common.EVIDENCE / 'spec.json', common.BASE_SPEC_SHA),
           'actual_ready.json': common.pinned(common.EVIDENCE / 'ready.json', common.BASE_READY_SHA)}
    desired = {'spec.json': raws['spec.json'], 'actual_ready.json': raws['ready.json']}
    for name in desired:
        path = canonical / name
        common.need(not path.is_symlink() and path.resolve() == path and path.read_bytes() in (old[name], desired[name]),
                    'canonical_changed_by_other_publication')
    evidence.mkdir(exist_ok=True)
    for name, raw in raws.items():
        exact_file(evidence / name, raw)
    mapping_path = evidence / 'source_mapping.json'
    if mapping_path.exists():
        previous = json.loads(mapping_path.read_bytes())
        validate_mapping(previous, spec, ready, installed)
        common.need(all(previous[key] == mapping[key] for key in ('supervisor', 'gtk', 'camera')),
                    'seal_retry_owner_changed')
    else:
        exact_file(mapping_path, common.encoded(mapping))
    for name, raw in old.items():
        exact_file(evidence / ('previous_canonical_' + name), raw)
    transaction = dict(phase='PREPARED', spec_sha256=common.sha(desired['spec.json']),
                       ready_sha256=common.sha(desired['actual_ready.json']))
    state_path = evidence / 'canonical_update_state.json'
    atomic_file(state_path, common.encoded(transaction))
    for name in ('actual_ready.json', 'spec.json'):
        for check in desired:
            path = canonical / check
            common.need(not path.is_symlink() and path.read_bytes() in (old[check], desired[check]),
                        'canonical_changed_during_evidence_seal')
        if (canonical / name).read_bytes() != desired[name]:
            atomic_file(canonical / name, desired[name])
    transaction['phase'] = 'COMMITTED'
    atomic_file(state_path, common.encoded(transaction))
    return dict(status='CAMERA_REBIND_EVIDENCE_SEALED_CANONICAL_COMMITTED', evidence=str(evidence),
                startup_sha256=spec['startup_sha256'], source_manifest_sha256=spec['source_manifest_sha256'],
                listening_enabled=False, current_verification_mono=mapping['observed_mono'])


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
    validate_inputs(spec, ready, installed)
    remote = build_remote(spec)
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_REBIND_SEAL_VALIDATED_NO_SSH_NO_WRITES', remote_sha256=common.sha(remote.encode()))))
        return
    mapping = common.execute_remote(remote, dict(SPEC=spec, ACTION='ready', TOKEN=None, WINDOW=None,
                                                  READY=ready, INSTALLED=installed, CONFIG_RELATIVE=common.CONFIG_RELATIVE), timeout=90)
    print(json.dumps(commit_local(raws, mapping)))


if __name__ == '__main__':
    main()
