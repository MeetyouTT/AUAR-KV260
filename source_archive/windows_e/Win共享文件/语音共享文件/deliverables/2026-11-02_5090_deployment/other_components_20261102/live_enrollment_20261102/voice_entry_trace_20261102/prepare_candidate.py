"""Local-only fixed metadata candidate; never executes production code."""
import difflib,hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'split_commands_20261102/actual_release/runtime'
EXPECTED={'board/runtime/audio/board_dialogue_jobs.py':'43708b7fcbf72b11d7a37b01ae090c2cdb3e621b5f334151601206735a34a1fc',
 'board/runtime/board_business.py':'ea4f4565f558e5e2b6a347360f362e7810dd5792b2d2fe7af3a26389e26514d7'}

JOBS_HELPERS='''def _entry_parser_flags(parser):
    # Only fixed code-constant membership is exposed, never code paths/text.
    code = getattr(parser, '__code__', None)
    constants = getattr(code, 'co_consts', ())
    pending = list(constants[:128]) if type(constants) is tuple else []
    face = voice = False
    for _ in range(256):
        if not pending:break
        value = pending.pop()
        if type(value) is str:
            face = face or value == 'face_only'
            voice = voice or value == 'voice_only'
        elif type(value) in (tuple, frozenset):
            pending.extend(list(value)[:128])
    return dict(parser_code_known=code is not None,parser_face_only_const=face, parser_voice_only_const=voice)


def _entry_route_trace():
    return dict(version=1,asr_characters=0,asr_result_seen=False,binding_kind='not_evaluated',
        speaker_requested=False,enrollment_checked=False,enrollment_active=False,
        capability='not_selected',handler_available=False,handler_called=False,
        handler_result='not_called',error_class='none',outcome='started',
        parser_code_known=False,parser_face_only_const=False,parser_voice_only_const=False,
        has_register=False,has_voiceprint=False,has_voice=False,has_warming=False,
        has_face=False,has_my_name=False,has_level=False,has_i_want=False,has_i_would_like=False,
        has_a_bit=False,has_voice_word=False,has_identity=False,has_name_word=False)


def _entry_asr_trace(trace, raw):
    if not isinstance(raw,str):return
    trace.update(asr_characters=min(len(raw),4097),asr_result_seen=True,
        has_register='登记' in raw,has_voiceprint='声纹' in raw,has_voice='声音' in raw,
        has_warming='升温' in raw,has_face='人脸' in raw,has_my_name='我叫' in raw,has_level='等级' in raw,
        has_i_want='我要' in raw,has_i_would_like='我想' in raw,has_a_bit='一下' in raw,
        has_voice_word='声文' in raw,has_identity='身份' in raw,has_name_word='名字' in raw)


'''

JOBS_METHODS='''    def _publish_entry_route_trace(self, job, trace):
        with self.condition:
            last = self.last_voice_route
            if isinstance(last,dict) and last.get('generation') == job.meta['generation']:
                last['entry_trace'] = copy.deepcopy(trace)

'''

BUSINESS_METHOD='''    def _entry_speaker_presence(self, meta):
        # Observe only original RAM membership/expiry. Do not invoke state(),
        # which can expire and remove a session, or read any gallery/store.
        speaker = getattr(getattr(self.business, 'hub', None), 'speaker', None)
        sessions = getattr(speaker, 'sessions', None)
        if type(sessions) is not dict:return dict(known=False,present=False,active=False)
        row = sessions.get((meta['board_boot_id'],meta['session_id']))
        if type(row) is not dict:return dict(known=True,present=False,active=False)
        until = row.get('until')
        return dict(known=True,present=True,
            active=bool(type(until) in (int,float) and self.clock() < until))

'''

