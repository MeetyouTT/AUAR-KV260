import fcntl,hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-system-pan-20261028/restore-5f167a36');s=json.loads((R/'gui-prepared.json').read_text());G=Path(s['gui']);OLD=Path(s['old_gui'])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(a,t=10):
 p=subprocess.run(a,capture_output=True,text=True,timeout=t);assert p.returncode==0,p.stderr[-400:];return p.stdout
def pid(n):return run(['systemctl','show',n,'-p','MainPID','--value']).strip()
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as f:return json.load(f)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot_id']
assert sha(G/'startup/config.json')==s['config_sha256'] and sha(OLD/'startup/config.json')=='3d84681a728617eea1cb28b619a376f9b3798a41c04d8fb57759947a3479294f'
assert pid('aura-avatar-ui.service')==str(s['old_gui_pid']) and pid('aura-camera-ui.service')==str(s['camera_pid'])
u=get(8783,'/api/state');assert u['phase']=='IDLE' and not u['playing'] and not u['manual_pan']['automatic_following'] and not u['handsfree_dialogue']['enabled']
cfg=json.loads((G/'startup/config.json').read_text());assert all(sha(G/'runtime/aura'/n)==h for n,h in cfg['component_sha256'].items())
lock=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
unit=Path('/etc/systemd/system/aura-avatar-ui.service.d')/('z'*33+'-aura-pan-continuity-20261028.conf')
assert not unit.exists()
run(['systemctl','stop','--no-block','aura-avatar-ui.service']);end=time.monotonic()+30
while pid('aura-avatar-ui.service')!='0' and time.monotonic()<end:time.sleep(.2)
assert pid('aura-avatar-ui.service')=='0'
text='[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(G/'startup/launcher.py')+' --config '+str(G/'startup/config.json')+'\nWorkingDirectory='+str(G/'runtime/aura')+'\n'
with unit.open('x') as f:f.write(text);f.flush();os.fsync(f.fileno())
run(['systemctl','daemon-reload'])
try:
 assert str(G/'startup/launcher.py') in run(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'])
 assert pid('aura-camera-ui.service')==str(s['camera_pid'])
 run(['systemctl','start','--no-block','aura-avatar-ui.service'])
except BaseException:
 assert unit.read_text()==text;unit.unlink();run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-avatar-ui.service']);raise
s.update(status='ACTIVATING',dropin=str(unit),dropin_sha256=sha(unit));(R/'gui-prepared.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':s['status'],'gui_pid':pid('aura-avatar-ui.service'),'camera_pid':pid('aura-camera-ui.service'),'motion_commands':0,'new_gui':str(G),'preserved_components':s['preserved_components']}))
