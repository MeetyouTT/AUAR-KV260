"""Independent M03-r2 sources against saved v18 pins; no production writes.

Every digest is computed from actual written bytes. Original M03 and all
independent counterexamples stay unchanged, with byte-for-byte review copies.
"""
import ast
import difflib
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
D=H/'candidate_m03_r2'
BASE=H/'board_integration_v17/local_runtime_v17'
V18=H.parent/'release_v18_candidate/v18_evidence/source_mapping.json'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def once(source,old,new):
    if source.count(old)!=1:raise ValueError('Non-unique edit anchor:'+old[:120])
    return source.replace(old,new)


DAY_RANGE='''def calendar_day(text, *, now, zone):
    """Deletion alone uses a full local calendar day with an exclusive end."""
    tz=ZoneInfo(zone)
    today=datetime.fromtimestamp(now,tz).date()
    if text in ('今天','昨天','前天'):
        selected=today-timedelta(days={'今天':0,'昨天':1,'前天':2}[text])
    else:
        match=re.fullmatch(r'(\\d{4})[-年](\\d{1,2})[-月](\\d{1,2})日?',text)
        if match is None:raise ValueError('Explicit single day required')
        selected=date(*map(int,match.groups()))
    start=datetime.combine(selected,day_time.min,tzinfo=tz)
    end=datetime.combine(selected+timedelta(days=1),day_time.min,tzinfo=tz)
    return dict(start=start.timestamp(),end=end.timestamp())


class DeletePreviewExpired(ValueError):
    pass


'''

CLOSURE='''        pending=list(ids)
        while pending:
            if len(ids)>512:
                raise DeletePreviewTooLarge('Dependent source limit exceeded')
            source=pending.pop()
            # Fact values have explicit memory_command co-sources in the SAME
            # fact version. Forgetting the root must erase these derived value
            # bodies too, without selecting another verbatim user co-source.
            related=[row[0] for row in db.execute(
                "SELECT DISTINCT sibling.event_id FROM bm_fact_sources origin "
                "JOIN bm_fact_sources sibling ON sibling.scope_kind=origin.scope_kind "
                "AND sibling.scope_id=origin.scope_id AND sibling.fact_key=origin.fact_key "
                "AND sibling.revision=origin.revision JOIN bm_events value "
                "ON value.event_id=sibling.event_id WHERE origin.event_id=? "
                "AND origin.scope_kind=? AND origin.scope_id=? AND value.source='memory_command'",
                (source,)+owner)]
            related.extend(row[0] for row in db.execute(
                'SELECT event_id FROM bm_event_dependencies WHERE source_event_id=?',(source,)))
            for event_id in related:
                if event_id not in ids:
                    ids.add(event_id);pending.append(event_id)
'''

CONFIRM='''    def _check_delete_live(self, scope, validate_live):
        # The real paired callback reads jobs._current without taking jobs or
        # controller locks. ProfileAccess.use is ALREADY held before SQLite.
        # Recheck grant expiry through the original checker, with no new lock.
        validate_live()
        if scope.get('kind')=='profile':
            self.store.profile_access._check(scope.get('grant'))

    def _confirm(self, scope, *, start, end, fingerprint, operation_id, operation_turn_id,
                 preview_turn_id, validate_live):
        if not callable(validate_live):
            raise TypeError('Original request-local deletion guard required')
        notify=getattr(self.store,'notify_history_delete_committed',None)
        if self.store.data_origin=='board' and not callable(notify):
            from board.runtime.audio.board_dialogue_jobs import BoardCapabilityNotReady
            raise BoardCapabilityNotReady('history_delete_presentation')
        payload_hash=self._digest([start,end,fingerprint,operation_turn_id,preview_turn_id])
        try:
            with self.store._scope(scope) as owner, self.store._db(True) as db:
                # A cached original receipt performs no new delete or display
                # notification. Original live scope authorization still applies.
                old=self.store._operation(db,operation_id,'transcript_delete',owner,payload_hash)
                if old is not None:return old
                self._check_delete_live(scope,validate_live)  # AFTER BEGIN acquired.
                self.store._operation_turn(db,owner,operation_turn_id)
                preview=db.execute('SELECT scope_kind,scope_id,status FROM bm_turns WHERE turn_id=?',(preview_turn_id,)).fetchone()
                if preview is None or tuple(preview[:2])!=owner or preview['status']!='played':
                    return dict(status='preview_not_played',source_events=0)
                try:selected=self._selection(db,owner,start,end)
                except DeletePreviewTooLarge:return dict(status='selection_changed',source_events=0)
                self._check_delete_live(scope,validate_live)
                if selected['fingerprint']!=fingerprint or not selected['source_ids']:
                    return dict(status='selection_changed',source_events=0)
                self.store._invalidate(db,owner,set(selected['delete_event_ids']),'forgotten',erase_fact_values=True)
                self.store._revoke_pending(db,owner,operation_turn_id)
                result=dict(status='deleted',source_events=selected['source_events'],operation_id=operation_id)
                self.store._save_operation(db,operation_id,'transcript_delete',owner,payload_hash,result)
                self.store._operation_turn(db,owner,operation_turn_id)
                # No early receipt/commit: expiration, cancel, deadline or
                # supersession here raises and rolls back ALL preceding writes.
                self._check_delete_live(scope,validate_live)
        except DeletePreviewExpired:
            return dict(status='preview_expired',source_events=0)
        # Both original SQLite and ProfileAccess contexts have now EXITED.
        # The production hook can safely resolve confirmation ownership, then
        # take presentation->bridge locks. No new authority or audio owner.
        if callable(notify):notify(operation_turn_id=operation_turn_id)
        return result

'''


