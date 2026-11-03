import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='16a07283-9e14-45e6-816d-3bda4cf333a7'
cfg=json.loads((N/'startup/config.json').read_text());pins=cfg['component_sha256']
assert all(sha(N/'runtime/aura'/p)==v for p,v in pins.items())
h=get(8790,'/health');u=get(8783,'/api/state');d=h['dpu_schedule'];m=u['manual_pan']
assert h['pid']==13537 and not d['owner_fenced']
assert m['state']=='FAULT' and not m['automatic_following'] and m.get('readback') is None
fw=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
assert fw=='aura-visual-servo-b4096-v2.bit.bin'
settings=json.loads((R/'face-zone-settings.json').read_text())
assert settings['board_boot_id']==boot and settings['left_camera_ratio']==.1 and settings['right_ratio']==.7158253629442671
units={}
for name in ('aura-camera-ui.service','aura-avatar-ui.service','aura-face-zone-editor.service'):
 p=subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','NRestarts'],text=True)
 units[name]=dict(x.split('=',1) for x in p.splitlines() if '=' in x)
 assert units[name]['ActiveState']=='active'
owners=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  if any(os.path.realpath(fd)=='/dev/mem' for fd in (proc/'fd').iterdir()):owners.append(int(proc.name))
 except OSError:pass
assert not owners
cp=json.loads((R/'id-stop.json').read_text());assert cp['identity_stop_passed'] and cp['boot_id']==boot and cp['after_stop']['flags']==0
report=dict(status='JOINT_VIDEO_AND_LIVE_SHADOW_RESTORED_PHYSICAL_CONTROL_UNBOUND',boot_id=boot,firmware=fw,
 camera_pid=h['pid'],gui_component_pins_verified=len(pins),units=units,
 identity_ready=h['identity']['ready'],identity_error=h['identity']['error'],owner_fenced=d['owner_fenced'],
 primary_overruns=d['primary_period_overruns'],optional={k:{n:d['optional'][k].get(n) for n in ('calls','overruns','disabled','recovery')} for k in ('sface','yunet')},
 manual_state=m['state'],manual_error=m.get('error'),automatic_following=m['automatic_following'],
 preview=u['ui_runtime'].get('preview_metrics'),page=u['ui_page'],settings=settings,
 mmio_owner_pids=owners,MMIO_opened=False,motor_commands=0,
 earlier_this_boot_id_stop=cp['after_stop'],id_stop_is_physical_calibration=False,
 physical_control_rebound=False,physical_follow_validated=False)
out=R/'current-restoration-status.json';tmp=out.with_suffix('.audit');tmp.write_text(json.dumps(report,indent=2)+'\n');os.replace(tmp,out)
print(json.dumps(report))
