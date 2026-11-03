"""汐蓝 local live stage: real Qt audio, existing sprite FSM and loopback UI."""
from __future__ import annotations
import argparse
from collections import deque
import io
import hashlib
import json
from pathlib import Path
import queue
import sys
import time

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QImage,QPixmap
from PySide6.QtWidgets import QApplication,QWidget,QLabel,QVBoxLayout,QHBoxLayout,QTextEdit,QPushButton,QComboBox
from PIL import Image
from board.runtime.character import CHARACTER_NAME,CHARACTER_DESCRIPTION,DEMO_LINES
from board.runtime.audio.selected_voice import WORKSPACE
from tools.demo_script import create_demo_core
from tools.selected_voice_service import SpeechJobs,VoiceWorker
from tools.realtime_audio import SelectedAudioOutput
from tools.realtime_controller import RealtimeController
from tools.realtime_bridge import StageBridge
from tools.realtime_dialogue import DialogueConnection
from tools.realtime_metrics import summarize

DEFAULT_ROOT=AURA.parent/'deliverables/2026-10-06_xilan_live'
PHASES={'IDLE':'等你开口','VOICE_PREPARING':'正在准备声音…','VOICE_STARTING':'正在准备播放…','SPEAKING':'正在说话','ACTION':'正在回应','DIALOGUE_WAITING':'正在思考…'}

def load_config(path):
    config=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if config.get('schema_version')!=1:raise ValueError('Unsupported stage configuration')
    return config

def runtime_path(value):
    if not value:return None
    path=Path(value);return path if path.is_absolute() else WORKSPACE/path

def warm(core):
    states=('IDLE','PRESENT','AWAKE','LISTENING','THINKING','ACK_NOD','DENY_SHAKE','PUZZLED')
    core.MAX_CACHED_SEQUENCES=len(states)
    for state in states:core.sequence(state);core.sop(state)

