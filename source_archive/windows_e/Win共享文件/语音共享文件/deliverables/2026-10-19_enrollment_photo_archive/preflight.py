"""Pinned real models/public image, actual asset imports and hidden GTK face view."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
candidate=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import base64,json,os,subprocess,sys
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage'])
env=dict(os.environ,PYTHONPATH=str(root/'aura'),PYTHONDONTWRITEBYTECODE='1',DISPLAY=':0')
probe=r"""
import json,tempfile,os
from pathlib import Path
import cv2
cv2.setNumThreads(2)
from board.vision.ui_camera_service import CameraState
from board.identity.camera_faces import CameraFaceExtractor,config_for
from board.identity.live import IdentityService
from board.identity.photo_archive import EnrollmentPhotoArchive
from board.identity.face_targets import FaceTargetService
from board.identity.store import IdentityStore
from board.identity.voice_enrollment import VoiceEnrollment
from board.vision.reference_faces import YuNetCompat
from board.interaction.ui_contract import validate_snapshot
root=Path.cwd();config=json.loads(Path(CONFIG_PATH).read_text())
image=cv2.imread('/home/root/aura-adaptation-20261006/identity/reference/lena.jpg');assert image is not None
image=cv2.resize(image,(640,480));blank=image*0;clock=[1000];fid=0
with tempfile.TemporaryDirectory(prefix='aura-public-face-') as directory:
 config['database']=str(Path(directory)/'public.sqlite')
 config['enrollment_photos']={'enabled':True,'directory':str(Path(directory)/'photos'),'max_images_per_session':192}
 path=Path(directory)/'identity.json';path.write_text(json.dumps(config))
 cfg=config_for(root,path);extractor=CameraFaceExtractor(cfg,face_targets=True);photos=EnrollmentPhotoArchive(cfg['enrollment_photos'])
 detector=YuNetCompat(cfg['face_model'],score_threshold=cfg['minimum_face_score'],input_size=cfg['input_size'])
 store=IdentityStore(cfg['database'],cfg['model_id'],128,cfg['threshold'],cfg['ambiguity_margin'],allow_cross_thread=True);os.chmod(cfg['database'],0o600)
 state=CameraState('public-test-boot','public-test-service',clock=lambda:clock[0])
 service=IdentityService(store,lambda:extractor,state.identity_target,lock=state.lock,clock=lambda:clock[0],result_ttl_ms=3000,multi_frame=True,backend='WINDOWS_CPU_SFACE_ORT',photo_archive=photos)
 service.ready=True;state.identity=service
 targets=FaceTargetService(lambda:detector,service.offer_face,state.camera_epoch,lock=state.lock,clock=lambda:clock[0])
 targets.ready=True;service.face_targets=targets
 def feed(source):
  global fid
  fid+=1;clock[0]+=700;state.captured(clock[0]);targets.process((source,fid,clock[0]),detector)
  packet,service.pending=service.pending,None
  if packet:service.process(packet,extractor)
 def command(action,params,cid):
  value=state.snapshot();now=clock[0]
  return {'protocol_version':'aura-ui-1','board_boot_id':state.boot,'service_epoch':state.epoch,
   'command_id':cid,'ui_epoch':'public-test','ui_generation':0,'context':value['context'],
   'snapshot_sequence':value['sequence'],'issued_mono_ms':now,'deadline_mono_ms':now+2500,'action':action,'params':params}
 try:
  for _ in range(3):feed(image)
  value=validate_snapshot(state.snapshot(),state.boot,clock[0]);identity=value['modules']['identity']
  assert value['modules']['target']['selected'] is None and value['capabilities']['identity_sample_start']
  flow=VoiceEnrollment(state.boot,state.snapshot,state.command,simple=True,now_ms=lambda:clock[0],clock=lambda:clock[0]/1000)
  assert flow.handle('帮我登记身份我叫测试访客',state.snapshot())['code']=='prepare_name' and store.revision==0
  assert flow.handle('确认登记',state.snapshot())['code']=='sample_auto' and store.revision==0
  for _ in range(27):feed(image)
  value=validate_snapshot(state.snapshot(),state.boot,clock[0]);identity=value['modules']['identity']
  assert identity['enrollment_sampling']['counts']=={'collect':10,'validate':5}
  assert value['capabilities']['identity_enroll'] and store.revision==0
  replies=[];flow.guide(lambda reply,final:replies.append((reply,final)))
  assert replies==[({'code':'registered','name':''},True)] and store.revision==1
  assert flow.public()['stage']=='idle'
  archive=json.loads((photos.root/photos.health()['latest_session']/'manifest.json').read_text())
  assert archive['outcome']=='committed' and archive['database_revision_after']==1
  assert len(archive['images'])==27 and len(archive['validation_frame_ids'])==5
  assert archive['selected']['frame_id'] not in archive['validation_frame_ids']
  assert not photos.health()['error']
  for row in archive['images']:
   assert cv2.imread(str(photos.root/archive['session_id']/row['filename'])).shape==(112,112,3)
  for _ in range(2):feed(image)
  assert state.snapshot()['modules']['identity']['state']=='KNOWN'
  assert flow.handle('我是谁',state.snapshot())=={'code':'identity_seen','name':'测试访客'}
  health=service.health();ref=state.snapshot()['modules']['identity']['face_preview']
  png=service.face_preview(ref['target'],ref['frame_id']);assert png and len(png)<65536
  feed(blank);assert state.snapshot()['modules']['identity']['state']=='UNKNOWN'
  assert flow.handle('我是谁',state.snapshot())=={'code':'identity_unavailable','name':''}
  assert service.face_preview(ref['target'],ref['frame_id']) is None
  print(json.dumps({'status':'PASS_REAL_PUBLIC_ENROLL_KNOWN_SPOKEN_QUERY_AND_LOSS_NO_NAME','identity_health':health,
   'counts':{'collect':10,'validate':5},'pose_labels_injected_for_public_fixture':False,
   'sequential_driver_with_logical_capture_clock':True,'user_database_opened':False,'camera_opened':False,'user_photos_saved':False,'public_test_photos_temporary':27,'all_saved_sizes':[112,112],'selected_and_five_later_validation_photos_labeled':True,'threshold':config['threshold']}))
 finally:service.close()
