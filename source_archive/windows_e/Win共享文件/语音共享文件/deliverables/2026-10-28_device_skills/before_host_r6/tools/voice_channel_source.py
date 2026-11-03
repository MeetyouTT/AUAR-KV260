"""Host-only 27B token stream -> natural clauses -> existing OmniVoice16.

OmniVoice still synthesizes a complete clause. This is clause pipelining, not
native token-to-audio TTS. No voice model or inference is installed on KV260.
"""
import hashlib
import queue
import re
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path

from common.voice_channel import MAX_SAMPLES, PACKET_SAMPLES, ChannelWriter
from common.voice_wire import REVISION
from tools.dialogue_stream import OllamaReplyStream,wire_history_within_budget
from common.thinking_policy import route,FeedbackGate
from common.spoken_input import prepare_spoken_input
from common.speech_motion import SpeechMotionPlan


class ClauseBuffer:
    def __init__(self, *, early_sentence=False):
        self.text = '';self.early_sentence=bool(early_sentence)

    def boundary(self,index,char):
        if char not in '，。！？；：':return False
        if index+1>=8:return True
        if not self.early_sentence or char not in '。！？；':return False
        phrase=re.sub(r'[\W_]','',self.text[:index+1])
        # A complete short sentence can be spoken immediately; a filler must
        # stay attached to a meaningful phrase. Never cut inside names/numbers.
        return len(phrase)>=3 and phrase not in {'嗯嗯嗯','好的呀','好呀呀','我想想','让我想想','我想一下','稍等一下','我在想'}

    def feed(self, delta):
        self.text += delta
        pieces = []
        # A tiny filler and a short pause stay attached to the meaningful phrase.
        # Never split arbitrary characters inside a number/name just to save time.
        while True:
            cut = next((i + 1 for i, c in enumerate(self.text) if self.boundary(i,c)),None)
            if cut is None: break
            pieces.append(self.text[:cut])
            self.text = self.text[cut:]
        return pieces

    def finish(self):
        text, self.text = self.text, ''
        return [text] if text.strip() else []


class FirstSentenceBuffer:
    """Release one meaningful whole sentence; coalesce everything after it.

    Short greetings, comma fragments and punctuation inside quoted names do
    not cause extra TTS calls. No text is dropped, shortened or rewritten.
    """
    def __init__(self):
        self.text = ''
        self.released = False

    def feed(self, delta):
        self.text += delta
        if self.released:
            return []
        stack = []
        pairs = {'“': '”', '‘': '’', '《': '》', '（': '）', '「': '」', '(': ')', '[': ']'}
        for index, char in enumerate(self.text):
            if char == '"':
                if stack and stack[-1] == char:
                    stack.pop()
                else:
                    stack.append(char)
            elif char in pairs:
                stack.append(pairs[char])
            elif stack and char == stack[-1]:
                stack.pop()
            elif char in '。！？' and not stack:
                part = self.text[:index+1]
                if len(re.sub(r'[\W_]', '', part)) >= 12:
                    self.text = self.text[index+1:]
                    self.released = True
                    return [part]
        return []

    def finish(self):
        text, self.text = self.text, ''
        return [text] if text.strip() else []


