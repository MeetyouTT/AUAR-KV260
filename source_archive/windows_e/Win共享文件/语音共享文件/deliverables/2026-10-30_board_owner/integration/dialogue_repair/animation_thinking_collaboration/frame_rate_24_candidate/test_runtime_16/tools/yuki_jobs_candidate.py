"""Instance-bound copies of exactly two pinned methods.
Only pair guards/address policy differ; core queues/ACK/PCM remain original.
"""
import re
from board.runtime.audio.board_dialogue_jobs import BoardCapabilityNotReady
from tools.yuki_business_candidate import LocalRecordText, LocalRecordController

def _admit_text(self, job, raw_text):
    from common.handsfree_entry import audio_candidate, acceptable_entry
    self.character_pair.require_ready()
    prepare_spoken_input = self.character_pair.speech.prepare
    wake_request = self.character_pair.speech.wake_request
    if not isinstance(raw_text, str) or not raw_text.strip() or len(raw_text) > 4096:
        raise ValueError('No bounded board ASR text')
    if any(ord(c) < 32 for c in raw_text):
        raise ValueError('ASR text cannot enter the stream protocol')
    text = raw_text.strip()
    interpreted = prepare_spoken_input(text)
    if job.entry:
        if not audio_candidate(job.pcm):
            raise self._entry_error()
        if job.entry == 'wake':
            text = wake_request(interpreted['text'])
            if text is None:
                raise self._entry_error()
            if not text:
                return None
        else:
            if self.visual_entry_handler is None:
                raise BoardCapabilityNotReady('visual_entry_authorization')
            accepted = self.visual_entry_handler(job.meta, job.capture_snapshot, text,
                                                is_current=lambda: self._current(job))
            if accepted is not True or not acceptable_entry(text):
                raise self._entry_error()
    # Preserve raw ASR for ordinary turns. A production context builder may
    # apply conservative vocative interpretation only to model input.
    return text


def _route(self, job, text, *, reply_sink=None):
    from common.voice_enrollment import (
        enrollment_requested, identity_query_requested, cancelled, confirmed, update_confirmed,
    )
    from common.binding_intent import binding_intent
    from common.thinking_policy import route
    from common.timeline import recall_requested, query
    from common.profile_memory import scoped_command
    from common.visual_question import requested as visual_requested
    self.character_pair.require_ready()
    if self.character_pair.speech.legacy_vocative(text):
        return None, None
    request_text = LocalRecordText.capture(job, text, self.character_pair.speech)
    text = request_text.intent_text
    prepare_spoken_input = self.character_pair.speech.prepare
    CHARACTER_NAME = self.character_pair.identity.display_name
    intent_text = prepare_spoken_input(text)['text']
    visual_requested_by_policy = bool(self.visual_intent_matcher is not None and
                                      self.visual_intent_matcher(intent_text))
    binding = binding_intent(intent_text)
    command_text = re.sub(r'^\s*' + re.escape(CHARACTER_NAME) + r'[\s，,：:]*', '', intent_text, count=1)
    command, _ = scoped_command(command_text, job.scope.get('kind') == 'profile')
    if command is not None and binding['kind'] not in ('remember_self', 'name_hint', 'invalid_name'):
        if self.controller.command_handler is None:
            raise BoardCapabilityNotReady('explicit_memory_commands')
        return None, None
    recalled = recall_requested(text)
    capability = None
    if (self._enrollment_state().get('active') or enrollment_requested(text)
            or cancelled(text) or confirmed(text) or update_confirmed(text)
            or binding['kind'] in ('remember_self', 'name_hint', 'invalid_name')):
        capability = 'identity_enrollment'
    elif identity_query_requested(text):
        capability = 'identity_query'
    elif re.search(r'(?:登记|注册|标定|识别|绑定|关联).{0,8}(?:声纹|声音)|(?:声纹|声音).{0,8}(?:登记|注册|标定|绑定|关联)', text):
        capability = 'speaker_identity'
    elif (re.search(r'(?:删除|清除|清理).{0,12}(?:昨天|前天|历史|时间轴|记录)', text)
          or re.fullmatch(r'(?:确认|取消)(?:删除|清除)(?:记录|历史|时间轴)?[。！!？?]*', text)):
        capability = 'history_delete_preview'
    elif visual_requested_by_policy or not recalled and visual_requested(text):
        capability = 'structured_visual_query'
    elif route(text)['mode'] == 'reasoning':
        capability = 'reasoning_dialogue'
    if capability:
        handler = self.special_handlers.get(capability)
        if handler is None:
            raise BoardCapabilityNotReady(capability)
        self._check(job)
        kwargs = dict(job=job, controller=LocalRecordController(self.controller, request_text),
                      is_current=lambda: self._current(job), cancel_event=job.cancelled)
        if getattr(handler, 'streaming_reply', False):
            kwargs['reply_sink'] = reply_sink
        return handler(text, **kwargs), None
    if self.history_router is not None:
        return None, self.history_router(text, scope=dict(job.scope),
                                         now=self.wall_clock() if self.wall_clock else None)
    if recalled:
        if self.wall_clock is None:
            raise BoardCapabilityNotReady('trusted_history_clock')
        selected = query(text, now=self.wall_clock(), zone=self.timezone)
        if selected.get('error'):
            raise BoardCapabilityNotReady('explicit_history_range')
        # Topic is an exact partition; search is the distinct pre-LIMIT
        # text/keyword filter. Keep the user's explicit subject in recall.
        return None, dict(start=selected['start'], end=selected['end'],
                          search=selected['topic'] or None, limit=20)
    return None, None

