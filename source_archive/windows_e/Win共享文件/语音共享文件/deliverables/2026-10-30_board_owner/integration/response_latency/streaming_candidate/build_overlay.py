"""Pinned two-file ordinary TTS streaming candidate; no runtime/model calls."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'source_before'
PINS={
 'board/runtime/board_dialogue.py':'bcaef073a6bcecfe33097074f1de5e16bb121b57d0c3c8d59ec6384435ed6f30',
 'board/runtime/audio/board_dialogue_jobs.py':'8afe32d3499517ff9fbb556674136bccc29deb2cb8a5da0a9e36738a2a302010'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def once(text,before,after):
    if text.count(before)!=1:raise ValueError('Current production source anchor changed')
    return text.replace(before,after,1)

def build():
    sources={}
    for name,pin in PINS.items():
        raw=(BASE/name).read_bytes()
        if sha(raw)!=pin:raise ValueError('Current production source pin changed')
        sources[name]=raw.decode('utf-8')
    text=sources['board/runtime/board_dialogue.py']
    text=once(text,'        self.cleanup_failures = 0\n',
        '        self.cleanup_failures = 0\n        self.last_prepare_metrics = {}\n')
    text=once(text,
        '    def prepare_text(self, text, *, scope, session_id, generation, budget_ms,\n'
        '                     turn_id=None, metadata=None, history_query=None, cancel_event=None):\n',
        '    def prepare_text(self, text, *, scope, session_id, generation, budget_ms,\n'
        '                     turn_id=None, metadata=None, history_query=None, cancel_event=None, chunk_sink=None):\n')
    start=text.index('    def prepare_text(')
    end=text.index('    def prepare_local_reply(',start)
    method=text[start:end]
    method=once(method,'        turn = self._start(',
        "        if chunk_sink is not None and not callable(chunk_sink):\n"
        "            raise TypeError('An owned audio chunk sink is required')\n"
        '        turn = self._start(')
    method=once(method,'return self._prepare(text, turn, metadata, history_query)',
        'return self._prepare(text, turn, metadata, history_query, chunk_sink=chunk_sink)')
    text=text[:start]+method+text[end:]
    start=text.index('    def _prepare(')
    end=text.index('    def acknowledge(',start)
    original=text[start:end]
    signature,body=original.split('        self._check(turn)\n',1)
    signature=once(signature,"topic='', input_source='user_said', input_recorded=False):",
        "topic='', input_source='user_said', input_recorded=False, chunk_sink=None):")
    body='        self._check(turn)\n'+body
    body=once(body,'        if reply_factory is not None:\n',
        '        local_started = self.clock()\n        if reply_factory is not None:\n')
    body=once(body,'        if reply is not None:\n',
        "        metrics['local_reply_ms'] = (self.clock()-local_started)*1000\n        if reply is not None:\n")
    body=once(body,'            messages = self._messages(turn, text, history_query)\n',
        '            context_started = self.clock()\n'
        '            messages = self._messages(turn, text, history_query)\n'
        "            metrics['context_ms'] = (self.clock()-context_started)*1000\n")
    body=once(body,"self._request('llm', turn, task='dialogue', messages=messages)",
        "timed_request('llm', task='dialogue', messages=messages)")
    body=once(body,'        self._check(turn)\n        self.store.generated(',
        '        self._check(turn)\n'
        '        sentences = split_sentences(reply.text)\n'
        '        prepared_check = None\n'
        '        if chunk_sink is not None:\n'
        "            if len(reply.text)>240:\n                raise ReplyRejected('Streamed reply exceeds existing player text limit')\n"
        "            prepared_check = getattr(self.store,'check_prepared_turn_current',None)\n"
        "            if not callable(prepared_check):\n                raise RuntimeError('Prepared-turn streaming guard is unavailable')\n"
        '        self.store.generated(')
    body=once(body,'        rate = None\n        for sentence in split_sentences(reply.text):\n'
        "            result, owner = self._request('tts', turn, text=sentence)\n",
        '        rate = None\n'
        '        token = self.id_factory() if chunk_sink is not None else None\n'
        '        for sentence in sentences:\n'
        '            if prepared_check is not None:\n'
        '                self._check(turn)\n'
        '                prepared_check(turn.turn_id,generation=turn.generation)\n'
        "            result, owner = timed_request('tts', text=sentence)\n")
    body=once(body,'            digest.update(pcm)\n            chunks.append(AudioChunk(owner, sentence, pcm, current_rate))\n',
        "            if 'first_tts_ready_ms' not in metrics:\n"
        "                metrics['first_tts_ready_ms'] = (self.clock()-prepare_started)*1000\n"
        '            chunk = AudioChunk(owner, sentence, pcm, current_rate)\n'
        '            if chunk_sink is not None:\n'
        '                if current_rate!=24000 or total//2>720000:\n'
        "                    raise ReplyRejected('Streamed replies require bounded native 24kHz playback')\n"
        '                self._check(turn)\n'
        '                prepared_check(turn.turn_id,generation=turn.generation)\n'
        '                chunk_sink(chunk,reply,(total-len(pcm))//2,token)\n'
        '                self._check(turn)\n'
        "                metrics['streamed_chunks'] += 1\n"
        "                if 'first_chunk_emitted_ms' not in metrics:\n"
        "                    metrics['first_chunk_emitted_ms'] = (self.clock()-prepare_started)*1000\n"
        '            digest.update(pcm)\n'
        '            chunks.append(chunk)\n')
    body=once(body,'turn.turn_id, self.id_factory(), reply, tuple(chunks),',
        'turn.turn_id, token if chunk_sink is not None else self.id_factory(), reply, tuple(chunks),')
    body=once(body,'        return plan\n',"        metrics['complete'] = True\n        return plan\n")
    prefix='''        prepare_started = self.clock()
        metrics = dict(metadata_only=True,streaming_enabled=chunk_sink is not None,
            context_ms=0.,local_reply_ms=0.,llm_rpc_ms=0.,llm_calls=0,tts_rpc_ms=0.,
            tts_calls=0,tts_max_rpc_ms=0.,streamed_chunks=0,complete=False,
            speaker_first_audio_measured=False)
        def timed_request(kind,**fields):
            started = self.clock()
            try:
                return self._request(kind,turn,**fields)
            finally:
                elapsed = (self.clock()-started)*1000
                metrics[kind+'_rpc_ms'] += elapsed
                metrics[kind+'_calls'] += 1
                if kind=='tts':metrics['tts_max_rpc_ms'] = max(metrics['tts_max_rpc_ms'],elapsed)
                self.last_prepare_metrics = dict(metrics)
        try:
'''
    wrapped=signature+prefix+''.join('    '+line if line.strip() else line for line in body.splitlines(keepends=True))
    wrapped+='''        finally:
            metrics['prepare_total_ms'] = (self.clock()-prepare_started)*1000
            self.last_prepare_metrics = dict(metrics)

'''
    text=text[:start]+wrapped+text[end:]
    sources['board/runtime/board_dialogue.py']=text

    text=sources['board/runtime/audio/board_dialogue_jobs.py']
    text=once(text,"        self.cleanup_error = ''\n", "        self.cleanup_error = ''\n        self.latency_metrics = {}\n")
    text=once(text,
        '    def _put(self, job, value):\n'
        '        with self.condition:\n'
        '            while len(self.progress) >= 128:\n'
        '                self._check(job); self.condition.wait(.05)\n'
        '            self._check(job)\n'
        '            self.progress.append(dict(value, context=dict(job.meta)))\n'
        '            self.condition.notify_all()\n',
        '    def _put(self, job, value, *, admission_guard=None):\n'
        '        if admission_guard is None:\n'
        '            with self.condition:\n'
        '                while len(self.progress) >= 128:\n'
        '                    self._check(job); self.condition.wait(.05)\n'
        '                self._check(job)\n'
        '                self.progress.append(dict(value, context=dict(job.meta)))\n'
        '                self.condition.notify_all()\n'
        '            return\n'
        '        while True:\n'
        '            admission_guard()  # SQL check outside the jobs condition, including after every wait.\n'
        '            with self.condition:\n'
        '                self._check(job)\n'
        '                if len(self.progress)<128:\n'
        '                    self.progress.append(dict(value, context=dict(job.meta)))\n'
        '                    self.condition.notify_all()\n'
        '                    return\n'
        '                self.condition.wait(.05)\n')
    start=text.index('    def _execute(self, job):\n');end=text.index('    def run_next(self):\n',start)
    method=text[start:end]
    signature,body=method.split('\n',1)
    body=once(body,'        state = ChannelState(job.meta)\n',
        '        state = ChannelState(job.meta)\n        ordinary_requested = False\n        ordinary_guard = None\n')
    body=once(body,'        raw = self.asr.transcribe(job.pcm, sample_rate=16000, deadline=job.deadline,\n'
        '                                  cancelled=job.cancelled.is_set)\n',
        '        stage_started = self.clock()\n'
        "        phase['asr_calls'] += 1\n"
        '        raw = self.asr.transcribe(job.pcm, sample_rate=16000, deadline=job.deadline,\n'
        '                                  cancelled=job.cancelled.is_set)\n'
        "        phase['asr_ms'] = (self.clock()-stage_started)*1000\n"
        "        phase['asr_completed'] = True\n        publish()\n")
    body=once(body,'        text = self._admit_text(job, raw)\n',
        '        stage_started = self.clock()\n        text = self._admit_text(job, raw)\n'
        "        phase['admission_ms'] = (self.clock()-stage_started)*1000\n        publish()\n")
    body=once(body,'        if text is None:\n',"        if text is None:\n            phase['wake_only'] = True\n")
    body=once(body,'            self._put(job, dict(channel_event=header, pcm=pcm))\n',
        '            self._put(job, dict(channel_event=header, pcm=pcm),admission_guard=ordinary_guard)\n'
        "            if kind=='audio' and 'first_audio_queued_ms' not in phase:\n"
        "                phase['first_audio_queued_ms'] = (self.clock()-job_started)*1000\n                publish()\n")
    body=once(body,'        plan, history = self._route(job, text, reply_sink=reply_sink)\n',
        '        stage_started = self.clock()\n'
        '        plan, history = self._route(job, text, reply_sink=reply_sink)\n'
        "        phase['route_ms'] = (self.clock()-stage_started)*1000\n"
        "        phase['ordinary_prepare'] = plan is None\n        publish()\n")
    body=once(body,'        def reply_sink(chunk, reply, start_sample, token):\n',
        '        def reply_sink(chunk, reply, start_sample, token):\n'
        '            nonlocal ordinary_guard\n'
        '            if ordinary_requested and ordinary_guard is None:\n'
        "                check = getattr(self.controller.store,'check_prepared_turn_current',None)\n"
        "                if not callable(check):raise RuntimeError('Prepared-turn streaming guard is unavailable')\n"
        "                ordinary_guard = lambda:check(job.meta['request_id'],generation=job.meta['generation'])\n")
    body=once(body,'            self.analysis_provider(text, job=job, is_current=lambda: self._current(job), cancel_event=job.cancelled)\n',
        '            stage_started = self.clock()\n'
        '            self.analysis_provider(text, job=job, is_current=lambda: self._current(job), cancel_event=job.cancelled)\n'
        "            phase['analysis_enqueue_ms'] = (self.clock()-stage_started)*1000\n            publish()\n")
    body=once(body,"            plan = self.controller.prepare_text(text, scope=job.scope, session_id=job.meta['session_id'],\n",
        '            ordinary_requested = self.audio_converter is None\n'
        "            plan = self.controller.prepare_text(text, scope=job.scope, session_id=job.meta['session_id'],\n")
    body=once(body,"                         dict(evidence='statement'))\n",
        "                         dict(evidence='statement'),\n"
        '                chunk_sink=reply_sink if self.audio_converter is None else None)\n'
        "            allowed = {'metadata_only','streaming_enabled','context_ms','local_reply_ms','llm_rpc_ms',\n"
        "                'llm_calls','tts_rpc_ms','tts_calls','tts_max_rpc_ms','first_tts_ready_ms',\n"
        "                'first_chunk_emitted_ms','prepare_total_ms','streamed_chunks','complete',\n"
        "                'speaker_first_audio_measured'}\n"
        "            phase['prepare'] = {k:v for k,v in getattr(self.controller,'last_prepare_metrics',{}).items()\n"
        '                if k in allowed and (type(v) is bool or type(v) in (int,float) and math.isfinite(v) and v>=0)}\n'
        '            publish()\n')
    body=once(body,"        self._put(job, dict(network_complete=result))\n",
        "        self._put(job, dict(network_complete=result),admission_guard=ordinary_guard)\n        phase['complete'] = True\n")
    prefix='''        job_started = self.clock()
        phase = dict(metadata_only=True,speaker_first_audio_measured=False,asr_calls=0,
                     asr_completed=False,wake_only=False,entry_rejected=False,complete=False)
        def publish():
            self.latency_metrics = copy.deepcopy(phase)
        publish()
        try:
'''
    method=signature+'\n'+prefix+''.join('    '+line if line.strip() else line for line in body.splitlines(keepends=True))
    method+='''        except Exception as exc:
            phase['entry_rejected'] = bool(getattr(exc,'entry_rejected',False))
            raise
        finally:
            phase['worker_total_ms'] = (self.clock()-job_started)*1000
            publish()

'''
    text=text[:start]+method+text[end:]
    text=once(text,'                cleanup_error=self.cleanup_error,\n',
        '                cleanup_error=self.cleanup_error, latency=copy.deepcopy(self.latency_metrics),\n')
    sources['board/runtime/audio/board_dialogue_jobs.py']=text
    files={}
    for name,text in sources.items():
        raw=text.encode('utf-8');ast.parse(text,feature_version=(3,9))
        path=ROOT/'after'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        files[name]=dict(sha256=sha(raw),bytes=len(raw),before_sha256=PINS[name])
    manifest=dict(schema='aura.ordinary-streaming-candidate.v1',files=files,hardware_executed=False,
        dependencies=['BoardMemoryStore.check_prepared_turn_current'],native_stream_sample_rate=24000)
    raw=(json.dumps(manifest,indent=2)+'\n').encode('utf-8')
    (ROOT/'overlay_manifest.json').write_bytes(raw)
    with zipfile.ZipFile(ROOT/'ordinary_streaming.overlay.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info=zipfile.ZipInfo('aura/'+name,(2026,10,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,(ROOT/'after'/name).read_bytes())
    (ROOT/'extra_source_map.json').write_text(json.dumps({'aura/'+name:str(ROOT/'after'/name)
        for name in sorted(files)},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(files=files,manifest_sha256=sha(raw),zip_sha256=sha((ROOT/'ordinary_streaming.overlay.zip').read_bytes()))))

if __name__=='__main__':build()
