"""Complete automatic capture in the sole frontend child; no new model owner.

Parent polling transports metadata only. Original PCM crosses the anonymous
socketpair once after the original capture has released its microphone owner.
"""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
import threading
import time

from board.runtime.audio.capture import CapturedAudio, FORMAT, DEVICE
from host.model_service.protocol import AudioRef
from . import board_frontend_process as wire

GATE_RELEASE, AUTO_START, AUTO_POLL, AUTO_TAKE, AUTO_CANCEL, AUTO_CLOSE = range(6, 12)
AUTO_KINDS = (AUTO_START, AUTO_POLL, AUTO_TAKE, AUTO_CANCEL, AUTO_CLOSE)
METADATA_MAX = 4096
PCM_MAX = 640000
STATES = frozenset(('IDLE','RECORDING','READY','ERROR','CANCELLED','CLOSED'))
_FIXED_ERRORS = frozenset(('', 'frontend_auto_capture_failed','frontend_auto_arecord_failed',
    'frontend_auto_capture_busy','frontend_auto_cleanup_failed','frontend_auto_owner_mismatch',
    'frontend_auto_mode_busy','frontend_auto_invalid_request','frontend_auto_not_ready',
    'pcm_input_queue_overflow','pcm_input_truncated_frame','pcm_input_read_failed',
    'pcm_input_source_stop_failed','pcm_input_reader_not_stopped'))
_NUMBERS = ('frame_bytes','capacity_frames','capacity_ms','queued_frames','peak_frames',
    'frames_read','frames_delivered','source_read_mean_ms','source_read_max_ms',
    'queue_mean_ms','queue_max_ms','frames','processed_samples','last_roundtrip_ms',
    'max_roundtrip_ms','worker_pid','worker_generation','worker_frame_wall_last_ms',
    'microphone_pid','worker_frame_wall_max_ms','worker_frame_wall_total_ms','worker_frame_cpu_last_ms',
    'worker_frame_cpu_max_ms','worker_frame_cpu_total_ms')
_FLAGS = ('enabled','eof','closed','cancelled','reader_alive','capture_lease_closed',
          'worker_process_alive','worker_capture_process')


class AutomaticRequestRejected(ValueError):
    pass


def exec_arecord_parent(expected_parent,command,*,getppid=os.getppid,arm=None,execvp=os.execvp):
    """Arm Linux PDEATHSIG before exec, without multi-threaded preexec_fn."""
    if (type(expected_parent) is not int or expected_parent<=1 or not isinstance(command,list)
            or not command or command[0]!='arecord' or len(command)>32
            or any(not isinstance(x,str) or len(x)>512 or '\0' in x for x in command)):
        raise ValueError('Invalid owned arecord command')
    if getppid()!=expected_parent:
        raise RuntimeError('Owned microphone parent changed')
    if arm is None:
        def arm():
            import ctypes
            libc=ctypes.CDLL(None,use_errno=True)
            if libc.prctl(1,int(signal.SIGTERM),0,0,0)!=0:
                raise OSError(ctypes.get_errno(),'Owned microphone parent-death setup failed')
    arm()
    if getppid()!=expected_parent:
        raise RuntimeError('Owned microphone parent changed')
    execvp(command[0],command)


def owned_arecord_factory(command,**kwargs):
    if not command or command[0]!='arecord':
        raise ValueError('The original MCP01 arecord command is required')
    entry=str(Path(wire.__file__).resolve())
    return subprocess.Popen([sys.executable,'-B',entry,'--exec-arecord-parent',str(os.getpid()),'--']
                            +list(command),**kwargs)


def _code(value):
    text = str(value or '').lower()
    if not text:
        return ''
    for code in _FIXED_ERRORS:
        if code and code in text:
            return code
    if 'overflow' in text:
        return 'pcm_input_queue_overflow'
    if 'arecord' in text or 'microphone ended' in text:
        return 'frontend_auto_arecord_failed'
    if 'already owned' in text:
        return 'frontend_auto_capture_busy'
    return 'frontend_auto_capture_failed'


def _metrics(value):
    value = value if isinstance(value,dict) else {}
    result = {}
    for key in _NUMBERS:
        item = value.get(key)
        if type(item) in (int,float) and math.isfinite(item) and item >= 0:
            result[key] = item
    for key in _FLAGS:
        if type(value.get(key)) is bool:
            result[key] = value[key]
    if value.get('error'):
        result['error'] = _code(value['error'])
    return result


