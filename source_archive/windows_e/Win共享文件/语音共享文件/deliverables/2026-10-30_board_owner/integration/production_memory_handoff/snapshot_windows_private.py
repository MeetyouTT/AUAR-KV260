"""Explicit five-store snapshot in the real Windows user's private AppData.

Default: read-only preflight. --execute requires the publisher's external
all-writers-stopped barrier. This script does not stop a process or service.
It never copies a database/key into the project or reports business values.
Run through the independently verified production WMI file view.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time

PROJECT=Path(__file__).resolve().parents[4]
NAMES={'conversation':'conversations.sqlite3','observation':'observations.sqlite3',
       'speaker':'speakers.sqlite3','anonymous_voice':'anonymous-voices.sqlite3',
       'identity_links':'identity-links.sqlite3'}
SCHEMA='aura.board.private-snapshot.v1'


class SnapshotRejected(ValueError):
    """A fixed code; never format a private value into an error report."""


def fail(code):raise SnapshotRejected(code)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()


def private_acl(path,sid):
    command=['icacls',str(path),'/inheritance:r','/grant:r','*'+sid+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F']
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
    if result.returncode:fail('private_acl_setup_failed')


def source_info(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>64*1024*1024:fail('invalid_required_source')
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.2,isolation_level=None)
    try:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        if db.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:fail('source_integrity_failed')
        schema=db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
        tables=[r[1] for r in schema if r[0]=='table']
        if len(tables)>128:fail('source_schema_bound')
        counts={name:db.execute('SELECT count(*) FROM "'+name.replace('"','""')+'"').fetchone()[0] for name in tables}
        return dict(application_id=db.execute('PRAGMA application_id').fetchone()[0],
                    user_version=db.execute('PRAGMA user_version').fetchone()[0],
                    schema_sha256=hashlib.sha256(canonical(schema)).hexdigest(),counts=counts)
    finally:db.close()


def backup(source,target,deadline):
    original=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True,timeout=.2)
    destination=sqlite3.connect(str(target),timeout=.2)
    try:
        original.execute('PRAGMA query_only=ON')
        def progress(status,left,total):
            if time.monotonic()>deadline:fail('snapshot_time_budget_exceeded')
        original.backup(destination,pages=128,progress=progress,sleep=.01)
        destination.commit()
    finally:destination.close();original.close()
    # No original journal/checkpoint/DELETE is issued. The private frozen copy
    # has its own complete main file and no sidecar dependency.
    if any(Path(str(target)+s).exists() for s in ('-wal','-shm','-journal')):fail('snapshot_sidecar_present')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-id',required=True)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--source-writers-stopped',action='store_true')
    parser.add_argument('--seconds',type=float,default=45.)
    args=parser.parse_args(argv)
    if os.name!='nt' or not re.fullmatch('[0-9a-f]{32}',args.bundle_id) or not 5<=args.seconds<=120:
        fail('windows_private_snapshot_bounds_required')
    private=Path.home()/'AppData/Local/Aura/device-memory'
    sources={kind:(PROJECT/'deliverables/2026-10-18_board_dialogue/model_host'/name if kind=='conversation' else private/name)
             for kind,name in NAMES.items()}
    info={kind:source_info(path) for kind,path in sources.items()}
    key=private/'identity-link-receipt.key'
    if key.is_symlink() or not key.is_file() or key.stat().st_size!=32:fail('original_private_key_required')
    if not args.execute:
        return dict(status='PREFLIGHT_ONLY',execute=False,databases=info,source_writers_stopped_attested=False,
                    key_size_verified=True,snapshot_created=False,business_values_exported=False)
    if not args.source_writers_stopped:fail('external_all_writers_stopped_barrier_required')
    base=Path.home()/'AppData/Local/Aura/private-migrations'
    if base.resolve()!=base.absolute() or base.drive.upper()=='E:':fail('canonical_windows_private_destination_required')
    sid_result=subprocess.run(['whoami','/user','/fo','csv','/nh'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
    match=re.search(rb'S-1-5-[0-9-]+',sid_result.stdout)
    if sid_result.returncode or not match:fail('current_user_sid_unavailable')
    sid=match.group().decode('ascii')
    base.mkdir(parents=True,exist_ok=True);private_acl(base,sid)
    target=base/args.bundle_id
    if target.exists():fail('new_private_snapshot_bundle_required')
    target.mkdir();private_acl(target,sid)
    deadline=time.monotonic()+args.seconds
    entries={}
    for kind,path in sources.items():
        # The external cross-store barrier is necessary. Per-file observations
        # also reject any main/WAL change while this coherent bundle is copied.
        before={s:digest(Path(str(path)+s)) for s in ('','-wal') if Path(str(path)+s).exists()}
        out=target/NAMES[kind];backup(path,out,deadline)
        after={s:digest(Path(str(path)+s)) for s in ('','-wal') if Path(str(path)+s).exists()}
        if before!=after or source_info(out)!=info[kind]:fail('source_changed_or_snapshot_mismatch')
        entries[kind]=dict(path=out.name,sha256=digest(out),bytes=out.stat().st_size,**info[kind])
    before=digest(key);copied=target/key.name
    with key.open('rb') as original,copied.open('xb') as destination:
        shutil.copyfileobj(original,destination);destination.flush();os.fsync(destination.fileno())
    if digest(key)!=before or digest(copied)!=before:fail('private_key_changed')
    value=dict(schema=SCHEMA,bundle_id=args.bundle_id,source_writers_stopped_attested=True,
               cross_store_barrier='publisher_confirmed_all_writers_stopped',
               databases=entries,receipt_key=dict(path=key.name,sha256=before,bytes=32))
    manifest=target/'private-snapshot.json'
    with manifest.open('xb') as stream:stream.write(canonical(value)+b'\n');stream.flush();os.fsync(stream.fileno())
    return dict(status='PRIVATE_SNAPSHOT_COMPLETE',bundle_id=args.bundle_id,databases=5,
                manifest_sha256=digest(manifest),business_values_exported=False,
                temporary_snapshot_cleanup_required_after_verified_handoff=True)


if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False,separators=(',',':')))
    except (ValueError,OSError,sqlite3.Error,subprocess.SubprocessError) as exc:
        code=str(exc) if isinstance(exc,SnapshotRejected) else ''
        if not re.fullmatch('[a-z]+_[a-z0-9_]{1,95}',code):code='private_snapshot_precondition_or_copy_failed'
        print(json.dumps(dict(status='REJECTED',error_code=code)))
        sys.exit(2)
