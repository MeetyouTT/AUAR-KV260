"""Qt display adapter; events and frame sampling stay in the shared ScriptRunner."""
import time
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QTimer,Qt
from PySide6.QtGui import QImage,QPixmap,QKeySequence,QShortcut
from PySide6.QtWidgets import QApplication,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QProgressBar

from preview_script import ScriptRunner
from tools.demo_script import SCRIPT,script_end
from fluency_metrics import write_review


def run_window(core):
    app=QApplication.instance() or QApplication([])
    runner=ScriptRunner(core,dt=1/30)
    cues=sorted(SCRIPT,key=lambda cue:cue.t)
    end=script_end()
    window=QWidget()
    using_reuse='talking_calm_reuse_v1' in core.pool('SPEAKING_NEUTRAL')
    window.setWindowTitle('AURA · 临时剧本（全说话口型）' if using_reuse else 'AURA · 临时剧本（原版对照）')
    window.resize(790,530)
    window.setStyleSheet('QWidget{background:#f4f3ef;color:#283540;font:15px "Microsoft YaHei";} QPushButton{padding:10px;border:1px solid #aabfc7;border-radius:8px;}')
    row=QHBoxLayout(window)
    stage=QLabel();stage.setFixedSize(464,480);stage.setAlignment(Qt.AlignCenter)
    row.addWidget(stage)
    panel=QVBoxLayout();row.addLayout(panel)
    heading=QLabel('现有素材 · 三档说话口型' if using_reuse else '原版素材 · 对照演出');heading.setWordWrap(True);panel.addWidget(heading)
    state=QLabel();state.setWordWrap(True);panel.addWidget(state)
    note=QLabel('重点观察：\n11.5–38.5 秒：中性短句／长句\n40.5–43.5 秒：高涨说话\n44.5–50 秒：低落说话\n51–59 秒：高涨与打断\n此窗口未连接真实语音。');note.setWordWrap(True);panel.addWidget(note)
    variant=QLabel();panel.addWidget(variant)
    marks=QLabel();marks.setWordWrap(True);panel.addWidget(marks)
    panel.addStretch()
    progress=QProgressBar();progress.setRange(0,int(end*100));panel.addWidget(progress)
    clock=QLabel();panel.addWidget(clock)
    replay=QPushButton('重播全剧（F5）');panel.addWidget(replay)
    timer=QTimer(window);timer.setInterval(33)
    cursor=0;wall=0.0
    submitted_frames=[];cue_delivery=[]

    def reset():
        nonlocal cursor,wall
        runner.reset();cursor=0;wall=time.perf_counter()
        submitted_frames.clear();cue_delivery.clear()
        marks.setText('演出开始');timer.start()

    def tick():
        nonlocal cursor
        tick_started=time.perf_counter()
        elapsed=tick_started-wall
        while cursor<len(cues) and cues[cursor].t<=elapsed:
            cue_delivery.append({'scheduled_seconds':cues[cursor].t,'delivered_seconds':time.perf_counter()-wall,
                                 'kind':cues[cursor].kind,'note':cues[cursor].note})
            runner._fire(cues[cursor],cues[cursor].t);cursor+=1
        meta=runner._sample(min(elapsed,end))
        if meta is not None:
            image=meta['image'].copy();image.thumbnail((464,480),Image.Resampling.LANCZOS)
            pixels=image.convert('RGBA').tobytes()
            qt_image=QImage(pixels,image.width,image.height,image.width*4,QImage.Format_RGBA8888).copy()
            stage.setPixmap(QPixmap.fromImage(qt_image))
            submitted_at=time.perf_counter()
            submitted_frames.append({'sampled_at_seconds':min(elapsed,end),'submitted_at_seconds':submitted_at-wall,
                                     'work_ms':(submitted_at-tick_started)*1000,
                                     'display_state':meta.get('display_state'),'asset':meta.get('asset'),
                                     'source_index':meta.get('index')})
            shown=meta.get('display_state')
            states={'SPEAKING_NEUTRAL':'中性说话','SPEAKING':'兴奋说话','SPEAKING_LOW':'低落说话','IDLE':'待机','LISTENING':'聆听','THINKING':'思考',
                    'PRESENT':'来访待机','AWAKE':'唤醒','PUZZLED':'疑惑','ACK_NOD':'点头','DENY_SHAKE':'摇头',
                    'CAMERA_LOST':'摄像头离线','NETWORK_LOST':'网络离线','CANCELLED':'已打断','ERROR':'异常'}
            state.setText(states.get(shown,shown or '准备中'))
            name=meta.get('asset','')
            names={'talking_calm_reuse_v1':'中性口型 A','talking_calm_reuse_v1_b':'中性口型 B',
                   'talking_high_reuse_v1':'高涨口型 A','talking_high_reuse_v1_b':'高涨口型 B','talking_low_reuse_v1':'低落口型'}
            variant.setText('当前：'+names[name] if name in names else '')
            if shown in ('SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW'):
                marks.setText('当前台词：\n'+core.reply_text)
            else:marks.setText('')
        progress.setValue(int(min(elapsed,end)*100));clock.setText(f'{min(elapsed,end):.1f} / {end:.0f} 秒')
        if elapsed>=end+.4:
            timer.stop();marks.setText('演出结束，可重播')
            # A completed real-window run is separate from virtual-clock evidence.
            import json
            speaking_assets={state:sorted({row['asset'] for row in runner.trace.samples if row.get('display_state')==state and row.get('asset')})
                             for state in ('SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW')}
            result={'duration_seconds':end,'samples':len(runner.trace.samples),'speaking_assets_used':speaking_assets,
                    'errors':runner.trace.errors,'rejected':runner.trace.rejected,
                    'final_state':core.fsm.state.label,'clock':'real_window_perf_counter_monotonic'}
            Path(__file__).with_name('speech_fix_window_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            write_review(submitted_frames,cue_delivery,end,using_reuse)

    timer.timeout.connect(tick);replay.clicked.connect(reset)
    shortcut=QShortcut(QKeySequence('F5'),window);shortcut.activated.connect(reset)
    window.show();window.raise_();window.activateWindow();reset()
    app.exec()
    return runner.trace
