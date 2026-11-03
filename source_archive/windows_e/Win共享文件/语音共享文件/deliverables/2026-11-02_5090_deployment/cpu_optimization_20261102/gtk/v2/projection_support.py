"""Only public, synthetic UI snapshots; no application imports or I/O."""
import ast
from collections import deque
import copy
import ipaddress
import json
from pathlib import Path
import threading
import time
import uuid

def sources():
    if 'SOURCE_BUNDLE' in globals():return SOURCE_BUNDLE
    root=Path(__file__).resolve().parent
    return {'contract':(root/'original/board/interaction/ui_contract.py').read_text(encoding='utf-8'),
        'original_services':(root/'original/board/interaction/ui_services.py').read_text(encoding='utf-8'),
        'candidate_services':(root/'candidate/board/interaction/ui_services.py').read_text(encoding='utf-8'),
        'original_preview':(root/'original/tools/board_camera_preview.py').read_text(encoding='utf-8'),
        'candidate_preview':(root/'candidate/tools/board_camera_preview.py').read_text(encoding='utf-8')}

SOURCES=sources()
CONTRACT={}
exec(compile(SOURCES['contract'],'<pinned-public-ui-contract>','exec'),CONTRACT)

def service_class(version):
    tree=ast.parse(SOURCES[version+'_services'])
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='validate_connection'
           or isinstance(node,ast.ClassDef) and node.name=='UiServiceClient'
           or isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='DEFAULT_CONNECTION' for target in node.targets)]
    space=dict(CONTRACT,copy=copy,deque=deque,threading=threading,uuid=uuid,ipaddress=ipaddress)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<'+version+'-UiServiceClient>','exec'),space)
    return space['UiServiceClient']

CLASSES={version:service_class(version) for version in ('original','candidate')}

class Clock:
    def __init__(self,value=10000):self.value=value
    def __call__(self):return self.value

def snapshot(*,now=10000,sequence=1,epoch='service-1',frame=1,filled=False):
    key={'camera_epoch':'camera-'+epoch,'track_id':7,'track_generation':2}
    value={'protocol_version':CONTRACT['PROTOCOL'],'board_boot_id':'boot-1','service_epoch':epoch,
        'sequence':sequence,'observed_mono_ms':now,'ttl_ms':2500,'source_kind':'actual',
        'context':{'session_id':'public-session','request_id':'public-request','generation':1},
        'capabilities':{name:True for name in CONTRACT['ACTIONS']},
        'preview':{'camera_epoch':key['camera_epoch'],'frame_id':frame,'captured_mono_ms':now},
        'modules':{'camera':{'state':'READY','preview_transport':'aura-local-bgr-1'},
            'interaction':{'state':'IDLE','reply':'公开合成回答','transcript':'公开合成问题'},
            'audio':{'state':'READY'},'vision':{'state':'READY','people_count':1},
            'target':{'state':'CONFIRMED','selected':key,'tracks':[{'key':key,'label':'公开测试对象'}]},
            'identity':{'state':'UNKNOWN','db_version':1,'people':[]}}}
    if filled:
        value['modules']['interaction'].update(reply='公开合成回答。'*180,transcript='公开合成问题。'*100,
            timings_ms={'asr':1000.,'vlm':1800.,'tts':800.,'first_audio':4200.})
        value['modules']['target']['tracks']=[{'key':dict(key,track_id=index+1),'label':'测试对象'+str(index+1)} for index in range(16)]
        value['modules']['identity']['people']=[{'person_id':'public-person-'+str(index),'display_name':'合成档案'+str(index)} for index in range(32)]
    return value

def client(version='candidate',*,filled=False):
    obj=CLASSES[version].__new__(CLASSES[version]);clock=Clock()
    obj.boot_id='boot-1';obj.clock=clock;obj.condition=threading.Condition()
    obj.connection={'enabled':True,'host':'127.0.0.1','port':8790}
    obj.gate=CONTRACT['SnapshotGate'](obj.boot_id,clock)
    value=snapshot(filled=filled);obj.gate.ingest(value)
    obj.local_raw=True;obj.link='READY';obj.error='';obj.closed=False
    obj.preview=b'PUBLIC-JPEG-1';obj.preview_key=copy.deepcopy(value['preview']);obj.preview_error=''
    obj.identity_preview_enabled=False;obj.identity_face=obj.identity_face_key=None;obj.identity_face_error=''
    obj.waiting=deque();obj.results=deque(maxlen=16);obj.inflight=None
    obj.ui_epoch='public-ui';obj.ui_generation=0;obj.config_generation=0
    if filled:
        obj.results.extend({'action':'ask_frame','accepted':True,'detail':'公开合成回执','command_id':'public-'+str(index)} for index in range(16))
    return obj,clock

def worker_projection(view):
    value=view['snapshot']
    if value is None:return {'snapshot':None,'preview':None,'raw_preview':False}
    camera=value['modules'].get('camera',{})
    return {'snapshot':copy.deepcopy({'board_boot_id':value['board_boot_id'],
        'service_epoch':value['service_epoch'],'source_kind':value['source_kind'],
        'preview':value.get('preview'),'modules':{'camera':{key:camera[key] for key in ('state','preview_transport') if key in camera}}}),
        'preview':view['preview'],'raw_preview':view['raw_preview']}

def pair(client):
    return worker_projection(client.read()),client.read_preview()

def populate(client,value,*,jpeg=True):
    with client.condition:
        client.gate=CONTRACT['SnapshotGate']('boot-1',client.clock)
        client.gate.ingest(value)
        client.link='READY'
        client.preview_key=copy.deepcopy(value.get('preview'))
        client.preview=(b'PUBLIC-JPEG-'+str(value.get('preview',{}).get('frame_id',0)).encode()) if jpeg else None

def worker_trace(version,services,clock):
    tree=ast.parse(SOURCES[version+'_preview'])
    cls=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='CameraPreviewWorker')
    trace=[]
    class Reader:
        def __init__(self,owner,directory):self.owner=copy.deepcopy(owner);trace.append(('reader',copy.deepcopy(owner)))
        def read(self,now):
            value=services.gate.value['preview']
            return dict(self.owner,frame_id=value['frame_id'],captured_mono_ms=value['captured_mono_ms']),b'PUBLIC-BGR'
    fake_time=type('Time',(),{'monotonic':staticmethod(lambda:clock.value/1000)})
    space={'deque':deque,'copy':copy,'threading':threading,'time':fake_time,'io':None,'PIXELS':640*480*3,'RawFrameReader':Reader}
    exec(compile(ast.Module(body=[cls],type_ignores=[]),'<'+version+'-preview>','exec'),space)
    klass=space['CameraPreviewWorker'];worker=klass.__new__(klass)
    worker.lock=threading.RLock();worker.services=services;worker.raw_directory='/not-opened'
    worker.reader=worker.reader_owner=worker.last_key=None;worker.error=''
    worker.stop=type('Stop',(),{'calls':0,'wait':lambda self,timeout:(setattr(self,'calls',self.calls+1) or self.calls>1)})()
    bus=type('Bus',(),{'pop_filtered':lambda self,kind:None})()
    pipeline=type('Pipeline',(),{'get_bus':lambda self:bus})()
    worker.outputs={'vision':{'pipeline':pipeline}}
    worker.Gst=type('Gst',(),{'MessageType':type('Type',(),{'ERROR':1})})
    worker.clear=lambda:trace.append(('clear',))
    worker.push=lambda header,pixels:trace.append(('push',copy.deepcopy(header),pixels))
    worker.work()
    return {'trace':trace,'error':worker.error}