def _json(data):
    encoded = json.dumps(data,separators=(',',':'),allow_nan=False).encode('utf-8')
    if len(encoded) > METADATA_MAX:
        raise wire.FrontendProcessError('frontend_auto_metadata_limit')
    return encoded


def _decode(data):
    if len(data) > METADATA_MAX:
        raise wire.FrontendProcessError('frontend_auto_metadata_limit')
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result:
                raise ValueError('duplicate')
            result[key] = value
        return result
    try:
        value = json.loads(data.decode('utf-8'),object_pairs_hook=unique,
                           parse_constant=lambda value:(_ for _ in ()).throw(ValueError('nonfinite')))
    except (UnicodeError,ValueError,TypeError):
        raise wire.FrontendProcessError('frontend_auto_protocol_failed') from None
    if not isinstance(value,dict):
        raise wire.FrontendProcessError('frontend_auto_protocol_failed')
    if 'rejected' in value:
        if set(value) != {'rejected'} or value['rejected'] not in _FIXED_ERRORS:
            raise wire.FrontendProcessError('frontend_auto_protocol_failed')
        raise AutomaticRequestRejected(value['rejected'])
    return value


def validate_status(value, *, generation=None, capture_id=None):
    required = {'state','capture_id','generation','speech_started','sample_count','speech_active',
        'input_ready','listening_seconds','has_result','error','audio_frontend','input_queue'}
    if not isinstance(value,dict) or set(value) != required:
        raise wire.FrontendProcessError('frontend_auto_protocol_failed')
    cid, gen = value['capture_id'], value['generation']
    if (value['state'] not in STATES or not isinstance(cid,str) or re.fullmatch('[0-9a-f]{32}',cid) is None
            or type(gen) is not int or gen < 1 or generation is not None and gen != generation
            or capture_id is not None and cid != capture_id):
        raise wire.FrontendProcessError('frontend_auto_owner_mismatch')
    if (any(type(value[k]) is not bool for k in ('speech_started','speech_active','input_ready','has_result'))
            or type(value['sample_count']) is not int or not 0 <= value['sample_count'] <= PCM_MAX//2
            or type(value['listening_seconds']) not in (int,float)
            or not math.isfinite(value['listening_seconds']) or value['listening_seconds'] < 0
            or value['error'] not in _FIXED_ERRORS
            or not isinstance(value['audio_frontend'],dict) or not isinstance(value['input_queue'],dict)
            or _metrics(value['audio_frontend']) != value['audio_frontend']
            or _metrics(value['input_queue']) != value['input_queue']):
        raise wire.FrontendProcessError('frontend_auto_protocol_failed')
    if value['state']=='READY' and (not value['speech_started'] or not value['has_result']):
        raise wire.FrontendProcessError('frontend_auto_missing_speech_event')
    return copy.deepcopy(value)


def decode_status(payload):
    return validate_status(_decode(payload))


def decode_take(payload):
    if payload.startswith(b'{'):
        _decode(payload)  # Fixed rejection response is allowed without any PCM.
        raise wire.FrontendProcessError('frontend_auto_protocol_failed')
    if len(payload)<4:
        raise wire.FrontendProcessError('frontend_auto_protocol_failed')
    size=struct.unpack_from('!I',payload)[0]
    if size>METADATA_MAX or len(payload)<4+size or len(payload)-4-size>PCM_MAX:
        raise wire.FrontendProcessError('frontend_auto_payload_limit')
    body=_decode(payload[4:4+size])
    if set(body)!={'status','clip'}:
        raise wire.FrontendProcessError('frontend_auto_protocol_failed')
    return validate_status(body['status']),body['clip'],bytes(payload[4+size:])


