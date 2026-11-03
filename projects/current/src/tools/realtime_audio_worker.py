"""Hidden Qt audio device process; bounded controls and processed-sample IPC."""
import hashlib
import json
from pathlib import Path
import queue
import sys
import threading
import time
AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from PySide6.QtCore import QByteArray,QBuffer,QIODevice,QObject,QTimer,Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QAudioFormat,QAudioSink,QMediaDevices
from tools.selected_voice_demo import read_pcm,output_clock_seconds

def emit(**fields):print('AUDIO '+json.dumps(fields,ensure_ascii=False),flush=True)

class AudioDevice(QObject):
    def __init__(self,application):
        super().__init__();self.application=application;self.commands=queue.Queue(maxsize=32);self.latest_token=0;self.token=0
        self.active=False;self.paused=False;self.clock=0.;self.offset=0.;self.duration=0.;self.pcm=b''
        device=QMediaDevices.defaultAudioOutput()
        if device.isNull():raise RuntimeError('未发现音频输出设备')
        fmt=QAudioFormat();fmt.setSampleRate(24000);fmt.setChannelCount(1);fmt.setSampleFormat(QAudioFormat.Int16)
        self.sink=QAudioSink(device,fmt,self);self.sink.setVolume(.9);self.buffer=QBuffer(self)
        threading.Thread(target=self.read_commands,daemon=True,name='audio-control').start()
        self.timer=QTimer(self);self.timer.setTimerType(Qt.TimerType.PreciseTimer);self.timer.timeout.connect(self.tick);self.timer.start(8)
        emit(kind='boot',device=device.description())

    def read_commands(self):
        for line in sys.stdin:
            try:command=json.loads(line);self.latest_token=max(self.latest_token,int(command['token']))
            except (ValueError,KeyError,TypeError):continue
            try:self.commands.put_nowait(command)
            except queue.Full:
                # Only the newest generation may play; discard an older queued control.
                try:self.commands.get_nowait()
                except queue.Empty:pass
                self.commands.put(command)
        self.commands.put({'type':'close','token':self.latest_token})

    def stop(self):self.active=False;self.paused=False;self.sink.stop();self.buffer.close()

    def handle(self,command):
        kind=command['type'];token=command['token']
        if kind=='close':self.stop();self.application.quit();return
        if kind=='stop':self.stop();emit(token=token,device_state=self.sink.state().name);return
        if token!=self.latest_token:return
        if kind=='play':
            self.stop();path=Path(command['path'])
            if command.get('sha256') and hashlib.sha256(path.read_bytes()).hexdigest()!=command['sha256']:raise ValueError('语音文件指纹发生变化')
            pcm=read_pcm(path)
            if token!=self.latest_token:return
            self.token=token;self.duration=len(pcm)/24000;self.clock=0.;self.offset=0.;self.pcm=pcm.tobytes()
            self.buffer.setData(QByteArray(self.pcm));self.buffer.open(QIODevice.ReadOnly);self.sink.start(self.buffer)
            if token!=self.latest_token:self.stop();return
            if self.sink.error().value:raise RuntimeError('音频输出失败：'+self.sink.error().name)
            self.active=True;emit(token=token,ready=True,started_at=time.monotonic(),clock=0.,device_state=self.sink.state().name)
        elif kind=='pause':
            if not self.active:return
            paused=bool(command['paused'])
            if paused==self.paused:return
            if paused:
                # This PC backend can fail on suspend/resume. Keep the processed
                # sample cursor and reopen the remaining PCM instead.
                self.clock=self.sample_position();self.offset=round(self.clock*24000)/24000;self.clock=self.offset
                self.sink.stop();self.buffer.close();self.paused=True
            else:
                self.paused=False;cursor=round(self.offset*24000)*2
                if cursor>=len(self.pcm):self.stop();emit(token=token,clock=self.duration,done=True,device_state=self.sink.state().name);return
                self.buffer.setData(QByteArray(self.pcm[cursor:]));self.buffer.open(QIODevice.ReadOnly);self.sink.start(self.buffer)
                if self.sink.error().value:raise RuntimeError('音频恢复失败：'+self.sink.error().name)
            emit(token=token,clock=self.clock,device_state=self.sink.state().name)

    def sample_position(self):
        return self.offset+output_clock_seconds(self.sink.processedUSecs(),self.duration-self.offset,max(0.,self.clock-self.offset),
                    exhausted=self.buffer.atEnd(),idle=self.sink.state().name=='IdleState',paused=self.paused)

    def tick(self):
        for _ in range(16):
            try:command=self.commands.get_nowait()
            except queue.Empty:break
            try:self.handle(command)
            except Exception as exc:self.stop();emit(token=command['token'],error=str(exc))
        if not self.active:return
        if self.token!=self.latest_token:self.stop();return
        if self.paused:
            emit(token=self.token,clock=self.clock,device_state=self.sink.state().name);return
        try:
            if self.sink.error().value:raise RuntimeError('音频输出失败：'+self.sink.error().name)
            exhausted=self.buffer.atEnd();idle=self.sink.state().name=='IdleState'
            self.clock=self.sample_position()
            emit(token=self.token,clock=self.clock,device_state=self.sink.state().name)
            if not self.paused and exhausted and idle:
                self.stop();emit(token=self.token,clock=self.duration,done=True,device_state=self.sink.state().name)
        except Exception as exc:self.stop();emit(token=self.token,error=str(exc))

def main():
    sys.stdin.reconfigure(encoding='utf-8');sys.stdout.reconfigure(encoding='utf-8')
    application=QApplication(sys.argv[:1])
    try:device=AudioDevice(application)
    except Exception as exc:emit(kind='boot',error=str(exc));return 1
    return application.exec()

if __name__=='__main__':raise SystemExit(main())
