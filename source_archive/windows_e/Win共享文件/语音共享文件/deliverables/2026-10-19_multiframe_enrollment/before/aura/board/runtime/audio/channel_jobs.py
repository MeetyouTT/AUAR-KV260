"""Bounded streaming jobs with cached local feedback and playback-only history ACK."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import copy
import json
import os
from pathlib import Path
import time
import uuid
import urllib.request

from board.runtime.audio.transcription import TranscriptionJobs,configuration
from board.runtime.audio.voice_channel import VoiceChannel
from common.voice_wire import wav_payload,MAX_WAV


def feedback_cache(config,cache_root):
    cache_root=Path(cache_root);cache_root.mkdir(parents=True,exist_ok=True)
    def get(path,limit):
        connection=http.client.HTTPConnection(config['host'],config['port'],timeout=5)
        try:
            connection.request('GET',path);response=connection.getresponse()
            if response.status!=200:raise RuntimeError('Feedback HTTP '+str(response.status))
            raw=response.read(limit+1)
            if len(raw)>limit:raise ValueError('Feedback exceeds size bound')
            return raw
        finally:connection.close()
    assets=json.loads(get('/v1/voice/feedback',8192)).get('assets',{})
    if set(assets)!={'thinking'}:raise ValueError('Selected-voice thinking clip is not ready')
    result={}
    for name,meta in assets.items():
        target=cache_root/(str(meta.get('sha256'))+'.wav')
        raw=target.read_bytes() if target.is_file() else get('/v1/voice/audio/'+str(meta.get('sha256'))+'.wav',MAX_WAV)
        value=wav_payload(meta,raw)
        if value['duration_seconds']>5:raise ValueError('Feedback is too long')
        if not target.is_file():
            temporary=target.with_name(target.name+'.part-'+uuid.uuid4().hex)
            try:temporary.write_bytes(raw);os.replace(str(temporary),str(target))
            finally:temporary.unlink(missing_ok=True)
        result[name]=dict(value,path=str(target))
    return result


class ChannelConversationJobs(TranscriptionJobs):
    def __init__(self,config,boot_id,cache_root):
        self.feedback_assets={};self.feedback_error='';self.feedback_address=None
        self.feedback_root=Path(cache_root)
        self.progress=deque();self.channel=None;self.last_ack=None
        self.identity_snapshot=None;self.capture_owners={}
        from board.identity.voice_enrollment import VoiceEnrollment
        self.identity_flow=VoiceEnrollment(boot_id,self._identity_snapshot,self._identity_command)
        self.acks=ThreadPoolExecutor(max_workers=1,thread_name_prefix='aura-playback-ack')
        super().__init__(config,boot_id,include_voice=True)

    @staticmethod
    def _identity_snapshot():
        with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/status',timeout=1.5) as response:
            raw=response.read(131073)
        if len(raw)>131072:raise ValueError('Identity snapshot exceeds bound')
        return json.loads(raw)

    @staticmethod
    def _identity_command(command):
        request=urllib.request.Request('http://127.0.0.1:8790/v1/ui/commands',
            data=json.dumps(command).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=1.5) as response:raw=response.read(8193)
        if len(raw)>8192:raise ValueError('Identity command response exceeds bound')
        return json.loads(raw)

    def capture_started(self,capture_id):
        # The provider is an in-memory UI snapshot read; never network IO here.
        from board.interaction.ui_contract import validate_snapshot,millis
        try:
            value=self.identity_snapshot() if self.identity_snapshot else None
            value=validate_snapshot(value,self.boot_id,millis())
        except (ValueError,KeyError,TypeError):value=None
        with self.condition:
            self.capture_owners={capture_id:copy.deepcopy(value)}

    def reset_enrollment(self):self.identity_flow.reset()

    def configure(self,values):
        self.reset_enrollment();super().configure(values)

    def prepare_feedback(self,config):
        address=(config['host'],config['port'])
        if self.feedback_assets and self.feedback_address==address:return
        try:
            assets=feedback_cache(config,self.feedback_root)
        except Exception as exc:
            self.feedback_error=type(exc).__name__+': '+str(exc)[:240]
            raise
        self.feedback_assets=assets;self.feedback_address=address;self.feedback_error=''

    def _invalidate(self):
        self.progress.clear()
        if self.channel:self.channel.cancel()
        super()._invalidate()

    def poll(self):
        with self.condition:
            if not self.progress:return None
            value=self.progress.popleft();self.condition.notify_all();return value

    def _put(self,meta,value):
        with self.condition:
            while len(self.progress)>=128 and not self.closed and meta['generation']==self.generation:
                self.condition.wait(.1)
            if self.closed or meta['generation']!=self.generation:return
            self.progress.append(dict(value,context=meta))

    def work(self):
        channel=None;address=None
        try:
            # Network preparation belongs to this worker, so the touchscreen can
            # still start when the PC voice service is unavailable.
            try:self.prepare_feedback(dict(self.config))
            except Exception:pass
            while True:
                with self.condition:
                    while not self.closed and self.waiting is None:self.condition.wait()
                    if self.closed:return
                    job,self.waiting=self.waiting,None;self.active=job[0]['request_id']
                meta,pcm,config,deadline=job
                try:
                    self.prepare_feedback(config)
                    if time.monotonic()>=deadline:raise TimeoutError('Recording expired before sending')
                    if address!=(config['host'],config['port']) or channel is None:
                        if channel:channel.close()
                        address=(config['host'],config['port']);channel=VoiceChannel(*address,feedback=True)
                    self.channel=channel
                    def current():
                        with self.condition:return not self.closed and meta['generation']==self.generation
                    def receive(header,payload):
                        if header['kind']=='transcript' and header.get('identity_request'):
                            if self.identity_snapshot is None:raise ValueError('Identity voice control not enabled')
                            with self.condition:start_owner=copy.deepcopy(self.capture_owners.get(meta['capture_id']))
                            reply=self.identity_flow.handle(header['text'],start_owner,is_current=current)
                            if reply is None:raise ValueError('Unexpected identity voice transcript')
                            if not current():raise InterruptedError('Stale identity voice result')
                            channel.identity_result(meta,header['identity_request'],reply)
                        self._put(meta,{'channel_event':header,'pcm':payload})
                    options={}
                    if self.identity_snapshot is not None:options['enrollment_state']=self.identity_flow.public()['active']
                    result=channel.exchange(meta,pcm,receive,is_current=current,**options)
                    self._put(meta,{'network_complete':result})
                except Exception as exc:
                    self._put(meta,{'error':type(exc).__name__+': '+str(exc)[:240]})
                with self.condition:self.active=None
        finally:
            if channel:channel.close()

    def acknowledge(self,meta,result):
        config=dict(self.config)
        body={'context':meta,'voice_sample_count':result['sample_count'],'pcm_sha256':result['pcm_sha256']}
        def send():
            connection=http.client.HTTPConnection(config['host'],config['port'],timeout=5)
            try:
                connection.request('POST','/v1/voice/channel/played',json.dumps(body).encode(),{'Content-Type':'application/json'})
                response=connection.getresponse();raw=response.read(4097)
                if response.status!=200 or len(raw)>4096 or not json.loads(raw).get('committed'):
                    raise RuntimeError('Playback history acknowledgement rejected')
                self.last_ack={'request_id':meta['request_id'],'committed':True}
            except Exception as exc:self.last_ack={'request_id':meta['request_id'],'committed':False,'error':str(exc)}
            finally:connection.close()
        self.acks.submit(send)

    def public(self):return dict(super().public(),streaming=True,feedback_ready=bool(self.feedback_assets),
                                 feedback_error=self.feedback_error,last_playback_ack=self.last_ack,
                                 voice_enrollment=self.identity_flow.public())

    def close(self):
        super().close();self.acks.shutdown(wait=False)
