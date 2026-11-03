"""Stop the inspected idle owners once and preserve their minimum history."""
import fcntl,hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
BOOT='c006a771-c3e4-4d4f-97d7-ade3dd774619'
ROOT=Path('/home/root/aura-hdmi-resume-20261029')/BOOT
CAM='aura-camera-ui.service';GUI='aura-avatar-ui.service'
PINS={
 '/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/board_camera_ui.proposed.json':'e137bbb7894ecebcaadc8e57abc4bd8794c80dc3b9c1f87f09389a53ef88af20',
 '/home/root/aura-device-skills-20261028/0cd7c3445a84475098b938d5b97175e0/startup/config.json':'69fa9b565e9e37cbe7d8cb5a6f2aaa071ee2fb2842845c2d7b6e1cd232f2e444',
 '/etc/systemd/system/aura-camera-ui.service':'29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512',
 '/etc/systemd/system/aura-avatar-ui.service':'e2012104d6db817609d00f1c0a53091741fd99fbb46f6b97dd74d33851df17a3',
 '/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/face-source-v17/entry.py':'f26be22cb640bf44a1bd81b66bb3fa014f5b847b13320781836bf3f173387623',
 '/home/root/aura-device-skills-20261028/0cd7c3445a84475098b938d5b97175e0/startup/launcher.py':'cd1680220b60f6120db1bc847ca59cfd445796ff37e48a3ba93efca65eddfd98'}
def props(unit):
    s=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','Result','-p','ExecMainStatus','-p','Restart','-p','KillMode','-p','SendSIGKILL','-p','TimeoutStopUSec'],text=True,timeout=3)
    return dict(v.split('=',1) for v in s.splitlines() if '=' in v)
def get(port,path):
    with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
def birth(pid):return int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])
def save(name,value):
    with (ROOT/name).open('x') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
lock=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in PINS.items())
c=props(CAM);g=props(GUI)
assert c['MainPID']=='1333' and birth(1333)==2352 and g['MainPID']=='15092' and birth(15092)==107356
assert c['Restart']=='no' and c['KillMode']=='process' and c['SendSIGKILL']=='no' and c['TimeoutStopUSec']=='infinity'
h=get(8790,'/health');u=get(8783,'/api/state')
assert h['pid']==1333 and h['dpu_schedule']['native_critical'] and not h['dpu_schedule']['owner_fenced']
assert u['phase']=='IDLE' and u['audio_output_state']=='IDLE_READY' and not u['playing'] and not u['pending_job']
assert u['manual_pan']['state']=='FAULT' and u['manual_pan']['automatic_following'] is False
assert not u['handsfree_dialogue']['enabled'] and not u['handsfree_dialogue']['microphone_open']
assert u['local_recording']['state']!='RECORDING' and not u['local_transcription'].get('service',{}).get('pending')
ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
save('before.json',{'boot_id':BOOT,'pid':1333,'birth':2352,'pins':PINS,'dpu_schedule':h['dpu_schedule'],'identity':{'feature_inference':{'completed':h['identity']['feature_inference']['completed']}},'original_page':u['ui_page']})
for unit in [GUI,CAM]:
    subprocess.run(['systemctl','stop','--no-block',unit],check=True,timeout=3)
    end=time.monotonic()+10
    while props(unit)['MainPID']!='0' and time.monotonic()<end:time.sleep(.2)
    v=props(unit);assert v['MainPID']=='0' and v['Result']=='success' and v['ExecMainStatus']=='0','Normal stop not verified; no poweroff'
save('stopped.json',{'gui':props(GUI),'camera':props(CAM),'boot_id':BOOT})
print(json.dumps({'normal_service_stop_verified':True,'poweroff_scheduled':False,'next':'Verify fresh checkpoint and released DPU before shutdown','journal':str(ROOT)}))
