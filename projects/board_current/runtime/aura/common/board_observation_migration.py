"""Private frozen legacy observation snapshot -> existing unified timeline.

No capture, model or live cache is started. Historical VLM text stays explicitly
legacy camera evidence in device scope, never current person counts or private
conversation/profile data. Exact duplicate cache coverage is indexed once.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import re

from .board_memory import BoardMemoryStore, _hash, _json, _text, _time, _identifier
from .board_memory_migration import LegacyMigrationRejected, _fingerprint, _quiescent, _rows, _reject

TOPIC = 'legacy.visual_observation'
DIGEST_COLUMNS = {'owner','id','kind','day','bucket_start','bucket_end','start_utc','end_utc',
                  'text','sources','source_count','limited','visual_revision','computed'}
SHAPES = {
    'observations':({'id','boot','epoch','frame','received','summary'},['id']),
    'visual_timeline':({'id','device','boot','epoch','first_frame','last_frame','first_received','last_received','samples','summary','frame_meta'},['id']),
    'visual_timeline_revision':({'device','revision'},['device']),
    'visual_timeline_cursor':({'device','boot','epoch','last_frame','received'},['device','boot','epoch']),
    'timeline_digests':(DIGEST_COLUMNS,['owner','id']),
    'timeline_digest_revisions':({'owner','revision'},['owner']),
    'timeline_digest_builds':({'owner','revision','computed'},['owner']),
}


def _integer(value):
    if type(value) is not int or value<0: _reject('invalid_visual_integer')
    return value


def _string(value, limit=32768):
    try: return _text(value,limit=limit)
    except ValueError: _reject('invalid_visual_text')


def _stamp(value):
    try: return _time(value)
    except ValueError: _reject('invalid_visual_timestamp')


def _plan(path,source_sha256,maximum):
    db=sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True,timeout=.15,isolation_level=None)
    db.row_factory=sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        if (db.execute('PRAGMA application_id').fetchone()[0]!=0 or db.execute('PRAGMA user_version').fetchone()[0]!=0
                or db.execute('PRAGMA quick_check').fetchone()[0]!='ok'):
            _reject('unsupported_visual_source_marker')
        schema=[tuple(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]
        tables={r[1] for r in schema if r[0]=='table'}
        if not set(SHAPES)<=tables or tables-set(SHAPES) or any(r[0]=='view' for r in schema):
            _reject('unsupported_visual_schema')
        for name,(columns,keys) in SHAPES.items():
            info=db.execute('PRAGMA table_info('+name+')').fetchall()
            if ({r['name'] for r in info}!=columns or
                    [r['name'] for r in sorted(info,key=lambda r:r['pk']) if r['pk']]!=keys):
                _reject('unsupported_visual_columns_or_keys')
        projected=_rows(db,'visual_timeline',list(SHAPES['visual_timeline'][0]),maximum)
        cached=_rows(db,'observations',list(SHAPES['observations'][0]),maximum)
        revisions=_rows(db,'visual_timeline_revision',['device','revision'],256)
        cursors=_rows(db,'visual_timeline_cursor',list(SHAPES['visual_timeline_cursor'][0]),maximum)
        digests=_rows(db,'timeline_digests',['sources'],maximum)
    except sqlite3.Error:
        _reject('visual_source_sqlite_read_failed')
    finally:db.close()
    devices={r['device'] for r in revisions}|{r['device'] for r in projected}|{r['device'] for r in cursors}
    if len(devices)!=1 or any(not isinstance(d,str) or not d or len(d)>64 for d in devices):
        _reject('ambiguous_visual_device_binding')
    for row in revisions: _integer(row['revision'])
    if len(revisions)!=1:_reject('missing_visual_effective_revision')
    source_revision=revisions[0]['revision']
    for row in cursors:
        _integer(row['last_frame']);_stamp(row['received']);_string(row['boot'],64);_string(row['epoch'],64)
    ids=set();records=[]
    for row in projected:
        key=_string(row['id'],160)
        if key in ids: _reject('duplicate_visual_source')
        ids.add(key)
        for keyname in ('boot','epoch'): _string(row[keyname],64)
        first,last=_integer(row['first_frame']),_integer(row['last_frame'])
        start,end=_stamp(row['first_received']),_stamp(row['last_received'])
        if first>last or start>end or end-start>300.001 or _integer(row['samples'])<1:
            _reject('invalid_visual_source_span')
        text=_string(row['summary'])
        try:
            meta=json.loads(row['frame_meta'])
            if not isinstance(meta,dict) or set(meta)-{'captured_mono_ms','observed_mono_ms'}:
                _reject('unknown_visual_time_metadata')
            for value in meta.values(): _stamp(value)
        except (ValueError,TypeError): _reject('invalid_visual_time_metadata')
        records.append(dict(key='timeline:'+row['id'],text=text,start=start,end=end,boot=row['boot'],epoch=row['epoch'],
                            first=first,last=last,samples=row['samples']))
    # A digest with missing/empty source references could be unique historical
    # data. It is a hard migration gate, never silently discarded as a cache.
    for row in digests:
        try: refs=json.loads(row['sources'])
        except (ValueError,TypeError): _reject('unique_visual_digest_requires_review')
        if not isinstance(refs,list) or not refs or any(not isinstance(v,str) or v not in ids for v in refs):
            _reject('unique_visual_digest_requires_review')
    covered=0;uncovered=0;cache_map=[]
    for row in cached:
        _integer(row['id']);frame=_integer(row['frame']);at=_stamp(row['received'])
        text=_string(row['summary']);_string(row['boot'],64);_string(row['epoch'],64)
        match=next((r for r in records if r['boot']==row['boot'] and r['epoch']==row['epoch']
                    and r['first']<=frame<=r['last'] and r['start']<=at<=r['end'] and r['text']==text),None)
        if match is None:
            match=dict(key='cache:'+str(row['id']),text=text,start=at,end=at,boot=row['boot'],epoch=row['epoch'],
                       first=frame,last=frame,samples=1)
            records.append(match);uncovered+=1
        else:covered+=1
        cache_map.append((str(row['id']),match['key']))
    schema_sha256=_hash(_json(schema));import_id='legacy_visual:'+_hash(_json([1,source_sha256,schema_sha256]))[:32]
    return dict(records=records,cache_map=cache_map,source_revision=source_revision,source_schema_sha256=schema_sha256,import_id=import_id,
                counts=dict(source_timeline_rows=len(projected),source_cache_rows=len(cached),
                            covered_cache_rows=covered,uncovered_cache_rows=uncovered,
                            imported_visual_events=len(records),reconstructable_digest_rows=len(digests),
                            imported_unique_digests=0))


def inspect_observation_snapshot(source_path, *, expected_sha256, max_rows=20000):
    """Read-only full schema/coverage preflight, with counts-only results."""
    if (not isinstance(expected_sha256,str) or re.fullmatch('[0-9a-f]{64}',expected_sha256) is None or
            type(max_rows) is not int or not 1<=max_rows<=50000):_reject('invalid_visual_migration_bounds')
    path=Path(source_path).resolve(strict=True)
    if path.stat().st_size>64*1024*1024:_reject('invalid_visual_source_path')
    _quiescent(path)
    if _fingerprint(path)!=expected_sha256:_reject('source_fingerprint_mismatch')
    plan=_plan(path,expected_sha256,max_rows)
    _quiescent(path)
    if _fingerprint(path)!=expected_sha256:_reject('source_changed')
    return dict(plan['counts'],source_sha256=expected_sha256,source_schema_sha256=plan['source_schema_sha256'],
                import_id=plan['import_id'],history_only=True,current_frame_asserted=False,read_only=True)


def migrate_observation_snapshot(source_path,target,*,expected_sha256,target_device_id,
                                  source_data_origin='synthetic',max_rows=20000,transaction_budget_seconds=2.):
    """Explicit source-preserving conversion, no pruning or worker startup."""
    if (not isinstance(target,BoardMemoryStore) or source_data_origin not in ('synthetic','board') or
            target.data_origin!=source_data_origin): _reject('source_target_origin_mismatch')
    if (not isinstance(expected_sha256,str) or re.fullmatch('[0-9a-f]{64}',expected_sha256) is None or
            type(max_rows) is not int or not 1<=max_rows<=50000 or not 0<transaction_budget_seconds<=2):
        _reject('invalid_visual_migration_bounds')
    _identifier(target_device_id,'device id')
    path=Path(source_path).resolve(strict=True)
    if str(path)==target.path or path.stat().st_size>64*1024*1024: _reject('invalid_visual_source_path')
    _quiescent(path)
    if _fingerprint(path)!=expected_sha256: _reject('source_fingerprint_mismatch')
    plan=_plan(path,expected_sha256,max_rows)
    _quiescent(path)
    if _fingerprint(path)!=expected_sha256: _reject('source_changed')
    report=dict(plan['counts'],source_sha256=expected_sha256,source_schema_sha256=plan['source_schema_sha256'],
                import_id=plan['import_id'],idempotent=False,source_data_origin=source_data_origin,
                target_data_origin=target.data_origin,history_only=True,scope_kind='device',
                current_frame_asserted=False,profile_grants_issued=0,source_deleted=False)
    with target._db(True) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='bm_observation_migrations'").fetchone():
            old=db.execute('SELECT * FROM bm_observation_migrations WHERE import_id=?',(plan['import_id'],)).fetchone()
            if old and old['state']=='complete' and old['source_sha256']==expected_sha256:
                return dict(json.loads(old['report']),idempotent=True)
            _reject('observation_target_already_imported')
        if db.execute("SELECT 1 FROM bm_scopes WHERE kind='device' AND id=?",(target_device_id,)).fetchone():
            _reject('device_scope_not_empty')
        deadline=time.perf_counter()+transaction_budget_seconds
        db.set_progress_handler(lambda:int(time.perf_counter()>deadline),1000)
        db.execute('CREATE TABLE bm_observation_migrations(import_id TEXT PRIMARY KEY,source_sha256 TEXT NOT NULL,'
                   'source_schema_sha256 TEXT NOT NULL,state TEXT NOT NULL,report TEXT NOT NULL,completed_utc REAL NOT NULL)')
        db.execute('CREATE TABLE bm_observation_migration_map(import_id TEXT NOT NULL,source_kind TEXT NOT NULL,'
                   'source_key TEXT NOT NULL,event_id TEXT NOT NULL REFERENCES bm_events(event_id),'
                   'source_boot TEXT NOT NULL,source_epoch TEXT NOT NULL,first_frame INTEGER NOT NULL,last_frame INTEGER NOT NULL,'
                   'samples INTEGER NOT NULL,source_revision INTEGER NOT NULL,PRIMARY KEY(import_id,source_kind,source_key))')
        target._ensure_scope(db,('device',target_device_id))
        mapping={}
        for row in plan['records']:
            if time.perf_counter()>deadline: _reject('target_transaction_budget_exceeded')
            event_id='camera_observed:'+_hash(plan['import_id']+row['key'])[:32];mapping[row['key']]=event_id
            metadata=dict(time_basis='host_received',evidence='visual_observation',
                source_id='legacy-device:'+_hash(plan['import_id'])[:24],
                claims=[dict(field='source_kind',value='legacy_vlm_history'),dict(field='current',value=False)])
            db.execute('INSERT INTO bm_events VALUES('+','.join('?' for _ in range(18))+')',
                (event_id,'device',target_device_id,None,'camera_observed',TOPIC,row['start'],None,row['end'],1,'valid','none',
                 _json(metadata),_hash(expected_sha256+row['key']),_hash(row['text']),None,None,1))
            db.execute('INSERT INTO bm_bodies VALUES(?,?)',(event_id,row['text']))
            kind,key=row['key'].split(':',1)
            db.execute('INSERT INTO bm_observation_migration_map VALUES(?,?,?,?,?,?,?,?,?,?)',
                (plan['import_id'],kind,key,event_id,row['boot'],row['epoch'],row['first'],row['last'],row['samples'],plan['source_revision']))
        for source_key,key in plan['cache_map']:
            if key.startswith('cache:'):continue
            row=next(r for r in plan['records'] if r['key']==key)
            db.execute('INSERT INTO bm_observation_migration_map VALUES(?,?,?,?,?,?,?,?,?,?)',
                (plan['import_id'],'cache',source_key,mapping[key],row['boot'],row['epoch'],row['first'],row['last'],row['samples'],plan['source_revision']))
        db.execute("INSERT INTO bm_observation_migrations VALUES(?,?,?,'complete',?,?)",
                   (plan['import_id'],expected_sha256,plan['source_schema_sha256'],_json(report),target._now()))
        if db.execute('PRAGMA foreign_key_check').fetchone() is not None: _reject('target_foreign_key_check_failed')
        db.set_progress_handler(None,0)
    return report


def legacy_visual_history(store,device_id,*,start=None,end=None,search=None,limit=20):
    """Explicit historical retrieval helper; never used as current evidence."""
    value=store.history_with_status({'kind':'device','id':device_id},start=start,end=end,search=search,topic=TOPIC,limit=limit)
    return dict(value,legacy_visual_only=True,current=False,identity_verified=False)
