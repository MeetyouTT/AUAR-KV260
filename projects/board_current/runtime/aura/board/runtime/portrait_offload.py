"""Latest-only portrait RPC, independent of the audio/render owner thread."""
import socket
import threading
import time
import uuid
from common import portrait_wire as wire

class PortraitOffload:
    def __init__(self,config,size,*,clock=time.monotonic,connect=socket.create_connection):
        if config.get('host')!='192.168.50.1':raise ValueError('Portrait host must be the wired Windows address')
        self.host=config['host'];self.port=wire.integer(config.get('port',8796),1,65535)
        self.revision=wire.identifier(config['revision']);self.size=tuple(size)
        self.target_fps=wire.integer(config.get('fps',24),8,24)
        self.enabled=True
        self.ttl=wire.number(config.get('max_age_ms',150),50,200)/1000
        self.clock=clock;self.connect=connect;self.session=uuid.uuid4().hex;self.sequence=0
        self.condition=threading.Condition();self.pending=None;self.latest=None;self.identity=None
        self.closed=False;self.connection=None;self.consumed=0;self.mode='local';self.error=''
        self.local_reset=True;self.sent=self.accepted=self.dropped=self.failures=0;self.max_audio_lag_ms=0.
        self.thread=threading.Thread(target=self.work,name='aura-portrait-wire',daemon=True);self.thread.start()

    def invalidate(self):
        with self.condition:
            self.session=uuid.uuid4().hex;self.latest=self.pending=None;self.identity=None
            self.mode='local';self.local_reset=True
            connection=self.connection
        if connection:
            try:connection.shutdown(socket.SHUT_RDWR)
            except OSError:pass

    def set_enabled(self,enabled):
        if type(enabled) is not bool:raise ValueError('Expected portrait enable boolean')
        with self.condition:self.enabled=enabled
        self.invalidate()
        return {'enabled':enabled}

    def set_fps(self,fps):
        if fps not in (8,12,16,24) or type(fps) is not int:raise ValueError('Unsupported portrait frame rate')
        with self.condition:self.target_fps=fps
        return {'fps':fps}

    def offer(self,core,now,gain,level,audio_sample,track):
        with self.condition:
            if self.closed or not self.enabled:return None
            self.sequence+=1
            request=wire.plan(dict(protocol=wire.PROTOCOL,kind='render',session=self.session,generation=core.talk_gen,
                sequence=self.sequence,state=core.fsm.state.label,clock=float(now),gain=float(gain),level=float(level),
                idle_gain=float(core.idle_gain),emotion=core.emotion if core.emotion in wire.EMOTIONS else 'neutral',
                characters=min(8000,len(getattr(core,'reply_text',''))),audio_sample=max(0,int(audio_sample)),track=track,
                width=self.size[0],height=self.size[1],revision=self.revision))
            identity=wire.owner(request)
            if self.identity!=identity:
                self.identity=identity;self.latest=None;self.local_reset=True
            if self.pending is not None:self.dropped+=1
            self.pending=(request,self.clock());self.condition.notify()
            value=self.latest
            if value and wire.owner(value[0])==identity and self.clock()-value[2]<=self.ttl:
                self.mode='remote';header,pixels,at=value
                # Never present an older answer position after the current PCM
                # clock has advanced beyond the allowed visual lag.
                if not 0<=audio_sample-header['audio_sample']<=round(self.ttl*24000):value=None
                elif header['sequence']==self.consumed:return {'_portrait_wait':True}
                else:
                    self.consumed=header['sequence'];self.error=''
                    self.max_audio_lag_ms=max(self.max_audio_lag_ms,(audio_sample-header['audio_sample'])/24.)
                    return dict(asset=header['asset'],index=header['index'],display_state=header['display_state'],
                        target_state=header['state'],transitioning=header['transitioning'],mouth_level=header['mouth_level'],
                        speech_gain=header['speech_gain'],_portrait_rgb=pixels,_portrait_sequence=header['sequence'],
                        _portrait_burst=header['burst_finished'],_portrait_sample=header['audio_sample'],
                        _portrait_expires=at+self.ttl)
            if self.mode=='remote':self.local_reset=True
            self.mode='local'
            return None

    def reset_local_if_needed(self,core):
        with self.condition:needed=self.local_reset;self.local_reset=False
        if needed:core.reset_playback()

    def status(self):
        with self.condition:
            return dict(mode=self.mode if self.enabled else 'disabled',selected=self.enabled,target_fps=self.target_fps,fallback_fps=8,sent=self.sent,accepted=self.accepted,
                discarded=self.dropped,failures=self.failures,error=self.error,
                frame_age_ms=round((self.clock()-self.latest[2])*1000,2) if self.latest else None,
                render_ms=self.latest[0]['render_ms'] if self.latest else None,max_accepted_audio_lag_ms=self.max_audio_lag_ms,
                pending=int(self.pending is not None),inflight_limit=1)

    def work(self):
        connection=None;connected_session=None
        try:
            while True:
                with self.condition:
                    while not self.closed and self.pending is None:self.condition.wait()
                    if self.closed:return
                    request,at=self.pending;self.pending=None
                if self.clock()-at>self.ttl:continue
                try:
                    if connection is not None and connected_session!=request['session']:
                        connection.close();connection=None
                    if connection is None:
                        connection=self.connect((self.host,self.port),timeout=.2)
                        connected_session=request['session']
                        connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                        with self.condition:self.connection=connection
                    # A total RPC timer bounds trickled header/body reads too.
                    connection.settimeout(self.ttl)
                    def expire(c=connection):
                        try:c.shutdown(socket.SHUT_RDWR)
                        except OSError:pass
                    timer=threading.Timer(self.ttl,expire);timer.daemon=True;timer.start()
                    try:
                        wire.send(connection,request)
                        header,pixels=wire.receive(connection,self.size[0]*self.size[1]*3)
                        wire.frame(header,pixels,request)
                    finally:timer.cancel()
                    with self.condition:
                        self.sent+=1
                        if not self.closed and wire.owner(request)==self.identity and self.clock()-at<=self.ttl:
                            self.latest=(header,pixels,at);self.accepted+=1
                        else:self.dropped+=1
                except (OSError,ValueError,EOFError) as exc:
                    if connection:connection.close()
                    connection=None
                    with self.condition:
                        if self.mode=='remote':self.local_reset=True
                        self.connection=None;self.latest=None;self.mode='local'
                        obsolete=request['session']!=self.session or not self.enabled or self.closed
                        if obsolete:self.dropped+=1
                        else:
                            self.failures+=1;self.error=(type(exc).__name__+': '+str(exc))[:160]
                            deadline=self.clock()+.35
                            while not self.closed and self.session==request['session'] and self.clock()<deadline:
                                self.condition.wait(deadline-self.clock())
        finally:
            if connection:connection.close()

    def close(self):
        with self.condition:self.closed=True;self.pending=None;connection=self.connection;self.condition.notify()
        if connection:
            try:connection.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        self.thread.join(timeout=2)
        if self.thread.is_alive():raise RuntimeError('Portrait receiver did not stop')
