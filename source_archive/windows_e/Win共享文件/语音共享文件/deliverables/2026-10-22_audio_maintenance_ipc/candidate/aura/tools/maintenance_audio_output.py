"""Opt-in bounded pipe transport and generation-checked idle maintenance.

Lifecycle callers serialize through one RLock. Pipe writes are nonblocking and
bounded; reader never waits for device work. Native hangs require process close.
"""
import json
import os
from pathlib import Path
import select
import subprocess
import threading
import time
import uuid

from tools.gstreamer_audio import GStreamerAudioOutput,DEFAULT_DEVICE
from tools.realtime_audio import SelectedAudioOutput


class MaintenanceAudioOutput(GStreamerAudioOutput):
    def __init__(self,log_path=None,device=DEFAULT_DEVICE,*,persistent=True,echo_reference=False,
                 synthetic_sink=False,clock=time.monotonic):
        if not persistent:raise ValueError('Idle maintenance requires persistent audio')
        if synthetic_sink and device!='SYNTHETIC_FAKESINK_NO_ALSA':
            raise ValueError('Synthetic maintenance sink requires its explicit non-device identifier')
        self.lifecycle=threading.RLock();self.send_lock=threading.Lock()
        self.reference_lock=threading.RLock();self.reference_handler=None;self.reference_error=''
        self.streaming=False;self.clock=clock;self.worker_instance=uuid.uuid4().hex
        self.pipeline_epoch=0;self.last_reference_sequence=0;self.dropped_messages=0
        self.maintenance_state='IDLE';self.maintenance_request=None;self.maintenance_deadline=None
        self.maintenance_held=False;self.transport_broken=False
        args=['--device',device,'--persistent','--maintenance-instance',self.worker_instance]
        if echo_reference:args.append('--echo-reference')
        if synthetic_sink:args.append('--maintenance-fakesink')
        SelectedAudioOutput.__init__(self,log_path,
            worker_path=Path(__file__).with_name('gstreamer_audio_worker.py'),worker_args=tuple(args))

    def _hold_failure(self,reason):
        self.maintenance_held=True;self.maintenance_state=reason
        self.maintenance_deadline=None

    def _expire(self):
        if (self.maintenance_held and self.maintenance_deadline is not None
                and self.clock()>=self.maintenance_deadline):
            self._hold_failure('FAILED_TIMEOUT')
            self.maintenance_deadline=None

    def _admit(self):
        self._expire()
        if self.closed or self.maintenance_held or self.transport_broken:
            raise RuntimeError('音频维护中或输出已关闭')

    def _write(self,message):
        if self.transport_broken or self.process.poll() is not None:
            self._hold_failure('FAILED_TRANSPORT');raise RuntimeError('Audio worker transport unavailable')
        raw=(json.dumps(message,ensure_ascii=False,allow_nan=False)+'\n').encode()
        if len(raw)>8192:raise ValueError('Audio command exceeds bounded pipe frame')
        fd=self.process.stdin.fileno();os.set_blocking(fd,False)
        deadline=time.monotonic()+.25;offset=0
        try:
            while offset<len(raw):
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('Audio command pipe deadline')
                if not select.select([],[fd],[],remaining)[1]:raise TimeoutError('Audio command pipe deadline')
                try:offset+=os.write(fd,raw[offset:])
                except BlockingIOError:continue
        except (OSError,TimeoutError):
            # A partial JSON frame cannot be followed by more ordinary frames.
            self.transport_broken=True;self._hold_failure('FAILED_TRANSPORT');raise

    def send(self,kind,**fields):
        with self.lifecycle:
            if kind not in ('stop','close'):self._admit()
            self._write(dict(type=kind,token=self.token,worker_instance=self.worker_instance,**fields))

    def _message(self,message):
        with self.lifecycle:
            self._expire();kind=message.get('kind')
            if message.get('worker_instance')!=self.worker_instance:
                self.dropped_messages+=1;return
            if kind=='boot':
                if (self.closed or self.booted.is_set() or type(message.get('token')) is not int
                        or message.get('token')!=0 or type(message.get('pipeline_epoch')) is not int
                        or message.get('pipeline_epoch')!=0):
                    self.dropped_messages+=1;return
                self.boot_error=message.get('error','');self.device_description=message.get('device','')
                self.booted.set();return
            if kind=='maintenance_ack':
                request=self.maintenance_request
                if (not request or self.maintenance_state!='REQUESTED'
                        or message.get('request_id')!=request['id']
                        or type(message.get('expected_token')) is not int
                        or type(message.get('requested_token')) is not int
                        or type(message.get('engine_token')) is not int
                        or type(message.get('pipeline_epoch')) is not int
                        or message.get('expected_token')!=request['expected']
                        or message.get('requested_token')!=request['token']):
                    self.dropped_messages+=1;return
                if message.get('accepted') is True:
                    if message.get('engine_token')!=request['token'] or message.get('pipeline_epoch')!=request['epoch']+1:
                        self._hold_failure('FAILED_PROTOCOL');return
                    self.pipeline_epoch=request['epoch']+1;self.maintenance_state='ACCEPTED'
                elif (message.get('accepted') is False and message.get('engine_token')==request['expected']
                        and message.get('pipeline_epoch')==request['epoch']):
                    self.token=request['expected'];self.maintenance_held=False
                    self.maintenance_state='REJECTED';self.maintenance_deadline=None
                else:self._hold_failure('FAILED_PROTOCOL')
                return
            if (type(message.get('token')) is not int or message.get('token')!=self.token
                    or type(message.get('pipeline_epoch')) is not int or message.get('pipeline_epoch')!=self.pipeline_epoch):
                self.dropped_messages+=1;return
            if kind=='reference':
                sequence=message.get('sequence')
                if (self.maintenance_held or self.closed or type(sequence) is not int
                        or sequence<=self.last_reference_sequence):
                    self.dropped_messages+=1;return
                self.last_reference_sequence=sequence
                super().receive_reference(message)
                return
            if kind!='state' or self.closed:return
            if self.maintenance_held:
                request=self.maintenance_request
                if (self.maintenance_state not in ('ACCEPTED','WARMING','READY_HELD')
                        or message.get('maintenance_request_id')!=(request or {}).get('id')):
                    self.dropped_messages+=1;return
                phase=message.get('maintenance_state')
                if phase=='READY_UNVERIFIED' and message.get('device_ready') is True:
                    self.maintenance_state='READY_HELD'
                elif phase in ('CLOSING','WARMING'):self.maintenance_state='WARMING'
                elif phase in ('FAILED_HELD','CLOSE_REQUESTED') or message.get('error'):
                    self._hold_failure('FAILED_WORKER')
            with self.lock:self.snapshot.update(message)

    def receive(self):
        for line in self.process.stdout:
            if not line.startswith('AUDIO '):continue
            try:
                value=json.loads(line[6:])
                if isinstance(value,dict):self._message(value)
            except (ValueError,TypeError,KeyError):
                with self.lifecycle:self.dropped_messages+=1
        with self.lifecycle:
            if not self.booted.is_set():self.boot_error='音频播放进程未能启动';self.booted.set()
            if not self.closed:
                self._hold_failure('FAILED_WORKER_EXIT')
                with self.lock:self.snapshot['error']='音频播放进程已退出'

    def begin_idle_maintenance(self):
        with self.lifecycle:
            self._admit()
            with self.reference_lock:
                if self.reference_handler is not None:raise ValueError('Active echo reference owner prevents idle maintenance')
            if self.active or self.paused or self.streaming:raise ValueError('Audio output is busy')
            with self.lock:
                if not self.snapshot.get('device_ready') or self.snapshot.get('error'):
                    raise ValueError('Audio output is not ready for idle maintenance')
            request={'id':uuid.uuid4().hex,'expected':self.token,'token':self.token+1,'epoch':self.pipeline_epoch}
            self.maintenance_request=request;self.maintenance_held=True;self.maintenance_state='REQUESTED'
            self.maintenance_deadline=self.clock()+12;self.token=request['token']
            self._write({'type':'recover_idle','worker_instance':self.worker_instance,
                'request_id':request['id'],'expected_token':request['expected'],'token':request['token']})
            return request['id']

    def finish_idle_maintenance(self,request_id):
        with self.lifecycle:
            self._expire()
            if (self.maintenance_state!='READY_HELD' or not self.maintenance_request
                    or request_id!=self.maintenance_request['id']):return False
            self.maintenance_held=False;self.maintenance_state='IDLE';self.maintenance_deadline=None
            return True

    def maintenance_status(self):
        with self.lifecycle:
            self._expire()
            return {'enabled':True,'state':self.maintenance_state,'held':self.maintenance_held,
                'request_id':(self.maintenance_request or {}).get('id'),'worker_instance':self.worker_instance,
                'pipeline_epoch':self.pipeline_epoch,'dropped_messages':self.dropped_messages,
                'usb_playback_health':'UNVERIFIED'}

    def subscribe_reference(self,handler):
        with self.lifecycle:
            self._admit();return super().subscribe_reference(handler)

    def play(self,*args,**kwargs):
        with self.lifecycle:self._admit();return super().play(*args,**kwargs)

    def begin_stream(self):
        with self.lifecycle:self._admit();return super().begin_stream()

    def append_pcm(self,*args,**kwargs):
        with self.lifecycle:self._admit();return super().append_pcm(*args,**kwargs)

    def feedback(self,*args,**kwargs):
        with self.lifecycle:self._admit();return super().feedback(*args,**kwargs)

    def end_stream(self):
        with self.lifecycle:self._admit();return super().end_stream()

    def pause(self,*args):
        with self.lifecycle:self._admit();return super().pause(*args)

    def stop(self):
        with self.lifecycle:
            if self.closed:return
            if self.maintenance_held:self._hold_failure('FAILED_CANCELLED')
            return super().stop()

    def close(self):
        with self.lifecycle:
            if self.closed:return
            self.closed=True;self._hold_failure('CLOSED')
            if self.process.poll() is None and not self.transport_broken:
                try:self._write({'type':'close','token':self.token,'worker_instance':self.worker_instance})
                except (OSError,TimeoutError,RuntimeError):pass
        # Reader remains free to drain stdout while this owned process exits.
        try:self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2)
        self.reader.join(timeout=1)
        # Popen does not close caller-owned PIPE handles on wait(). The reader
        # must finish before stdout is closed from this thread.
        for name in ('stdin','stdout'):
            pipe=getattr(self.process,name,None)
            if pipe is not None and (name!='stdout' or not self.reader.is_alive()):pipe.close()
        if self.log:self.log.close()
