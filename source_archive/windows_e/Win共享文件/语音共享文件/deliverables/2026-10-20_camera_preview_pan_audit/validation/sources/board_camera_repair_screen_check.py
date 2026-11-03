"""Verify screen, geometry and hashes; no jog."""
import base64,hashlib,json,sys,time,urllib.request
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
p=Path('/home/root/aura-pan-manual-ui-20261020/camera-fix-v3')
assert json.loads((p/'deployment-result.json').read_text())['status']=='CAMERA_FIX_INSTALLED_PANEL_OPEN_SCREEN_VERIFICATION_PENDING'
conf=json.loads((p/'startup/config.json').read_text());root=Path(conf['runtime'])/'aura'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));url='http://127.0.0.1:8783'
def api(data=None):
 req=url+'/api/state' if data is None else urllib.request.Request(url+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':url})
 with op.open(req,timeout=2) as r:return json.load(r)
ack=api({'type':'save_evidence'});assert ack['ok'];report_path=Path(ack['report'])
for _ in range(30):
 if report_path.exists():break
 time.sleep(.1)
assert report_path.is_file(),api().get('diagnostic_job')
report=json.loads(report_path.read_text());s=api();geometry=report['ui_geometry']
controls=geometry['visible_controls'];pan={k:v for k,v in controls.items() if k in ['pan_left','pan_stop','pan_right']}
assert len(pan)==3
assert all(v['x']>=593 and v['x']+v['width']<=1016 and v['y']+v['height']<=548 for v in pan.values()),pan
assert not geometry['dialogs'] and not report['errors']
bad=[rel for rel,sha in conf['component_sha256'].items() if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=sha]
assert not bad,bad
baseline=json.loads(Path('/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/startup/config.json').read_text())['component_sha256']
preserved=[rel for rel,sha in baseline.items() if hashlib.sha256((root/rel).read_bytes()).hexdigest()==sha]
assert len(preserved)==len(baseline)-1
sys.path.insert(0,str(root))
from board.vision.local_preview import RawFrameReader
from tools.board_screen_capture import capture
with op.open('http://127.0.0.1:8790/v1/ui/status',timeout=1) as r:snap=json.load(r)
owner={k:snap[k] for k in ['board_boot_id','service_epoch']};owner['camera_epoch']=snap['preview']['camera_epoch']
packet=RawFrameReader(owner).read(int(time.monotonic()*1000));assert packet
header,pixels=packet
dest=p/'screen-panel-private.png';capture(dest)
with Image.open(str(dest)) as source:
 camera=source.crop((92,112,492,412)).resize((64,48))
 expected=Image.frombytes('RGB',(640,480),pixels,'raw','BGR').resize((64,48))
 difference=sum(ImageStat.Stat(ImageChops.difference(camera,expected)).mean)/3
 source.thumbnail((768,450));preview=p/'screen-panel-private.jpg';source.save(str(preview),quality=72)
assert difference<60,('Camera pixels do not match source',difference)
readback=s['manual_pan']['readback'];assert readback['flags']==0 and readback['lease_left_ms']==0
data=preview.read_bytes()
v={'status':'SCREEN_AND_MANIFEST_PASS','geometry':geometry,'errors':report['errors'],'diagnostic_job':s['diagnostic_job'],
 'component_count':len(conf['component_sha256']),'hash_mismatches':bad,'original_core_count':len(baseline),'original_core_preserved':len(preserved),
 'camera_source_frame':header['frame_id'],'screen_source_mean_abs_rgb_difference':round(difference,3),
 'preview':s.get('ui_runtime',{}).get('preview_metrics'),'pan':s['manual_pan'],'display_off_seconds':conf['display_retrain_off_seconds'],
 'artifacts':{'repaired-panel-private.jpg':{'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}}}
print(json.dumps(v),flush=True)
