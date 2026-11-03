"""Board-local explicit history deletion and existing-model reasoning admission.

Construction starts no IO/model/device. Preview receipts live only in this
process for 60 monotonic seconds and require the same original actor/grant.
The Store reselects under one write transaction before forgetting anything.
No model text can confirm a delete or manufacture a ProfileAccess grant.
"""
import re
import threading

from board.runtime.board_dialogue import SourcedBoardReply, StaleGeneration
from common.thinking_policy import route as thinking_route
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


class LocalReasoningDialogue:
    """Admit the existing controller's reasoning path without replacing it."""
    def __call__(self, text, *, job, controller, is_current, cancel_event):
        if not is_current() or cancel_event.is_set():
            raise StaleGeneration('Reasoning admission no longer owns its input')
        if controller.clock() >= job.deadline:
            raise TimeoutError('Original reasoning turn deadline expired')
        controller.store.check_scope(job.scope)
        if thinking_route(text)['mode'] != 'reasoning':
            raise ValueError('No explicit reasoning intent')
        # A None plan deliberately rejoins the original ordinary path: original
        # raw ASR recording, prepare_text, per-packet authority, TTS and full ACK.
        # BoardDialogueController adds think=True only for this existing policy.
        return None


class LocalHistoryDelete:
    def __init__(self, store, timeline, *, clock, zone='America/Los_Angeles'):
        if store.clock != timeline.event_time or timeline.monotonic is not clock:
            raise ValueError('Original board Store and exact timeline are required')
        self.store, self.timeline, self.clock, self.zone = store, timeline, clock, zone
        self.lock, self.pending = threading.RLock(), {}

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
                    snapshot = self.store.preview_transcript_delete(job.scope, start=selected['start'], end=selected['end'],
                        operation_turn_id=job.meta['request_id'])
                    if not snapshot['source_events']:
                        return SourcedBoardReply('所选日期没有可删除的对话来源；本轮没有删除。')
                    now = self.clock()
                    self.pending = {key:value for key,value in self.pending.items() if now < value['until']}
                    if len(self.pending) >= 32:
                        self.pending.pop(next(iter(self.pending)))
                    self.pending[actor] = dict(start=selected['start'], end=selected['end'],
                        fingerprint=snapshot['fingerprint'], generation=job.meta['generation'],
                        grant=grant, until=now+60.)
                    return SourcedBoardReply('本范围拟删除%d条对话来源及关联记忆。请说“确认删除记录”或“取消删除记录”。' % snapshot['source_events'])
                pending = self.pending.pop(actor, None)
                if (pending is None or self.clock() >= pending['until'] or pending['grant'] is not grant
                        or job.meta['generation'] <= pending['generation']):
                    return SourcedBoardReply('没有同一会话内有效的删除预览，请重新说明日期。')
                current()
                result = self.store.confirm_transcript_delete(job.scope, start=pending['start'], end=pending['end'],
                    fingerprint=pending['fingerprint'], operation_id='history-delete:'+job.meta['request_id'],
                    operation_turn_id=job.meta['request_id'])
                current()
                if result['status'] != 'deleted':
                    return SourcedBoardReply('预览后的来源或关联记忆已变化，没有删除，请重新预览。')
                return SourcedBoardReply('已按预览删除本范围%d条对话来源，并使关联记忆失效。' % result['source_events'])
        budget = int((job.deadline-self.clock())*1000)
        if budget < 1:
            raise TimeoutError('Original history command deadline expired')
        return controller.prepare_local_reply(text, reply, scope=job.scope, session_id=job.meta['session_id'],
            generation=job.meta['generation'], budget_ms=budget, turn_id=job.meta['request_id'],
            cancel_event=cancel_event, topic=MANAGEMENT_TOPIC)
