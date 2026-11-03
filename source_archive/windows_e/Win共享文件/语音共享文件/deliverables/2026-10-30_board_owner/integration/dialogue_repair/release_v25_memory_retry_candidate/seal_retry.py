"""Seal actual two-source retry evidence after full380 and paused checks."""
import argparse
import ast
import json
import os
from pathlib import Path

import retry_common as common


EVIDENCE = common.HERE / 'memory_retry_evidence'
CANONICAL = common.REPAIR.parent / 'production_business_acceptance'


def validate_inputs(spec, ready, installed):
    common.validate_spec(spec)
    products = {relative: row['sha256'] for relative, row in spec['summary_retry']['payload']['sources'].items()}
    common.need(installed.get('status') == 'SUMMARY_RETRY_SOURCE_APPLIED_UI_STOPPED' and installed.get('spec') == spec
                and installed.get('source_files') == products and installed.get('component_pins') == 380
                and installed.get('changed_component_count') == 2 and installed.get('unchanged_component_count') == 378
                and installed.get('production_bootstrap_verified') is True
                and installed.get('profiles_migration_verified') is True
                and installed.get('gui_configuration_bytes_unchanged') is True
                and installed.get('face_readback_unchanged') is True
                and installed.get('private_data_replayed') is False and installed.get('ui_started') is False
                and installed.get('service_stop_or_kill') is False and installed.get('listening_preference_changed') is False
                and common.valid_sha(installed.get('transaction_sha256')), 'matching_selected_source_install_receipt_required')
    common.need(ready.get('status') == 'PRODUCTION_BOARD_BUSINESS_READY' and ready.get('root') == spec['target']
                and ready.get('guard_removed') is True and ready.get('data_origin') == 'board'
                and ready.get('listening_enabled') is False and ready.get('listening_state') == 'PAUSED'
                and ready.get('physical_microphone_opened') is False and ready.get('retention_enabled') is True
                and all(type(ready.get(key)) is int and ready[key] > 1 for key in ('main_pid', 'gtk_pid')),
                'actual_ready_with_user_pause_required')
    return products


def verifier_body():
    body = common.previous_seal().verifier_body()
    old = """need(j.get('summary_followup',{}).get('state')=='APPLIED'
     and j['summary_followup'].get('stage')==SPEC['summary_followup']['stage']
     and j['summary_followup'].get('transaction_sha256')==INSTALLED['transaction_sha256'],'completed_followup_transaction_changed')
followup_tx=c.parse(c.read(Path(SPEC['summary_followup']['stage'])/'transaction.json',INSTALLED['transaction_sha256']))
need(followup_tx.get('applied_spec_sha256')==c.sha(c.encoded(SPEC)),'completed_followup_spec_changed')"""
    new = """need(j.get('summary_followup',{}).get('state')=='APPLIED'
     and j['summary_followup'].get('stage')==SPEC['summary_followup']['stage'],'original_followup_transaction_changed')
followup_tx=c.parse(c.read(Path(SPEC['summary_followup']['stage'])/'transaction.json',j['summary_followup']['transaction_sha256']))
need(followup_tx.get('applied_spec_sha256')==""" + repr(common.BASE_SPEC_SHA) + """,'original_followup_spec_changed')
need(j.get('summary_retry',{}).get('state')=='APPLIED'
     and j['summary_retry'].get('stage')==SPEC['summary_retry']['stage']
     and j['summary_retry'].get('transaction_sha256')==INSTALLED['transaction_sha256'],'completed_retry_transaction_changed')
retry_tx=c.parse(c.read(Path(SPEC['summary_retry']['stage'])/'transaction.json',INSTALLED['transaction_sha256']))
need(retry_tx.get('applied_spec_sha256')==c.sha(c.encoded(SPEC)),'completed_retry_spec_changed')"""
    body = common.replace_once(body, old, new)
    body = common.replace_once(body,
        "'source_files':{relative:row['sha256'] for relative,row in SPEC['summary_followup']['payload']['sources'].items()}",
        "'source_files':{relative:row['sha256'] for relative,row in SPEC['summary_retry']['payload']['sources'].items()}")
    return body.replace('SUMMARY_FOLLOWUP_SOURCE_AND_SERVICE_VERIFIED', 'SUMMARY_RETRY_SOURCE_AND_SERVICE_VERIFIED')