def rebuild_clip(metadata,pcm,capture_id,max_seconds):
    required={'capture_id','audio_epoch','first_sample_index','sample_count','format',
        'duration_seconds','pcm_bytes','pcm_sha256','started_mono_ms','ended_mono_ms'}
    if not isinstance(metadata,dict) or set(metadata)!=required:
        raise wire.FrontendProcessError('frontend_auto_clip_metadata_failed')
    integer=('audio_epoch','first_sample_index','sample_count','pcm_bytes','started_mono_ms','ended_mono_ms')
    if (metadata['capture_id']!=capture_id or any(type(metadata[k]) is not int or metadata[k]<0 for k in integer)
            or metadata['format']!={'rate_hz':16000,'channels':1,'sample_format':'S16_LE'}
            or not isinstance(pcm,bytes) or len(pcm)%2 or not 3200<=len(pcm)<=min(PCM_MAX,int(max_seconds*32000))
            or metadata['sample_count']!=len(pcm)//2 or metadata['pcm_bytes']!=len(pcm)
            or metadata['pcm_sha256']!=hashlib.sha256(pcm).hexdigest()
            or metadata['duration_seconds']!=metadata['sample_count']/16000
            or metadata['ended_mono_ms']<metadata['started_mono_ms']):
        raise wire.FrontendProcessError('frontend_auto_clip_metadata_failed')
    return CapturedAudio(capture_id,AudioRef(metadata['audio_epoch'],metadata['first_sample_index'],
        metadata['sample_count'],FORMAT),pcm,metadata['started_mono_ms'],metadata['ended_mono_ms'])


class ChildAutomaticSession:
    def __init__(self,pool,*,capture_factory=None):
        if capture_factory is None:
            from .board_capture import BoardAutomaticCapture
            capture_factory=lambda *args,**kwargs:BoardAutomaticCapture(*args,
                process_factory=owned_arecord_factory,**kwargs)
        self.pool,self.capture_factory=pool,capture_factory
        self.capture=None
        self.generation=0
        self.capture_id=None
        self.speech_started=False
        self.accept_speech=False
        self.max_seconds=20
        self.lock=threading.Lock()
        self.retired={}

    def _remember_retired(self,status):
        key=(status['generation'],status['capture_id'])
        self.retired[key]=copy.deepcopy(status)
        while len(self.retired)>2:self.retired.pop(next(iter(self.retired)))

    def _released(self):
        c=self.capture
        return (c is None or (getattr(c,'_owner',None) is None and getattr(c,'_process',None) is None
            and not (getattr(c,'_thread',None) and c._thread.is_alive())))

    def retire_idle(self):
        if self.capture is None:
            return
        state=self.capture.snapshot()
        if state['state']=='RECORDING' or state.get('has_result') or not self._released():
            raise AutomaticRequestRejected('frontend_auto_mode_busy')
        old=self.status()
        self.capture.close()
        if not self._released() or self.pool.active is not None:
            raise AutomaticRequestRejected('frontend_auto_cleanup_failed')
        self.capture=None
        old.update(state='CLOSED',has_result=False,speech_started=False,speech_active=False)
        self._remember_retired(old)

    def start(self,generation,max_seconds):
        if type(max_seconds) not in (int,float) or not math.isfinite(max_seconds) or not 1<=max_seconds<=20:
            raise AutomaticRequestRejected('frontend_auto_invalid_request')
        if self.capture is not None:
            old=self.capture.snapshot()
            if old['state']=='RECORDING' or old.get('has_result') or not self._released():
                raise AutomaticRequestRejected('frontend_auto_mode_busy')
            if getattr(self.capture,'_closed',False) or max_seconds!=self.max_seconds:
                self.capture.close();self.capture=None
        if self.pool.active is not None:
            raise AutomaticRequestRejected('frontend_auto_mode_busy')
        if self.capture is None:
            self.capture=self.capture_factory(lambda:False,frontend_factory=self.pool.acquire,max_seconds=max_seconds)
        self.generation,self.max_seconds=generation,max_seconds
        with self.lock:
            self.speech_started=False;self.accept_speech=True
        def speech_started():
            with self.lock:
                if self.generation==generation and self.accept_speech:
                    self.speech_started=True
        self.capture.on_speech_start=speech_started
        try:
            self.capture_id=self.capture.start()
        except BaseException:
            with self.lock:self.accept_speech=False
            self.capture.cancel()
            # Original start() may fail in endpoint creation after Popen but
            # before its reader thread exists. Retire that exact owned source.
            process=getattr(self.capture,'_process',None)
            thread=getattr(self.capture,'_thread',None)
            if process is not None and not (thread and thread.is_alive()):
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    try:process.wait(timeout=2.)
                    except subprocess.TimeoutExpired:
                        process.kill();process.wait(timeout=2.)
                if process.stdout is not None:process.stdout.close()
                self.capture._process=None
                self.capture._release_owner()
                self.capture._close_endpoint()
            raise
        return self.status()

    def require(self,generation,capture_id):
        if self.capture is None or generation!=self.generation or capture_id!=self.capture_id:
            raise AutomaticRequestRejected('frontend_auto_owner_mismatch')

    def retired_status(self,generation,capture_id,kind):
        old=self.retired.get((generation,capture_id))
        if old is None or kind not in (AUTO_POLL,AUTO_CANCEL,AUTO_CLOSE):return None
        status=copy.deepcopy(old)
        status['state']='CANCELLED' if kind==AUTO_CANCEL else 'CLOSED'
        return status

    def status(self):
        if self.capture is None:
            raise AutomaticRequestRejected('frontend_auto_owner_mismatch')
        state=self.capture.snapshot()
        visible=state['state']
        if visible=='READY' and not self._released():
            visible='RECORDING'  # Never publish result before original microphone cleanup.
        with self.lock:speech=self.speech_started
        frontend=_metrics(state.get('audio_frontend'))
        frontend.update(worker_pid=os.getpid(),worker_process_alive=True,worker_capture_process=True,
                        worker_generation=self.generation)
        pid=getattr(getattr(self.capture,'_process',None),'pid',None)
        if type(pid) is int and pid>1:frontend['microphone_pid']=pid
        return dict(state=visible,capture_id=self.capture_id,generation=self.generation,
            speech_started=bool(speech),sample_count=state.get('sample_count',0),
            speech_active=bool(state.get('speech_active')),input_ready=bool(state.get('input_ready')),
            listening_seconds=state.get('listening_seconds',0.),
            has_result=bool(state.get('has_result') and visible=='READY'),error=_code(state.get('error')),
            audio_frontend=frontend,input_queue=_metrics(state.get('input_queue')))

    def take(self,*,stop=False):
        if stop:
            self.capture.stop()
        if self.status()['state']!='READY' or not self._released():
            raise AutomaticRequestRejected('frontend_auto_not_ready')
        clip=self.capture.take()
        metadata=clip.metadata()
        rebuild_clip(metadata,clip.pcm,self.capture_id,self.max_seconds)
        body=_json(dict(status=self.status(),clip=metadata))
        return struct.pack('!I',len(body))+body+clip.pcm

    def cancel(self,*,close=False):
        with self.lock:self.accept_speech=False;self.speech_started=False
        if self.capture is not None:
            (self.capture.close if close else self.capture.cancel)()
        if not self._released() or self.pool.active is not None:
            raise AutomaticRequestRejected('frontend_auto_cleanup_failed')
        status=self.status()
        if close:
            self._remember_retired(status)
            self.capture=None
        return status

    def shutdown(self):
        if self.capture is not None:
            self.cancel(close=True)


