"""GTK controls for one finite edge-follow window, with exclusive motor owner."""
import copy,hashlib,json,os,signal,subprocess,threading,time
from pathlib import Path
from tools.pan_controls import stage_type as manual_stage_type


class FacePanProcess:
    def __init__(self, config, *, manual_factory=None):
        if manual_factory is None:
            from board.motion.manual_process import ManualPanProcess
            manual_factory=lambda:ManualPanProcess(config)
        self.config=config;self.factory=manual_factory
        self.manual=self.factory();self.lock=threading.RLock();self.running=self.closed=False
        self.cancelled=threading.Event();self.child=None;self.thread=None;self.result={}

    def read(self):
        with self.lock:
            value=self.manual.read()
            if self.running:
                value.update(state='MOVING',automatic_following=True,
                    message='人脸边缘随动：中间保持，靠近边缘才转；最多10秒',error='')
            value['face_follow']=copy.deepcopy(self.result)
            return value

    def jog(self,*args,**kwargs):
        with self.lock:
            if self.running:raise ValueError('请先停止人脸随动')
            return self.manual.jog(*args,**kwargs)
    def reverse(self):
        with self.lock:
            if self.running:raise ValueError('请先停止人脸随动')
            return self.manual.reverse()
    def reconnect(self):
        with self.lock:
            if self.running:raise ValueError('请先停止人脸随动')
            return self.manual.reconnect()
    def stop(self):
        with self.lock:
            if not self.running:return self.manual.stop()
            self.cancelled.set()
            if self.child is not None and self.child.poll() is None:self.child.send_signal(signal.SIGTERM)
            return dict(ok=True,message='正在停止人脸随动')
    def close(self):
        with self.lock:self.closed=True
        self.stop()
        if self.thread:self.thread.join(timeout=3)
        self.manual.close()

    def start(self):
        with self.lock:
            if self.closed or self.running:raise ValueError('请等待本次随动结束')
            state=self.manual.read();r=state.get('readback') or {}
            if state['state']!='READY' or r.get('flags')!=0 or r.get('lease_left_ms')!=0:
                raise ValueError('请先恢复转轴连接并停止点动')
            self.running=True;self.cancelled.clear();self.result=dict(state='STARTING')
            self.thread=threading.Thread(target=self.work,name='aura-face-follow',daemon=True);self.thread.start()
        return dict(ok=True,message='开始10秒人脸边缘随动')

    def arguments(self):
        cfg=json.loads(Path(self.config['face_follow_config']).read_text())
        root=Path(cfg['release_root']);m=root/'deployment-manifest.json'
        if hashlib.sha256(m.read_bytes()).hexdigest()!=cfg['manifest_sha256']:raise RuntimeError('Follow release changed')
        manifest=json.loads(m.read_text())
        if not all(hashlib.sha256(Path(x['destination']).read_bytes()).hexdigest()==x['sha256'] for x in manifest['files']):
            raise RuntimeError('Follow source changed')
        output=root/'runs'/('ui-'+str(time.monotonic_ns()))/'trial.json'
        args=['/usr/bin/python3','-B',str(root/'run_face_motion.py')]
        for key,value in cfg['arguments'].items():args+=['--'+key,value]
        return args+['--output',str(output),'--confirmation','FACE_EDGE_OBSERVED_RANGE','--duration','10'],output

    def work(self):
        released=False
        try:
            args,output=self.arguments()
            # The GUI stays visible; only its manual motor child gives up the lock.
            self.manual.close()
            released=True
            if self.cancelled.is_set():return
            with self.lock:
                if self.cancelled.is_set():return
                self.child=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:stdout,stderr=self.child.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                self.child.send_signal(signal.SIGTERM)
                try:stdout,stderr=self.child.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    self.child.kill();stdout,stderr=self.child.communicate(timeout=2)
            report=json.loads(output.read_text()) if output.exists() else {}
            result=report.get('result',{})
            self.result=dict(state=report.get('status','FAILED'),reason=result.get('reason',report.get('error','No report')),
                commands_accepted=result.get('commands_accepted',0),elapsed_s=result.get('elapsed_s'),
                final_flags=result.get('stopped',{}).get('flags'),report=str(output),
                error=stderr[-160:] if self.child.returncode else '')
        except BaseException as exc:self.result=dict(state='FAILED',reason=type(exc).__name__+': '+str(exc)[:160])
        finally:
            # A new manual backend must acquire the same exclusive flock.
            with self.lock:
                self.child=None
                if released and not self.closed:self.manual=self.factory()
            if released and not self.closed:
                end=time.monotonic()+5
                while time.monotonic()<end:
                    state=self.manual.read()
                    if state['state']=='READY':
                        if state['left_sign']==-1:self.manual.reverse()
                        break
                    if state['state']=='FAULT':break
                    time.sleep(.05)
            with self.lock:self.running=False


def stage_type(base, factory):
    manual=manual_stage_type(base,factory)
    class FaceStage(manual):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.bridge.allowed_commands.add('pan_face_follow')
        def command(self,data):
            if data.get('type')=='pan_face_follow':return self.pan.start()
            return super().command(data)
        def open_pan_dialog(self):
            existing=self.pan_dialog
            result=super().open_pan_dialog()
            if not existing:
                button=self.Gtk.Button(label='人脸边缘随动 · 10秒')
                button.set_size_request(220,52)
                button.connect('clicked',lambda *_:self.native({'type':'pan_face_follow'}))
                self.pan_dialog.get_child().pack_start(button,False,False,0)
                button.show()
                self.pan_message.set_text('中间不动；脸接近左右边缘才转。停止按钮可随时结束。')
            return result
    return FaceStage