class LiveStage(QWidget):
    def __init__(self,root,config,port):
        super().__init__();self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        voice=config.get('voice',{});core=create_demo_core('reuse');warm(core)
        self.jobs=SpeechJobs(root,VoiceWorker(root,python=runtime_path(voice.get('python')),model_path=runtime_path(voice.get('model_path'))))
        self.controller=RealtimeController(core,self.jobs,SelectedAudioOutput(self.root/'audio_output.log'))
        self.dialogue=DialogueConnection(config.get('dialogue',{}))
        self.bridge=StageBridge(root,port);self.samples=deque(maxlen=20000);self.errors=[];self.closed=False
        self.last_tick=None;self.last_publish=0.;self.last_image=None;self.dialogue_input=''
        self.source_hashes={f'tools/{name}':hashlib.sha256((AURA/'tools'/name).read_bytes()).hexdigest()
                            for name in ('realtime_stage.py','realtime_controller.py','realtime_audio.py','realtime_audio_worker.py','realtime_facials.py','realtime_bridge.py','realtime_dialogue.py','realtime_metrics.py','selected_voice_service.py','facial_layers.py','mouth_compositor.py')}
        reuse_source=AURA.parent/'deliverables/2026-10-06_avatar_reuse/preview_script.py'
        self.source_hashes['../deliverables/2026-10-06_avatar_reuse/preview_script.py']=hashlib.sha256(reuse_source.read_bytes()).hexdigest()
        self.setWindowTitle(f'{CHARACTER_NAME} · {CHARACTER_DESCRIPTION} · 实时交互演示');self.resize(930,680)
        self.setStyleSheet('QWidget{background:#111e30;color:#e5edf8;font-size:15px} QPushButton,QComboBox,QTextEdit{background:#20364f;border:1px solid #375873;border-radius:7px;padding:9px} QPushButton:hover{background:#315978} QLabel#title{font-size:27px;font-weight:600}')
        layout=QHBoxLayout(self);left=QVBoxLayout();right=QVBoxLayout();layout.addLayout(left);layout.addLayout(right)
        title=QLabel(f'{CHARACTER_NAME}');title.setObjectName('title');left.addWidget(title)
        left.addWidget(QLabel(f'{CHARACTER_DESCRIPTION} · 柔亮俏皮'))
        self.portrait=QLabel();self.portrait.setFixedSize(464,480);left.addWidget(self.portrait)
        self.status=QLabel('正在启动');left.addWidget(self.status)
        right.addWidget(QLabel(f'让{CHARACTER_NAME}说一句（最多 240 字）'))
        self.text=QTextEdit();self.text.setPlainText(DEMO_LINES[0]['text']);self.text.setMaximumHeight(130);right.addWidget(self.text)
        self.emotion=QComboBox()
        for label,value in [('平静','neutral'),('开心','happy'),('温柔安慰','sad')]:self.emotion.addItem(label,value)
        self.action=QComboBox()
        for label,value in [('自然说话',''),('先点头','ack_nod'),('先摇头','deny_shake'),('先惊讶','emo_surprised'),('先疑惑','emo_puzzled')]:self.action.addItem(label,value)
        row=QHBoxLayout();row.addWidget(self.emotion);row.addWidget(self.action);right.addLayout(row)
        button=QPushButton('开始说话');button.clicked.connect(lambda:self.native({'type':'speak','text':self.text.toPlainText(),'emotion':self.emotion.currentData(),'action':self.action.currentData()}));right.addWidget(button)
        row=QHBoxLayout()
        for label,data in [('暂停 / 继续',{'type':'pause'}),('打断',{'type':'event','event':'cancel'})]:
            button=QPushButton(label);button.clicked.connect(lambda checked=False,d=data:self.native(d));row.addWidget(button)
        right.addLayout(row);right.addWidget(QLabel('快速体验'))
        for index,label in enumerate(['打招呼','开心回应 · 点头','轻声安慰','长句说明']):
            button=QPushButton(label);button.clicked.connect(lambda checked=False,i=index:self.native({'type':'demo','index':i}));right.addWidget(button)
        right.addWidget(QLabel('场景状态'))
        row=QHBoxLayout()
        for label,event in [('有人靠近','person_enter'),('唤醒','wake'),('倾听','listen'),('重置','reset')]:
            button=QPushButton(label);button.clicked.connect(lambda checked=False,e=event:self.native({'type':'event','event':e}));row.addWidget(button)
        right.addLayout(row)
        right.addWidget(QLabel('对话接口已配置' if self.dialogue.enabled else '对话模型未连接 · 可在另一台电脑接入'))
        right.addWidget(QLabel(f'浏览器同步控制：http://127.0.0.1:{port}/\n声音由本机演示窗口播放。'));right.addStretch()
        self.timer=QTimer(self);self.timer.setTimerType(Qt.TimerType.PreciseTimer);self.timer.timeout.connect(self.tick);self.timer.start(16)

    def native(self,data):
        try:self.command(data)
        except Exception as exc:self.controller.last_error=str(exc)

    def command(self,data):
        kind=data['type']
        if kind=='speak':
            job=self.controller.submit(data['text'],data.get('emotion','neutral'),data.get('action',''));return {'ok':True,'job':job}
        if kind=='demo':
            index=data.get('index')
            if not isinstance(index,int) or not 0<=index<len(DEMO_LINES):raise ValueError('请选择有效台词')
            line=DEMO_LINES[index];self.text.setPlainText(line['text']);return self.command(dict(type='speak',**line))
        if kind=='event':self.controller.event(data['event'])
        elif kind=='pause':self.controller.toggle_pause()
        elif kind=='dialogue':
            if not self.dialogue.enabled:raise ValueError('对话模型未连接，请先配置服务')
            from board.runtime.audio.selected_voice import normalize_text
            text=normalize_text(data.get('text'));generation=self.controller.begin_dialogue()
            try:self.dialogue.submit(text,generation)
            except Exception:
                self.controller.cancel();raise
            self.dialogue_input=text
        elif kind in {'snapshot','save_evidence'}:
            return self.save_evidence()
        else:raise ValueError('不支持的操作')
        return {'ok':True}

    def tick(self):
        if self.closed:return
        started=time.perf_counter();interval=None if self.last_tick is None else (started-self.last_tick)*1000;self.last_tick=started
        try:
            for _ in range(16):
                try:request=self.bridge.commands.get_nowait()
                except queue.Empty:break
                if time.monotonic()>request['deadline']:request['error']='操作已超时';request['done'].set();continue
                try:request['result']=self.command(request['data'])
                except Exception as exc:request['error']=str(exc);self.controller.last_error=str(exc)
                request['done'].set()
            result=self.dialogue.poll()
            if result:
                if result['generation']!=self.controller.core.talk_gen:self.controller.metrics['late_results_dropped']+=1
                elif result.get('error'):self.controller.last_error=result['error'];self.controller.cancel()
                else:self.controller.accept_dialogue(result['generation'],result['text'],result['emotion'],result['action'])
            meta=self.controller.tick()
            if meta:
                background=Image.new('RGBA',meta['image'].size,(22,41,63,255));background.alpha_composite(meta['image']);self.last_image=background.convert('RGB')
                raw=self.last_image.tobytes();qimage=QImage(raw,self.last_image.width,self.last_image.height,self.last_image.width*3,QImage.Format.Format_RGB888).copy()
                self.portrait.setPixmap(QPixmap.fromImage(qimage))
            state=self.controller.public();state.update(character=CHARACTER_NAME,description=CHARACTER_DESCRIPTION,voice='柔亮俏皮',dialogue_enabled=self.dialogue.enabled,dialogue_input=self.dialogue_input)
            state['status_text']='已暂停' if state['paused'] else PHASES.get(state['phase'],state['phase'])
            self.status.setText(state['error'] or state['status_text'])
            self.samples.append({'t':round(state['visual_time'],4),'interval_ms':interval,'render_ms':(time.perf_counter()-started)*1000,
                                  **{key:state[key] for key in ('phase','state','asset','index','speech_gain','mouth_level','blink_active','playing','paused','audio_time')}})
            if started-self.last_publish>=1/30 and self.last_image:
                stream=io.BytesIO();self.last_image.save(stream,format='JPEG',quality=90)
                self.bridge.publish(state,stream.getvalue());self.last_publish=started
        except Exception as exc:
            message=f'{type(exc).__name__}: {exc}';self.controller.last_error=message
            if not self.errors or self.errors[-1]!=message:self.errors.append(message);print('STAGE ERROR '+message,flush=True)
            # Leave controls reachable even after a failed audio device or voice request.
            try:self.controller.cancel()
            except Exception:pass

    def save_evidence(self):
        evidence=self.root/'evidence';evidence.mkdir(exist_ok=True)
        stamp=f'{time.time_ns()}';self.grab().save(str(evidence/f'window_{stamp}.png'))
        if self.last_image:self.last_image.save(evidence/f'frame_{stamp}.png')
        samples=list(self.samples);stats=summarize(samples)
        report={'character':CHARACTER_NAME,'mode':'actual local Qt audio and live controls; no dialogue model connected' if not self.dialogue.enabled else 'configured dialogue host',
                'source_hashes_at_launch':self.source_hashes,'state':self.controller.public(),'stats':stats,'errors':self.errors,'samples':samples}
        path=evidence/f'live_{stamp}.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        (self.root/'latest_verification.json').write_text(json.dumps({key:value for key,value in report.items() if key!='samples'},ensure_ascii=False,indent=2),encoding='utf-8')
        return {'ok':True,'report':path.name,'stats':stats}

    def closeEvent(self,event):
        self.closed=True;self.timer.stop();self.save_evidence();self.controller.cancel();self.controller.output.close();self.jobs.close();self.dialogue.close();self.bridge.close();event.accept()

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    parser.add_argument('--config',type=Path);parser.add_argument('--port',type=int);parser.add_argument('--check',action='store_true');args=parser.parse_args(argv)
    config=load_config(args.config or args.root/'stage_config.json');port=args.port or int(config.get('browser_port',8773))
    if args.check:
        core=create_demo_core('reuse');warm(core)
        from tools.realtime_facials import RealtimeFacials
        facials=RealtimeFacials(core);worker=VoiceWorker(args.root);clips=[]
        for line in DEMO_LINES:
            cached=worker.synth.cached(line['text'])
            if not cached:raise ValueError('Missing or changed cached demonstration: '+line['id'])
            clips.append({'id':line['id'],'sha256':cached['sha256'],'cache_hit':cached['cache_hit']})
        print(json.dumps({'status':'PASS','character':CHARACTER_NAME,'cached_clips':clips,'mouth_sets':len(facials.mouths.keys),
                          'blink_poses':len(facials.eyes.images),'inference_model_loaded':worker.synth.model is not None},ensure_ascii=False));worker.close();return 0
    application=QApplication.instance() or QApplication(sys.argv[:1]);window=LiveStage(args.root,config,port);window.show()
    print(f'READY {CHARACTER_NAME} http://127.0.0.1:{port}/',flush=True);return application.exec()

if __name__=='__main__':raise SystemExit(main())