def build_remote(spec):
    remote = common.publisher_remote(spec)
    anchor = "\nboot()\nwith open('/run/aura-production-publisher.lock','a') as lock:"
    common.need(remote.count(anchor) == 1, 'unique_frozen_dispatch_anchor_required')
    remote = remote.split(anchor, 1)[0] + '\n' + verifier_body()
    ast.parse(remote, feature_version=(3, 9))
    return remote


def validate_mapping(mapping, spec, ready, installed):
    products = validate_inputs(spec, ready, installed)
    base = common.baseline()
    common.need(mapping.get('status') == 'SUMMARY_RETRY_SOURCE_AND_SERVICE_VERIFIED'
                and all(mapping.get(key) == spec[key] for key in
                        ('boot_id', 'startup_sha256', 'source_manifest_sha256', 'configuration_sha256'))
                and mapping.get('root') == spec['target'] and mapping.get('component_pins') == spec['component_sha256']
                and mapping.get('source_files') == products
                and mapping.get('configuration_path') == base['minor_prepared_configuration_path']
                and mapping.get('supervisor', {}).get('pid') == ready['main_pid']
                and mapping.get('gtk', {}).get('pid') == ready['gtk_pid']
                and mapping.get('camera', {}).get('pid') == base['camera_owner']['camera_pid']
                and str(mapping.get('camera', {}).get('birth_ticks')) == base['camera_owner']['camera_start_ticks']
                and mapping.get('camera', {}).get('command_sha256') == base['camera_owner']['camera_cmdline_sha256']
                and mapping.get('current_publication_committed') is True
                and mapping.get('saved_listening_preference') == {'version': 1, 'enabled': False}
                and type(mapping.get('saved_listening_preference', {}).get('version')) is int
                and mapping.get('saved_listening_preference', {}).get('enabled') is False
                and mapping.get('listening') == {'enabled': False, 'state': 'PAUSED', 'microphone_open': False}
                and mapping.get('listening', {}).get('enabled') is False
                and mapping.get('listening', {}).get('microphone_open') is False
                and mapping.get('phase') == 'IDLE' and mapping.get('playing') is False
                and mapping.get('native_visible') is True and mapping.get('private_data_exported') is False
                and mapping.get('camera_rebind_observation_sha256') == base['camera_rebind']['binding']['written_proof']['observation_sha256']
                and mapping.get('transaction_sha256') == installed['transaction_sha256'],
                'fresh_two_retry_sources_and_sameboot_owner_proof_required')


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
    temporary = path.with_name(path.name + '.v25-seal-tmp')
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
        common.need(all(previous[key] == mapping[key] for key in ('supervisor', 'gtk', 'camera')), 'seal_retry_owner_changed')
    else:
        exact_file(mapping_path, common.encoded(mapping))
    for name, raw in old.items():
        exact_file(evidence / ('previous_canonical_' + name), raw)
    state = dict(phase='PREPARED', spec_sha256=common.sha(desired['spec.json']), ready_sha256=common.sha(desired['actual_ready.json']))
    state_path = evidence / 'canonical_update_state.json'
    atomic_file(state_path, common.encoded(state))
    for name in ('actual_ready.json', 'spec.json'):
        for check in desired:
            path = canonical / check
            common.need(not path.is_symlink() and path.read_bytes() in (old[check], desired[check]),
                        'canonical_changed_during_evidence_seal')
        if (canonical / name).read_bytes() != desired[name]:
            atomic_file(canonical / name, desired[name])
    state['phase'] = 'COMMITTED'
    atomic_file(state_path, common.encoded(state))
    return dict(status='SUMMARY_RETRY_SOURCE_EVIDENCE_SEALED_CANONICAL_COMMITTED', evidence=str(evidence),
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
        print(json.dumps(dict(status='DRY_SUMMARY_SEAL_VALIDATED_NO_SSH_NO_WRITES', remote_sha256=common.sha(remote.encode()))))
        return
    mapping = common.execute_remote(remote, dict(SPEC=spec, ACTION='ready', TOKEN=None, WINDOW=None,
                                                  READY=ready, INSTALLED=installed,
                                                  BASE_SPEC_SHA=common.BASE_SPEC_SHA), timeout=90)
    print(json.dumps(commit_local(raws, mapping)))


if __name__ == '__main__':
    main()
