"""Selected cached voice, sample-based cue sheet and amplitude-driven mouth gate.

The normal ScriptRunner/FSM still decides states, assets and display recovery.
Audio activity only blends each reuse mouth toward its own closed-mouth anchor.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
from pathlib import Path
import sys
import wave

import numpy as np

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from board.runtime.events import EventType as E
from tools.demo_script import Cue,ScriptRunner,create_demo_core

VOICE=AURA.parent/'deliverables'/'2026-10-06_voice_selected_soft_young'
OUT=AURA.parent/'deliverables'/'2026-10-06_voice_script_sync'
RATE=24000
HOP=.01


def output_clock_seconds(processed_us,duration,previous,*,exhausted=False,idle=False,paused=False):
    """Use processed audio only; settle a drained partial block at EOF."""
    if exhausted and idle and not paused:return duration
    return min(duration,max(previous,processed_us/1e6))


def warm_script_assets(core):
    """PC-only bounded preload. Board budgets remain unchanged."""
    states=('IDLE','PRESENT','AWAKE','LISTENING','THINKING','ACK_NOD')
    core.MAX_CACHED_SEQUENCES=len(states)
    sizes=[]
    for state in states:
        sequence=core.sequence(state)
        if sequence is None:raise ValueError('Missing script asset: '+state)
        core.sop(state)
        frames=sequence[0]
        sizes.append({'state':state,'asset':sequence[3],'frames':len(frames),
                      'decoded_rgba_bytes':sum(im.width*im.height*4 for im in frames)})
    return {'states':sizes,'decoded_rgba_bytes':sum(row['decoded_rgba_bytes'] for row in sizes),
            'scope':'six PC script sequences; reuse mouth arrays are retained separately; not a board memory budget'}


def read_pcm(path):
    with wave.open(str(path),'rb') as stream:
        if (stream.getframerate(),stream.getnchannels(),stream.getsampwidth())!=(RATE,1,2):
            raise ValueError('Expected verified 24k mono PCM16: '+str(path))
        return np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').copy()


def activity_envelope(pcm):
    """20ms energy at 10ms steps; bridge tiny gaps, then ramp onset/recovery.

    This is activity detection, not phoneme alignment. Do not gate individual
    quiet consonants: merge gaps up to 70ms and retain a short closing tail.
    """
    data=pcm.astype(np.float64)/32768.0
    hop=round(RATE*HOP);win=hop*2
    starts=np.arange(0,len(data),hop)
    sums=np.concatenate(([0.0],np.cumsum(data*data)))
    ends=np.minimum(starts+win,len(data))
    rms=np.sqrt((sums[ends]-sums[starts])/np.maximum(1,ends-starts))
    threshold=max(.008,float(np.percentile(rms,95))*.10)
    active=rms>=threshold
    indices=np.flatnonzero(active)
    if not len(indices):raise ValueError('No speech activity')
    for left,right in zip(indices[:-1],indices[1:]):
        if right-left-1<=7:active[left:right+1]=True
    # Keep 40ms after voiced activity; helps quiet word endings.
    padded=active.copy()
    for offset in range(1,5):padded[offset:]|=active[:-offset]
    gain=np.zeros(len(active),dtype=float)
    value=0.0
    for i,on in enumerate(padded):
        value=min(1.0,value+HOP/.03) if on else max(0.0,value-HOP/.08)
        gain[i]=value*value*(3-2*value)
    # Outside the clip always has zero gain; use a continuous final closure.
    tail=max(0,len(gain)-12)
    gain[tail:]*=np.linspace(1,0,len(gain)-tail)
    intervals=[];begin=None
    for i,on in enumerate(padded):
        if on and begin is None:begin=i*HOP
        if begin is not None and (not on or i==len(padded)-1):
            intervals.append([round(begin,3),round(min(len(data)/RATE,(i+(1 if on else 0))*HOP),3)])
            begin=None
    return {'hop_seconds':HOP,'threshold_rms':threshold,
            'gains':np.round(gain,5).tolist(),'active_intervals':intervals}


class VoicePlan:
    def __init__(self,source=VOICE):
        self.source=Path(source)
        self.scenes={row['id']:row for row in json.loads((self.source/'scenes.json').read_text(encoding='utf-8'))['scenes']}
        verified=json.loads((self.source/'audio_verification.json').read_text(encoding='utf-8'))
        self.clips={};self.envelopes={}
        for row in verified['clips']:
            path=self.source/'audio'/f"{row['id']}.wav"
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row['output_sha256']:
                raise ValueError('Selected audio hash changed: '+str(path))
            self.clips[row['id']]=read_pcm(path)
            self.envelopes[row['id']]=activity_envelope(self.clips[row['id']])
        self.cues=[Cue(0,'reset',note='开机待机'),Cue(1,'event',E.SCENE_PERSON_ENTER,note='来访'),
                   Cue(2,'event',E.AUDIO_KWS_DETECTED,note='唤醒'),Cue(4.2,'event',E.AUDIO_VAD_END,note='倾听结束')]
        self.utterances=[]
        finish=self.add_speech(5.2,'greeting','friendly')
        finish=self.add_round(finish+.65,'explanation','neutral')
        finish=self.add_round(finish+.65,'excited','happy',action='ack_nod',lead=1.05)
        finish=self.add_round(finish+.65,'gentle','sad')
        finish=self.add_round(finish+.65,'excited','excited',cut=3.2)
        self.cues+=[Cue(round(finish+2.2,3),'reset',note='重置检查'),Cue(round(finish+4.7,3),'mark',note='演出结束')]
        self.cues.sort(key=lambda cue:cue.t)
        self.end=self.cues[-1].t
        self.starts=[row['start'] for row in self.utterances]

    def add_round(self,t,scene,emotion,action='',lead=0,cut=None):
        t=round(t,3)
        self.cues.extend([Cue(t,'event',E.BOARD_KEY_PRESSED,note='倾听下一句'),Cue(round(t+.4,3),'event',E.AUDIO_VAD_END)])
        return self.add_speech(round(t+.55,3),scene,emotion,action,lead,cut)

    def add_speech(self,t,scene,emotion,action='',lead=0,cut=None):
        start=round(t+lead,3)
        duration=len(self.clips[scene])/RATE if cut is None else cut
        end=round(start+duration,3)
        label=self.scenes[scene]['label'] if cut is None else '中途打断'
        row={'scene':scene,'label':label,'text':self.scenes[scene]['text'],'emotion':emotion,
             'reply_at':t,'start':start,'end':end,'interrupted':cut is not None}
        self.utterances.append(row)
        self.cues.append(Cue(t,'reply',{'reply_text':row['text'],'emotion':emotion,'avatar_action':action},label,end-t))
        self.cues.append(Cue(end,'cancel' if cut is not None else 'stop',note='中途打断并收口' if cut else '语音播放结束'))
        return end

    def utterance_at(self,t):
        i=bisect.bisect_right(self.starts,t)-1
        return self.utterances[i] if i>=0 and t<self.utterances[i]['end'] else None

    def gain_at(self,t):
        i=bisect.bisect_right(self.starts,t)-1
        if i<0:return 0.0
        row=self.utterances[i]
        elapsed=t-row['start']
        if t>=row['end']:
            if not row['interrupted'] or t>=row['end']+.18:return 0.0
            u=(t-row['end'])/.18
            return self._clip_gain(row['scene'],row['end']-row['start'])*(1-u*u*(3-2*u))
        return self._clip_gain(row['scene'],elapsed)

    def _clip_gain(self,scene,t):
        gains=self.envelopes[scene]['gains']
        p=max(0,t/HOP);left=int(p)
        if left>=len(gains):return 0.0
        a=gains[left];b=gains[left+1] if left+1<len(gains) else 0.0
        return a+(b-a)*(p-left)

    def write_audio(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        track=np.zeros(round(self.end*RATE),dtype='<i2')
        for row in self.utterances:
            n=round((row['end']-row['start'])*RATE)
            chunk=self.clips[row['scene']][:n].copy()
            if row['interrupted']:
                fade=min(round(.02*RATE),n)
                chunk[-fade:]=(chunk[-fade:].astype(float)*np.linspace(1,0,fade)).astype('<i2')
            start=round(row['start']*RATE);track[start:start+len(chunk)]=chunk
        with wave.open(str(path),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(RATE);stream.writeframes(track.tobytes())
        return track

    def public(self):
        return {'voice':'柔亮俏皮','duration_seconds':self.end,'sample_rate':RATE,
                'audio_clock':'actual audio output / browser audio.currentTime',
                'mouth_method':'energy activity + local mouth loop; not phoneme alignment',
                'utterances':self.utterances,'envelopes':self.envelopes}


class SelectedVoiceRunner(ScriptRunner):
    def __init__(self,core,plan=None,effects=False):
        super().__init__(core,dt=1/30)
        self.plan=plan or VoicePlan()
        self.cursor=0;self.previous=-1.0
        self.facials=None
        if effects:
            from tools.facial_layers import FacialController
            self.facials=FacialController(core,self.plan)

    def reset(self):
        super().reset()
        self.cursor=0;self.previous=-1.0;self.core.speech_gain=0.0

    def advance(self,t):
        if t<self.previous-1e-6:raise ValueError('Reset the runner before replaying or seeking backward')
        self.previous=t
        while self.cursor<len(self.plan.cues) and self.plan.cues[self.cursor].t<=t+1e-9:
            cue=self.plan.cues[self.cursor];self._fire(cue,cue.t);self.cursor+=1
        self.core.speech_gain=self.plan.gain_at(t)
        meta=self._sample(t)
        if meta is not None:
            row=self.plan.utterance_at(t)
            meta.update(audio_scene=row['scene'] if row else None,audio_time=t,
                        speech_gain=self.core.speech_gain)
            self.trace.samples[-1].update(speech_gain=self.core.speech_gain,audio_scene=meta['audio_scene'])
            if self.facials:
                meta=self.facials.apply(meta,t)
                self.trace.samples[-1].update(blink_active=meta['blink_active'],blink_phase=meta['blink_phase'],mouth_level=meta['mouth_level'])
        return meta


def run_qt_window(verification_path=None,effects=False):
    """Clock the same runner from audio frames processed by the output device."""
    import time
    from PySide6.QtCore import QByteArray,QBuffer,QIODevice,QTimer,Qt
    from PySide6.QtGui import QImage,QPixmap,QShortcut,QKeySequence
    from PySide6.QtMultimedia import QAudioSink,QAudioFormat,QMediaDevices
    from PySide6.QtWidgets import QApplication,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QProgressBar
    app=QApplication.instance() or QApplication([])
    output=OUT if not effects else OUT.parent/'2026-10-06_voice_blink'
    output.mkdir(exist_ok=True)
    plan=VoicePlan();audio=plan.write_audio(output/'audio'/'script.wav')
    core=create_demo_core('reuse');cache=warm_script_assets(core);runner=SelectedVoiceRunner(core,plan,effects=effects)
    fmt=QAudioFormat();fmt.setSampleRate(RATE);fmt.setChannelCount(1);fmt.setSampleFormat(QAudioFormat.Int16)
    device=QMediaDevices.defaultAudioOutput()
    if device.isNull():raise RuntimeError('未发现音频输出设备；请改用浏览器试听入口')
    sink=QAudioSink(device,fmt);sink.setVolume(.9)
    buffer=QBuffer();buffer.setData(QByteArray(audio.tobytes()));buffer.open(QIODevice.ReadOnly)
    window=QWidget();window.setWindowTitle('AURA · 柔亮俏皮（独立眨眼与语音）' if effects else 'AURA · 柔亮俏皮（真实语音与口型）');window.resize(800,545)
    window.setStyleSheet('QWidget{background:#FCFCF3;color:#283540;font:15px "Microsoft YaHei";} QPushButton{padding:10px;border:1px solid #aabfc7;border-radius:8px;}')
    layout=QHBoxLayout(window);stage=QLabel();stage.setFixedSize(464,480);stage.setAlignment(Qt.AlignCenter);layout.addWidget(stage)
    panel=QVBoxLayout();layout.addLayout(panel)
    heading=QLabel('汐蓝 · 柔亮俏皮');panel.addWidget(heading)
    label=QLabel();label.setWordWrap(True);panel.addWidget(label)
    text=QLabel();text.setWordWrap(True);panel.addWidget(text)
    panel.addStretch();progress=QProgressBar();progress.setRange(0,round(plan.end*100));panel.addWidget(progress)
    clock=QLabel();panel.addWidget(clock)
    replay=QPushButton('重播全剧（F5）');pause=QPushButton('暂停');panel.addWidget(replay);panel.addWidget(pause)
    timer=QTimer(window);timer.setInterval(16)
    frames=[];paused=False;last_audio=0.0;started=0.0;last_progress=0.0;finished=False;ended_at=None;idle_blink_samples=0
    states={'IDLE':'待机','PRESENT':'来访待机','AWAKE':'唤醒','LISTENING':'聆听','THINKING':'思考','ACK_NOD':'点头',
            'SPEAKING_NEUTRAL':'中性说话','SPEAKING':'兴奋说话','SPEAKING_LOW':'低落与安慰'}

    def reset():
        nonlocal paused,last_audio,started,last_progress,finished,ended_at,idle_blink_samples
        sink.stop();buffer.seek(0);runner.reset();frames.clear();paused=False;last_audio=0;started=time.perf_counter()
        last_progress=0.0;finished=False;ended_at=None;idle_blink_samples=0;pause.setEnabled(True);pause.setText('暂停');sink.start(buffer);timer.start()

    def tick():
        nonlocal last_audio,last_progress,finished,ended_at,idle_blink_samples
        # Device buffers report time in blocks. Once every PCM byte has been
        # consumed and the sink is idle, a final partial block is complete too.
        t=output_clock_seconds(sink.processedUSecs(),plan.end,last_audio,
                               idle=sink.state().name=='IdleState',exhausted=buffer.atEnd(),paused=paused)
        last_audio=t
        render_time=plan.end+time.perf_counter()-ended_at if effects and ended_at is not None else t
        if finished:
            meta=core.frame_at(core.fsm.state.label,render_time)
            if meta:
                meta=dict(meta,display_state=core.fsm.state.label,speech_gain=0,mouth_level=0)
                meta=runner.facials.eyes.apply(meta,render_time,core)
        else:meta=runner.advance(render_time)
        if meta:
            image=meta['image'].convert('RGBA');raw=image.tobytes()
            qimage=QImage(raw,image.width,image.height,image.width*4,QImage.Format_RGBA8888).copy()
            stage.setPixmap(QPixmap.fromImage(qimage))
            shown=meta.get('display_state');row=plan.utterance_at(t)
            label.setText('演出结束，眨眼继续运行' if finished and effects else row['label'] if row else states.get(shown,shown))
            text.setText(row['text'] if row else ('语音已打断，正在收口' if any(u['interrupted'] and u['end']<=t<u['end']+.4 for u in plan.utterances) else ''))
            if finished and meta.get('blink_active'):idle_blink_samples+=1
            if not finished:frames.append({'audio_time':t,'wall_time':time.perf_counter()-started,'display_state':shown,
                           'speech_gain':meta['speech_gain'],'asset':meta['asset'],
                           'blink_active':meta.get('blink_active',False),'mouth_level':meta.get('mouth_level',0)})
        progress.setValue(round(t*100));clock.setText(f'{t:.1f} / {plan.end:.1f} 秒')
        if sink.error().value:
            timer.stop();label.setText('音频输出异常，请使用浏览器试听')
            (output/'qt_window_verification.json').write_text(json.dumps({'status':'FAIL','error':sink.error().name,'audio_time':t},ensure_ascii=False),encoding='utf-8');return
        if time.perf_counter()-last_progress>=2:
            last_progress=time.perf_counter()
            (output/'qt_progress.json').write_text(json.dumps({'audio_time':t,'wall_seconds':time.perf_counter()-started,
                'sink_state':sink.state().name,'buffer_at_end':buffer.atEnd(),'error':sink.error().name,'samples':len(frames),
                'finished':finished,'idle_blink_samples':idle_blink_samples}),encoding='utf-8')
        if t>=plan.end-.001 and not finished:
            finished=True;ended_at=time.perf_counter()
            if not effects:timer.stop()
            sink.stop();label.setText('演出结束，眨眼继续运行' if effects else '演出结束，可重播');pause.setText('暂停');pause.setEnabled(False)
            result={'status':'PASS' if not runner.trace.errors and not runner.trace.rejected else 'FAIL',
                    'clock':'QAudioSink.processedUSecs','duration_seconds':plan.end,'samples':len(frames),
                    'audio_device':device.description(),'asset_preload':cache,
                    'errors':runner.trace.errors,'rejected':runner.trace.rejected,
                    'final_state':core.fsm.state.label,'frames':frames}
            target=Path(verification_path) if verification_path else output/'qt_window_verification.json'
            target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

    def toggle():
        nonlocal paused
        if not timer.isActive() or finished:return
        paused=not paused
        sink.suspend() if paused else sink.resume()
        pause.setText('继续' if paused else '暂停')
    replay.clicked.connect(reset);pause.clicked.connect(toggle);timer.timeout.connect(tick)
    shortcut=QShortcut(QKeySequence('F5'),window);shortcut.activated.connect(reset)
    app.aboutToQuit.connect(sink.stop)
    window.show();window.raise_();window.activateWindow();reset();app.exec()
    return runner.trace