def serve_shared(stream,gate_factory,*,apply_priority=None,clock=time.monotonic,
                 thread_clock=time.thread_time,priority_reader=None,auto_capture_factory=None):
    from .board_capture import BoardFrontendPool
    channel=wire._Channel(stream,clock)
    gate=pool=auto=None
    lease=None
    def result(*args,**kwargs):
        kwargs['nice']=priority_reader() if priority_reader is not None else -10
        return wire._result(*args,**kwargs)
    try:
        try:
            if apply_priority is not None:apply_priority()
        except Exception:
            channel.send(wire.HELLO|128,0,0,result(wire.PRIORITY_FAILED),clock()+1.);return
        try:
            gate=gate_factory();pool=BoardFrontendPool(gate)
            auto=ChildAutomaticSession(pool,capture_factory=auto_capture_factory)
        except Exception:
            channel.send(wire.HELLO|128,0,0,result(wire.INIT_FAILED),clock()+1.);return
        channel.send(wire.HELLO|128,0,0,result(gate=gate),clock()+1.)
        generation=last_sequence=0
        reset_pending=False
        timing=[0.]*6
        while True:
            kind,current,sequence,payload=channel.receive(None,poll_interval=.5)
            if sequence<=last_sequence or kind&128:
                raise wire.FrontendProcessError('frontend_worker_protocol_failed')
            last_sequence=sequence
            if kind==wire.STOP and not payload:
                auto.shutdown()
                if lease is not None:lease.close();lease=None
                channel.send(wire.STOP|128,current,sequence,result(gate=gate,timing=timing),clock()+1.);return
            if kind in AUTO_KINDS:
                try:
                    if kind==AUTO_START:
                        if len(payload)!=8 or current!=generation+1 or lease is not None:
                            raise AutomaticRequestRejected('frontend_auto_mode_busy')
                        response=auto.start(current,struct.unpack('!d',payload)[0]);generation=current
                    else:
                        if len(payload) not in ((16,17) if kind==AUTO_TAKE else (16,)):
                            raise AutomaticRequestRejected('frontend_auto_invalid_request')
                        cid=payload[:16].hex()
                        retired=auto.retired_status(current,cid,kind)
                        if retired is not None:
                            channel.send(kind|128,current,sequence,_json(validate_status(retired)),clock()+1.);continue
                        auto.require(current,cid)
                        if kind==AUTO_TAKE:
                            data=auto.take(stop=len(payload)==17 and payload[16:]==b'\x01')
                            channel.send(kind|128,current,sequence,data,clock()+2.);continue
                        response=(auto.status() if kind==AUTO_POLL else auto.cancel(close=kind==AUTO_CLOSE))
                    data=_json(validate_status(response))
                except AutomaticRequestRejected as exc:
                    data=_json(dict(rejected=str(exc)))
                except Exception:
                    try:auto.cancel()
                    except Exception:pass
                    data=_json(dict(rejected='frontend_auto_capture_failed'))
                channel.send(kind|128,current,sequence,data,clock()+1.);continue
            if kind==GATE_RELEASE and not payload and current==generation:
                if lease is not None:lease.close();lease=None
                reset_pending=False
            elif kind==wire.RESET_DENOISER and not payload and current==generation+1:
                try:
                    auto.retire_idle()
                    if lease is not None:lease.close();lease=None
                    lease=pool.acquire()
                except (AutomaticRequestRejected,RuntimeError):
                    channel.send(kind|128,current,sequence,result(wire.MODE_BUSY),clock()+1.);continue
                generation=current;reset_pending=True;timing=[0.]*6
            elif kind==wire.RESET_VAD and not payload and current==generation and reset_pending:
                reset_pending=False
            elif kind==wire.FRAME and current==generation and lease is not None and not reset_pending:
                if len(payload)!=wire.FRAME_BYTES:
                    raise wire.FrontendProcessError('frontend_worker_protocol_failed')
                import numpy as np
                frame=np.frombuffer(payload,dtype='<f4')
                start,cpu=clock(),thread_clock()
                try:decision=lease(frame)
                except Exception:
                    channel.send(kind|128,current,sequence,result(wire.COMPUTE_FAILED),clock()+1.);return
                wall_ms,cpu_ms=(clock()-start)*1000.,(thread_clock()-cpu)*1000.
                timing=[wall_ms,max(timing[1],wall_ms),timing[2]+wall_ms,cpu_ms,max(timing[4],cpu_ms),timing[5]+cpu_ms]
                del frame,payload
                channel.send(kind|128,current,sequence,result(decision=decision,gate=gate,timing=timing),clock()+1.);continue
            else:
                channel.send(kind|128,current,sequence,result(wire.PROTOCOL_FAILED),clock()+1.);return
            channel.send(kind|128,current,sequence,result(gate=gate,timing=timing),clock()+1.)
    except (OSError,wire.FrontendProcessError):
        pass
    finally:
        if auto is not None:
            try:auto.shutdown()
            except Exception:pass
        if lease is not None:lease.close()
        if pool is not None:pool.close()
        elif gate is not None:gate.close()
        stream.close()