""".replace('CONFIG_PATH',repr(str(stage/'camera_live_config/board_identity.json')))
run=subprocess.run(['python3','-B','-c',probe],cwd=root/'aura',env=env,capture_output=True,text=True,timeout=100)
(stage/'real_models.log').write_text(run.stdout+run.stderr)
bootstrap=r"""
import json,tempfile
from pathlib import Path
from unittest.mock import patch
from tools.board_avatar_gtk import create_runtime_core
from tools.demo_script import create_demo_core
core=create_runtime_core(create_demo_core)
from board.runtime.audio.channel_jobs import ChannelConversationJobs
import board.identity.face_targets as targets
assert Path(targets.__file__).resolve().is_relative_to(Path.cwd())
with tempfile.TemporaryDirectory() as directory:
 with patch.object(ChannelConversationJobs,'prepare_feedback',lambda *a:None):
  jobs=ChannelConversationJobs({'enabled':False,'host':'127.0.0.1','port':8792,'timeout_ms':1000},'no-user-test',directory)
  assert jobs.identity_flow.public()['stage']=='idle';jobs.close()
print(json.dumps({'status':'PASS_ASSET_IMPORT_AND_VOICE_JOB_BOOTSTRAP','microphone_opened':False}))
"""
boot=subprocess.run(['python3','-B','-c',bootstrap],cwd=root/'aura',env=env,capture_output=True,text=True,timeout=45)
(stage/'bootstrap.log').write_text(boot.stdout+boot.stderr)
gui=r"""
import base64,json
from pathlib import Path
from types import SimpleNamespace
from tools.board_avatar_gtk import BoardAvatarStage,load_gtk,register_font
from tests.framework.test_identity_face_targets import png
Gtk,Gdk,Pixbuf,GLib=load_gtk();assert Gtk.init_check([])[0]
register_font(Path.cwd()/'assets/fonts/DroidSansFallbackFull.ttf')
provider=Gtk.CssProvider();provider.load_from_data(b'* {font:16px "Droid Sans Fallback";} button {font-size:18px;}')
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
class HiddenDialog(Gtk.Dialog):
 def show_all(self):self.get_content_area().show_all()
