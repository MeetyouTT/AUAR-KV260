"""Metadata-only five-store inspection in the independent hidden WMI view.

Never copies a DB, reads business values/keys, stops a writer or checkpoints.
Per-store transactions are NOT one cross-store atomic snapshot. The publisher
must confirm this helper's WMI launch context before relying on its paths.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time


PROJECT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--seconds', type=float, default=25.)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{32}', args.job_id) or not 1 <= args.seconds <= 30:
        raise SystemExit('Invalid metadata inspection bounds')
    output = HERE/('source-inspection-'+args.job_id+'.json')
    if output.exists():
        raise SystemExit('Do not overwrite source evidence')
    private = Path.home()/'AppData/Local/Aura/device-memory'
    sources = {'conversation': PROJECT/'deliverables/2026-10-18_board_dialogue/model_host/conversations.sqlite3',
               'observation':private/'observations.sqlite3', 'speaker':private/'speakers.sqlite3',
               'anonymous_voice':private/'anonymous-voices.sqlite3', 'identity_links':private/'identity-links.sqlite3'}
    deadline = time.monotonic()+args.seconds
    report = dict(schema_version=1, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  job_id=args.job_id, pid=os.getpid(), executable=sys.executable,
                  launch_context_required='independent_hidden_WMI_production_file_view',
                  launch_context_requires_parent_verification=True, read_only=True,
                  business_values_exported=False, private_key_read=False, backup=False,
                  live_db_hash_is_not_claimed=True, cross_database_atomic_snapshot=False,
                  databases={})
    for kind, path in sources.items():
        row = dict(path=str(path), exists=path.is_file(), tables={}, checked=False)
        report['databases'][kind] = row
        if not row['exists']:
            row['error_code'] = 'required_source_missing'; continue
        db = None
        try:
            db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=.15, isolation_level=None)
            db.execute('PRAGMA query_only=ON')
            db.set_progress_handler(lambda:int(time.monotonic()>deadline), 1000)
            db.execute('BEGIN')
            row['application_id'] = db.execute('PRAGMA application_id').fetchone()[0]
            row['user_version'] = db.execute('PRAGMA user_version').fetchone()[0]
            row['integrity_ok'] = db.execute('PRAGMA quick_check').fetchall() == [('ok',)]
            schema = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
            row['schema_sha256'] = hashlib.sha256(json.dumps(schema,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            names = [r[1] for r in schema if r[0] == 'table']
            if len(names)>128: raise ValueError('schema_bound')
            for name in names:
                quoted = '"'+name.replace('"','""')+'"'
                info = db.execute('PRAGMA table_info('+quoted+')').fetchall()
                row['tables'][name] = dict(count=db.execute('SELECT count(*) FROM '+quoted).fetchone()[0],
                    columns=[{'name':r[1],'type':r[2],'notnull':r[3],'pk':r[5]} for r in info])
            if kind == 'conversation':
                row['profile_conversation_local_facts'] = db.execute(
                    'SELECT count(*) FROM conversation_facts f JOIN conversation_profiles p USING(conversation_id)').fetchone()[0]
            if 'timeline_digests' in names:
                if kind == 'observation':
                    references = {r[0] for r in db.execute('SELECT id FROM visual_timeline')}
                elif kind == 'conversation':
                    references = set()
                    for request,status,assistant in db.execute('SELECT request_id,status,assistant IS NOT NULL FROM turns WHERE seq NOT IN (SELECT seq FROM recall_exclusions)'):
                        digest = hashlib.sha256(request.encode()).hexdigest()[:32]
                        references.add('user:'+digest)
                        if status=='played' and assistant: references.add('assistant:'+digest)
                else: references = set()
                total = missing = empty = invalid = 0
                for (encoded,) in db.execute('SELECT sources FROM timeline_digests'):
                    total += 1
                    try:
                        refs = json.loads(encoded)
                        if not isinstance(refs,list) or any(not isinstance(v,str) for v in refs): raise ValueError()
                        if not refs: empty += 1
                        if any(ref not in references for ref in refs): missing += 1
                    except ValueError: invalid += 1
                row['digest_source_availability'] = dict(digests=total, missing_source_rows=missing,
                    empty_source_rows=empty, invalid_source_rows=invalid, refs_or_text_exported=False)
            row['checked'] = True
            db.rollback()
        except (OSError, ValueError, sqlite3.Error):
            row['error_code'] = 'bounded_source_metadata_read_failed'
        finally:
            if db is not None: db.close()
    key = private/'identity-link-receipt.key'
    report['receipt_key'] = dict(path=str(key), exists=key.is_file(), bytes=key.stat().st_size if key.is_file() else None,
                                 value_or_fingerprint_exported=False)
    report['status'] = 'PASS' if all(r['checked'] and r.get('integrity_ok') for r in report['databases'].values()) else 'INCOMPLETE'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2), encoding='utf-8')
    print(json.dumps(dict(status=report['status'],report=str(output),job_id=args.job_id)))


if __name__ == '__main__':
    main()
