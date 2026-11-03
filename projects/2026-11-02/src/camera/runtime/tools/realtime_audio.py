"""Audio subprocess facade: device operations never hold the GUI's Python lock."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import wave

class SelectedAudioOutput:
    def __init__(self,log_path=None,*,worker_path=None,worker_args=()):
        self.active=False;self.paused=False;self.duration=0.;self.last_time=0.;self.finished_count=0;self.token=0;self.closed=False
        self.lock=threading.Lock();self.snapshot={'ready':False,'clock':0.,'done':False,'error':''};self.booted=threading.Event();self.boot_error=''
        self.log=Path(log_path).open('a',encoding='utf-8') if log_path else None
        self.process=subprocess.Popen([sys.executable,'-B','-u',str(worker_path or Path(__file__).with_name('realtime_audio_worker.py')),*worker_args],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log or subprocess.DEVNULL,
                    text=True,encoding='utf-8',bufsize=1,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.reader=threading.Thread(target=self.receive,daemon=True,name='aura-audio-clock');self.reader.start()
        if not self.booted.wait(10) or self.boot_error:
            self.close();raise RuntimeError(self.boot_error or '音频播放进程启动超时')

    def receive(self):
        for line in self.process.stdout:
            if not line.startswith('AUDIO '):continue
            try:message=json.loads(line[6:])
            except ValueError:continue
            if message.get('kind')=='boot':
                self.boot_error=message.get('error','');self.device_description=message.get('device','');self.booted.set();continue
            with self.lock:
                if message.get('token')==self.token:self.snapshot.update(message)
        if not self.booted.is_set():self.boot_error='音频播放进程未能启动';self.booted.set()
        with self.lock:
            if not self.closed:self.snapshot['error']='音频播放进程已退出'

    def send(self,kind,**fields):
        if self.process.poll() is not None:raise RuntimeError('音频播放进程已退出')
        self.process.stdin.write(json.dumps(dict(type=kind,token=self.token,**fields),ensure_ascii=False)+'\n');self.process.stdin.flush()

    def read(self):
        with self.lock:return dict(self.snapshot)

    @property
    def ready(self):return bool(self.read()['ready'])

    @property
    def started_at(self):return self.read().get('started_at')

    def play(self,path,sha256=None):
        with wave.open(str(path),'rb') as stream:
            if (stream.getframerate(),stream.getnchannels(),stream.getsampwidth())!=(24000,1,2):raise ValueError('语音文件格式不正确')
            duration=stream.getnframes()/24000
        self.stop();self.token+=1;self.duration=duration;self.last_time=0.;self.active=True;self.paused=False
        with self.lock:self.snapshot={'ready':False,'clock':0.,'done':False,'error':''}
        self.send('play',path=str(path),sha256=sha256)

    def position(self):
        if self.active and not self.paused:self.last_time=min(self.duration,max(self.last_time,self.read()['clock']))
        return self.last_time

    def finished(self):
        if not self.active:return False
        state=self.read()
        if state['error']:raise RuntimeError(state['error'])
        if state['done']:self.last_time=self.duration;self.active=False;self.finished_count+=1;return True
        return False

    def pause(self,paused):
        if not self.active:return
        self.position();self.paused=paused;self.send('pause',paused=paused)

    def stop(self):
        self.position();self.token+=1;self.active=False;self.paused=False
        with self.lock:self.snapshot={'ready':False,'clock':self.last_time,'done':False,'error':''}
        if self.process.poll() is None:
            try:self.send('stop')
            except (BrokenPipeError,OSError):pass

    def close(self):
        if self.closed:return
        self.closed=True
        if self.process.poll() is None:
            self.send('close')
            try:self.process.wait(5)
            except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(5)
        self.reader.join(timeout=1)
        if self.log:self.log.close()