class Services:
 def set_identity_preview(self,enabled):self.enabled=enabled
 def read(self):
  key={'camera_epoch':'synthetic','track_id':7,'track_generation':1}
  ref={'target':key,'frame_id':1,'captured_mono_ms':1,'ttl_ms':3000}
  return {'snapshot':{'modules':{'identity':{'target_kind':'face','face_target':key,'state':'UNKNOWN'},
   'target':{'selected':None}},'capabilities':{'identity_enroll':True}},'pending_count':0,
   'identity_face':png(),'identity_face_reference':ref}
stage=BoardAvatarStage.__new__(BoardAvatarStage)
stage.Gtk=SimpleNamespace(Dialog=HiddenDialog,Label=Gtk.Label,Frame=Gtk.Frame,Image=Gtk.Image,Align=Gtk.Align,ResponseType=Gtk.ResponseType)
stage.Pixbuf=Pixbuf;stage.services=Services();stage.window=Gtk.Window();stage.identity_face_dialog=None
dialog=stage.create_identity_face_dialog();panel=stage.identity_face_dialog
assert panel['image'].get_pixbuf().get_width()==264 and panel['button'].get_sensitive()
content=dialog.get_content_area();parent=content.get_parent();parent.remove(content)
offscreen=Gtk.OffscreenWindow();offscreen.set_default_size(440,440);offscreen.add(content);offscreen.show_all()
while Gtk.events_pending():Gtk.main_iteration_do(False)
pixbuf=offscreen.get_pixbuf();assert pixbuf is not None
ok,raw=pixbuf.save_to_bufferv('png',[],[]);assert ok
print(json.dumps({'status':'PASS_REAL_GTK_FACE_ONLY_WIDGET','render_width':pixbuf.get_width(),'render_height':pixbuf.get_height(),
 'fixture_only':True,'visible_user_window_opened':False,'png_base64':base64.b64encode(raw).decode()}))
offscreen.destroy();stage.close_identity_face_dialog();stage.window.destroy()
"""
widget=subprocess.run(['python3','-B','-c',gui],cwd=root/'aura',env=env,capture_output=True,text=True,timeout=25)
(stage/'widget.log').write_text(widget.stderr)
result={'real_models_passed':run.returncode==0,'bootstrap_passed':boot.returncode==0,'widget_passed':widget.returncode==0,
 'real_models_log':run.stdout+run.stderr,'bootstrap_log':boot.stdout+boot.stderr,'widget_error':widget.stderr}
if widget.returncode==0:result['widget']=json.loads(widget.stdout)
print(json.dumps(result))
'''.replace('CANDIDATE',repr(candidate),1)
result=json.loads(ssh('python3 -B -',remote,timeout=180))
for key,name in [('real_models_log','real_models.log'),('bootstrap_log','bootstrap.log'),('widget_error','widget.log')]:
    (HERE/name).write_text(result.pop(key),encoding='utf-8')
if result.get('widget'):
    (HERE/'face_dialog_synthetic.png').write_bytes(base64.b64decode(result['widget'].pop('png_base64'),validate=True))
(HERE/'preflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
assert all(result[key] for key in ('real_models_passed','bootstrap_passed','widget_passed'))
