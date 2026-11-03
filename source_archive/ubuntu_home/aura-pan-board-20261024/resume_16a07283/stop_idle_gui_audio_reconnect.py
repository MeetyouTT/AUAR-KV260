import fcntl,hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura';OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
def props():
 raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus','-p','Restart','-p','SendSIGKILL','-p','TimeoutStopUSec'],text=True)
 return dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
lock=(OPS/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
s=json.loads((R/'state.json').read_text());assert s['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health');unit=props()
assert u['phase']=='IDLE' and not u.get('playing') and u['audio_output_state']=='IDLE_READY'
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert Path('/proc/asound/card1/pcm0c/sub0/status').read_text().strip()=='closed'
assert h['pid']==604389 and not h['dpu_schedule']['owner_fenced']
assert unit['MainPID']=='137253' and unit['ActiveState']=='active' and unit['Restart']=='no' and unit['SendSIGKILL']=='no'
cfg=json.loads((G/'startup/config.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
before={'gui_pid':137253,'camera_pid':h['pid'],'readback':m['readback'],
 'primary_overruns':h['dpu_schedule']['primary_period_overruns'],'optional_overruns':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},
 'audio_output_state':u['audio_output_state'],'pcm_playback_state':Path('/proc/asound/card1/pcm0p/sub0/status').read_text().splitlines()[0],
 'startup_sha256':sha(G/'startup/config.json'),'boot':s['boot']}
p=R/'idle-gui-audio-reconnect-before.json';assert not p.exists();p.write_text(json.dumps(before,indent=2)+'\n')
subprocess.run(['systemctl','stop','--no-block','aura-avatar-ui.service'],check=True)
end=time.monotonic()+12
while time.monotonic()<end:
 unit=props()
 if unit['MainPID']=='0':break
 time.sleep(.2)
assert unit['MainPID']=='0' and unit['Result']=='success' and unit['ExecMainStatus']=='0',unit
pcm=Path('/proc/asound/card1/pcm0p/sub0/status').read_text().strip()
assert pcm=='closed',pcm
after=get(8790,'/health');assert after['pid']==h['pid'] and not after['dpu_schedule']['owner_fenced']
s.update(phase='IDLE_GUI_AUDIO_RECONNECT_STOPPED',automatic_following=False)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'gui_stop_result':unit,'pcm_closed':True,'camera_pid_unchanged':after['pid'],
 'primary_overruns':after['dpu_schedule']['primary_period_overruns'],'old_readback':m['readback'],'new_motion_requested':False}))