def channel_frames(models, meta, text, timeout, *, model, host, stream_factory=OllamaReplyStream, feedback=False, recognition_ms=None,identity_exchange=None,conversation=None,motion=False,profile_token=None,visual_exchange=None,device_reply=None):
    """Yield validated wire frames; caller retains exclusive model ownership.

    Streaming history is deliberately not committed here: receiving bytes is
    not evidence that the user heard them. The old complete-WAV endpoint keeps
    its existing history behavior. Playback acknowledgement is a later UI step.
    """
    from tools.device_client import DeviceReplyStream
    board_exchange=identity_exchange or visual_exchange or (DeviceReplyStream(device_reply) if device_reply else None)
    if identity_exchange is not None and visual_exchange is not None:raise ValueError('Conflicting board routes')
    deadline = time.monotonic() + timeout
    owner = ChannelWriter(meta)
    motion_plan = SpeechMotionPlan()
    history = list(models.histories.get((meta['board_boot_id'], meta['session_id']), []))
    interpreted=prepare_spoken_input(text)
    model_text=interpreted['text']
    if board_exchange is not None:feedback=False
    plan=route(model_text) if feedback else {'mode':'chat','reason':'delayed','feedback_after_ms':10**9}
    if hasattr(models,'register_stream'):models.register_stream(meta)
    durable=None;memory_reply=None
    if profile_token is not None and (conversation is None or board_exchange is not None):
        raise ValueError('Profile access requires an ordinary durable conversation')
    if conversation is not None and board_exchange is None:
        options={} if profile_token is None else {'profile_token':profile_token}
        memory_reply=models.begin_conversation(meta,conversation,model_text,text,**options)
        durable=models.conversation_context(meta,model_text,reasoning=plan['mode']=='reasoning')
        history=durable[0]
        if memory_reply is not None:
            from common.memory_commands import MemoryReplyStream
            plan={'mode':'chat','reason':'memory_command','feedback_after_ms':10**9}
            feedback=False
    latency=getattr(models,'latency_options',{})
    reuse_history=bool(board_exchange is None and durable is None and latency.get('reuse_history') and latency.get('reply_first') and plan['mode']=='chat')
    history_format='plain'
    history_reason='disabled'
    if reuse_history and hasattr(models,'history_for_stream'):
        history,candidate=models.history_for_stream(meta)
        history_reason='no_confirmed_cache'
        if candidate is not None:
            if wire_history_within_budget(model,candidate,model_text):
                history=candidate;history_format='exact_json';history_reason='confirmed_history'
            else:history_reason='context_budget'
    preference_messages=0
    preference_reason='none'
    if board_exchange is None and durable is None and hasattr(models,'history_with_preferences'):
        recalled=models.history_with_preferences(meta,history,wire=history_format=='exact_json')
        if len(recalled)>len(history):
            if wire_history_within_budget(model,recalled,model_text):
                preference_messages=len(recalled)-len(history)
                history=recalled;preference_reason='confirmed_color_preference'
            else:preference_reason='context_budget'
    if board_exchange is None:
        from tools.device_client import recall
        from common.device_memory import context_message
        observation=context_message(recall(meta,text))
        if observation is not None and wire_history_within_budget(model,[observation]+history,model_text):
            history=[observation]+history
    gate=FeedbackGate(plan)
    yield owner.frame('start', context=meta, sample_rate=24000, channels=1, sample_width=2,
                      source_kind='actual', llm_model=model, engine='omnivoice', revision=REVISION,
                      num_step=16, synthesis_mode='full-clause', tone_control=False,
                      history_commit='playback_ack',thinking_mode=plan['mode'],feedback_enabled=bool(feedback),
                      latency_options=latency,speech_motion='v1' if motion else 'disabled')
    transcript_fields={'text':text}
    if identity_exchange is not None:transcript_fields['identity_request']=identity_exchange.token
    if visual_exchange is not None:transcript_fields['visual_request']=visual_exchange.token
    if interpreted['adjustments']:
        transcript_fields['input_adjustments']=interpreted['adjustments']
    yield owner.frame('transcript', **transcript_fields)
    options={'think':True,'num_predict':768} if plan['mode']=='reasoning' else {}
    if latency.get('reply_first'):options['reply_first']=True
    if latency.get('compact_grammar') and plan['mode']=='chat':options['compact_grammar']=True
    stream = (board_exchange if board_exchange is not None else MemoryReplyStream(memory_reply)
              if memory_reply is not None else stream_factory(host, model, history, model_text, max(.01, deadline-time.monotonic()),**options))
    pending = queue.Queue(maxsize=8)
    stopped = threading.Event()

    def put(value):
        while not stopped.is_set():
            try:
                pending.put(value, timeout=.1)
                return
            except queue.Full:
                continue

    def read_llm():
        try:
            for kind, value in stream:
                if stopped.is_set(): return
                put((kind, value))
        except Exception as exc:
            put(('failure', exc))
        finally:
            put(('eof', None))

    thread = threading.Thread(target=read_llm, daemon=True, name='aura-27b-text-stream')
    thread.start()
    coalesce_chat=bool(latency.get('coalesce_chat') and plan['mode']=='chat')
    clause = ClauseBuffer(early_sentence=latency.get('early_sentence',False))
    first_sentence = (FirstSentenceBuffer() if coalesce_chat and
                      latency.get('first_sentence_chat') and memory_reply is None and
                      board_exchange is None else None)
    reply = None
    first_pcm_ms = None
    started = time.monotonic()
    last_heartbeat = started
    segment_id = 0
    first_text_ms = None
    timing = {} if recognition_ms is None else {'recognition_ms':recognition_ms}
    timing.update(history_format=history_format,history_reuse_reason=history_reason,history_messages=len(history))
    if durable is not None:timing['conversation_context']=durable[1]
    if memory_reply is not None:timing['memory_command']=True
    if preference_reason!='none':
        timing.update(preference_memory_messages=preference_messages,preference_memory_reason=preference_reason)
    if interpreted['adjustments']:timing['input_adjustments']=interpreted['adjustments']
    tts_total_ms = 0.0
    tts_cache_hits = 0
    executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='aura-clause-tts')
    generated=False
    active_tts_id=None

    def hint():
        if feedback and gate.due((time.monotonic()-started)*1000):
            return owner.frame('thinking',feedback_id='thinking',reason=plan['reason'])
        return None

    def synthesize(part):
        nonlocal segment_id, first_pcm_ms, tts_total_ms, tts_cache_hits, active_tts_id
        if time.monotonic() >= deadline: raise TimeoutError('Channel synthesis budget expired')
        before = time.monotonic()
        if segment_id==0:
            timing.update(first_clause_ready_ms=round((before-started)*1000,2),first_clause_text=part)
        active_tts_id=meta['request_id']+':tts:'+str(segment_id)
        bounded=getattr(models.voice,'generate_bounded',None)
        future=(executor.submit(bounded,part,deadline=deadline,cancelled=stopped,request_id=active_tts_id)
                if callable(bounded) else executor.submit(models.voice.generate,part))
        while True:
            if time.monotonic()>=deadline:raise TimeoutError('Channel synthesis budget expired')
            try:
                generated=future.result(timeout=.1)
                break
            except FutureTimeout:
                if future.done():raise
                cue=hint()
                if cue:yield cue
        tts_total_ms += (time.monotonic()-before)*1000
        active_tts_id=None
        tts_cache_hits += int(bool(generated.get('cache_hit')))
        if segment_id==0:
            timing.update(first_tts_request_ms=round((time.monotonic()-before)*1000,2),
                          first_tts_cache_hit=bool(generated.get('cache_hit')),
                          first_tts_generation_ms=round(generated.get('generation_seconds',0)*1000,2))
        if time.monotonic() >= deadline: raise TimeoutError('Channel synthesis budget expired')
        path = Path(generated['path'])
        if generated.get('sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Generated clause SHA256 mismatch')
        gate.ready()
        with wave.open(str(path), 'rb') as audio:
            if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (24000, 1, 2):
                raise ValueError('Clause must be 24kHz mono PCM16')
            if not 0 < audio.getnframes() <= MAX_SAMPLES - owner.state.samples:
                raise ValueError('Channel audio exceeds duration bound')
            # Cue precedes its PCM, so the board can apply it at audible time.
            # This also works when reply metadata arrives after the first sentence.
            if motion:
                cue=motion_plan.cue(part, owner.state.samples,
                                   emotion=reply.get('emotion') if reply else None,
                                   action=reply.get('avatar_action','') if reply else '')
                yield owner.frame('control', **cue, tone_applied=False)
            while True:
                if hasattr(models,'validate_conversation'):models.validate_conversation(meta)
                if time.monotonic()>=deadline:raise TimeoutError('Voice channel audio budget expired')
                pcm = audio.readframes(PACKET_SAMPLES)
                if not pcm: break
                if first_pcm_ms is None: first_pcm_ms = round((time.monotonic()-started)*1000, 2)
                yield owner.frame('audio', pcm, start_sample=owner.state.samples,
                                  sha256=hashlib.sha256(pcm).hexdigest(), segment_id=segment_id,
                                  tts_ms=round((time.monotonic()-before)*1000, 2))
        segment_id += 1

    try:
        cue=hint()
        if cue:yield cue
        while True:
            if hasattr(models,'validate_conversation'):models.validate_conversation(meta)
            if time.monotonic() >= deadline: raise TimeoutError('Voice channel budget expired')
            try:
                kind, value = pending.get(timeout=.1)
            except queue.Empty:
                cue=hint()
                if cue:yield cue
                if time.monotonic()-last_heartbeat >= 1:
                    yield owner.frame('heartbeat')
                    last_heartbeat = time.monotonic()
                continue
            if kind == 'failure': raise value
            if kind == 'text':
                if first_text_ms is None: first_text_ms=round((time.monotonic()-started)*1000,2)
                yield owner.frame('text', text=value)
                if coalesce_chat:
                    if first_sentence is not None:
                        for part in first_sentence.feed(value):
                            yield from synthesize(part)
                    else:
                        clause.text+=value
                    continue
                for part in clause.feed(value):
                    yield from synthesize(part)
            elif kind=='speech_ready':
                # Short conversational replies remain one continuous utterance.
                # Start TTS as soon as the spoken field closes, while metadata
                # continues generating; no artificial pause between commas.
                for part in (first_sentence or clause).finish():
                    yield from synthesize(part)
            elif kind == 'complete':
                reply = value
                timing['llm']=dict(getattr(stream,'metrics',{}))
                timing['llm_complete_observed_ms']=round((time.monotonic()-started)*1000,2)
                # The current schema may emit emotion after reply_text. It is
                # applied to subsequent audio, never retroactively to old samples.
                yield owner.frame('control', emotion=value['emotion'], action='',
                                  at_sample=owner.state.samples, tone_applied=False)
            elif kind == 'eof':
                if reply is None: raise ValueError('Incomplete LLM response')
                if reply['reply_text'] != owner.state.text:
                    raise ValueError('Streamed text differs from complete reply')
                for part in (first_sentence or clause).finish():
                    yield from synthesize(part)
                if hasattr(models,'complete_stream'):
                    extra={}
                    if board_exchange is not None:extra['history_allowed']=False
                    if reuse_history and getattr(stream,'raw_reply',None) is not None:
                        extra['wire_reply']=stream.raw_reply
                        extra['reuse_previous_wire']=history_format=='exact_json'
                    models.complete_stream(meta,model_text,owner.state.text,owner.state.samples,owner.state.digest.hexdigest(),**extra)
                    generated=True
                yield owner.frame('end', reply_text=owner.state.text, sample_count=owner.state.samples,
                                  pcm_sha256=owner.state.digest.hexdigest(), first_pcm_ms=first_pcm_ms,
                                  first_text_ms=first_text_ms, timing=timing, clauses=segment_id,
                                  tts_total_ms=round(tts_total_ms,2), tts_cache_hits=tts_cache_hits,
                                  thinking_mode=plan['mode'],thinking_characters=getattr(stream,'thinking_characters',0),
                                  total_ms=round((time.monotonic()-started)*1000, 2))
                return
    except Exception as exc:
        if not owner.state.ended:
            yield owner.frame('error', error=(type(exc).__name__ + ': ' + str(exc))[:300])
    finally:
        stopped.set()
        gate.cancel()
        try:
            if durable is not None and not generated:models.interrupt_conversation(meta)
        finally:
            try:
                cancel_tts=getattr(models.voice,'cancel_request',None)
                if active_tts_id is not None and callable(cancel_tts):cancel_tts(active_tts_id)
            finally:
                try:stream.cancel()
                finally:
                    thread.join(timeout=1)
                    executor.shutdown(wait=False,cancel_futures=True)