class AutomaticCaptureTransport:
    def __init__(self,pool):
        self.pool,self.gate=pool,pool.gate
    def start(self,max_seconds):
        with self.pool.lock:
            if self.pool.closed or self.pool.active is not None:
                raise AutomaticRequestRejected('frontend_auto_mode_busy')
            self.gate.close()
            self.gate._rpc(GATE_RELEASE,timeout=1.)
            generation=self.gate._generation+1
            try:
                status=self.gate._rpc(AUTO_START,payload=struct.pack('!d',max_seconds),generation=generation,
                    timeout=4.,decoder=decode_status)
            except (OSError,wire.FrontendProcessError):
                # A lost START acknowledgement can still own a real microphone.
                # Retire the exact child instead of guessing a new capture ID.
                self.gate.shutdown()
                raise
            self.gate._generation=generation
            return status
    def _request(self,kind,generation,capture_id,*,stop=False):
        payload=bytes.fromhex(capture_id)+(b'\x01' if stop else b'')
        decoder=decode_take if kind==AUTO_TAKE else decode_status
        try:
            response=self.gate._rpc(kind,payload=payload,generation=generation,
                timeout=6. if kind in (AUTO_CANCEL,AUTO_CLOSE) else 2. if kind==AUTO_TAKE else .5,decoder=decoder)
        except (OSError,wire.FrontendProcessError):
            if kind in (AUTO_CANCEL,AUTO_CLOSE):self.gate.shutdown()
            raise
        status=response[0] if kind==AUTO_TAKE else response
        validate_status(status,generation=generation,capture_id=capture_id)
        return response
    def poll(self,generation,capture_id):return self._request(AUTO_POLL,generation,capture_id)
    def take(self,generation,capture_id):return self._request(AUTO_TAKE,generation,capture_id)
    def stop(self,generation,capture_id):return self._request(AUTO_TAKE,generation,capture_id,stop=True)
    def cancel(self,generation,capture_id):return self._request(AUTO_CANCEL,generation,capture_id)
    def close(self,generation,capture_id):return self._request(AUTO_CLOSE,generation,capture_id)
    def public_metadata(self):
        process=self.gate.process
        return dict(worker_pid=process.pid,worker_process_alive=process.poll() is None,worker_capture_process=True)


