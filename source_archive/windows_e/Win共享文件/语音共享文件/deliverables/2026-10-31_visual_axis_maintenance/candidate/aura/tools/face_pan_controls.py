"""Continuous face following with visible start/stop and exclusive motor owner."""
import copy,hashlib,json,math,os,signal,subprocess,threading,time
from pathlib import Path
from tools.pan_controls import stage_type as manual_stage_type
from tools.follow_process_cleanup import terminate_follow_child,describe

FOLLOW_REPORT_TTL_MS=1500


class FacePanProcess:
    def __init__(self, config, *, manual_factory=None):
        if manual_factory is None:
            from board.motion.manual_process import ManualPanProcess
            manual_factory=lambda:ManualPanProcess(config)
        self.config=config;self.factory=manual_factory
        self.manual=self.factory();self.lock=threading.RLock();self.running=self.closed=False
        self.cancelled=threading.Event();self.child=None;self.thread=None;self.result={}
        self.output=None;self.last_report_read=0
        self.cleanup_pending=self.cleanup_running=False

    def read(self):
        with self.lock:
            value=self.manual.read()
            if self.running:
                if not self.cleanup_pending and self.output is not None and time.monotonic()-self.last_report_read>=.5:
                    try:
                        report=json.loads(self.output.read_text());r=report.get('result',{})
                        self.result=dict(state=report.get('status'),phase=r.get('state'),reason=r.get('reason'),
                            commands_accepted=r.get('commands_accepted',0),segments=r.get('segments',0),
                            pulse_us=r.get('pulse_us'),control=r.get('control'),
                            readback=r.get('readback'),heartbeat_mono_ms=r.get('heartbeat_mono_ms'),report=str(self.output))
                    except (OSError,ValueError):pass
                    self.last_report_read=time.monotonic()
                phase=self.result.get('phase');reason=self.result.get('reason')
                message=('人脸越界，正在平滑跟随' if phase=='FOLLOWING' else
                    '已到本次转动范围，等待人脸回到区域内' if phase=='HOLD_AT_LIMIT' else
                    '人脸在边界内，转轴保持' if reason in ('SAFE_ZONE_HOLD','SAFE_ZONE_REACHED') else '监测中，等待清晰单张人脸')
                heartbeat=self.result.get('heartbeat_mono_ms')
                age=(time.monotonic()*1000-heartbeat if type(heartbeat) in (int,float)
                     and math.isfinite(heartbeat) else None)
                fresh=(self.result.get('state')=='CONTINUOUS_FACE_ZONE_RUNNING'
                       and age is not None and -1<=age<FOLLOW_REPORT_TTL_MS)
                self.result.update(report_fresh=fresh,report_age_ms=None if age is None else round(age))
                if not fresh:message='跟随状态暂不可用，可点击停止'
                if self.cleanup_pending:message='停止尚未确认，可再次点击停止'
                # The former manual owner has released its lock. Its last pulse
                # is historical, and a stale follow report is not current feedback.
                value.update(state='STOPPING' if self.cleanup_pending else 'MOVING' if fresh else 'UNAVAILABLE',
                    automatic_following=True,message=message,error='',
                    pulse_us=None,target_us=None,readback=None)
                readback=self.result.get('readback');pulse=self.result.get('pulse_us')
                if (fresh and not self.cleanup_pending and isinstance(readback,dict)
                        and type(pulse) is int and 500<=pulse<=2500 and readback.get('width_us')==pulse):
                    value.update(pulse_us=pulse,target_us=readback.get('target_us'),readback=copy.deepcopy(readback))
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
            if self.child is not None:
                try:self.child.send_signal(signal.SIGTERM)
                except BaseException as exc:self.result['stop_request_error']=describe(exc)
            if (self.cleanup_pending and not self.cleanup_running
                    and (self.thread is None or not self.thread.is_alive())):
                self.cleanup_running=True
                self.thread=threading.Thread(target=lambda:self.finish_owner(True),name='aura-face-stop-retry',daemon=True)
                try:self.thread.start()
                except BaseException as exc:
                    self.cleanup_running=self.thread.is_alive();self.result['stop_retry_error']=describe(exc)
            return dict(ok=True,message='正在停止人脸随动')
    def close(self):
        with self.lock:self.closed=True
        self.stop()
        if self.thread and self.thread.is_alive():self.thread.join(timeout=4.5)
        with self.lock:
            if self.child is None:self.manual.close()

    def start(self):
        with self.lock:
            if self.config.get('automatic_following_enabled', True) is not True:
                raise ValueError('人脸随动尚未开放，请先完成方向确认')
            sign=self.config.get('left_button_pulse_sign',1)
            if type(sign) is not int or sign not in (-1,1):
                raise ValueError('转轴方向参数无效，请先确认方向')
            if self.closed or self.running:raise ValueError('请等待本次随动结束')
            state=self.manual.read();r=state.get('readback') or {}
            if state['state']!='READY' or r.get('flags')!=0 or r.get('lease_left_ms')!=0:
                raise ValueError('请先恢复转轴连接并停止点动')
            self.running=True;self.cancelled.clear();self.result=dict(state='STARTING')
            self.thread=threading.Thread(target=self.work,name='aura-face-follow',daemon=True)
            try:self.thread.start()
            except BaseException:
                self.cancelled.set()
                if not self.thread.is_alive():self.running=False;self.thread=None
                raise
        return dict(ok=True,message='已开启人脸跟随；边界内保持，丢脸即停')

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
        if cfg.get('mode')!='continuous_face_zone':raise RuntimeError('Explicit continuous mode required')
        duration=cfg.get('duration_s',0)
        if type(duration) not in (int,float) or not math.isfinite(duration) or not 0<=duration<=300:
            raise RuntimeError('Finite follow duration required')
        return args+['--output',str(output),'--confirmation','FACE_ZONE_CONTINUOUS','--duration',str(duration)],output

    def work(self):
        released=False
        try:
            args,output=self.arguments()
            self.output=output
            # The GUI stays visible; only its manual motor child gives up the lock.
            self.manual.close()
            released=True
            if self.cancelled.is_set():return
            with self.lock:
                if self.cancelled.is_set():return
                self.child=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            stopping=None
            while True:
                try:stdout,stderr=self.child.communicate(timeout=.5);break
                except subprocess.TimeoutExpired:
                    if self.cancelled.is_set() or self.closed:
                        if stopping is None:self.child.send_signal(signal.SIGTERM);stopping=time.monotonic()
                        elif time.monotonic()-stopping>2:
                            self.child.kill();stdout,stderr=self.child.communicate(timeout=2);break
            report=json.loads(output.read_text()) if output.exists() else {}
            result=report.get('result',{})
            self.result=dict(state=report.get('status','FAILED'),reason=result.get('reason',report.get('error','No report')),
                commands_accepted=result.get('commands_accepted',0),elapsed_s=result.get('elapsed_s'),
                final_flags=result.get('stopped',{}).get('flags'),report=str(output),
                error=stderr[-160:] if self.child.returncode else '')
        except BaseException as exc:
            with self.lock:self.result=dict(state='FAILED',reason=describe(exc));self.cleanup_pending=True
        finally:
            self.finish_owner(released)

    def finish_owner(self,released):
        with self.lock:
            child=self.child;self.cleanup_running=True;self.cleanup_pending=True
        if child is not None:
            try:cleanup=terminate_follow_child(child)
            except BaseException as exc:
                cleanup=dict(exit_confirmed=False,errors=[describe(exc)])
            with self.lock:
                self.result['process_cleanup']=cleanup
                if not cleanup['exit_confirmed']:
                    # Preserve the sole owner's handle and STOP control. No
                    # replacement manual backend may race a live follow child.
                    self.cleanup_pending=True;self.running=True;self.cleanup_running=False
                    return False
                self.child=None
        try:
            # The old child is confirmed exited before another backend exists.
            with self.lock:
                if released and not self.closed:self.manual=self.factory()
            if released and not self.closed:
                end=time.monotonic()+5
                while time.monotonic()<end:
                    state=self.manual.read()
                    if state['state']=='READY':
                        if state['left_sign']!=self.config.get('left_button_pulse_sign',1):self.manual.reverse()
                        break
                    if state['state']=='FAULT':break
                    time.sleep(.05)
        except BaseException as exc:
            with self.lock:self.result['manual_reopen_error']=describe(exc)
        finally:
            with self.lock:self.running=False;self.cleanup_running=self.cleanup_pending=False
        return True


