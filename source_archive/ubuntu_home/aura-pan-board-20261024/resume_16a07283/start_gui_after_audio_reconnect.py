import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura';unit='aura-avatar-ui.service'
b=json.loads((R/'idle-gui-audio-reconnect-before.json').read_text());s=json.loads((R/'state.json').read_text())
assert s['phase']=='IDLE_GUI_AUDIO_RECONNECT_STOPPED' and s['boot']==b['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()=='0'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(G/'startup/config.json')==b['startup_sha256']
cfg=json.loads((G/'startup/config.json').read_text());assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as f:return json.load(f)
assert get(8790,'/health')['pid']==b['camera_pid']
subprocess.run(['systemctl','start','--no-block',unit],check=True)
end=time.monotonic()+18;u=None
while time.monotonic()<end:
 try:
  v=get(8783,'/api/state');m=v['manual_pan']
  if m['state']=='READY' and v.get('audio_output_state')=='IDLE_READY':u=v;break
 except (OSError,ValueError,KeyError):pass
 time.sleep(.25)
pid=int(subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True))
if u is None:
 print(json.dumps({'status':'GUI_RECONNECT_STARTING','gui_pid':pid,'automatic_kill':False}));raise SystemExit(0)
m=u['manual_pan'];assert not m['automatic_following'] and m['readback']==b['readback']
h=get(8790,'/health');assert h['pid']==b['camera_pid'] and not h['dpu_schedule']['owner_fenced']
s.update(phase='R12_SOURCE_V14_READY_OUTPUT_STOPPED',current_gui_pid=pid,automatic_following=False,
 idle_audio_reconnect_completed=True,current_camera_pid=h['pid'])
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
out={'status':s['phase'],'gui_pid':pid,'camera_pid_unchanged':h['pid'],'readback_unchanged':m['readback'],
 'audio_output_state':u['audio_output_state'],'phase':u['phase'],'primary_overruns':h['dpu_schedule']['primary_period_overruns'],
 'optional_overruns':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},'new_motion_requested':False}
(R/'idle-gui-audio-reconnect-after.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