def history_source():
    path=H/'candidate_m03/after/board/runtime/history_delete.py'
    raw=path.read_bytes();assert sha(raw)=='26015f4cec1077ab3a888116eb1e3f7c592f352cc506e3350fb17b8b06695026'
    source=raw.decode().replace('\r\n','\n')
    source=source.replace('Board-local explicit history deletion and existing-model reasoning admission.',
        'Board-local single-day deletion with original scope and full-ACK guards.')
    source=once(source,'import threading\n','import threading\nfrom datetime import datetime, date, time as day_time, timedelta\nfrom zoneinfo import ZoneInfo, ZoneInfoNotFoundError\n')
    source=source.replace('from common.timeline import query\n','')
    source=once(source,'class DeletePreviewTooLarge(ValueError):',DAY_RANGE+'class DeletePreviewTooLarge(ValueError):')
    source=once(source,'recorded_utc<=?','recorded_utc<?')
    source=once(source,"return dict(source_ids=[],source_events=0,fingerprint=self._digest([]))",
        "return dict(source_ids=[],delete_event_ids=[],source_events=0,fingerprint=self._digest([]))")
    a=source.index('        pending=list(ids)');b=source.index('        events=[];summaries={};facts={};edges=[]',a)
    source=source[:a]+CLOSURE+source[b:]
    source=once(source,"return dict(source_ids=sorted(row['event_id'] for row in roots),source_events=len(roots),fingerprint=fingerprint)",
        "return dict(source_ids=sorted(row['event_id'] for row in roots),delete_event_ids=sorted(ids),source_events=len(roots),fingerprint=fingerprint)")
    a=source.index('    def _confirm(');b=source.index('    def __call__(',a)
    source=source[:a]+CONFIRM+source[b:]
    source=once(source,'        def current():\n', '        def live_request():\n')
    source=once(source,'            self.store.check_scope(job.scope)\n        current()',
        '        def current():\n            live_request()\n            self.store.check_scope(job.scope)\n        current()')
    old="""                    selected = query(command['date'], now=self.timeline.event_time(), zone=self.zone)
                    if selected['error'] or selected['start'] is None or not selected['explicit_range']:
                        return SourcedBoardReply('日期范围无效，请明确单日；本轮没有删除。')"""
    new="""                    try:
                        selected = calendar_day(command['date'], now=self.timeline.event_time(), zone=self.zone)
                    except (ValueError, OverflowError, ZoneInfoNotFoundError):
                        return SourcedBoardReply('日期范围无效，请明确单日；本轮没有删除。')"""
    source=once(source,old,new)
    source=once(source,"                result = self._confirm(job.scope, start=pending['start'], end=pending['end'],",
        "                def validate_live():\n                    live_request()\n                    if self.clock() >= pending['until']:\n                        raise DeletePreviewExpired('Original deletion preview expired')\n                result = self._confirm(job.scope, start=pending['start'], end=pending['end'],")
    source=once(source,"operation_turn_id=job.meta['request_id'], preview_turn_id=pending['preview_turn_id'])",
        "operation_turn_id=job.meta['request_id'], preview_turn_id=pending['preview_turn_id'], validate_live=validate_live)")
    source=once(source,"                if result['status'] == 'preview_not_played':",
        "                if result['status'] == 'preview_expired':\n                    return SourcedBoardReply('删除预览已过期，没有删除，请重新预览。')\n                if result['status'] == 'preview_not_played':")
    return source