def stage_type(base, factory):
    manual=manual_stage_type(base,factory)
    class FaceStage(manual):
        def __init__(self,*args,**kwargs):
            self.face_toolbar=self.face_status=None
            super().__init__(*args,**kwargs)
            self.bridge.allowed_commands.add('pan_face_follow')
            self.show_page(self.page)
        def attach_preview(self,area,name,width,height):
            # GstVideoOverlay renders directly into this native X11 window.
            # A GTK offscreen backing buffer must not overwrite those pixels.
            area.set_double_buffered(False);area.set_app_paintable(True)
            if not getattr(area,'_face_native_draw_connected',False):
                area._face_native_draw_connected=True
                area.connect('draw',self.face_native_draw,name)
            return super().attach_preview(area,name,width,height)
        def face_native_draw(self,area,context,name):
            if not getattr(area,'_face_native_expose_pending',False):
                area._face_native_expose_pending=True
                self.GLib.idle_add(self.face_native_expose,area,name)
            return True
        def face_native_expose(self,area,name):
            area._face_native_expose_pending=False
            preview=self.preview_output
            if preview is None or not area.get_mapped():return False
            with preview.lock:output=preview.outputs.get(name)
            if output is None:return False
            with output['lifecycle_lock']:
                if not preview.is_current(name,output):return False
                with preview.lock:reference=copy.deepcopy(output['reference']);cleared=output['cleared']
                if cleared or not reference or not 0<=time.monotonic()*1000-reference['captured_mono_ms']<250:return False
                sink=output['pipeline'].get_by_name('screen')
                preview.GstVideo.VideoOverlay.set_render_rectangle(sink,0,0,area.get_allocated_width(),area.get_allocated_height())
                preview.GstVideo.VideoOverlay.expose(sink)
            return False
        def build_window(self,windowed):
            super().build_window(windowed)
            self.face_status=self.Gtk.Label(label='人脸跟随未开启');self.face_status.set_size_request(400,24)
            self.face_status.set_no_show_all(True);self.fixed.put(self.face_status,604,490)
            self.face_toolbar=self.Gtk.Box(spacing=12);self.face_toolbar.set_no_show_all(True)
            self.face_toggle=self.Gtk.Button(label='开始人脸跟随');self.face_toggle.set_size_request(200,48)
            self.face_toggle.connect('clicked',lambda *_:self.native({'type':'pan_face_follow'}))
            self.face_toolbar.pack_start(self.face_toggle,False,False,0)
            stop=self.Gtk.Button(label='停止转轴');stop.set_size_request(184,48);stop.get_style_context().add_class('danger')
            stop.connect('clicked',lambda *_:self.native({'type':'pan_stop'}));self.face_toolbar.pack_start(stop,False,False,0)
            self.fixed.put(self.face_toolbar,604,520)
        def show_page(self,page):
            super().show_page(page)
            if self.face_toolbar is not None:
                visible=page=='vision' and self.pan_dialog is None
                if visible:
                    self.face_toolbar.show();self.face_status.show()
                    for child in self.face_toolbar.get_children():child.show()
                else:self.face_toolbar.hide();self.face_status.hide()
        def refresh_runtime(self,state,settings_text):
            super().refresh_runtime(state,settings_text)
            if self.preview_output is not None:
                display=self.preview_output.read('vision')
                camera=(self.runtime_view.get('snapshot') or {}).get('modules',{}).get('camera',{}).get('state')
                self.preview_placeholder.set_visible(self.preview_output.placeholder_visible(display,camera))
                if self.page=='vision':self.preview_image.queue_draw()
                state['native_canvas']={'visible':self.preview_image.get_visible(),'mapped':self.preview_image.get_mapped(),
                    'placeholder_visible':self.preview_placeholder.get_visible(),'double_buffered':self.preview_image.get_double_buffered(),
                    'width':self.preview_image.get_allocated_width(),'height':self.preview_image.get_allocated_height()}
            if self.face_toolbar is not None:
                value=state['manual_pan'];self.face_toggle.set_label('停止人脸跟随' if value.get('automatic_following') else '开始人脸跟随')
                self.face_status.set_text(value['message'] if value.get('automatic_following') else '人脸跟随未开启')
        def command(self,data):
            if data.get('type')=='pan_face_follow':return self.pan.stop() if self.pan.running else self.pan.start()
            return super().command(data)
        def open_pan_dialog(self):
            existing=self.pan_dialog
            result=super().open_pan_dialog()
            if self.face_toolbar is not None:self.face_toolbar.hide();self.face_status.hide()
            if not existing:
                button=self.Gtk.Button(label='开启 / 停止人脸跟随')
                button.set_size_request(220,52)
                button.connect('clicked',lambda *_:self.native({'type':'pan_face_follow'}))
                self.pan_dialog.get_child().pack_start(button,False,False,0)
                button.show()
                self.pan_message.set_text('只跟随人脸；边界内保持。停止按钮可随时结束。')
            return result
        def close_pan_dialog(self):
            super().close_pan_dialog()
            if self.face_toolbar is not None and self.page=='vision':self.show_page('vision')
    return FaceStage
