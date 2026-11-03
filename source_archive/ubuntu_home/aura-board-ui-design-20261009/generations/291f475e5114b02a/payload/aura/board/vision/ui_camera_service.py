"""Single-owner UVC preview and existing CPU face baseline for aura-ui-1.

This adapter has no motion, identity, audio, model-host or FPGA control path.
The detector and association are loaded from A's explicitly pinned sources.
"""
import argparse
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
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit
import uuid

AURA = Path(__file__).resolve().parents[2]
if str(AURA) not in sys.path:sys.path.insert(0,str(AURA))
from board.interaction.ui_contract import ACTIONS, PROTOCOL, integer, millis, validate_action


class CameraState:
    """A bounded, expiring view of actual capture/inference observations."""
    def __init__(self,boot,epoch=None,clock=millis):
        self.boot,self.epoch,self.clock = boot,epoch or uuid.uuid4().hex,clock
        self.camera_epoch = uuid.uuid4().hex
        self.session = uuid.uuid4().hex
        self.lock = threading.RLock()
        self.sequence = self.capture_frames = self.detected_frames = self.preview_frames = 0
        self.capture_stamp = self.processed_stamp = None
        self.frames = OrderedDict()
        self.observation = None
        self.detector_error = self.camera_error = ''
        self.started = clock()
        self.inference_ms = None
        self.observation_fid = None
        self.preview_error = ''
        self.selected_id = None
        self.requested_target = None
        self.receipts = OrderedDict()

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

    def snapshot(self):
        with self.lock:
            now = self.clock();self.sequence += 1
            fresh = self.capture_stamp is not None and 0<=now-self.capture_stamp<1000 and not self.camera_error
            detected = (fresh and self.processed_stamp is not None and
                        0<=now-self.processed_stamp<750 and self.observation is not None and not self.detector_error)
            modules = {'camera':{'state':'READY' if fresh else 'ERROR' if self.camera_error else 'LOST',
                        'detail':self.camera_error or 'USB 相机 · 640×480 · 镜像预览'},
                       'vision':{'state':'READY' if detected else 'ERROR' if self.detector_error else 'DEGRADED',
                        'detail':self.detector_error or 'CPU YuNet 人脸检测 + IoU 基础关联',
                        'count_kind':'faces'},
                       'target':{'state':'NONE','selected':None,'tracks':[]}}
            tracks = []
            if detected:
                tracks = [t for t in self.observation['tracks'] if t['visible'] and t['confirmed']][:16]
                modules['vision']['people_count'] = sum(t['visible'] for t in self.observation['tracks'])
                modules['target']['tracks'] = [{'key':{'camera_epoch':self.camera_epoch,'track_id':t['track_id'],
                    'track_generation':t['generation']},'label':'人脸 #'+str(t['track_id'])} for t in tracks]
                selected = next((r['key'] for r in modules['target']['tracks'] if r['key']['track_id']==self.selected_id),None)
                modules['target'].update(state='CONFIRMED' if selected else 'CANDIDATE' if tracks else 'NONE',selected=selected)
            elif self.observation is not None:
                modules['target']['state'] = 'LOST'
            result = {'protocol_version':PROTOCOL,'board_boot_id':self.boot,'service_epoch':self.epoch,
                'sequence':self.sequence,'observed_mono_ms':now,'ttl_ms':2000,'source_kind':'actual',
                'context':{'session_id':self.session,'request_id':'','generation':0},'modules':modules,
                'capabilities':{a:bool(a=='target_select' and tracks) for a in ACTIONS}}
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
                if command.get('action')!='target_select':raise ValueError('该服务仅提供相机预览与人脸目标选择')
                if command['command_id'] in self.receipts:
                    previous,ack = self.receipts[command['command_id']]
                    if previous!=command:raise ValueError('重复请求的内容发生变化')
                    return copy.deepcopy(ack)
                snapshot = self.snapshot()
                params = validate_action('target_select',command.get('params'),snapshot)
                self.requested_target = params['target']['track_id']
                ack = dict(owner,accepted=True,detail='已受理目标选择，等待下一帧确认')
                self.receipts[command['command_id']] = (copy.deepcopy(command),ack)
                while len(self.receipts)>128:self.receipts.popitem(last=False)
                return copy.deepcopy(ack)
            except (ValueError,TypeError) as exc:return dict(owner,accepted=False,detail=str(exc))

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
                'role':'CPU_FACE_PREVIEW','identity_recognition':False,'motion_command_emitted':False,
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
    return Handler


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
    detector=loaded['face_compat_fast.py'].YuNetCompat(Path(config['model_root'])/'models/yunet_2022mar.onnx',input_size=192)
    reference=cv2.imread(str(Path(config['model_root'])/'reference/lena.jpg'))
    if reference is None or len(detector.detect(reference))!=1 or len(detector.detect(np.zeros((480,640,3),np.uint8)))!=0:
        raise RuntimeError('Existing detector reference checks failed')
    return cv2,np,detector,loaded['vision_core.py'].FaceTracks


