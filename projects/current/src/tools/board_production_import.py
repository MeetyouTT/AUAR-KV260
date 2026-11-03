"""Offline explicit five-store import; never starts ASR, a model or retention.

Default is read-only source preflight. The publisher alone supplies a private
frozen bundle, its SHA, a trusted UTC anchor and an external stopped-writer
barrier. A valid existing receipt is verified without replaying any snapshot.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys

from common.board_memory import BoardMemoryStore
from common.board_memory_migration import inspect_legacy_snapshot,migrate_legacy_snapshot,LegacyMigrationRejected
from common.board_observation_migration import inspect_observation_snapshot,migrate_observation_snapshot
from common.board_production_bootstrap import (verify_production_bootstrap,seal_production_bootstrap,
    stage_initial_conversation_selection,_private_root,_private_file,ProductionBootstrapRejected)
from board.runtime.board_speaker_business import inspect_speaker_snapshot,migrate_speaker_snapshots

SCHEMA='aura.board.private-snapshot.v1'
NAMES={'conversation':'conversations.sqlite3','observation':'observations.sqlite3',
       'speaker':'speakers.sqlite3','anonymous_voice':'anonymous-voices.sqlite3','identity_links':'identity-links.sqlite3'}


class ImportRejected(ValueError):pass


def fail(code):raise ImportRejected(code)


def fingerprint(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda:stream.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


def source_bundle(manifest_path,expected_sha256):
    path=Path(manifest_path).absolute();root=_private_root(path.parent);path=_private_file(root,path.name)
    if (not isinstance(expected_sha256,str) or not re.fullmatch('[0-9a-f]{64}',expected_sha256) or
            path.stat().st_size>65536 or fingerprint(path)!=expected_sha256):fail('private_manifest_fingerprint')
    value=json.loads(path.read_bytes())
    if (not isinstance(value,dict) or set(value)!={'schema','bundle_id','source_writers_stopped_attested',
            'cross_store_barrier','databases','receipt_key'} or value['schema']!=SCHEMA or
            value['source_writers_stopped_attested'] is not True or
            value['cross_store_barrier']!='publisher_confirmed_all_writers_stopped' or
            not isinstance(value['bundle_id'],str) or not re.fullmatch('[0-9a-f]{32}',value['bundle_id']) or
            not isinstance(value['databases'],dict) or set(value['databases'])!=set(NAMES)):
        fail('private_manifest_schema')
    for kind,name in NAMES.items():
        item=value['databases'][kind]
        if not isinstance(item,dict) or item.get('path')!=name:fail('private_manifest_path')
        db=_private_file(root,name)
        if db.stat().st_size!=item.get('bytes') or fingerprint(db)!=item.get('sha256'):fail('private_bundle_file_changed')
        if any(Path(str(db)+s).exists() for s in ('-wal','-shm','-journal')):fail('frozen_source_sidecar_present')
    key=value['receipt_key'];path=_private_file(root,'identity-link-receipt.key')
    if (not isinstance(key,dict) or set(key)!={'path','sha256','bytes'} or key['path']!=path.name or
            key['bytes']!=32 or path.stat().st_size!=32 or fingerprint(path)!=key['sha256']):fail('original_key_fingerprint')
    return root,value


def utc_anchor(value):
    try:
        parsed=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset()!=datetime.timedelta(0):fail('trusted_utc_required')
        stamp=parsed.timestamp()
        if not 1735689600<=stamp<=4102444800:fail('trusted_utc_out_of_bounds')
        return stamp
    except (ValueError,TypeError):fail('explicit_trusted_utc_required')


def _existing_directory_mode(path):
    info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid():fail('import_parent_owner_or_type')
    return stat.S_IMODE(info.st_mode)


def _canonical_import_target(target):
    target=Path(target).absolute()
    if target.resolve()!=target or any(p.casefold()=='win共享文件' for p in target.parts):
        fail('canonical_private_import_target_required')
    return target


def prepare_import_target(target):
    """Explicit import only: create private directories, never a DB.

    Existing ancestors must be canonical, owned by this user and not writable
    by another user, up to a private 0700 boundary. No existing mode is changed.
    The normal GUI/factory is deliberately not allowed to call this helper.
    """
    target=_canonical_import_target(target)
    pending=[];parent=target
    while not parent.exists():
        if parent.is_symlink() or parent.parent==parent:fail('private_import_parent_missing')
        pending.append(parent);parent=parent.parent
    boundary=parent
    while True:
        mode=_existing_directory_mode(boundary)
        if mode&0o022:fail('import_parent_writable_by_others')
        if not mode&0o077:break
        if boundary.parent==boundary:fail('private_import_boundary_required')
        boundary=boundary.parent
    for directory in reversed(pending):
        # A concurrent creator is an error; do not bless or chmod its path.
        directory.mkdir(mode=0o700,exist_ok=False)
        _private_root(directory)
    return _private_root(target)


def preflight(root,bundle,model_id,stamp):
    pins={kind:item['sha256'] for kind,item in bundle['databases'].items()}
    reports=dict(conversation=inspect_legacy_snapshot(root/NAMES['conversation'],expected_sha256=pins['conversation'],
                     imported_at_utc=stamp,max_turns=8192),
                 observation=inspect_observation_snapshot(root/NAMES['observation'],expected_sha256=pins['observation']))
    for kind in ('speaker','anonymous_voice','identity_links'):
        reports[kind]=inspect_speaker_snapshot(root/NAMES[kind],NAMES[kind],model_id=model_id)
    return pins,reports


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest',required=True)
    parser.add_argument('--source-manifest-sha256',required=True)
    parser.add_argument('--speaker-model-id',required=True)
    parser.add_argument('--visual-device-id',required=True)
    parser.add_argument('--trusted-utc',required=True)
    parser.add_argument('--private-root',default='/home/root/.local/share/aura-board-business')
    parser.add_argument('--selection-source',help='Private legacy version-1 ConversationSelection JSON; never pass its CID on CLI')
    parser.add_argument('--existing-receipt-sha256')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--source-writers-stopped',action='store_true')
    args=parser.parse_args(argv)
    stamp=utc_anchor(args.trusted_utc)
    source,bundle=source_bundle(args.source_manifest,args.source_manifest_sha256)
    target=Path(args.private_root).absolute()
    if (os.name!='posix' or target.resolve()!=target or target==source or target in source.parents or source in target.parents
            or any(p.casefold()=='win共享文件' for p in target.parts)):
        fail('separate_canonical_board_private_target_required')
    receipt=target/'production-bootstrap.json'
    if receipt.exists():
        if not args.existing_receipt_sha256:fail('existing_receipt_pin_required_no_snapshot_replay')
        verified=verify_production_bootstrap(target,receipt,args.existing_receipt_sha256)
        if verified['bundle_id']!=bundle['bundle_id']:fail('different_completed_bundle')
        # Do not open writable Store, replay source rows or recreate lost files.
        return dict(status='EXISTING_RECEIPT_VERIFIED',idempotent=True,snapshot_replayed=False,
                    receipt_sha256=args.existing_receipt_sha256,initial_retention_enabled=False)
    pins,reports=preflight(source,bundle,args.speaker_model_id,stamp)
    safe=dict(status='PREFLIGHT_ONLY',execute=False,source_validation=reports,databases=5,
              source_deleted=False,retention_started=False,profile_grants_issued=0,business_values_exported=False)
    if not args.execute:return safe
    if args.source_writers_stopped is not True:fail('external_all_writers_stopped_barrier_required')
    os.umask(0o077)
    prepare_import_target(target)
    # The same lock file/protocol as the normal factory, held through seal.
    from board.runtime.board_business import _BoardWriterLock
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    lease=_BoardWriterLock(target,boot_id)
    try:
        _private_root(target)
        if receipt.exists():fail('receipt_appeared_reverify_without_import')
        store=BoardMemoryStore(target/'timeline.sqlite3',clock=lambda:stamp,data_origin='board')
        os.chmod(target/'timeline.sqlite3',0o600)
        conversation=migrate_legacy_snapshot(source/NAMES['conversation'],store,expected_sha256=pins['conversation'],
            source_data_origin='board',max_turns=8192,transaction_budget_seconds=2.)
        observation=migrate_observation_snapshot(source/NAMES['observation'],store,expected_sha256=pins['observation'],
            target_device_id=args.visual_device_id,source_data_origin='board',transaction_budget_seconds=2.)
        speaker_pins={NAMES[k]:pins[k] for k in ('speaker','anonymous_voice','identity_links')}
        speaker_pins['identity-link-receipt.key']=bundle['receipt_key']['sha256']
        speakers=migrate_speaker_snapshots(source,target/'speaker',expected_sha256=speaker_pins,
            expected_model_id=args.speaker_model_id,single_writer_stopped=True,data_origin='board')
        if args.selection_source:
            stage_initial_conversation_selection(store,target,args.selection_source,import_id=conversation['import_id'])
        sealed=seal_production_bootstrap(target,receipt,bundle_id=bundle['bundle_id'],
            conversation_import={k:conversation[k] for k in ('import_id','source_sha256')},
            observation_import={k:observation[k] for k in ('import_id','source_sha256')},source_sha256=pins,
            speaker_model_id=args.speaker_model_id,single_writer_stopped=True)
        verified=verify_production_bootstrap(target,receipt,sealed['receipt_sha256'])
        return dict(status='PRIVATE_IMPORT_SEALED',receipt_sha256=sealed['receipt_sha256'],
                    counts=dict(turns=conversation['turns'],visual_events=observation['imported_visual_events'],
                                profiles=conversation['profiles']),
                    speaker_files=speakers['files'],conversation_selection_verified=verified['conversation_selection_verified'],
                    source_deleted=False,retention_started=False,initial_retention_enabled=False,
                    profile_grants_issued=0,business_values_exported=False)
    finally:lease.close()


if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False,separators=(',',':')))
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError,RuntimeError) as exc:
        code=str(exc) if isinstance(exc,(ImportRejected,LegacyMigrationRejected,ProductionBootstrapRejected)) else ''
        if not re.fullmatch('[a-z]+_[a-z0-9_]{1,95}',code):code='private_import_precondition_or_validation_failed'
        print(json.dumps(dict(status='REJECTED',error_code=code)))
        sys.exit(2)
