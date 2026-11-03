"""Single-owner UVC preview with an explicitly selected, verified detector.

Optional CPU identity consumes the same immutable frames; no extra camera is
opened. This adapter has no motion, audio, model-host or FPGA control path.
The detector and association are loaded from A's explicitly pinned sources.
"""
import argparse
from board.vision.native_errors import PrimaryAdmissionDeferred
from collections import OrderedDict
import copy
import fcntl
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit
import uuid

AURA = Path(__file__).resolve().parents[2]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from board.interaction.ui_contract import ACTIONS, PROTOCOL, integer, millis, validate_action
from board.vision.local_preview import RawFrameStore, TRANSPORT
from board.vision.camera_device import CAMERA_IDENTITY, PINNED_CAMERA, CameraUnavailable, resolve_camera_device


class CameraState:
    """A bounded, expiring view of actual capture/inference observations."""
    def __init__(self,boot,epoch=None,clock=millis,detector_info=None,device=None):
        self.boot,self.epoch,self.clock = boot,epoch or uuid.uuid4().hex,clock
        self.camera_epoch = uuid.uuid4().hex
        self.device = copy.deepcopy(device)
        self.session = uuid.uuid4().hex
        self.lock = threading.RLock()
        self.sequence = self.capture_frames = self.detected_frames = self.preview_frames = 0
        self.capture_stamp = self.processed_stamp = None
        self.frames = OrderedDict()
        self.observation = None
        self.detector_error = self.camera_error = ''
        self.identity = None
        self.identity_error = ''
        self.dpu_schedule = None
        from board.vision.pipeline_metrics import PipelineMetrics
        self.pipeline_metrics = PipelineMetrics(enabled=os.environ.get('AURA_PIPELINE_METRICS')=='1',
            diagnostics_enabled=os.environ.get('AURA_PIPELINE_METRICS')=='1' and os.environ.get('AURA_DPU_DIAGNOSTICS')=='1')
        self.started = clock()
        self.inference_ms = None
        self.observation_fid = None
        self.preview_error = ''
        self.raw_preview = False
        self.selected_id = None
        self.requested_target = None
        self.requested_target_key = None
        self.requested_target_deadline = None
        self.receipts = OrderedDict()
        self.detector_info = detector_info or {'role':'CPU_FACE_PREVIEW','count_kind':'faces',
            'detail':'CPU YuNet 人脸检测 + IoU 基础关联','target_label':'人脸'}

    def captured(self,stamp):
        with self.lock:
            self.capture_frames += 1
            self.capture_stamp = stamp
            self.camera_error = ''
            return self.capture_frames

    def publish_preview(self,fid,stamp,jpeg):
        with self.lock:
            self.frames[fid] = (stamp,jpeg)
            while len(self.frames)>8:self.frames.popitem(last=False)
            self.preview_frames += 1
            self.preview_error = ''

    def observed(self,fid,stamp,observation,inference_ms):
        with self.lock:
            self.processed_stamp = stamp
            self.observation_fid = fid
            self.observation = copy.deepcopy(observation)
            self.inference_ms = inference_ms
            if observation is not None:
                self.detected_frames += 1
                self.selected_id = observation['target_id']

    def overlay_observation(self):
        with self.lock:
            if (self.processed_stamp is None or not 0<=self.clock()-self.processed_stamp<250
                    or self.detector_error):return None
            return copy.deepcopy(self.observation)

    def identity_target(self):
        with self.lock:
            now = self.clock()
            if self.identity and self.identity.face_targets:
                if self.camera_error or self.capture_stamp is None or not 0<=now-self.capture_stamp<1000:return None
                return self.identity.face_targets.current_target()
            if (self.requested_target is not None or self.camera_error or self.detector_error
                    or self.capture_stamp is None or not 0 <= now-self.capture_stamp < 1000
                    or self.processed_stamp is None or not 0 <= now-self.processed_stamp < 750
                    or self.observation is None):
                return None
            track = next((t for t in self.observation['tracks'] if t['track_id'] == self.selected_id
                          and t['visible'] and t['confirmed']), None)
            return None if track is None else {'camera_epoch': self.camera_epoch, 'track_id': track['track_id'],
                                               'track_generation': track['generation']}

    def snapshot(self):
        with self.lock:
            now = self.clock();self.sequence += 1
            fresh = self.capture_stamp is not None and 0<=now-self.capture_stamp<1000 and not self.camera_error
            detected = (fresh and self.processed_stamp is not None and
                        0<=now-self.processed_stamp<750 and self.observation is not None and not self.detector_error)
            modules = {'camera':{'state':'READY' if fresh else 'ERROR' if self.camera_error else 'LOST',
                        'detail':self.camera_error or 'USB 相机 · 640×480 · 镜像预览'},
                       'vision':{'state':'READY' if detected else 'ERROR' if self.detector_error else 'DEGRADED',
                        'detail':self.detector_error or self.detector_info['detail'],
                        'count_kind':self.detector_info['count_kind']},
                       'target':{'state':'NONE','selected':None,'tracks':[]}}
            tracks = []
            if self.raw_preview:modules['camera']['preview_transport']=TRANSPORT
            if self.detector_info['role']=='DPU_YOLOX_PERSON_PREVIEW':
                modules['npu']={'state':'READY' if detected else 'ERROR' if self.detector_error else 'DEGRADED',
                    'detail':self.detector_error or 'YOLOX-Nano · B4096 · 人体检测'}
            if detected:
                tracks = [t for t in self.observation['tracks'] if t['visible'] and t['confirmed']][:16]
                modules['vision']['people_count'] = sum(t['visible'] for t in self.observation['tracks'])
                modules['target']['tracks'] = [{'key':{'camera_epoch':self.camera_epoch,'track_id':t['track_id'],
                    'track_generation':t['generation']},'label':self.detector_info['target_label']+' #'+str(t['track_id'])} for t in tracks]
                selected = next((r['key'] for r in modules['target']['tracks'] if r['key']['track_id']==self.selected_id),None)
                modules['target'].update(state='CONFIRMED' if selected else 'CANDIDATE' if tracks else 'NONE',selected=selected)
            elif self.observation is not None:
                modules['target']['state'] = 'LOST'
            result = {'protocol_version':PROTOCOL,'board_boot_id':self.boot,'service_epoch':self.epoch,
                'sequence':self.sequence,'observed_mono_ms':now,'ttl_ms':2000,'source_kind':'actual',
                'context':{'session_id':self.session,'request_id':'','generation':0},'modules':modules,
                'capabilities':{a:bool(a=='target_select' and tracks) for a in ACTIONS}}
            if self.identity:
                modules['identity'], capabilities = self.identity.view()
                result['capabilities'].update(capabilities)
            elif self.identity_error:
                modules['identity'] = {'state': 'ERROR', 'detail': self.identity_error}
            if fresh and self.frames:
                fid = next(reversed(self.frames));stamp,_ = self.frames[fid]
                if 0<=now-stamp<1000:
                    result['preview'] = {'camera_epoch':self.camera_epoch,'frame_id':fid,'captured_mono_ms':stamp}
            return result

    def preview(self,epoch,fid):
        with self.lock:
            value = self.frames.get(fid)
            if (epoch != self.camera_epoch or value is None or not 0<=self.clock()-value[0]<1000
                    or self.camera_error):return None
            return value[1]

    def command(self,command):
        with self.lock:
            now = self.clock()
            names = ('protocol_version','board_boot_id','service_epoch','command_id','ui_epoch','ui_generation')
            owner = {k:command.get(k) for k in names}
            try:
                if set(command)!=set(names)|{'context','snapshot_sequence','issued_mono_ms','deadline_mono_ms','action','params'}:
                    raise ValueError('请求字段不完整或未知')
                if command.get('protocol_version')!=PROTOCOL or command.get('board_boot_id')!=self.boot or command.get('service_epoch')!=self.epoch:
                    raise ValueError('请求属于其他服务或板卡启动')
                if (not isinstance(command.get('command_id'),str) or not 0<len(command['command_id'])<=96 or
                        not isinstance(command.get('ui_epoch'),str) or not 0<len(command['ui_epoch'])<=96 or
                        not integer(command.get('ui_generation'))):raise ValueError('请求归属无效')
                issued,deadline = command.get('issued_mono_ms'),command.get('deadline_mono_ms')
                if not (integer(issued) and integer(deadline) and issued<=now+100 and now<deadline<=issued+2500):
                    raise ValueError('请求已过期或期限无效')
                if (command.get('context') != {'session_id':self.session,'request_id':'','generation':0} or
                        not integer(command.get('snapshot_sequence'),1) or command['snapshot_sequence']>self.sequence):
                    raise ValueError('请求状态上下文不匹配')
                action = command.get('action')
                if action not in ('target_select', 'identity_enroll', 'identity_delete','identity_sample_start','identity_sample_cancel'):
                    raise ValueError('该服务仅提供视觉目标与身份操作')
                if command['command_id'] in self.receipts:
                    previous,ack = self.receipts[command['command_id']]
                    if previous!=command:raise ValueError('重复请求的内容发生变化')
                    return copy.deepcopy(ack)
                snapshot = self.snapshot()
                params = validate_action(action,command.get('params'),snapshot)
                if action == 'target_select':
                    self.requested_target = params['target']['track_id']
                    self.requested_target_key = copy.deepcopy(params['target'])
                    self.requested_target_deadline = deadline
                    detail = '已受理目标选择，等待下一帧确认'
                elif action == 'identity_enroll':
                    detail = self.identity.enroll(params, command['command_id'])
                elif action == 'identity_sample_start':
                    detail = self.identity.sample_start(params,command['command_id'])
                elif action == 'identity_sample_cancel':
                    detail = self.identity.sample_cancel(params,command['command_id'])
                else:
                    detail = self.identity.delete(params, command['command_id'])
                ack = dict(owner,accepted=True,detail=detail)
                self.receipts[command['command_id']] = (copy.deepcopy(command),ack)
                while len(self.receipts)>128:self.receipts.popitem(last=False)
                return copy.deepcopy(ack)
            except (ValueError,TypeError,sqlite3.Error) as exc:return dict(owner,accepted=False,detail=str(exc)[:160])

    def health(self):
        with self.lock:
            now = self.clock();seconds=max((now-self.started)/1000,.001)
            return {'pid':os.getpid(),'board_boot_id':self.boot,'service_epoch':self.epoch,
                'camera_epoch':self.camera_epoch,'capture_frames':self.capture_frames,'detected_frames':self.detected_frames,
                'capture_age_ms':None if self.capture_stamp is None else now-self.capture_stamp,
                'observation_age_ms':None if self.processed_stamp is None else now-self.processed_stamp,
                'capture_hz':round(self.capture_frames/seconds,2),'detection_hz':round(self.detected_frames/seconds,2),
                'preview_frames':self.preview_frames,'preview_hz':round(self.preview_frames/seconds,2),
                'observation_frame_id':self.observation_fid,'preview_error':self.preview_error,
                'last_inference_ms':self.inference_ms,'preview_buffers':len(self.frames),
                'camera_error':self.camera_error,'detector_error':self.detector_error,
                'device':copy.deepcopy(self.device),
                'role':self.detector_info['role'],'detector':copy.deepcopy(self.detector_info),
                'people_count':None if self.observation is None or self.processed_stamp is None or
                    not 0<=now-self.processed_stamp<750 or self.detector_error or self.camera_error else
                    sum(t['visible'] for t in self.observation['tracks']),
                'identity_recognition':bool(self.identity and self.identity.health()['ready']),
                'identity':self.identity.health() if self.identity else {'ready':False,'error':self.identity_error},
                'dpu_schedule':self.dpu_schedule.health() if self.dpu_schedule else None,
                'motion_command_emitted':False,
                'pipeline_metrics':self.pipeline_metrics.snapshot(),
                'timestamp_kind':'appsink_dequeue_monotonic','mirror_horizontal':True}