def serve_channel(handler, meta, text, timeout, *, recognition_ms=None,device_reply=None):
    """HTTP/1.1 chunking flushes frames immediately; old routes stay unchanged."""
    import socket
    from common.voice_channel import CONTENT_TYPE
    from tools.board_model_host import MODEL, OLLAMA_HOST
    handler.protocol_version = 'HTTP/1.1'
    handler.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    handler.send_response(200)
    handler.send_header('Content-Type', CONTENT_TYPE)
    handler.send_header('Transfer-Encoding', 'chunked')
    handler.send_header('Cache-Control', 'no-store')
    handler.send_header('Connection', 'keep-alive')
    if handler.headers.get('X-Aura-Conversation'):handler.send_header('X-Aura-Conversation','v1')
    if handler.headers.get('X-Aura-Entry'):handler.send_header('X-Aura-Entry',handler.headers['X-Aura-Entry'])
    if handler.headers.get('X-Aura-Visual')=='frame-question-v1':handler.send_header('X-Aura-Visual','frame-question-v1')
    handler.end_headers()
    features=handler.headers.get('X-Aura-Features','')
    identity_exchange=None;visual_exchange=None
    identity_feature=handler.headers.get('X-Aura-Identity','')
    query_feature=handler.headers.get('X-Aura-Identity-Query','')
    if device_reply is None and identity_feature in ('enrollment-v1','enrollment-active-v1'):
        from common.voice_enrollment import enrollment_requested,cancelled,identity_query_requested
        if (identity_feature=='enrollment-active-v1' or enrollment_requested(text) or cancelled(text)
                or query_feature=='current-face-v1' and identity_query_requested(text)):
            identity_exchange=handler.server.models.open_identity_exchange(meta,timeout)
    from common.visual_question import requested
    if device_reply is None and identity_exchange is None and handler.headers.get('X-Aura-Visual')=='frame-question-v1' and requested(text):
        from tools.visual_voice_host import open_exchange
        visual_exchange=open_exchange(handler.server.models,meta,text,timeout)
    frames = channel_frames(handler.server.models, meta, text, timeout, model=MODEL, host=OLLAMA_HOST,
                            visual_exchange=visual_exchange,device_reply=device_reply,
                            feedback=features=='thinking-feedback-v1',recognition_ms=recognition_ms,identity_exchange=identity_exchange,
                            conversation=(handler.headers['X-Aura-Conversation'][3:] if handler.headers.get('X-Aura-Conversation') else None),
                            profile_token=(handler.headers['X-Aura-Profile'][3:] if handler.headers.get('X-Aura-Profile') and visual_exchange is None and device_reply is None and identity_exchange is None else None),
                            motion=handler.headers.get('X-Aura-Motion')=='speech-v1')
    try:
        for frame in frames:
            handler.wfile.write(('%x\r\n' % len(frame)).encode('ascii') + frame + b'\r\n')
            handler.wfile.flush()
        handler.wfile.write(b'0\r\n\r\n')
        handler.wfile.flush()
        handler.close_connection = False
    except OSError:
        handler.close_connection = True
    finally:
        frames.close()
        if identity_exchange is not None:identity_exchange.cancel()
        if visual_exchange is not None:visual_exchange.cancel()
