"""Switch only the owned GUI; no physical move and no camera restart."""
import fcntl,hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
DROP=Path('/etc/systemd/system/aura-avatar-ui.service.d/zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz-aura-pan-da36-reference-merged.conf')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def command(args):return subprocess.check_output(args,text=True,stderr=subprocess.PIPE,timeout=10)
def pid(unit):return command(['systemctl','show',unit,'-p','MainPID','--value']).strip()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
s=json.loads((R/'state.json').read_text());assert s['phase']=='CURRENT_REFERENCE_GUI_PREPARED_NO_MOTION'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot'] and not DROP.exists()
G=Path(s['gui_release']);assert sha(G/'startup/config.json')==s['startup_config_sha256'] and sha(G/'manual-release/release.json')==s['manual_release_sha256']
h=get(8790,'/health');u=get(8783,'/api/state')
assert h['pid']==54394 and not h['dpu_schedule']['owner_fenced'] and pid('aura-avatar-ui.service')=='294019'
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
assert u.get('local_recording',{}).get('state')!='RECORDING' and not u.get('local_transcription',{}).get('service',{}).get('pending')
assert not u['manual_pan']['automatic_following'] and u['manual_pan']['state']=='FAULT'
lock=(O/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert pid("aura-avatar-ui.service")=='294019'
assert sha(Path('/home/root/aura-animation-dialogue-20261026/d6d1617467724213b3d9fd3d11530a47/startup/config.json'))=='43d918e8dac724149cd9eaa5c3b709f0e7186516b5484f0150fab911bcbecd2f'
assert '/home/root/aura-animation-dialogue-20261026/d6d1617467724213b3d9fd3d11530a47/startup/config.json' in command(["systemctl","show","aura-avatar-ui.service","-p","ExecStart","--value"])
command(['systemctl','stop','--no-block','aura-avatar-ui.service']);end=time.monotonic()+35
while pid('aura-avatar-ui.service')!='0' and time.monotonic()<end:time.sleep(.2)
assert pid('aura-avatar-ui.service')=='0'
raw=('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(G/'startup/launcher.py')+' --config '+str(G/'startup/config.json')+'\nWorkingDirectory='+str(G/'runtime/aura')+'\n').encode()
with DROP.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
command(['systemctl','daemon-reload']);command(['systemctl','start','--no-block','aura-avatar-ui.service'])
s.update(phase='CURRENT_REFERENCE_GUI_STARTING_NO_MOTION',gui_dropin=str(DROP),gui_dropin_sha256=sha(DROP),previous_gui_release='/home/root/aura-animation-dialogue-20261026/d6d1617467724213b3d9fd3d11530a47')
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'camera_pid':get(8790,'/health')['pid'],'gui_pid':pid('aura-avatar-ui.service'),'motor_commands_sent':0,'automatic_following':False,'center_command_applied':False}))