def handler_for(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def respond(self,code,value,mime='application/json',headers=None):
            body = value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(code);self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            for k,v in (headers or {}).items():self.send_header(k,v)
            self.end_headers()
            try:self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_GET(self):
            path = urlsplit(self.path)
            if path.path=='/v1/ui/status':self.respond(200,state.snapshot())
            elif path.path=='/health':self.respond(200,state.health())
            elif path.path=='/v1/ui/preview.jpg':
                try:
                    args=parse_qs(path.query);epoch=args['camera_epoch'][0];fid=int(args['frame_id'][0])
                    jpeg=state.preview(epoch,fid)
                    if jpeg is None:raise ValueError()
                    self.respond(200,jpeg,'image/jpeg',{'X-Aura-Boot-Id':state.boot,
                        'X-Aura-Camera-Epoch':epoch,'X-Aura-Frame-Id':str(fid)})
                except (KeyError,ValueError,IndexError):self.respond(404,{'error':'画面已过期或换代'})
            elif path.path=='/v1/ui/identity-face.png':
                try:
                    args=parse_qs(path.query)
                    key={'camera_epoch':args['camera_epoch'][0], 'track_id':int(args['track_id'][0]),
                         'track_generation':int(args['track_generation'][0])}
                    fid=int(args['frame_id'][0])
                    crop=state.identity.face_preview(key,fid) if state.identity else None
                    if crop is None:raise ValueError()
                    self.respond(200,crop,'image/png',{'X-Aura-Boot-Id':state.boot,
                        'X-Aura-Service-Epoch':state.epoch,'X-Aura-Camera-Epoch':key['camera_epoch'],
                        'X-Aura-Frame-Id':str(fid)})
                except (KeyError,ValueError,IndexError):self.respond(404,{'error':'人脸已失效，请重新正对摄像头'})
            else:self.respond(404,{'error':'未知接口'})
        def do_POST(self):
            if self.path!='/v1/ui/commands':self.respond(404,{});return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=8192 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError()
                command=json.loads(self.rfile.read(size))
                if not isinstance(command,dict):raise ValueError()
                self.respond(200,state.command(command))
            except (ValueError,TypeError):self.respond(400,{'error':'请求格式无效'})
    from board.identity.calibration_http import wrap_handler
    return wrap_handler(Handler,state)


class PersonPreviewTracks:
    """Reuse the pinned geometry-only IoU baseline; no identity or face output."""
    def __init__(self,epoch,reference):
        self.reference=reference(epoch)
        self.last_visible=set()
        self.generations={}

    @property
    def tracks(self):return self.reference.tracks

    @property
    def target_id(self):return self.reference.target_id

    @target_id.setter
    def target_id(self,value):self.reference.target_id=value

    def update(self,people,fid,stamp,width,height):
        # The existing association uses only xywh and score. Padding is private
        # compatibility data; it is never exposed or used as face landmarks.
        rows=[list(d.box)+[0.]*10+[d.score] for d in people]
        observation=self.reference.update(rows,fid,stamp,width,height)
        current=set()
        for track in observation['tracks']:
            tid=track['track_id']
            if track['visible']:
                if tid not in self.last_visible:self.generations[tid]=self.generations.get(tid,0)+1
                current.add(tid)
            track['generation']=self.generations.get(tid,1)
            self.reference.tracks[tid]['generation']=track['generation']
        self.last_visible=current
        self.generations={k:v for k,v in self.generations.items() if k in self.reference.tracks}
        observation['association']='PERSON_IOU_BASELINE'
        return observation


def detector_info(config):
    if config.get('detector_backend','cpu_yunet')=='dpu_yolox':
        tracking=config.get('tracking',{}).get('backend')=='bytetrack_numpy'
        return {'role':'DPU_YOLOX_PERSON_PREVIEW','count_kind':'people','target_label':'人体',
            'detail':'DPU YOLOX-Nano 人体检测 + '+('ByteTrack 跟踪' if tracking else 'IoU 基础关联'),'model':'YOLOX-Nano',
            'tracking_backend':'BYTETRACK_PINNED_NUMPY' if tracking else 'PERSON_IOU_BASELINE',
            'model_sha256':config['yolo']['model_sha256'],'arch_fingerprint':config['yolo']['arch_fingerprint']}
    return None


def checked_backend(config):
    import cv2
    import numpy as np
    loaded = {}
    directory = Path(config['backend_dir'])
    for name,expected in config['backend_sha256'].items():
        path=directory/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Backend hash mismatch: '+name)
        spec=importlib.util.spec_from_file_location('_aura_camera_'+path.stem,str(path))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);loaded[name]=module
    cv2.setNumThreads(2)
    if config.get('detector_backend','cpu_yunet')=='dpu_yolox':
        from board.vision.yolo_dpu import DpuYoloX, checked_file
        detector=DpuYoloX(config['yolo'])
        try:
            reference_path=checked_file(config['yolo']['reference_image'],config['yolo']['reference_sha256'])
            reference=cv2.imread(str(reference_path))
            if reference is None:raise RuntimeError('YOLO reference image cannot be read')
            count=sum(d.score>=.3 for d in detector.detect_bgr(reference))
            blank=len(detector.detect_bgr(np.zeros((480,640,3),np.uint8)))
            if count<2 or blank:raise RuntimeError('YOLO fixed reference or blank check failed')
            detector.reference_check={'reference_people':count,'blank_people':blank}
        except BaseException:
            detector.close()
            raise
        backend=config.get('tracking',{}).get('backend','iou')
        if backend=='bytetrack_numpy':
            from board.vision.person_bytetrack import PersonByteTracks
            if config['yolo']['score_threshold']!=.1:
                detector.close();raise ValueError('ByteTrack requires low-score person detections')
            return cv2,np,detector,lambda epoch:PersonByteTracks(epoch,config['tracking'])
        if backend!='iou':
            detector.close();raise ValueError('Unknown tracking backend')
        return cv2,np,detector,lambda epoch:PersonPreviewTracks(epoch,loaded['vision_core.py'].FaceTracks)
    if config.get('detector_backend','cpu_yunet')!='cpu_yunet':raise ValueError('Unknown detector backend')
    detector=loaded['face_compat_fast.py'].YuNetCompat(Path(config['model_root'])/'models/yunet_2022mar.onnx',input_size=192)
    reference=cv2.imread(str(Path(config['model_root'])/'reference/lena.jpg'))
    if reference is None or len(detector.detect(reference))!=1 or len(detector.detect(np.zeros((480,640,3),np.uint8)))!=0:
        raise RuntimeError('Existing detector reference checks failed')
    return cv2,np,detector,loaded['vision_core.py'].FaceTracks


