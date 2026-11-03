import hashlib,json,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');G=Path('/home/root/aura-pan-current-20261024/da36c36a/gui-reference-bound-v2')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get():
 with o.open(base+'/api/state',timeout=3) as f:return json.load(f)
before=get();m=before['manual_pan'];follow=m.get('face_follow') or {};path=Path(follow.get('report',''))
assert path.is_file() and str(path).startswith('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v11r1/runs/')
raw=path.read_bytes();report=json.loads(raw);assert report['consumer_manifest_sha256']=='524ad777aec14dc2d853708412bcef4f75e1e6937d528674cc154b361b8ce76d'
stop_reply=None
if m['automatic_following']:
 q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_stop"}',headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=3) as f:stop_reply=json.load(f)
end=time.monotonic()+10;after=None
while time.monotonic()<end:
 after=get()['manual_pan'];rb=after.get('readback') or {}
 if not after['automatic_following'] and after['state']=='READY' and rb.get('flags')==0 and rb.get('lease_left_ms')==0:break
 time.sleep(.2)
assert after and not after['automatic_following'] and after['state']=='READY'
assert after['readback']['flags']==0 and after['readback']['lease_left_ms']==0
s=json.loads((R/'state.json').read_text());s.update(phase='RECENTER_STOPPED_TWITCH_REVIEW',automatic_following=False,
 current_gui_pid=int(__import__('subprocess').check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)))
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
out=dict(status='CURRENT_RECENTER_STOPPED_TWITCH_TRACE_CAPTURED',boot_id=s['boot'],report=str(path),
 report_sha256=hashlib.sha256(raw).hexdigest(),pre_stop=follow,stop_request=stop_reply,
 stopped_readback=after['readback'],automatic_following=False,physical_smoothness_verified=False,
 camera_pid=s['current_camera_pid'])
print(json.dumps(out,ensure_ascii=False))
