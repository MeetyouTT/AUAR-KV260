"""Device-owner candidate: two public-request hashes, scoped numeric metadata only.

This file is not installed or executed on production by its author. The CLI has
fixed paths/pins, SQLite mode=ro/query_only, a short VM budget and no inference.
No body text, summary, event metadata, fact value, audio or image is selected.
"""
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
PRIVATE = Path('/home/root/.local/share/aura-board-business')
DATABASE = PRIVATE / 'timeline.sqlite3'
SELECTION = PRIVATE / 'conversation_selection.json'
EXPECTED_STARTUP = '22317f7933447b28a2ca535a47246de8b3869989cc0d964a13cd169cd2289311'
SOURCE_PINS = {
    'common/board_memory.py': '8905770197f114cc063addb2dd40bc745d9af942f674140f43e597ff3a6b1905',
    'board/runtime/board_memory_policy.py': 'd6e459f913a6c3d9827e0d90322cb9a2fb17ada87144b853dfdf02ed300f36c6',
    'board/runtime/audio/board_dialogue_jobs.py': '687b80cde20d70e4de56dd71956683b9cec59f55bd25965491dc08d00c8cb248',
    'board/runtime/board_dialogue.py': 'c877cdee602ff0bda669cc2b2fefa77e9328ce205a744e317df82ffb17146de6',
    'common/board_timeline_clock.py': '93b65ec3d9ca393b32499845297c78a2f1f71bc19e069b2ce3dc6f69e795af02',
    'common/conversation_selection.py': '69c80251ac3b531944bc151e0456c5b9cf4012edbe52e5e4780fdbc192cfa2b0',
    'tools/production_memory_presentation.py': 'de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2',
}
HASH = re.compile(r'[0-9a-f]{64}')
ID = re.compile(r'[0-9a-f]{32}')
STATUSES = {'generating', 'awaiting_playback', 'played', 'interrupted'}
SOURCES = {'user_said', 'assistant_reply', 'assistant_played'}
APPLICATION_ID = 1096110658


class Refused(Exception):
    def __init__(self, code):
        self.code = code


