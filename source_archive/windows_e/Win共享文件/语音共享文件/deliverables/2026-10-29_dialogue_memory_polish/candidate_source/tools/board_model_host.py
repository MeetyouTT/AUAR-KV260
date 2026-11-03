"""Actual Paraformer -> Qwen3 -> OmniVoice16 service for the GTK board client."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys
import threading
import time

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from common.asr_wire import context,decode_context,MAX_PCM
from common.voice_wire import PROTOCOL,REVISION,voice_reply
from tools.asr_server import AsrServer,Handler,Paraformer
from tools import dialogue_host_ollama as dialogue
from tools.selected_voice_service import VoiceWorker
from common.spoken_input import prepare_spoken_input
from tools.profile_control import turn_profile,profile_options

MODEL_CONFIG=json.loads((AURA/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
MODEL=MODEL_CONFIG['model']
OLLAMA_HOST=MODEL_CONFIG['ollama_host']

class ModelHost:
    def __init__(self,root,python,model_path):
        from common.voice_service_capabilities import source_fingerprint
        from tools.voice_service_health import OllamaDependencyHealth
        self.service_fingerprint=source_fingerprint(AURA)
        self.warmed_up=False
        self.llm_health=OllamaDependencyHealth(OLLAMA_HOST,MODEL)
        self.root=Path(root)
        self.voice=VoiceWorker(self.root,python=python,model_path=model_path,engine='omnivoice')
        self.lock=threading.Lock()
        self.histories={}
        self.wire_histories={}
        self.preference_memories={}
        from common.timeline_conversations import TimelineConversationStore
        from tools.profile_control import access_from_config
        self.conversations=TimelineConversationStore(self.root/'conversations.sqlite3')
        from common.timeline_config import load_config
        self.timeline_zone=load_config(AURA/'config/timeline_memory.json')['timezone']
        self.conversations.start_summaries(zone=self.timeline_zone)
        self.profile_access=access_from_config(AURA)
        self.profile_turns={}
        self.conversation_turns={}
        self.meta_lock=threading.Lock();self.pending_streams={};self.latest_generations={};self.feedback_assets={}
        latency_path=AURA/'config/voice_latency.json'
        self.latency_options=json.loads(latency_path.read_text(encoding='utf-8-sig')) if latency_path.is_file() else {}
        self.face_features=None;self.face_feature_error=''
        try:
            from tools.face_feature_host import FaceFeatureHost
            self.face_features=FaceFeatureHost(AURA/'models/vision/sface_2021dec.onnx')
        except Exception as exc:self.face_feature_error=type(exc).__name__+': '+str(exc)[:160]
        if (set(self.latency_options)-{'reply_first','early_sentence','coalesce_chat','reuse_history','compact_grammar','first_sentence_chat'} or
                any(type(value) is not bool for value in self.latency_options.values())):
            raise ValueError('Invalid voice latency options')

    def register_stream(self,meta):
        key=(meta['board_boot_id'],meta['session_id'])
        with self.meta_lock:
            if meta['generation']<self.latest_generations.get(key,-1):raise ValueError('Stale stream generation')
            self.latest_generations[key]=meta['generation']
            for request,pending in list(self.pending_streams.items()):
                owner=pending['context']
                if ((owner['board_boot_id'],owner['session_id'])==key
                        and owner['generation']<meta['generation']):
                    if request in getattr(self,'conversation_turns',{}):self.conversations.failed(owner)
                    del self.pending_streams[request]
            while len(self.latest_generations)>32:self.latest_generations.pop(next(iter(self.latest_generations)))

    def begin_conversation(self,meta,cid,text,raw_text,*,profile_token=None):
        from tools.memory_timeline_host import sync_visual_archive
        sync_visual_archive(self,meta)
        with self.meta_lock:
            if profile_token is not None:
                from tools.profile_control import validate_request
                validate_request(self,meta,cid,profile_token)
                grant=self.profile_access.resolve(profile_token,meta)
                self.profile_turns[meta['request_id']]={'context':dict(meta),'grant':grant}
                while len(self.profile_turns)>64:self.profile_turns.pop(next(iter(self.profile_turns)))
            with turn_profile(self,meta) as pid:
                self.conversations.begin(cid,meta,text,raw_text,**profile_options(pid))
                reply=self.conversations.memory_command(meta,text,**profile_options(pid))
            self.conversation_turns[meta['request_id']]=cid
            while len(self.conversation_turns)>64:self.conversation_turns.pop(next(iter(self.conversation_turns)))
            return reply

    def conversation_context(self,meta,text,*,reasoning=False):
        from common.conversation_context import build_context
        cid=getattr(self,'conversation_turns',{}).get(meta['request_id'])
        if not cid:return None
        with turn_profile(self,meta) as pid:
            records,facts=self.conversations.context_snapshot(cid,exclude=meta['request_id'],**profile_options(pid))
            if hasattr(self.conversations,'visual_revision_for_records'):
                revision=self.conversations.visual_revision_for_records(records)
                if revision is not None:
                    from tools.memory_timeline_host import use_visual_revision
                    use_visual_revision(self,meta,revision)
            result=build_context(MODEL,records,text,reasoning=reasoning,memories=facts)
            if hasattr(self.conversations,'attach_sources'):
                metrics=result[1]
                sources=metrics['source_turns']+metrics.get('recent_source_turns',[])+metrics['explicit_fact_sources']
                self.conversations.attach_sources(meta,sources,mark_complete=True,**profile_options(pid))
            return result

    def validate_conversation(self,meta):
        from tools.memory_timeline_host import validate_visual_memory
        validate_visual_memory(self,meta)
        if meta['request_id'] in getattr(self,'conversation_turns',{}):
            with turn_profile(self,meta):self.conversations.assert_current(meta)

    def interrupt_conversation(self,meta):
        if meta['request_id'] in getattr(self,'conversation_turns',{}):self.conversations.failed(meta)

    def open_identity_exchange(self,meta,timeout):
        from tools.identity_voice_host import IdentityReplyStream
        exchange=IdentityReplyStream(meta,min(110,timeout))
        with self.meta_lock:
            exchanges=getattr(self,'identity_exchanges',None)
            if exchanges is None:exchanges={};self.identity_exchanges=exchanges
            for key,value in list(exchanges.items()):
                if time.monotonic()>=value.until or value.cancelled.is_set():exchanges.pop(key,None)
            while len(exchanges)>=8:exchanges.pop(next(iter(exchanges))).cancel()
            exchanges[meta['request_id']]=exchange
        return exchange

    def accept_identity_result(self,value):
        if (not isinstance(value,dict) or set(value) not in ({'context','token','reply'},
                {'context','token','reply','sequence','final'})):raise ValueError('Invalid identity result')
        meta=context(value['context']);key=(meta['board_boot_id'],meta['session_id'])
        with self.meta_lock:
            exchange=getattr(self,'identity_exchanges',{}).get(meta['request_id'])
            if exchange is None or self.latest_generations.get(key)!=meta['generation']:raise ValueError('Stale identity result')
            exchange.accept(meta,value['token'],value['reply'],sequence=value.get('sequence',0),final=value.get('final',True))
        return {'accepted':True}

    def history_for_stream(self,meta):
        key=(meta['board_boot_id'],meta['session_id'])
        with self.meta_lock:
            plain=[dict(row) for row in self.histories.get(key,[])]
            cached=getattr(self,'wire_histories',{}).get(key)
            wire=[dict(row) for row in cached['wire']] if cached and cached['plain']==plain else None
            return plain,wire

    def history_with_preferences(self,meta,history,*,wire=False):
        """Recall an older confirmed turn, preserving its original roles/text.

        This is bounded volatile session memory, not an additional model call
        or a system-prompt instruction. Stop/start retains the same session.
        """
        key=(meta['board_boot_id'],meta['session_id'])
        with self.meta_lock:
            anchor=getattr(self,'preference_memories',{}).get(key)
            if not anchor:return history
            if any(row['role']=='user' and row['content']==anchor['plain'][0]['content'] for row in history):
                return history
            prefix=anchor['wire'] if wire else anchor['plain']
            return [dict(row) for row in prefix]+[dict(row) for row in history]

    def _remember_confirmed_preference(self,key,pending):
        from common.session_memory import color_update
        update=color_update(pending['user'])
        memories=getattr(self,'preference_memories',None)
        if memories is None:memories={};self.preference_memories=memories
        if not update:return
        if update['operation']=='forget':memories.pop(key,None)
        elif update['operation']=='remove':
            if memories.get(key,{}).get('color')==update['color']:memories.pop(key,None)
        else:
            user={'role':'user','content':pending['user']}
            memories[key]={'color':update['color'],
                'plain':[user,{'role':'assistant','content':pending['text']}],
                'wire':[dict(user),{'role':'assistant','content':pending.get('wire_reply') or pending['text']}]}

    def complete_stream(self,meta,user,text,samples,sha,*,wire_reply=None,reuse_previous_wire=False,history_allowed=True):
        from tools.memory_timeline_host import validate_visual_memory
        validate_visual_memory(self,meta,force=True)
        if meta['request_id'] in getattr(self,'timeline_turns',{}) and meta['request_id'] not in getattr(self,'conversation_turns',{}):
            history_allowed=False  # Volatile histories have no source-revocation index.
        if wire_reply is not None:
            from tools.dialogue_stream import ReplyDecoder,REPLY_FIRST_FIELDS
            decoder=ReplyDecoder(field_names=REPLY_FIRST_FIELDS)
            decoder.feed(wire_reply)
            if decoder.finish()['reply_text']!=text:raise ValueError('Wire history differs from spoken reply')
        with self.meta_lock:
            if meta['request_id'] in getattr(self,'conversation_turns',{}):
                if self.latest_generations.get((meta['board_boot_id'],meta['session_id']))!=meta['generation']:
                    self.conversations.failed(meta)
                    raise ValueError('Obsolete conversation completion')
                with turn_profile(self,meta):self.conversations.generated(meta,text,samples,sha)
            self.pending_streams[meta['request_id']]={'context':dict(meta),'user':user,'text':text,
                'samples':samples,'sha256':sha,'wire_reply':wire_reply,
                'history_allowed':bool(history_allowed),
                'reuse_previous_wire':bool(reuse_previous_wire),'expires':time.monotonic()+180}
            for key,value in list(self.pending_streams.items()):
                if value['expires']<time.monotonic():del self.pending_streams[key]
            while len(self.pending_streams)>32:self.pending_streams.pop(next(iter(self.pending_streams)))

    def acknowledge_stream(self,value):
        if not isinstance(value,dict) or set(value)!={'context','voice_sample_count','pcm_sha256'}:
            raise ValueError('Invalid playback acknowledgement')
        meta=context(value['context']);key=(meta['board_boot_id'],meta['session_id'])
        from tools.memory_timeline_host import validate_visual_memory
        validate_visual_memory(self,meta,force=True)
        with self.meta_lock:
            pending=self.pending_streams.get(meta['request_id'])
            if (not pending or pending['context']!=meta or pending['expires']<time.monotonic()
                    or self.latest_generations.get(key)!=meta['generation']
                    or type(value['voice_sample_count']) is not int or value['voice_sample_count']!=pending['samples']
                    or value['pcm_sha256']!=pending['sha256']):raise ValueError('Stale or mismatched playback acknowledgement')
            if not pending.get('history_allowed',True):
                del self.pending_streams[meta['request_id']]
                return {'committed':True}
            if meta['request_id'] in getattr(self,'conversation_turns',{}):
                with turn_profile(self,meta):self.conversations.played(meta,pending['samples'],pending['sha256'])
                # Retain the pending receipt until expiry so a lost HTTP ACK can
                # be retried idempotently. No volatile four-turn cache is reused.
                return {'committed':True}
            old=self.histories.get(key,[])
            wires=getattr(self,'wire_histories',None)
            if wires is None:wires={};self.wire_histories=wires
            cached=wires.get(key)
            wire_before=cached['wire'] if pending.get('reuse_previous_wire') and cached and cached['plain']==old else old
            self.histories[key]=(old+[{'role':'user','content':pending['user']},
                                     {'role':'assistant','content':pending['text']}])[-8:]
            if pending.get('wire_reply') is not None:
                wire=(wire_before+[{'role':'user','content':pending['user']},
                                   {'role':'assistant','content':pending['wire_reply']}])[-8:]
                wires[key]={'plain':[dict(row) for row in self.histories[key]],'wire':[dict(row) for row in wire]}
            else:wires.pop(key,None)
            self._remember_confirmed_preference(key,pending)
            while len(self.histories)>32:
                evicted=next(iter(self.histories));self.histories.pop(evicted);wires.pop(evicted,None)
                getattr(self,'preference_memories',{}).pop(evicted,None)
            del self.pending_streams[meta['request_id']]
        return {'committed':True}

    def answer(self,meta,text):
        text=prepare_spoken_input(text)['text']
        key=(meta['board_boot_id'],meta['session_id'])
        history=self.histories.get(key,[])
        request={'request_id':meta['request_id'],'transcript':text,'scene_state':{'scene_seq':meta['generation']},
                 'allowed_emotions':['neutral','friendly','happy','sad'],'allowed_avatar_actions':[]}
        started=time.monotonic()
        reply=dialogue.build_response(request,'ollama',MODEL,history=history,strict=True,fast=True,host=OLLAMA_HOST)
        llm_ms=(time.monotonic()-started)*1000
        started=time.monotonic()
        generated=self.voice.generate(reply['reply_text'])
        tts_ms=(time.monotonic()-started)*1000
        wav=Path(generated['path']);sha=hashlib.sha256(wav.read_bytes()).hexdigest()
        # Audio transport keys are content hashes, separate from engine cache identity.
        target=self.root/'audio'/f'{sha}.wav';target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():target.write_bytes(wav.read_bytes())
        result=voice_reply({'protocol':PROTOCOL,'source_kind':'actual','engine':'omnivoice','revision':REVISION,
                           'num_step':16,'reply_text':reply['reply_text'],'emotion':reply['emotion'],
                           'sha256':sha,'bytes':target.stat().st_size,'duration_seconds':generated['duration_seconds'],
                           'llm_ms':round(llm_ms,2),'tts_ms':round(tts_ms,2),'llm_model':MODEL})
        history=(history+[{'role':'user','content':text},{'role':'assistant','content':reply['reply_text']}])[-8:]
        self.histories[key]=history
        wires=getattr(self,'wire_histories',{})
        wires.pop(key,None)
        while len(self.histories)>32:
            evicted=next(iter(self.histories));self.histories.pop(evicted);wires.pop(evicted,None)
            getattr(self,'preference_memories',{}).pop(evicted,None)
        return result

    def warmup(self):
        self.warmed_up=False
        self.voice.warmup()
        if not self.voice.ready:raise RuntimeError(self.voice.error)
        if self.latency_options.get('reply_first'):
            from tools.dialogue_stream import OllamaReplyStream
            # Prime the same stable system prefix and serialization used by
            # live turns; do not write this maintenance request into history.
            stream=OllamaReplyStream(OLLAMA_HOST,MODEL,[],'你好',120,reply_first=True,
                                    compact_grammar=self.latency_options.get('compact_grammar',False))
            try:
                for kind,value in stream:
                    if kind=='complete':break
            finally:stream.cancel()
        else:
            dialogue.build_response({'request_id':'warmup','transcript':'你好','scene_state':{'scene_seq':1}},
                                    'ollama',MODEL,strict=True,fast=True,host=OLLAMA_HOST)
        from tools.thinking_feedback import prepare
        prepare(self)
        from tools.social_feedback import prepare as prepare_social
        try:prepare_social(self)
        except Exception:self.social_assets={}
        self.warmed_up=True

    def dependency_health(self,engine):
        from common.voice_service_capabilities import SERVICE_REVISION,CAPABILITIES
        voice=self.voice.health()
        llm=self.llm_health.status()
        asr={'ready':bool(getattr(engine,'model_id',None))}
        return {'ready':bool(self.warmed_up and voice['ready'] and llm['ready'] and asr['ready']),
                'dependencies':{'tts':voice,'llm':llm,'asr':asr},
                'startup_warmup_complete':self.warmed_up,'service_revision':SERVICE_REVISION,
                'source_fingerprint':self.service_fingerprint,'capabilities':dict(CAPABILITIES)}

class ModelHandler(Handler):
    def do_GET(self):
        if self.path=='/health':
            from common.voice_channel import PROTOCOL as CHANNEL_PROTOCOL
            from tools.voice_service_health import dependency_health
            state=dependency_health(self.server.models,self.server.engine)
            self.send(200 if state['ready'] else 503,{**state,'source_kind':'actual','asr_model':self.server.engine.model_id,
                           'llm_model':MODEL,'tts':'omnivoice','num_step':16,'voice_protocol':PROTOCOL,
                           'voice_channel_protocol':CHANNEL_PROTOCOL,'channel_experimental':True,
                           'thinking_feedback_ready':bool(getattr(self.server.models,'feedback_assets',{})),
                           'identity_voice_enrollment':{'version':1,'decision_owner':'board','llm_actions':False,
                               'sampling_guidance_version':3,'confirmation_before_sampling':True,
                                 'identity_query_version':1,'identity_query_scope':'fresh_current_face',
                                 'identity_query_intent_revision':2},
                           'identity_features':(self.server.models.face_features.health()
                               if getattr(self.server.models,'face_features',None) else
                               {'ready':False,'error':getattr(self.server.models,'face_feature_error','not initialized')}),
                           'session_preference_memory':{'version':1,'fields':['favorite_color'],
                               'parser_revision':2,
                               'scope':'volatile_boot_session','commit':'playback_ack',
                               'sessions_with_preference':len(getattr(self.server.models,'preference_memories',{}))},
                           'latency_options':getattr(self.server.models,'latency_options',{}),
                           'conversation_memory':(self.server.models.conversations.health()
                               if getattr(self.server.models,'conversations',None) else {'version':0}),
                           'profile_access':(self.server.models.profile_access.health()
                               if getattr(self.server.models,'profile_access',None) else {'version':0,'configured':False}),
                           'handsfree_entry':{'version':1,'gate':'energy_then_asr_first_turn','speaker_identity':False},
                           'busy':self.server.models.lock.locked()});return
        prefix='/v1/voice/audio/'
        if self.path=='/v1/voice/social':
            self.send(200,{'assets':getattr(self.server.models,'social_assets',{})});return
        if self.path=='/v1/voice/feedback':
            self.send(200,{'assets':getattr(self.server.models,'feedback_assets',{})});return
        if self.path.startswith(prefix):
            import re
            name=self.path[len(prefix):]
            if not re.fullmatch(r'[0-9a-f]{64}\.wav',name):self.send(400,{'error':'Invalid audio key'});return
            file=self.server.models.root/'audio'/name
            if not file.is_file():self.send(404,{'error':'Audio expired or missing'});return
            raw=file.read_bytes()
            try:
                self.send_response(200);self.send_header('Content-Type','audio/wav')
                self.send_header('Content-Length',str(len(raw)));self.send_header('Connection','close');self.end_headers()
                self.wfile.write(raw)
            except ConnectionError:pass
            finally:self.close_connection=True
            return
        self.send(404,{'error':'Unknown route'})

    def do_POST(self):
        if self.path=='/v1/profile/release':
            from tools.profile_control import handle_release
            handle_release(self);return
        if self.path=='/v1/profile/control':
            from tools.profile_control import handle_control
            handle_control(self);return
        if self.path=='/v1/identity/face-features':
            try:
                from common.face_features import MAX_PNG,decode_meta
                if (self.headers.get('Origin') or self.headers.get('Transfer-Encoding')
                        or len(self.headers.get_all('Content-Length',[]))!=1
                        or len(self.headers.get_all('X-Aura-Face',[]))!=1):raise ValueError('Invalid face transport')
                size=int(self.headers['Content-Length'])
                if not 24<=size<=MAX_PNG or self.headers.get('Content-Type')!='image/png':raise ValueError('Invalid face body')
                meta=decode_meta(self.headers['X-Aura-Face']);png=self.rfile.read(size)
                host=getattr(self.server.models,'face_features',None)
                if host is None:self.send(503,{'error':'Face feature service not ready'});return
                self.send(200,host.feature(meta,png))
            except BlockingIOError:self.send(503,{'error':'Face feature worker busy'})
            except (ValueError,TypeError,KeyError,UnicodeError):self.send(400,{'error':'Invalid face feature request'})
            except Exception:self.send(503,{'error':'Face feature computation failed'})
            return
        if self.path=='/v1/voice/visual/frame':
            from tools.visual_voice_host import handle_frame
            handle_frame(self);return
        if self.path=='/v1/voice/identity/result':
            try:
                if self.headers.get('Origin') or self.headers.get('Transfer-Encoding'):raise ValueError('Invalid transport')
                if len(self.headers.get_all('Content-Length',[]))!=1:raise ValueError('Expected one length')
                size=int(self.headers['Content-Length'])
                if not 1<=size<=4096 or self.headers.get('Content-Type')!='application/json':raise ValueError('Invalid body')
                self.send(200,self.server.models.accept_identity_result(json.loads(self.rfile.read(size))))
            except (ValueError,TypeError,KeyError):self.send(400,{'error':'Invalid/stale identity result'})
            return
        if self.path=='/v1/voice/channel/played':
            try:
                if self.headers.get('Origin') or self.headers.get('Transfer-Encoding'):raise ValueError('Invalid acknowledgement transport')
                if len(self.headers.get_all('Content-Length',[]))!=1:raise ValueError('Expected one length')
                size=int(self.headers['Content-Length'])
                if not 1<=size<=4096 or self.headers.get('Content-Type')!='application/json':raise ValueError('Invalid acknowledgement body')
                self.send(200,self.server.models.acknowledge_stream(json.loads(self.rfile.read(size))))
            except (ValueError,TypeError,KeyError):self.send(400,{'error':'Invalid/stale playback acknowledgement'})
            return
        if self.path not in ('/v1/voice/converse','/v1/voice/channel'):super().do_POST();return
        if self.headers.get('Origin') or self.headers.get('Transfer-Encoding'):
            self.send(403,{'error':'Browser/chunked requests rejected'});return
        try:
            if len(self.headers.get_all('Content-Length',[]))!=1 or len(self.headers.get_all('X-Aura-Asr',[]))!=1:
                raise ValueError('Missing or repeated headers')
            size=int(self.headers['Content-Length'])
            if not 6400<=size<=MAX_PCM or size%2 or self.headers.get('Content-Type')!='application/octet-stream':
                raise ValueError('Bounded PCM16 required')
            meta=decode_context(self.headers['X-Aura-Asr'])
            visual_headers=self.headers.get_all('X-Aura-Visual',[])
            if visual_headers and (visual_headers!=['frame-question-v1'] or self.path!='/v1/voice/channel'):
                raise ValueError('Invalid visual question negotiation')
            entry_headers=self.headers.get_all('X-Aura-Entry',[])
            if entry_headers and (entry_headers not in (['visual-speech-v1'],['wake-word-v1']) or self.path!='/v1/voice/channel'):
                raise ValueError('Invalid visual speech entry transport')
            conversation_headers=self.headers.get_all('X-Aura-Conversation',[])
            if conversation_headers:
                from common.conversation_store import conversation_id
                if len(conversation_headers)!=1 or self.path!='/v1/voice/channel':raise ValueError('Invalid conversation transport')
                header=conversation_headers[0]
                if not header.startswith('v1:'):raise ValueError('Unsupported conversation version')
                conversation_id(header[3:])
            profile_headers=self.headers.get_all('X-Aura-Profile',[])
            if profile_headers:
                import re
                if (len(profile_headers)!=1 or not conversation_headers or self.path!='/v1/voice/channel'
                        or self.headers.get('X-Aura-Identity') or not re.fullmatch('v1:[0-9a-f]{64}',profile_headers[0])):
                    raise ValueError('Invalid profile transport')
            if conversation_headers:
                from tools.profile_control import validate_request
                validate_request(self.server.models,meta,conversation_headers[0][3:],profile_headers[0][3:] if profile_headers else None)
            started=time.monotonic();pcm=self.rfile.read(size);context(meta,pcm)
        except PermissionError:self.send(403,{'error':'Profile access denied'});return
        except (ValueError,UnicodeError,socket.timeout) as exc:self.send(400,{'error':str(exc)});return
        if entry_headers:
            from common.handsfree_entry import audio_candidate
            if not audio_candidate(pcm):
                self.send(422,{'code':'entry_rejected','stage':'audio','error':'No sustained initial audio activity'});return
        if not self.server.models.lock.acquire(blocking=False):self.send(503,{'error':'Voice host busy'});return
        try:
            with self.server.inference:
                before=time.monotonic();text=self.server.engine.transcribe(pcm);asr_ms=(time.monotonic()-before)*1000
            if entry_headers==['wake-word-v1']:
                from common.voice_wake import wake_request
                # Reuse only the previously accepted, conservative vocative
                # correction. Never add arbitrary names or rewrite spelling talk.
                text=wake_request(prepare_spoken_input(text)['text'])
                if text is None:
                    self.send(422,{'code':'entry_rejected','error':'Wake word not detected'});return
                if not text:
                    self.send_response(204)
                    self.send_header('X-Aura-Entry','wake-word-v1')
                    self.send_header('Content-Length','0')
                    self.send_header('Cache-Control','no-store')
                    self.end_headers()
                    return
            elif entry_headers:
                from common.handsfree_entry import acceptable_entry
                if not acceptable_entry(text):
                    self.send(422,{'code':'entry_rejected','error':'No valid initial speech'});return
            if self.path=='/v1/voice/channel':
                if not text:self.send(422,{'error':'No recognized speech'});return
                from tools.device_client import command
                device_reply=command(meta,text,pcm)
                remaining=meta['budget_ms']/1000-(time.monotonic()-started)
                if remaining<=0:self.send(504,{'error':'Conversation budget expired'});return
                from tools.voice_channel_source import serve_channel
                serve_channel(self,meta,text,remaining,recognition_ms=round(asr_ms,2),device_reply=device_reply)
                return
            reply={'context':meta,'source_kind':'actual','text':text,'model_id':self.server.engine.model_id,
                   'recognition_ms':round(asr_ms,2)}
            adjustments=prepare_spoken_input(text)['adjustments']
            if adjustments:reply['input_adjustments']=adjustments
            if text:reply['voice_reply']=self.server.models.answer(meta,text)
            if (time.monotonic()-started)*1000>=meta['budget_ms']:
                self.send(504,{'error':'Conversation budget expired'});return
            self.send(200,reply)
        except Exception as exc:self.send(500,{'error':type(exc).__name__+': '+str(exc)[:240]})
        finally:self.server.models.lock.release()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--listen',default='192.168.50.1')
    parser.add_argument('--port',type=int,default=8792);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--voice-python',default=sys.executable)
    args=parser.parse_args()
    models=ModelHost(args.root,args.voice_python,AURA/'models/tts/OmniVoice')
    try:
        engine=Paraformer(AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14')
        models.warmup()
        server=AsrServer((args.listen,args.port),engine,handler=ModelHandler);server.models=models
        print(json.dumps({'status':'READY','listen':args.listen,'port':args.port,'protocol':PROTOCOL,
                          'asr':engine.model_id,'llm':MODEL,'tts_revision':REVISION,'num_step':16}),flush=True)
        try:server.serve_forever(poll_interval=.2)
        finally:server.server_close()
    finally:models.voice.close()

if __name__=='__main__':main()