def main():
    mapping=json.loads(V18.read_bytes())
    assert mapping['startup_sha256']=='12a26c81167ecee7293d0d9be77ec7834894d413f07bab6d8a27e4c8cdfe0392'
    assert mapping['source_manifest_sha256']=='f694dd48a7bcf2cf4fcbfaf8453e421038b5251d209c75490021d03e2f7e373a'
    assert len(mapping['component_pins'])==379
    edits={}
    rel='board/runtime/board_business.py';raw=(BASE/rel).read_bytes()
    assert sha(raw)==mapping['component_pins'][rel]
    text=raw.decode().replace('\r\n','\n')
    edits[rel]=(raw,once(text,'        handlers = dict(extra_handlers or {})',
        "        handlers = dict(extra_handlers or {})\n        from board.runtime.history_delete import LocalHistoryDelete\n        handlers.setdefault('history_delete_preview', LocalHistoryDelete(self.store, self.timeline, clock=clock, zone=config.timezone))"))
    rel='tools/production_memory_presentation.py';raw=(BASE/rel).read_bytes()
    assert sha(raw)==mapping['component_pins'][rel]
    text=raw.decode().replace('\r\n','\n')
    text=once(text,'        setattr(store, name, after_commit)\n    return lifecycle',
        '''        setattr(store, name, after_commit)
    def history_delete_committed(*, operation_turn_id):
        # The deletion adapter calls this ONLY after its SQLite transaction and
        # original grant context exit, exactly like the existing public hooks.
        confirmed = committed_command_owner(operation_turn_id)
        lifecycle.invalidate(confirmed)
    store.notify_history_delete_committed = history_delete_committed
    return lifecycle''')
    edits[rel]=(raw,text)
    edits['board/runtime/history_delete.py']=(None,history_source())
    files={}
    for relative,(before,after) in edits.items():
        ast.parse(after,feature_version=(3,9))
        path=D/'after'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(after.encode('utf-8'))
        if before is not None:
            old=D/'before'/relative;old.parent.mkdir(parents=True,exist_ok=True);old.write_bytes(before)
        prior=before.decode().replace('\r\n','\n') if before else ''
        patch=D/(Path(relative).name+'.patch')
        patch.write_bytes(''.join(difflib.unified_diff(prior.splitlines(True),after.splitlines(True),
            fromfile='before/'+relative,tofile='after/'+relative)).encode('utf-8'))
        files[relative]=dict(before_sha256=sha(before) if before is not None else None,
            sha256=sha(path.read_bytes()),bytes=path.stat().st_size,source=str(path))
    refs=[H/'review_m03_win_inference/test_delete_boundaries.py',H/'review_m03_win_inference/PUBLIC_COUNTEREXAMPLES.json',
          H/'candidate_m03/SOURCE_MANIFEST.json',H/'candidate_m03/after/board/runtime/board_business.py',
          H/'candidate_m03/after/board/runtime/history_delete.py']
    snapshots={}
    for path in refs:
        target=D/'frozen_before_review'/path.relative_to(H)
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert target.read_bytes()==path.read_bytes()
        else:target.write_bytes(path.read_bytes())
        snapshots[str(path.relative_to(H)).replace('\\','/')]=sha(path.read_bytes())
    value=dict(schema='aura.m03-r2.source-candidate.v1',status='CANDIDATE_PREPARED_NOT_DEPLOYED_TESTS_PENDING',
        baseline_startup_sha256=mapping['startup_sha256'],baseline_source_manifest_sha256=mapping['source_manifest_sha256'],
        baseline_mapping_sha256=sha(V18.read_bytes()),files=files,
        original_counterexamples_and_candidate_frozen=snapshots,actual_written_bytes_hashed=True,
        destructive_day_range='timezone calendar [midnight,next_midnight); no preview-now cap',
        postcommit='dedicated production presentation hook after SQLite and ProfileAccess exit; new successful commit only',
        original_store_schema_model_budget_or_profile_authority_changed=False)
    (D/'SOURCE_MANIFEST.json').write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({p:row['sha256'] for p,row in files.items()},ensure_ascii=False))


if __name__=='__main__':main()