def token(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def scalar(db, sql, parameters=()):
    return db.execute(sql, parameters).fetchone()[0]


def finite(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def inspect_connection(db, seed_hash, answer_hash, *, selected_conversation, clock_lower=None, clock_safe=False):
    """Pure metadata SELECTs; public tests inject a synthetic SQLite connection."""
    if not HASH.fullmatch(seed_hash) or (answer_hash is not None and not HASH.fullmatch(answer_hash)):
        raise Refused('invalid_request_hash')
    if answer_hash == seed_hash:
        raise Refused('request_hashes_must_differ')
    if not isinstance(selected_conversation, str) or not ID.fullmatch(selected_conversation):
        raise Refused('selection_unavailable')
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    if scalar(db, 'PRAGMA application_id') != APPLICATION_ID or scalar(db, 'PRAGMA user_version') != 1:
        raise Refused('schema_mismatch')
    rows = db.execute('SELECT turn_id,scope_kind,scope_id,user_event_id,assistant_event_id,status,closed_utc '
                      'FROM bm_turns ORDER BY created_utc DESC,turn_id DESC LIMIT 64').fetchall()
    def match(wanted):
        found = [row for row in rows if token(row['turn_id']) == wanted]
        if len(found) != 1:
            raise Refused('target_not_unique_within_latest64')
        return found[0]
    seed = match(seed_hash)
    answer = match(answer_hash) if answer_hash else None
    same_scope = None if answer is None else (seed['scope_kind'],seed['scope_id']) == (answer['scope_kind'],answer['scope_id'])
    report = dict(schema='aura.target-public-memory-metadata.v1', metadata_only=True, read_only=True,
        seed_request_token=seed_hash, answer_request_token=answer_hash, search_limit=64,
        matched_seed=True, matched_answer=answer is not None, same_scope=same_scope,
        seed_scope_token=token('conversation:'+seed['scope_id']) if seed['scope_kind']=='conversation' else None,
        answer_scope_token=token('conversation:'+answer['scope_id']) if answer is not None and answer['scope_kind']=='conversation' else None,
        selected_conversation_matches_seed=seed['scope_kind']=='conversation' and seed['scope_id']==selected_conversation,
        profile_or_device_scope_supported=False, clock_safe_for_compaction=clock_safe is True,
        clock_age_available=finite(clock_lower) is not None,
        actual_prompt_retrieval_observed=False, dependency_records_prove_prompt_inclusion=False)
    if seed['scope_kind'] != 'conversation' or seed['scope_id'] != selected_conversation:
        report['status'] = 'SELECTION_OR_SCOPE_MISMATCH_NO_EVENT_INSPECTION'
        return report
    if answer is not None and not same_scope:
        report['status'] = 'ANSWER_SCOPE_MISMATCH_NO_EVENT_INSPECTION'
        return report
    owner = ('conversation', seed['scope_id'])
    clock_safe = clock_safe is True
    now = finite(clock_lower)
    closed = finite(seed['closed_utc'])
    report['seed_turn_status'] = seed['status'] if seed['status'] in STATUSES else 'other'
    report['seed_turn_closed_age_seconds'] = now - closed if now is not None and closed is not None else None
    report['seed_full_playback_recorded'] = seed['status'] == 'played'
    seed_events = []
    internal_events = []
    for role, eid in [('user', seed['user_event_id']), ('assistant', seed['assistant_event_id'])]:
        if eid is None:
            continue
        event = db.execute('SELECT event_id,source,state,revision,closed_utc,compacted_summary_id '
            'FROM bm_events WHERE event_id=? AND scope_kind=? AND scope_id=? AND turn_id=?',
            (eid,) + owner + (seed['turn_id'],)).fetchone()
        if event is None:
            raise Refused('target_event_scope_or_owner_mismatch')
        internal_events.append(eid)
        linked = db.execute('SELECT s.summary_id FROM bm_summary_sources ss JOIN bm_summaries s USING(summary_id) '
            "WHERE ss.event_id=? AND ss.revision=? AND s.scope_kind=? AND s.scope_id=? AND s.state='valid' AND s.summary_id=? LIMIT 4",
            (eid,event['revision']) + owner + (event['compacted_summary_id'],)).fetchall()
        committed = scalar(db, 'SELECT COUNT(*) FROM bm_task_sources ts JOIN bm_tasks t USING(task_id) '
            "WHERE ts.event_id=? AND t.scope_kind=? AND t.scope_id=? AND t.status='committed' AND t.summary_id=?",
            (eid,) + owner + (event['compacted_summary_id'],))
        facts = scalar(db, 'SELECT COUNT(*) FROM bm_fact_sources fs JOIN bm_facts f '
            'ON f.scope_kind=fs.scope_kind AND f.scope_id=fs.scope_id AND f.fact_key=fs.fact_key AND f.revision=fs.revision '
            "WHERE fs.event_id=? AND fs.scope_kind=? AND fs.scope_id=? AND f.state='current'", (eid,) + owner)
        stamp = finite(event['closed_utc'])
        age = now-stamp if now is not None and stamp is not None else None
        seed_events.append(dict(role=role,event_token=token(eid),source=event['source'] if event['source'] in SOURCES else 'other',
            valid=event['state']=='valid', body_rows=scalar(db,'SELECT COUNT(*) FROM bm_bodies WHERE event_id=?',(eid,)),
            closed_age_seconds=age, eligible_age_reached=bool(clock_safe and age is not None and age>=300 and closed is not None and now-closed>=300),
            compacted_summary_link_present=event['compacted_summary_id'] is not None,
            valid_summary_link_count=len(linked), available_source_category='timeline_summary' if linked else 'none',
            valid_summary_tokens=[token(row['summary_id']) for row in linked],
            committed_task_count=committed, current_fact_source_links=facts))
    report['seed_events'] = seed_events
    report['target_compaction_proven'] = bool(report['seed_full_playback_recorded'] and len(seed_events)==2 and all(
        row['valid'] and row['body_rows']==0 and row['compacted_summary_link_present'] and row['valid_summary_link_count']>=1
        and row['committed_task_count']>=1 and row['eligible_age_reached'] for row in seed_events))
    report['target_has_current_fact_source_links'] = any(row['current_fact_source_links']>0 for row in seed_events)
    if answer is not None:
        report['answer_turn_status'] = answer['status'] if answer['status'] in STATUSES else 'other'
        aid = answer['assistant_event_id']
        assistant = db.execute('SELECT event_id,provenance_complete FROM bm_events '
            'WHERE event_id=? AND scope_kind=? AND scope_id=? AND turn_id=?',
            (aid,) + owner + (answer['turn_id'],)).fetchone() if aid else None
        if assistant is None:
            report['answer_assistant_record_present'] = False
        else:
            report['answer_assistant_record_present'] = True
            report['answer_provenance_complete'] = bool(assistant['provenance_complete'])
            report['answer_seed_dependencies'] = [dict(source_event_token=token(eid),
                recorded_dependency=bool(scalar(db,'SELECT COUNT(*) FROM bm_event_dependencies WHERE event_id=? AND source_event_id=?',(aid,eid))))
                for eid in internal_events]
    report['status'] = 'TARGET_METADATA_COMPLETE'
    return report


def checked_file(path, *, private=False):
    if path.is_symlink() or not path.is_file() or path.resolve(strict=True) != path:
        raise Refused('unsafe_fixed_path')
    info = path.stat()
    if info.st_nlink != 1 or (private and (info.st_uid != os.geteuid() or info.st_mode & 0o077)):
        raise Refused('unsafe_fixed_file')
    return info


def read_state_clock():
    connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=2)
    try:
        connection.request('GET','/api/state')
        response = connection.getresponse()
        body = response.read(1048577)
        if response.status != 200 or len(body)>1048576:
            raise Refused('state_unavailable')
        state = json.loads(body)
    finally:
        connection.close()
    if state.get('phase')!='IDLE' or state.get('playing') is not False:
        raise Refused('foreground_not_idle')
    h=state.get('handsfree_dialogue',{})
    if h.get('enabled') is not False or h.get('microphone_open') is not False:
        raise Refused('paused_microphone_closed_required')
    clock=state.get('board_business',{}).get('clock',{})
    return dict(lower=finite(clock.get('utc_lower_bound')),safe=clock.get('safe_for_compaction') is True,
                anchored=clock.get('anchored') is True)


def diagnose(seed_hash, answer_hash=None):
    startup=ROOT/'startup/config.json'
    checked_file(startup)
    def pins():
        if hashlib.sha256(startup.read_bytes()).hexdigest()!=EXPECTED_STARTUP:
            raise Refused('startup_changed_repin_required')
        for relative,expected in SOURCE_PINS.items():
            path=ROOT/'runtime/aura'/relative
            checked_file(path)
            if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                raise Refused('source_changed_repin_required')
    pins()
    if not HASH.fullmatch(seed_hash) or (answer_hash is not None and not HASH.fullmatch(answer_hash)):
        raise Refused('invalid_request_hash')
    clock=read_state_clock()
    checked_file(SELECTION,private=True)
    selected_bytes=SELECTION.read_bytes()
    if len(selected_bytes)>4096:
        raise Refused('selection_invalid')
    selected=json.loads(selected_bytes)
    if set(selected)!={'version','conversation_id'} or selected['version']!=1:
        raise Refused('selection_invalid')
    before=checked_file(DATABASE,private=True)
    began=time.monotonic()
    db=sqlite3.connect(DATABASE.as_uri()+'?mode=ro',uri=True,timeout=.15)
    db.set_progress_handler(lambda:int(time.monotonic()-began>.4),500)
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        result=inspect_connection(db,seed_hash,answer_hash,selected_conversation=selected['conversation_id'],
            clock_lower=clock['lower'],clock_safe=clock['safe'] and clock['anchored'])
    finally:
        db.close()
    after=checked_file(DATABASE,private=True)
    if (before.st_dev,before.st_ino)!=(after.st_dev,after.st_ino) or SELECTION.read_bytes()!=selected_bytes:
        raise Refused('owner_or_selection_changed')
    pins()
    result.update(startup_sha256=EXPECTED_STARTUP,source_pins_match=True,selection_file_unchanged=True,
        saved_selection_is_not_a_new_profile_grant=True,reading_elapsed_ms=round((time.monotonic()-began)*1000,3),
        no_text_summary_metadata_or_fact_value_selected=True,actual_model_or_audio_request_sent=False,
        actual_prompt_source_category='unknown_not_in_existing_diagnostics')
    return result


def main():
    try:
        if len(sys.argv) not in (2,3):
            raise Refused('one_or_two_explicit_request_hashes_required')
        result=diagnose(*sys.argv[1:])
    except Refused as exc:
        result=dict(schema='aura.target-public-memory-metadata.v1',status='REFUSED',code=exc.code,metadata_only=True,read_only=True)
    except Exception as exc:
        name=type(exc).__name__
        allowed={'OperationalError','DatabaseError','ValueError','KeyError','TypeError','OSError','FileNotFoundError',
                 'PermissionError','TimeoutError','ConnectionRefusedError','JSONDecodeError'}
        result=dict(schema='aura.target-public-memory-metadata.v1',status='UNAVAILABLE',
            error_class=name if name in allowed else 'other',metadata_only=True,read_only=True)
    print(json.dumps(result,ensure_ascii=True,allow_nan=False))
    return 0 if result.get('status')=='TARGET_METADATA_COMPLETE' else 2


if __name__=='__main__':
    raise SystemExit(main())