def video_owners(device):
    owners=[]
    for folder in Path('/proc').iterdir():
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
    import gi
    gi.require_version('Gst','1.0')
    from gi.repository import Gst
    cv2,np,detector,Tracks=checked_backend(config)
    Gst.init(None)
    state=CameraState(Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    stop=threading.Event();condition=threading.Condition();latest=[None]
    capture=None;server=None;thread=None;worker=None;preview_worker=None
    lock_path=Path('/run/aura-camera-ui.lock')
    with lock_path.open('a+') as ownership:
        fcntl.flock(ownership,fcntl.LOCK_EX|fcntl.LOCK_NB)
        owners=video_owners(config['device'])
        if owners:raise RuntimeError('Camera already owned by PID '+str(owners))
        tracker=Tracks(state.camera_epoch)
        def sample(sink):
            try:
                item=sink.emit('pull-sample')
                if item is None:return Gst.FlowReturn.EOS
                buffer=item.get_buffer();caps=item.get_caps().get_structure(0)
                w,h=caps.get_value('width'),caps.get_value('height')
                data=buffer.extract_dup(0,buffer.get_size())
                if (w,h)!=(640,480) or len(data)!=w*h*3:raise ValueError('Unexpected BGR capture layout')
                image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3).copy()
                stamp=millis();fid=state.captured(stamp)
                with condition:latest[0]=(fid,stamp,cv2.flip(image,1));condition.notify_all()
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
                        faces=detector.detect(image)
                        with state.lock:
                            if state.requested_target is not None:
                                if state.requested_target in tracker.tracks:tracker.target_id=state.requested_target
                                state.requested_target = None
                            observation=tracker.update(faces,fid,stamp/1000,640,480)
                        elapsed=round((time.monotonic()-inference_started)*1000,2)
                        state.observed(fid,stamp,observation,elapsed)
                except Exception as exc:
                    with state.lock:state.detector_error=str(exc)[:150]
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
                    # Capture/inference share an immutable source. Paint on a copy.
                    image=source.copy()
                    observation=state.overlay_observation()
                    if observation:
                        for track in observation['tracks']:
                            if not track['visible']:continue
                            x,y,w,h=[round(v) for v in track['box']]
                            color=(40,220,60) if track['track_id']==observation['target_id'] and track['confirmed'] else (0,190,255)
                            cv2.rectangle(image,(x,y),(x+w,y+h),color,2)
                            cv2.putText(image,'#'+str(track['track_id']),(x,max(18,y-6)),cv2.FONT_HERSHEY_SIMPLEX,.6,color,2)
                    ok,encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,72])
                    if not ok or encoded.nbytes>256*1024:raise ValueError('Preview encoding failed or exceeded size limit')
                    state.publish_preview(fid,stamp,encoded.tobytes())
                except Exception as exc:
                    with state.lock:state.preview_error=str(exc)[:150]
        signal.signal(signal.SIGTERM,lambda *_:stop.set())
        signal.signal(signal.SIGINT,lambda *_:stop.set())
        try:
            server=ThreadingHTTPServer(('127.0.0.1',config['port']),handler_for(state))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            capture=Gst.parse_launch('v4l2src device='+config['device']+' io-mode=mmap ! '
                'video/x-raw,format=YUY2,width=640,height=480,framerate='+str(config['capture_fps'])+'/1 ! videoconvert ! '
                'video/x-raw,format=BGR ! appsink name=input emit-signals=true sync=false max-buffers=1 drop=true')
            capture.get_by_name('input').connect('new-sample',sample)
            worker=threading.Thread(target=inference,name='camera-face-inference',daemon=True);worker.start()
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
            with condition:condition.notify_all()
            if capture:capture.set_state(Gst.State.NULL)
            if worker:worker.join(timeout=2)
            if preview_worker:preview_worker.join(timeout=2)
            if server:server.shutdown();server.server_close()
            if thread:thread.join(timeout=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=AURA/'config/board_camera_ui.json')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args();config=json.loads(args.config.read_text())
    if config['device']!='/dev/video0' or config['port']!=8790:raise ValueError('Only the reviewed camera/loopback endpoint is supported')
    if config.get('capture_fps')!=30 or config.get('inference_fps')!=10:
        raise ValueError('Only reviewed 30 Hz capture / 10 Hz inference budgets are supported')
    if args.check:
        cv2,_,_,_=checked_backend(config)
        print(json.dumps({'status':'PASS','opencv':cv2.__version__,'camera_opened':False,
            'reference_faces':1,'blank_faces':0,'backend_sha256':config['backend_sha256']}))
    else:run(config)


if __name__=='__main__':main()