CALL_TRACE='''        trace = dict(version=1,observed=True,input_mode='none',resolved_mode='none',binding_kind='not_evaluated',
            parser_code_known=False,parser_face_only_const=False,parser_voice_only_const=False,face_active_before=False,face_active_after=False,
            speaker_state_known=False,speaker_present_before=False,speaker_active_before=False,
            speaker_present_after=False,speaker_active_after=False,business_turn_calls=0,
            business_turn_result='not_called',error_class='none',phase='entered',reset_since_trace=False)
        entry_before = getattr(self,'_standalone_entry',None)
        if entry_before is not None and entry_before.get('mode') in ('face','voice'):
            trace['input_mode'] = entry_before['mode']
        trace.update(_entry_parser_flags(binding_intent))
        trace['face_active_before'] = bool(self.flow.public()['active'])
        before = self._entry_speaker_presence(job.meta)
        trace.update(speaker_state_known=before['known'],speaker_present_before=before['present'],
                     speaker_active_before=before['active'])
        self._entry_trace = trace  # A new object prevents an older turn overwriting the next trace.
        def traced_business_turn(*args,**kwargs):
            trace['business_turn_calls'] = min(8,trace['business_turn_calls']+1)
            trace['business_turn_result'] = 'calling'
            trace['phase'] = 'business_turn'
            try:
                value = self.business.turn(*args,**kwargs)
            except BaseException as exc:
                trace['business_turn_result'] = 'error'
                trace['error_class'] = BoardDialogueJobs._diagnostic_error_class(exc)
                raise
            else:
                trace['business_turn_result'] = 'none' if value is None else 'reply'
                return value
            finally:
                after = self._entry_speaker_presence(job.meta)
                trace.update(speaker_state_known=after['known'],speaker_present_after=after['present'],
                             speaker_active_after=after['active'])
'''

def replace(text,old,new,count=1):
    assert text.count(old)==count,(old[:100],text.count(old),count)
    return text.replace(old,new)

