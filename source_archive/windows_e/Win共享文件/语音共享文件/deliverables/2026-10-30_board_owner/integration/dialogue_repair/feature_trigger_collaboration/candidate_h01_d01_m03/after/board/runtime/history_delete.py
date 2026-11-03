"""Board-local explicit history deletion and existing-model reasoning admission.

Construction starts no IO/model/device. Preview receipts live only in this
process for 60 monotonic seconds and require the same original actor/grant.
The Store reselects under one write transaction before forgetting anything.
No model text can confirm a delete or manufacture a ProfileAccess grant.
"""
import re
import hashlib
import json
import threading

from board.runtime.board_dialogue import SourcedBoardReply, StaleGeneration
from common.timeline import query


MANAGEMENT_TOPIC = '记录管理'


def deletion_intent(text):
    if not isinstance(text, str) or not 1 <= len(text) <= 200:
        return None
    value = re.sub(r'[。！!？?]+$', '', text.strip())
    value = re.sub(r'^(?:请(?:你)?|麻烦你)?(?:帮我)?', '', value).strip()
    if re.search(r'不要|不用|不必|无需|别|如果|假如|假设|他说|她说|[“”「」『』"\n\x00]', value):
        return None
    if value in ('确认删除', '确认删除记录', '确认删除历史', '确认删除时间轴', '确认删除对话记录', '确认删除这些对话记录'):
        return {'op': 'confirm'}
    if value in ('取消删除', '取消删除记录', '取消删除历史', '取消删除时间轴', '取消删除对话记录', '取消删除这些对话记录'):
        return {'op': 'cancel'}
    match = re.fullmatch(r'(?:删除|清除)(?:(本次对话|当前对话|个人|我的长期)(?:中|里)?)?'
        r'(今天|昨天|前天|\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)(?:的)?(?:对话|聊天)?(?:记录|历史|时间轴)', value)
    if match:
        return dict(op='preview', scope='profile' if match[1] in ('个人', '我的长期') else 'conversation', date=match[2])
    return None


class DeletePreviewTooLarge(ValueError):
    pass


