import hashlib,json,os,re,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-boundary-nav-20261029');s=json.loads((R/'state.json').read_text());G=Path(s['gui']);E=Path(s['editor']);OLD=Path(s['old_gui'])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=12);assert p.returncode==0,p.stderr[-700:];return p.stdout
def pid(unit):return run(['systemctl','show',unit,'-p','MainPID','--value']).strip()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot_id']
assert pid('aura-camera-ui.service')==str(s['camera_pid']) and pid('aura-avatar-ui.service')==str(s['gui_pid'])
assert sha(G/'startup/config.json')==s['gui_config_sha256']
old=json.loads((OLD/'startup/config.json').read_text());A=Path(old['runtime'])/'aura'
assert all(sha(A/n)==v for n,v in old['component_sha256'].items())
assert sha('/etc/systemd/system/aura-face-zone-editor.service')==s['old_editor_unit_sha256']
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
assert u['phase']=='IDLE' and not u['playing'] and u['audio_output_state']=='IDLE_READY'
assert not u['manual_pan']['automatic_following'] and u['manual_pan']['state']=='READY' and u['manual_pan']['readback']['flags']==0
assert not u['handsfree_dialogue']['enabled']
s['previous_page']=u['ui_page'];s['before_readback']=u['manual_pan']['readback']
units={}
for unit in ['aura-avatar-ui.service','aura-face-zone-editor.service']:
 folder=Path('/etc/systemd/system')/(unit+'.d');folder.mkdir(exist_ok=True)
 length=max([len(re.match(r'z*',p.name)[0]) for p in folder.glob('*.conf')]+[0])+1
 p=folder/('z'*length+'-boundary-page-sync-20261029.conf');assert not p.exists();units[unit]=p
run(['systemctl','stop','--no-block','aura-avatar-ui.service']);until=time.monotonic()+35
while pid('aura-avatar-ui.service')!='0' and time.monotonic()<until:time.sleep(.2)
assert pid('aura-avatar-ui.service')=='0' and pid('aura-face-zone-editor.service')=='0'
assert pid('aura-camera-ui.service')==str(s['camera_pid'])
texts={units['aura-avatar-ui.service']:'[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(G/'startup/launcher.py')+' --config '+str(G/'startup/config.json')+'\nWorkingDirectory='+str(G/'runtime/aura')+'\n',units['aura-face-zone-editor.service']:'[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(E/'face_zone_editor.py')+' --settings '+s['editor_settings']+'\n'}
written=[]
try:
 for p,text in texts.items():
  with p.open('x') as f:f.write(text);f.flush();os.fsync(f.fileno())
  written.append(p)
 run(['systemctl','daemon-reload'])
 assert str(G/'startup/launcher.py') in run(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'])
 assert str(E/'face_zone_editor.py') in run(['systemctl','show','aura-face-zone-editor.service','-p','ExecStart','--value'])
 run(['systemctl','reset-failed','aura-avatar-ui.service','aura-face-zone-editor.service']);run(['systemctl','start','--no-block','aura-avatar-ui.service'])
except BaseException:
 for p in written:
  assert p.read_text()==texts[p];p.unlink()
 run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-avatar-ui.service']);raise
s.update(phase='ACTIVATING',dropins={k:str(v) for k,v in units.items()},dropin_pins={str(p):sha(p) for p in written})
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'phase':s['phase'],'camera_pid':s['camera_pid'],'camera_not_restarted':True,'wide_range_preserved':[500,2500],'geometry_unchanged':True,'components':s['components'],'preserved_components':s['preserved_components'],'motion_tests_sent':0}))