def video_owners(device,proc_root=Path('/proc')):
    device=os.path.realpath(device)
    owners=[]
    for folder in proc_root.iterdir():
        if not folder.name.isdigit() or int(folder.name)==os.getpid():continue
        try:
            for fd in (folder/'fd').iterdir():
                try:
                    if os.path.realpath(str(fd))==device:
                        owners.append(int(folder.name));break
                except OSError:pass
        except OSError:pass
    return owners


def run(config):
    # Resolve again on every process restart: USB reconnects can change videoN.
    device=resolve_camera_device(config['device'],identity=CAMERA_IDENTITY if config['device']==PINNED_CAMERA else None)
    import gi
    gi.require_version('Gst','1.0')
    from gi.repository import Gst
    native_loaded=None
    if config.get('native_execution') is not None:
        from board.vision.native_startup import preflight
        native_loaded=preflight(config,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),root=AURA)
    cv2,np,detector,Tracks=checked_backend(config)
    Gst.init(None)
    state=CameraState(Path('/proc/sys/kernel/random/boot_id').read_text().strip(),detector_info=detector_info(config),device=device)
    tracker=Tracks(state.camera_epoch)
    if config.get('native_execution') is not None:
        from board.vision.native_startup import attach
        detector,state.dpu_schedule=attach(config,state,detector,native_loaded)
    elif config.get('detector_backend') == 'dpu_yolox':
        from board.vision.dpu_vision_schedule import DpuVisionSchedule
        state.dpu_schedule = DpuVisionSchedule(diagnostics=state.pipeline_metrics.optional_diagnostics,
            yunet_recovery=config.get('yunet_dpu_recovery', False),
            sface_recovery=config.get('sface_dpu_recovery', False),
            admission_floor_ms=config.get('optional_admission_floor_ms', 0),
            yunet_slot_wait_ms=config.get('yunet_slot_wait_ms', 0),
            sface_slot_wait_ms=config.get('sface_slot_wait_ms', 0))
        if config.get('dpu_protection_seed') is not None:
            from board.vision.dpu_protection_handoff import restore_protection
            restore_protection(state.dpu_schedule, config['dpu_protection_seed'], boot_id=state.boot,
                allow_new_boot=config.get('dpu_protection_allow_new_boot',False))
    if detector is not None:detector.pipeline_metrics=state.pipeline_metrics
    stop=threading.Event();condition=threading.Condition();latest=[None]
    capture=None;server=None;thread=None;worker=None;preview_worker=None;raw=None
    lock_path=Path('/run/aura-camera-ui.lock')
    with lock_path.open('a+') as ownership:
        fcntl.flock(ownership,fcntl.LOCK_EX|fcntl.LOCK_NB)
        owners=video_owners(device['resolved'])
        if owners:raise RuntimeError('Camera already owned by PID '+str(owners))
        if config.get('identity', {}).get('enabled'):
            try:
                from board.identity.camera_faces import create_service
                state.identity = create_service(AURA, config['identity']['config'], state,
                    schedule=state.dpu_schedule, owner=detector)
            except Exception as exc:
                state.identity_error = ('身份服务不可用：'+str(exc))[:150]
        raw=RawFrameStore({'board_boot_id':state.boot,'service_epoch':state.epoch,'camera_epoch':state.camera_epoch})
        state.raw_preview=True
        def sample(sink):
            stage_started=time.monotonic_ns()
            try:
                item=sink.emit('pull-sample')
                if item is None:return Gst.FlowReturn.EOS
                buffer=item.get_buffer();caps=item.get_caps().get_structure(0)
                w,h=caps.get_value('width'),caps.get_value('height')
                data=buffer.extract_dup(0,buffer.get_size())
                if (w,h)!=(640,480) or len(data)!=w*h*3:raise ValueError('Unexpected BGR capture layout')
                image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3)
                stamp=millis();fid=state.captured(stamp)
                source=cv2.flip(image,1)
                state.pipeline_metrics.elapsed('capture.callback_prepare',stage_started)
                with condition:latest[0]=(fid,stamp,source);condition.notify_all()
                if state.identity and state.identity.face_targets:state.identity.face_targets.offer(source,fid,stamp)
                return Gst.FlowReturn.OK
            except Exception as exc:
                state.camera_error=str(exc)[:150];stop.set();return Gst.FlowReturn.ERROR
        def inference():
            nonlocal detector
            previous=0
            while not stop.is_set():
                started=time.monotonic()
                with condition:
                    condition.wait_for(lambda:stop.is_set() or latest[0] is not None and latest[0][0]>previous,timeout=.5)
                    if stop.is_set():return
                    packet=latest[0]
                if packet is None or packet[0]<=previous:continue
                fid,stamp,image=packet;previous=fid
                try:
                    if detector:
                        inference_started=time.monotonic()
                        state.pipeline_metrics.value('yolo.source_age_at_start',max(0,millis()-stamp))
                        schedule_started=time.monotonic_ns()
                        if state.dpu_schedule:
                            with state.dpu_schedule.primary(started + 1/config['inference_fps']):
                                state.pipeline_metrics.elapsed('yolo.schedule_wait',schedule_started)
                                native_started=time.monotonic_ns()
                                if getattr(detector,'native_critical',False):
                                    detections=detector.detect_bgr(image,source_mono_ms=stamp)
                                else:detections=detector.detect_bgr(image)
                                state.pipeline_metrics.elapsed('yolo.native_and_decode',native_started)
                        else:
                            detections=detector.detect_bgr(image) if hasattr(detector,'detect_bgr') else detector.detect(image)
                        track_started=time.monotonic_ns()
                        with state.lock:
                            observation=tracker.update(detections,fid,stamp/1000,640,480)
                            if state.requested_target is not None:
                                key=state.requested_target_key
                                target=tracker.tracks.get(state.requested_target)
                                if (key and key['camera_epoch']==state.camera_epoch and target and
                                        target['visible'] and target['confirmed'] and
                                        target['generation']==key['track_generation'] and
                                        millis()<state.requested_target_deadline and 0<=millis()-stamp<750):
                                    tracker.target_id=state.requested_target
                                    observation['target_id']=state.requested_target
                                state.requested_target = None
                                state.requested_target_key=None
                                state.requested_target_deadline=None
                        state.pipeline_metrics.elapsed('yolo.track',track_started)
                        elapsed=round((time.monotonic()-inference_started)*1000,2)
                        state.pipeline_metrics.value('yolo.path',elapsed)
                        state.observed(fid,stamp,observation,elapsed)
                        state.pipeline_metrics.value('yolo.publish_source_age',max(0,millis()-stamp))
                        if state.identity and not state.identity.face_targets:
                            state.identity.offer(image, fid, stamp, observation, state.camera_epoch)
                except PrimaryAdmissionDeferred:
                    state.pipeline_metrics.value('yolo.native_source_or_deadline_deferred',1)
                except Exception as exc:
                    with state.lock:state.detector_error=str(exc)[:150]
                    if detector and hasattr(detector,'close'):
                        try:detector.close()
                        except Exception:
                            # Unknown completion retains the native owner;
                            # the context registry forbids replacement jobs.
                            state._retained_native_owner=detector
                    detector=None
                # Detection has its own budget; live preview never waits for it.
                stop.wait(max(0,1/config['inference_fps']-(time.monotonic()-started)))

        def preview():
            previous=0
            while not stop.is_set():
                with condition:
                    condition.wait_for(lambda:stop.is_set() or latest[0] is not None and latest[0][0]>previous,timeout=.5)
                    if stop.is_set():return
                    packet=latest[0]
                if packet is None or packet[0]<=previous:continue
                fid,stamp,source=packet;previous=fid
                try:
                    preview_started=time.monotonic_ns()
                    # Capture/inference share an immutable source. Paint on a copy.
                    image=source.copy()
                    observation=state.overlay_observation()
                    if observation:
                        for track in observation['tracks']:
                            if not track['visible']:continue
                            x,y,w,h=[round(v) for v in track['box']]
                            color=(40,220,60) if track['track_id']==observation['target_id'] and track['confirmed'] else (0,190,255)
                            cv2.rectangle(image,(x,y),(x+w,y+h),color,2)
                            label=('person #%s %.2f'%(track['track_id'],track['score'])
                                if state.detector_info['count_kind']=='people' else '#'+str(track['track_id']))
                            cv2.putText(image,label,(x,max(18,y-6)),cv2.FONT_HERSHEY_SIMPLEX,.6,color,2)
                    raw.publish(fid,stamp,image.tobytes())
                    ok,encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,72])
                    if not ok or encoded.nbytes>256*1024:raise ValueError('Preview encoding failed or exceeded size limit')
                    state.publish_preview(fid,stamp,encoded.tobytes())
                    state.pipeline_metrics.elapsed('preview.render_encode_publish',preview_started)
                    state.pipeline_metrics.value('preview.publish_source_age',max(0,millis()-stamp))
                except Exception as exc:
                    with state.lock:state.preview_error=str(exc)[:150]
        signal.signal(signal.SIGTERM,lambda *_:stop.set())
        signal.signal(signal.SIGINT,lambda *_:stop.set())
        try:
            server=ThreadingHTTPServer(('127.0.0.1',config['port']),handler_for(state))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            capture=Gst.parse_launch('v4l2src device='+device['resolved']+' io-mode=mmap ! '
                'video/x-raw,format=YUY2,width=640,height=480,framerate='+str(config['capture_fps'])+'/1 ! videoconvert ! '
                'video/x-raw,format=BGR ! appsink name=input emit-signals=true sync=false max-buffers=1 drop=true')
            capture.get_by_name('input').connect('new-sample',sample)
            worker=threading.Thread(target=inference,name='camera-detection',daemon=True);worker.start()
            preview_worker=threading.Thread(target=preview,name='camera-live-preview',daemon=True);preview_worker.start()
            if capture.set_state(Gst.State.PLAYING)==Gst.StateChangeReturn.FAILURE:raise RuntimeError('Cannot start camera')
            started=millis()
            while not stop.wait(.1):
                message=capture.get_bus().timed_pop_filtered(0,Gst.MessageType.ERROR|Gst.MessageType.EOS)
                if message:
                    error=message.parse_error()[0] if message.type==Gst.MessageType.ERROR else 'Camera stream ended'
                    raise RuntimeError(str(error))
                if millis()-started>5000 and (state.capture_stamp is None or millis()-state.capture_stamp>2000):
                    raise RuntimeError('Camera stopped producing frames')
            if state.camera_error:raise RuntimeError(state.camera_error)
        except Exception as exc:
            with state.lock:state.camera_error=str(exc)[:150]
            print(json.dumps({'event':'CAMERA_FAILED','error':str(exc)}),flush=True)
            raise
        finally:
            stop.set()
            state.pipeline_metrics.close()
            with condition:condition.notify_all()
            if capture:capture.set_state(Gst.State.NULL)
            if worker:
                worker.join(timeout=2)
                if config.get('native_execution') is not None and worker.is_alive():
                    raise RuntimeError('Native YOLO worker did not stop; checkpoint refused')
            if preview_worker:preview_worker.join(timeout=2)
            if state.identity:state.identity.close()
            if config.get('native_execution') is not None and detector is not None:
                from board.vision.native_startup import shutdown
                state.native_checkpoint=shutdown(config,state,detector)
            if raw:raw.close()
            if server:server.shutdown();server.server_close()
            if thread:thread.join(timeout=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=AURA/'config/board_camera_ui.json')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args();config=json.loads(args.config.read_text())
    if config['device'] not in ('/dev/video0',PINNED_CAMERA) or config['port']!=8790:
        raise ValueError('Only the reviewed camera/loopback endpoint is supported')
    if config.get('capture_fps')!=30 or config.get('inference_fps')!=10:
        raise ValueError('Only reviewed 30 Hz capture / 10 Hz inference budgets are supported')
    if args.check:
        cv2,_,detector,Tracks=checked_backend(config)
        yolo=config.get('detector_backend')=='dpu_yolox'
        tracker=Tracks('check-epoch')
        if config.get('tracking',{}).get('backend')=='bytetrack_numpy':
            from common.contracts import Detection
            people=[Detection((10.,20.,100.,200.),.8)]
            tracker.update(people,1,1.,640,480)
            track_check=tracker.update(people,2,1.1,640,480)
            if not any(t['confirmed'] for t in track_check['tracks']):raise RuntimeError('ByteTrack self-check failed')
        if hasattr(detector,'close'):detector.close()
        identity_check = None
        if config.get('identity', {}).get('enabled'):
            from board.identity.camera_faces import CameraFaceExtractor, config_for
            cfg = config_for(AURA, config['identity']['config'])
            CameraFaceExtractor(cfg)
            identity_check = {'backend': 'CPU_SFACE_REFERENCE', 'models_loaded': True,
                              'accuracy_calibrated': False, 'database_opened': False}
        print(json.dumps({'status':'PASS','opencv':cv2.__version__,'camera_opened':False,
            'backend':'dpu_yolox' if yolo else 'cpu_yunet','tracking_backend':getattr(tracker,'kind','PERSON_IOU_BASELINE'),
            'reference_faces':None if yolo else 1,'blank_faces':None if yolo else 0,
            'yolo_reference':getattr(detector,'reference_check',None),
            'backend_sha256':config['backend_sha256'],'detector':detector_info(config), 'identity': identity_check}))
    else:
        try:run(config)
        except CameraUnavailable as exc:
            print(json.dumps({'event':'CAMERA_WAITING','device':config['device'],'error':str(exc)}),flush=True)
            raise SystemExit(1)


if __name__=='__main__':main()