class LocalHistoryDelete:
    def __init__(self, store, timeline, *, clock, zone='America/Los_Angeles'):
        if store.clock != timeline.event_time or getattr(timeline, 'monotonic', clock) is not clock:
            raise ValueError('Original board Store and exact timeline are required')
        self.store, self.timeline, self.clock, self.zone = store, timeline, clock, zone
        self.lock, self.pending = threading.RLock(), {}

    @staticmethod
    def _digest(value):
        return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
            separators=(',', ':')).encode('utf-8')).hexdigest()

    def _selection(self, db, owner, start, end):
        # Transcript sources only. Camera/device records have a separate owner;
        # management commands cannot select themselves or the preview response.
        roots = db.execute("SELECT event_id,turn_id,recorded_utc FROM bm_events WHERE "
            "scope_kind=? AND scope_id=? AND source='user_said' AND state='valid' "
            "AND closed_utc IS NOT NULL AND recorded_utc>=? AND recorded_utc<=? "
            "AND topic!=? ORDER BY event_id LIMIT 257", owner+(start,end,MANAGEMENT_TOPIC)).fetchall()
        if len(roots)>256:
            raise DeletePreviewTooLarge('Source limit exceeded')
        if not roots:
            return dict(source_ids=[],source_events=0,fingerprint=self._digest([]))
        ids={row['event_id'] for row in roots}
        # Match the ORIGINAL Store._invalidate closure; do not implement a
        # second deletion policy. The original invalidator is the sole writer.
        for turn in {row['turn_id'] for row in roots}-{None}:
            ids.update(row[0] for row in db.execute('SELECT event_id FROM bm_events WHERE turn_id=?',(turn,)))
        earliest=min(row['recorded_utc'] for row in roots)
        ids.update(row[0] for row in db.execute("SELECT event_id FROM bm_events WHERE scope_kind=? "
            "AND scope_id=? AND recorded_utc>=? AND source IN ('assistant_reply','assistant_played') "
            "AND provenance_complete=0",owner+(earliest,)))
        pending=list(ids)
        while pending:
            if len(ids)>512:
                raise DeletePreviewTooLarge('Dependent source limit exceeded')
            source=pending.pop()
            for row in db.execute('SELECT event_id FROM bm_event_dependencies WHERE source_event_id=?',(source,)):
                if row[0] not in ids:
                    ids.add(row[0]);pending.append(row[0])
        events=[];summaries={};facts={};edges=[]
        for event_id in sorted(ids):
            event=db.execute("SELECT e.event_id,e.scope_kind,e.scope_id,e.revision,e.state,e.body_hash,"
                "e.compacted_summary_id,b.event_id IS NOT NULL AS body_present FROM bm_events e "
                "LEFT JOIN bm_bodies b USING(event_id) WHERE e.event_id=?",(event_id,)).fetchone()
            if event is None or tuple(event[1:3])!=owner:
                raise PermissionError('Dependency escaped the original memory scope')
            events.append(tuple(event))
            edges.extend(tuple(row) for row in db.execute('SELECT event_id,source_event_id FROM bm_event_dependencies WHERE event_id=? ORDER BY source_event_id',(event_id,)))
            for row in db.execute('SELECT s.* FROM bm_summaries s JOIN bm_summary_sources ss USING(summary_id) WHERE ss.event_id=?',(event_id,)):
                summaries[row['summary_id']]=dict(row)
            for row in db.execute('SELECT f.* FROM bm_facts f JOIN bm_fact_sources fs USING(scope_kind,scope_id,fact_key,revision) WHERE fs.event_id=?',(event_id,)):
                key=(row['scope_kind'],row['scope_id'],row['fact_key'],row['revision'])
                facts[key]=dict(row)
        fingerprint=self._digest([events,edges,[summaries[key] for key in sorted(summaries)],
                                  [facts[key] for key in sorted(facts)]])
        return dict(source_ids=sorted(row['event_id'] for row in roots),source_events=len(roots),fingerprint=fingerprint)

    def _preview(self, scope, *, start, end, operation_turn_id):
        with self.store._scope(scope) as owner, self.store._db() as db:
            self.store._operation_turn(db,owner,operation_turn_id)
            return self._selection(db,owner,start,end)

    def _confirm(self, scope, *, start, end, fingerprint, operation_id, operation_turn_id, preview_turn_id):
        payload_hash=self._digest([start,end,fingerprint,operation_turn_id,preview_turn_id])
        # Scope/grant stays held across reselect, original invalidation and
        # idempotency receipt commit; no TOCTOU separate Store.forget call.
        with self.store._scope(scope) as owner, self.store._db(True) as db:
            old=self.store._operation(db,operation_id,'transcript_delete',owner,payload_hash)
            if old is not None:
                return old
            self.store._operation_turn(db,owner,operation_turn_id)
            preview=db.execute('SELECT scope_kind,scope_id,status FROM bm_turns WHERE turn_id=?',(preview_turn_id,)).fetchone()
            if preview is None or tuple(preview[:2])!=owner or preview['status']!='played':
                return dict(status='preview_not_played',source_events=0)
            try:
                selected=self._selection(db,owner,start,end)
            except DeletePreviewTooLarge:
                return dict(status='selection_changed',source_events=0)
            if selected['fingerprint']!=fingerprint or not selected['source_ids']:
                return dict(status='selection_changed',source_events=0)
            self.store._invalidate(db,owner,set(selected['source_ids']),'forgotten',erase_fact_values=True)
            self.store._revoke_pending(db,owner,operation_turn_id)
            result=dict(status='deleted',source_events=selected['source_events'],operation_id=operation_id)
            self.store._save_operation(db,operation_id,'transcript_delete',owner,payload_hash,result)
            return result

    def __call__(self, text, *, job, controller, is_current, cancel_event):
        def current():
            if not is_current() or cancel_event.is_set():
                raise StaleGeneration('History command no longer owns its input')
            if self.clock() >= job.deadline:
                raise TimeoutError('Original history command deadline expired')
            self.store.check_scope(job.scope)
        current()
        command = deletion_intent(text)
        actor = (job.meta['board_boot_id'], job.meta['session_id'], job.scope.get('kind'), job.scope.get('id'))
        grant = job.scope.get('grant')
        def reply():
            current()
            with self.lock:
                # Invalid, negated, quoted or unsupported date syntax cannot
                # retain a previous actionable preview for a later confirm.
                if command is None:
                    self.pending.pop(actor, None)
                    return SourcedBoardReply('请明确单日和范围，如“删除昨天的对话记录”，确认前不会删除。')
                op = command['op']
                if op == 'cancel':
                    self.pending.pop(actor, None)
                    return SourcedBoardReply('已取消本轮待确认的记录删除。')
                if op == 'preview':
                    self.pending.pop(actor, None)
                    if command['scope'] != job.scope.get('kind') or command['scope'] not in ('conversation', 'profile'):
                        return SourcedBoardReply('请先选择并授权所需记忆范围，再预览删除。')
                    selected = query(command['date'], now=self.timeline.event_time(), zone=self.zone)
                    if selected['error'] or selected['start'] is None or not selected['explicit_range']:
                        return SourcedBoardReply('日期范围无效，请明确单日；本轮没有删除。')
                    try:
                        snapshot = self._preview(job.scope, start=selected['start'], end=selected['end'],
                            operation_turn_id=job.meta['request_id'])
                    except DeletePreviewTooLarge:
                        return SourcedBoardReply('所选范围超出本次预览限量，本轮没有删除。')
                    if not snapshot['source_events']:
                        return SourcedBoardReply('所选日期没有可删除的对话来源；本轮没有删除。')
                    now = self.clock()
                    self.pending = {key:value for key,value in self.pending.items() if now < value['until']}
                    if len(self.pending) >= 32:
                        self.pending.pop(next(iter(self.pending)))
                    self.pending[actor] = dict(start=selected['start'], end=selected['end'],
                        fingerprint=snapshot['fingerprint'], generation=job.meta['generation'],
                        preview_turn_id=job.meta['request_id'],
                        grant=grant, until=now+60.)
                    return SourcedBoardReply('本范围拟删除%d条对话来源及关联记忆。请说“确认删除记录”或“取消删除记录”。' % snapshot['source_events'])
                pending = self.pending.pop(actor, None)
                if (pending is None or self.clock() >= pending['until'] or pending['grant'] is not grant
                        or job.meta['generation'] <= pending['generation']):
                    return SourcedBoardReply('没有同一会话内有效的删除预览，请重新说明日期。')
                current()
                result = self._confirm(job.scope, start=pending['start'], end=pending['end'],
                    fingerprint=pending['fingerprint'], operation_id='history-delete:'+job.meta['request_id'],
                    operation_turn_id=job.meta['request_id'], preview_turn_id=pending['preview_turn_id'])
                current()
                if result['status'] == 'preview_not_played':
                    return SourcedBoardReply('上一轮预览未完成完整播放确认，没有删除，请重新预览。')
                if result['status'] != 'deleted':
                    return SourcedBoardReply('预览后的来源或关联记忆已变化，没有删除，请重新预览。')
                return SourcedBoardReply('已按预览删除本范围%d条对话来源，并使关联记忆失效。' % result['source_events'])
        budget = int((job.deadline-self.clock())*1000)
        if budget < 1:
            raise TimeoutError('Original history command deadline expired')
        return controller.prepare_local_reply(text, reply, scope=job.scope, session_id=job.meta['session_id'],
            generation=job.meta['generation'], budget_ms=budget, turn_id=job.meta['request_id'],
            cancel_event=cancel_event, topic=MANAGEMENT_TOPIC)
