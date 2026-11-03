"""Load restored display configuration and start the existing owned GUI."""
import hashlib,json,subprocess,time
from pathlib import Path
root=Path('/home/root/aura-ui-time-rollback-20261021/before-2559')
record=json.loads((root/'result.json').read_text())
assert record['status']=='FILES_ROLLED_BACK_WAITING_DISPLAY_RESTART'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==record['boot_id']
for name,expected in record['targets'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected
def cmd(args,timeout=5):return subprocess.check_output(args,stderr=subprocess.STDOUT,text=True,timeout=timeout)
assert cmd(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']).strip()=='0'
assert cmd(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value']).strip()=='987'
marker=root/'display-restart-requested.json'
assert not marker.exists(),'Display restart already requested; inspect readiness instead of replaying'
marker.write_text(json.dumps({'boot_id':record['boot_id'],'at_monotonic':time.monotonic()})+'\n')
cmd(['systemctl','restart','--no-block','xserver-nodm.service'])
deadline=time.monotonic()+10
while time.monotonic()<deadline:
 current=cmd(['systemctl','show','xserver-nodm.service','-p','MainPID','--value']).strip()
 if current not in ['0','1047']:break
 time.sleep(.2)
else:raise RuntimeError('Xserver restart did not create a new owner; inspect before continuing')
cmd(['systemctl','reset-failed','aura-avatar-ui.service'])
cmd(['systemctl','start','--no-block','aura-avatar-ui.service'])
v={'status':'RESTORED_GRAPHICS_RESTARTED_UI_START_REQUESTED','boot_id':record['boot_id'],'xserver_pid':int(current),'camera_pid':987,'movement_commands_sent':0,'physical_panel_verified':False}
(root/'activation.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v),flush=True)