diff=[];manifest={}
for name,expected in EXPECTED.items():
 raw=(BASE/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
 text=raw.decode('utf-8')
 if name.endswith('board_dialogue_jobs.py'):
  text=replace(text,'class BoardCapabilityNotReady(RuntimeError):',JOBS_HELPERS+'class BoardCapabilityNotReady(RuntimeError):')
  text=replace(text,'    def _route(self, job, text, *, reply_sink=None):',JOBS_METHODS+'    def _route(self, job, text, *, reply_sink=None):')
  text=replace(text,"        intent_text = prepare_spoken_input(text)['text']\n",'''        trace = getattr(job,'entry_route_trace',None)
        if trace is None:
            trace = _entry_route_trace();_entry_asr_trace(trace,text);job.entry_route_trace = trace
        trace.update(_entry_parser_flags(binding_intent))
        def enrollment_active():
            active = self._enrollment_state().get('active')
            trace.update(enrollment_checked=True,enrollment_active=bool(active))
            return active
        intent_text = prepare_spoken_input(text)['text']
''')
  text=replace(text,'        speaker_requested_by_policy = speaker_requested(intent_text)\n', '''        speaker_requested_by_policy = speaker_requested(intent_text)
        kind = binding.get('kind')
        trace.update(binding_kind=kind if type(kind) is str and kind in
            ('ordinary','remember_self','name_hint','invalid_name','face_only','voice_only') else 'other',
            speaker_requested=bool(speaker_requested_by_policy))
        self._publish_entry_route_trace(job,trace)
''')
  text=replace(text,"            if self.controller.command_handler is None:\n                raise BoardCapabilityNotReady('explicit_memory_commands')", "            trace['capability'] = 'explicit_memory_commands'\n            self._publish_entry_route_trace(job,trace)\n            if self.controller.command_handler is None:\n                raise BoardCapabilityNotReady('explicit_memory_commands')")
  text=replace(text,"elif (self._enrollment_state().get('active') or enrollment_requested(text)","elif (enrollment_active() or enrollment_requested(text)")
  text=replace(text,'        if capability:\n            handler = self.special_handlers.get(capability)\n', '''        trace['capability'] = capability or 'ordinary_dialogue'
        self._publish_entry_route_trace(job,trace)
        if capability:
            handler = self.special_handlers.get(capability)
            trace['handler_available'] = handler is not None
            self._publish_entry_route_trace(job,trace)
''')
  text=replace(text,'            return handler(text, **kwargs), None\n', '''            trace['handler_called'] = True
            trace['handler_result'] = 'calling'
            self._publish_entry_route_trace(job,trace)
            try:
                value = handler(text, **kwargs)
            except BaseException as exc:
                trace['handler_result'] = 'error'
                trace['error_class'] = self._diagnostic_error_class(exc)
                self._publish_entry_route_trace(job,trace)
                raise
            trace['handler_result'] = 'none' if value is None else 'returned'
            self._publish_entry_route_trace(job,trace)
            return value, None
''')
  text=replace(text,'        with self.condition:\n            self.progress_diagnostics = job.diagnostics\n', '''        trace = _entry_route_trace();job.entry_route_trace = trace
        with self.condition:
            self.progress_diagnostics = job.diagnostics
            if (not self.closed and job.meta['generation']==self.generation
                    and job.meta['session_id']==self.session_id):
                self.last_voice_route = dict(generation=job.meta['generation'],transcript_characters=0,
                    board_owned=True,history_requested=False,entry_trace=copy.deepcopy(trace))
''')
  text=replace(text,"            phase['asr_ms'] = (self.clock()-stage_started)*1000\n", "            _entry_asr_trace(trace,raw)\n            self._publish_entry_route_trace(job,trace)\n            phase['asr_ms'] = (self.clock()-stage_started)*1000\n")
  text=replace(text,'                                             board_owned=True, history_requested=history is not None)\n', '                                             board_owned=True, history_requested=history is not None,\n                                             entry_trace=copy.deepcopy(trace))\n')
  text=replace(text,"            phase['entry_rejected'] = bool(getattr(exc,'entry_rejected',False))\n", "            trace.update(outcome='rejected' if getattr(exc,'entry_rejected',False) else 'error',\n                         error_class=self._diagnostic_error_class(exc))\n            phase['entry_rejected'] = bool(getattr(exc,'entry_rejected',False))\n")
  text=replace(text,"            phase['complete'] = True\n", "            phase['complete'] = True\n            trace['outcome'] = 'complete'\n")
  text=replace(text,"                phase['worker_total_ms'] = (self.clock()-job_started)*1000\n                publish()\n", "                phase['worker_total_ms'] = (self.clock()-job_started)*1000\n                self._publish_entry_route_trace(job,trace)\n                publish()\n")
 else:
  text=replace(text,'from board.runtime.audio.board_dialogue_jobs import BoardDialogueJobs, BoardCapabilityNotReady\n', 'from board.runtime.audio.board_dialogue_jobs import BoardDialogueJobs, BoardCapabilityNotReady, _entry_parser_flags\n')
  text=replace(text,'        self._standalone_epoch = 0\n', "        self._standalone_epoch = 0\n        self._entry_trace = dict(version=1,observed=False,reset_since_trace=False)\n")
  text=replace(text,'    def reset(self):\n        with self.flow.lock:\n', "    def reset(self):\n        with self.flow.lock:\n            if getattr(self,'_entry_trace',None) is not None:self._entry_trace['reset_since_trace'] = True\n")
  text=replace(text,"        state.update(entry_mode=entry['mode'] if entry else None, entry_name_pending=pending)\n", "        state.update(entry_mode=entry['mode'] if entry else None, entry_name_pending=pending,\n                     entry_trace=copy.deepcopy(getattr(self,'_entry_trace',dict(version=1,observed=False))))\n")
  text=replace(text,'    def _visual(self, job):',BUSINESS_METHOD+'    def _visual(self, job):')
  begin=text.index('    def __call__(self, text, *, job, controller, is_current, cancel_event, reply_sink=None):')
  end=text.index('\n\ndef board_entry_policy',begin)
  call=text[begin:end]
  assert call.count('self.business.turn(')==3
  call=call.replace('self.business.turn(','traced_business_turn(')
  call=replace(call,'        def current():\n',CALL_TRACE+'        def current():\n')
  call=replace(call,'                intent = binding_intent(text)\n', '''                intent = binding_intent(text)
                kind = intent.get('kind')
                trace['binding_kind'] = kind if type(kind) is str and kind in (
                    'ordinary','remember_self','name_hint','invalid_name','face_only','voice_only') else 'other'
                trace['phase'] = 'producer'
''')
  call=replace(call,"                if intent['kind'] == 'invalid_name':\n", "                trace['resolved_mode'] = entry['mode'] if entry is not None and entry.get('mode') in ('face','voice') else 'none'\n                if intent['kind'] == 'invalid_name':\n")
  call=replace(call,'            except BaseException:\n', "            except BaseException as exc:\n                trace.update(phase='error',error_class=BoardDialogueJobs._diagnostic_error_class(exc))\n")
  call=replace(call,'            finally:\n                if exchange is not None:\n', "            finally:\n                trace['face_active_after'] = bool(self.flow.public()['active'])\n                if trace['phase'] != 'error':trace['phase'] = 'finished'\n                if exchange is not None:\n")
  text=text[:begin]+call+text[end:]
 after=text.encode('utf-8');target=HERE/'candidate'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(after)
 target=HERE/'baseline'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 manifest[name]=dict(before_sha256=expected,after_sha256=hashlib.sha256(after).hexdigest(),before_bytes=len(raw),after_bytes=len(after))
 diff.extend(difflib.unified_diff(raw.decode('utf-8').splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(status='LOCAL_TRACE_CANDIDATE_NOT_DEPLOYED',files=manifest,board_accessed=False),indent=2)+'\n',encoding='utf-8')
(HERE/'CANDIDATE.diff').write_text(''.join(diff),encoding='utf-8',newline='\n')
print(json.dumps(manifest))
