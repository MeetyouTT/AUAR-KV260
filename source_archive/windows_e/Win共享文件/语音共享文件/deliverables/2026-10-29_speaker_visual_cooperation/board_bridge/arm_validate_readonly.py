"""Compile/run candidate code from stdin RAM only; no deployment or model load."""
import base64,datetime,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;C=H/'candidate'
sys.path.insert(0,str(H.parents[1]/'2026-10-29_audio_animation_polish'))
from board_guard import ssh
baseline=json.loads((H/'board_preflight.json').read_text())
names=['common/binding_intent.py','common/speaker_visual.py','common/face_binding_wire.py','tools/enrollment_receipts.py',
 'board/runtime/audio/face_gallery_readback.py','board/runtime/audio/face_binding_bridge.py',
 'board/runtime/audio/voice_channel.py','board/runtime/audio/channel_jobs.py']
sources={name:base64.b64encode((C/name).read_bytes()).decode() for name in names}
configuration=json.loads((C/'config/face_gallery_readback.local.json').read_text())
script=r'''
import base64,copy,hashlib,importlib,json,sys,types,urllib.request
from pathlib import Path
root=Path(ROOT)/'aura';sys.path.insert(0,str(root))
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
for name,digest in BASEPINS.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
sources=SOURCES
for filename,encoded in sources.items():
 name=filename[:-3].replace('/','.');importlib.import_module(name.rsplit('.',1)[0])
 source=base64.b64decode(encoded);module=types.ModuleType(name);module.__file__=str(root/filename)
 module.__package__=name.rsplit('.',1)[0];sys.modules[name]=module
 exec(compile(source,str(root/filename),'exec'),module.__dict__)
from common.face_binding_wire import validate_packet,packet_sha256,encode_gallery_header,decode_gallery_header,validate_binding_request
from board.runtime.audio.face_gallery_readback import FaceGalleryReadback
raw=bytes(6400);owner=dict(protocol='aura-asr-1',board_boot_id=BOOT,session_id='synthetic-readonly',request_id='synthetic-readonly',
 generation=1,capture_id='synthetic-readonly',sample_count=3200,pcm_sha256=hashlib.sha256(raw).hexdigest(),budget_ms=10000)
packet=dict(version=1,context=owner,gallery=dict(store_id='synthetic',model_id='synthetic',revision=2,source_kind='actual'),
 current=None,inventory=[['synthetic-id','1'*64]])
assert decode_gallery_header(encode_gallery_header(packet,owner),owner)['packet_sha256']==packet_sha256(packet)
request=dict(version=1,attempt_id='name-wait-'+'1'*32,origin_context=owner,name=None,board_text='帮我登记身份',confirmed_existing=False,
 face_guard=dict(service_epoch='synthetic',camera_epoch='synthetic',target=dict(camera_epoch='synthetic',track_id=1,track_generation=1),gallery_revision=2,face_identity_id=None))
assert validate_binding_request(request,owner)==request
from board.runtime.audio.face_binding_bridge import FaceBindingBridge
from board.identity.voice_enrollment import VoiceEnrollment
from board.interaction.ui_contract import millis
stamp=millis();key=dict(camera_epoch='synthetic',track_id=1,track_generation=1);name='测试小林';person='1'*32
before=dict(protocol_version='aura-ui-1',board_boot_id=BOOT,service_epoch='synthetic',sequence=1,
 observed_mono_ms=stamp,ttl_ms=2000,source_kind='actual',context=dict(session_id='synthetic-ui',request_id='',generation=0),
 modules=dict(camera=dict(state='READY'),identity=dict(state='UNKNOWN',backend='DPU_SFACE_INT8',person_id='',display_name='',db_version=2,
 target_kind='face',face_count=1,face_target=key,face_targets=[dict(key=key,label='synthetic')],target=key,
 source_frame_id=1,source_mono_ms=stamp,people=[])),capabilities=dict(identity_enroll=True),
 preview=dict(camera_epoch='synthetic',frame_id=1,captured_mono_ms=stamp))
after=copy.deepcopy(before);after['sequence']=2;after['preview']['frame_id']=2
after['modules']['identity'].update(state='KNOWN',person_id=person,display_name=name,db_version=3,source_frame_id=2,
 people=[dict(person_id=person,display_name=name)])
latest=[before];commands=[]
def send(command):
 commands.append(command);latest[0]=after
 after['modules']['identity']['last_operation']=dict(command_id=command['command_id'],action='identity_enroll',state='COMMITTED',db_version=3,detail='synthetic commit')
 ack={k:command[k] for k in ('protocol_version','board_boot_id','service_epoch','command_id','ui_epoch','ui_generation')}
 return dict(ack,accepted=True,detail='synthetic ACK')
class SyntheticReadback:
 config={'result_ttl_ms':3000}
 def read(self,meta,snapshot):
  return dict(version=1,context=meta,gallery=dict(store_id='synthetic',model_id='synthetic',revision=3,source_kind='actual'),
   current=dict(identity_id=person,template_fingerprint='1'*64),inventory=[[person,'1'*64]])
bridge=FaceBindingBridge(lambda:latest[0],send,SyntheticReadback(),clock=lambda:stamp)
flow=VoiceEnrollment(BOOT,bridge.snapshot,bridge.command,now_ms=lambda:stamp,simple=True)
assert flow.handle('帮我登记身份',before)['code']=='ask_name'
assert flow.handle('我叫'+name,before)['code']=='confirm_name' and not commands
bound=copy.deepcopy(request);bound.update(attempt_id='2'*32,name=name,board_text='确认登记')
exchange=bridge.exchange(owner,bound,before,'确认登记',lambda:True)
with bridge.scope(exchange):reply=flow.handle('确认登记',before)
assert reply['code']=='registered' and len(commands)==1
receipt=exchange.receipt(reply,lambda:after)
assert receipt['state']=='COMMITTED' and receipt['identity_id']==person and receipt['commit_context']==owner
reader=FaceGalleryReadback(CONFIG)
reader.verify(reader.config)
with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/status',timeout=1.5) as response:snapshot=json.load(response)
actual=reader.read(owner,snapshot)
# Only non-personal aggregate evidence leaves the board validation process.
result=dict(status='PASS',python=sys.version.split()[0],compiled_modules=len(sources),source_checks=True,
 codec_synthetic=True,name_wait_synthetic=True,original_fsm_synthetic_commit=True,actual_gallery=dict(store_id=actual['gallery']['store_id'],model_id=actual['gallery']['model_id'],
 revision=actual['gallery']['revision'],template_count=len(actual['inventory'])),
 read_only=True,templates_exported=False,camera_restarted=False,models_loaded=False,files_installed=False)
print(json.dumps(result))
'''
script=script.replace('ROOT',repr(baseline['actual_runtime'])).replace('BOOT',repr(baseline['boot']))
script=script.replace('BASEPINS',repr(baseline['pins'])).replace('SOURCES',repr(sources)).replace('CONFIG',repr(configuration))
result=json.loads(ssh('python3 -B -',script,timeout=25));result['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(H/'arm_readonly.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
