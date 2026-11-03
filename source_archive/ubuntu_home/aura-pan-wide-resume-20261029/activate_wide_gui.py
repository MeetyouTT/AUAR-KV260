import hashlib,json,os,re,subprocess
from pathlib import Path
BOOT='55152f95-ea3a-4c6c-82e6-51bd553d96fd';R=Path('/home/root/aura-pan-wide-resume-20261029/55152f95')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=10);assert p.returncode==0,p.stderr[-600:];return p.stdout
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
s=json.loads((R/'wide-gui-prepared.json').read_text());G=Path(s['gui']);OLD=Path(s['old_gui'])
assert run(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']).strip()=='0'
assert run(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value']).strip()==str(s['camera_pid'])
old=json.loads((OLD/'startup/config.json').read_text());oldroot=Path(old['runtime'])/'aura'
assert all(sha(oldroot/n)==v for n,v in old['component_sha256'].items()),'Original device-skills source changed'
assert sha(G/'startup/config.json')==s['config_sha256']
cfg=json.loads((G/'startup/config.json').read_text());newroot=Path(cfg['runtime'])/'aura'
assert all(sha(newroot/n)==v for n,v in cfg['component_sha256'].items())
assert (newroot/'board/motion').resolve()==newroot/'board/motion'
folder=Path('/etc/systemd/system/aura-avatar-ui.service.d')
length=max([len(re.match(r'z*',p.name)[0]) for p in folder.glob('*.conf')]+[0])+1
unit=folder/('z'*length+'-aura-pan-wide-20261029.conf');assert not unit.exists()
text='[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(G/'startup/launcher.py')+' --config '+str(G/'startup/config.json')+'\nWorkingDirectory='+str(newroot)+'\n'
with unit.open('x') as f:f.write(text);f.flush();os.fsync(f.fileno())
run(['systemctl','daemon-reload'])
try:
 assert str(G/'startup/launcher.py') in run(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'])
 run(['systemctl','reset-failed','aura-avatar-ui.service']);run(['systemctl','start','--no-block','aura-avatar-ui.service'])
except BaseException:
 assert unit.read_text()==text;unit.unlink();run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-avatar-ui.service']);raise
s.update(phase='WIDE_GUI_STARTING',dropin=str(unit),dropin_sha256=sha(unit),original_components_still_intact=True)
(R/'wide-gui-prepared.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'phase':s['phase'],'gui':str(G),'component_count':s['components'],'preserved_components':s['preserved_components'],'range_us':[500,2500],'motion_commands':0,'dropin':str(unit)}))