class RemoteAutomaticCapture:
    def __init__(self,playback_active,*,frontend_pool=None,transport=None,max_seconds=20,
                 speech_start_ready=None,clock=time.monotonic,poll_interval=.05):
        if (not callable(playback_active) or type(max_seconds) not in (int,float)
                or not math.isfinite(max_seconds) or not 1<=max_seconds<=20 or not .02<=poll_interval<=.25):
            raise ValueError('Bounded remote automatic capture required')
        self.playback_active,self.max_seconds,self.clock=playback_active,max_seconds,clock
        self.transport=transport if transport is not None else AutomaticCaptureTransport(frontend_pool)
        self.speech_start_ready=speech_start_ready or (lambda capture_id:True)
        self.poll_interval=poll_interval
        self._lock=threading.RLock();self._stop=threading.Event();self._thread=None
        self._status=None;self._closed=False;self._closing=False;self._version=0;self._taking=False
        self._transport_failed=False
        self._owner_thread=None;self._speech_delivered=False;self._generation=None
        self.capture_id=None;self.state='IDLE';self.error='';self.on_speech_start=None

    def _install(self,status):
        self._status=validate_status(status,generation=self._generation,capture_id=self.capture_id)
        self.state=self._status['state'];self.error=self._status['error']

    def _stop_poll(self):
        self._stop.set()
        thread=self._thread
        if thread is not None and thread is not threading.current_thread():thread.join(timeout=.75)
        if thread is not None and thread.is_alive():
            raise wire.FrontendProcessError('frontend_auto_poll_not_stopped')
        self._thread=None

    def start(self):
        with self._lock:
            if self._closed or self._closing or self._transport_failed or self.state in ('RECORDING','READY') or self._taking:
                raise RuntimeError('Remote automatic capture is closed or still owned')
        if self.playback_active() is not False:
            raise RuntimeError('Stop playback before recording')
        self._stop_poll()
        status=validate_status(self.transport.start(self.max_seconds))
        with self._lock:
            self._version+=1;version=self._version
            self.capture_id=status['capture_id'];self._generation=status['generation']
            self._owner_thread=threading.get_ident();self._speech_delivered=False
            self._install(status);self._stop=threading.Event()
            self._thread=threading.Thread(target=self._poll,args=(version,self._generation,self.capture_id,self._stop),
                name='aura-automatic-control-poll',daemon=True)
            self._thread.start()
            return self.capture_id

    def _poll(self,version,generation,capture_id,stop):
        while not stop.wait(self.poll_interval):
            try:
                status=validate_status(self.transport.poll(generation,capture_id),generation=generation,capture_id=capture_id)
            except Exception:
                with self._lock:
                    if self._version==version and not self._closed and not self._taking:
                        self.state='ERROR';self.error='frontend_auto_capture_failed'
                return
            with self._lock:
                if self._version!=version or self._closed or self._taking:return
                self._install(status)
                if self.state in ('READY','ERROR','CANCELLED','CLOSED'):return

    def _dispatch_speech(self):
        with self._lock:
            status=self._status
            if (self._closed or self._closing or self._taking or self.state in ('ERROR','CANCELLED','CLOSED')
                    or status is None or self._speech_delivered
                    or not status['speech_started'] or threading.get_ident()!=self._owner_thread):return
            version,cid=self._version,self.capture_id
        if not self.speech_start_ready(cid):return
        with self._lock:
            if self._version!=version or self._closed or self._speech_delivered:return
            self._speech_delivered=True
            callback=self.on_speech_start
        if callable(callback):
            try:callback()  # No proxy mutex spans controller/job locks.
            except BaseException:
                with self._lock:self.state='ERROR';self.error='frontend_auto_capture_failed'
                raise

    def snapshot(self):
        self._dispatch_speech()
        with self._lock:
            result=copy.deepcopy(self._status) if self._status is not None else dict(
                sample_count=0,speech_active=False,input_ready=False,listening_seconds=0.,has_result=False,
                audio_frontend={},input_queue={})
            state=self.state
            if state=='READY' and not self._speech_delivered or self._taking:state='RECORDING'
            result.update(state=state,error=self.error,device=DEVICE,max_seconds=self.max_seconds,automatic=True)
            metadata=getattr(self.transport,'public_metadata',None)
            if callable(metadata):result['audio_frontend'].update(metadata())
            if state!='READY':result['has_result']=False
            return result

    def _consume(self,*,stop=False):
        self._dispatch_speech()
        with self._lock:
            if self._closed or self._closing or self._taking or threading.get_ident()!=self._owner_thread:
                raise RuntimeError('Remote automatic result owner mismatch')
            if not stop and (self.state!='READY' or not self._speech_delivered):
                raise RuntimeError(self.error or 'No completed recording')
            self._version+=1;version=self._version;self._taking=True
            generation,cid=self._generation,self.capture_id
        try:
            self._stop_poll()  # Invalidated late poll cannot overwrite this consume.
            status,metadata,pcm=(self.transport.stop if stop else self.transport.take)(generation,cid)
            validate_status(status,generation=generation,capture_id=cid)
            if status['state']!='IDLE' or status['has_result']:
                raise wire.FrontendProcessError('frontend_auto_result_not_consumed')
            clip=rebuild_clip(metadata,pcm,cid,self.max_seconds)
            with self._lock:
                if self._version!=version or self._closed:
                    raise InterruptedError('Remote automatic take was cancelled')
                self._taking=False;self._install(status)
            if stop:self._dispatch_speech()
            if not self._speech_delivered:
                raise wire.FrontendProcessError('frontend_auto_missing_speech_event')
            return clip
        except BaseException:
            with self._lock:
                if self._version==version:self._taking=False;self.state='ERROR';self.error='frontend_auto_capture_failed'
            raise

    def take(self):return self._consume()
    def stop(self):return self._consume(stop=True)

    def _finish(self,close):
        with self._lock:
            if self._closed:return
            self._version+=1;self._taking=False;self._speech_delivered=False;self._closing=True
            generation,cid=self._generation,self.capture_id
        try:
            self._stop_poll()
            if cid is not None:
                status=(self.transport.close if close else self.transport.cancel)(generation,cid)
                validate_status(status,generation=generation,capture_id=cid)
                if status['state']!=('CLOSED' if close else 'CANCELLED'):
                    raise wire.FrontendProcessError('frontend_auto_cleanup_failed')
        except BaseException:
            with self._lock:
                self._closing=False;self._transport_failed=True;self.state='ERROR';self.error='frontend_auto_cleanup_failed'
            raise
        with self._lock:
            self._status=None;self.error='';self._closing=False
            self.state='CLOSED' if close else 'CANCELLED';self._closed=bool(close)
    def cancel(self):return self._finish(False)
    def close(self):return self._finish(True)
