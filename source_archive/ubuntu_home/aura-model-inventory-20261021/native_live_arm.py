import hashlib,json,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
assert hashlib.sha256((root/'boot_ops.py').read_bytes()).hexdigest()=='779200674f546e7735366de776e4f6ea4c0152b92563fee5371a858bd10246f5'
p=subprocess.run(['/usr/bin/python3','-B',str(root/'boot_ops.py'),'--root',str(root),'arm'],capture_output=True,text=True,timeout=25)
assert p.returncode==0,p.stderr[-1500:]
state=json.loads(p.stdout)
units={}
for name in ['aura-camera-ui.service','aura-avatar-ui.service']:
 out=subprocess.check_output(['systemctl','show',name,'-p','ExecCondition','-p','Restart','-p','MainPID','-p','ActiveState'],text=True)
 units[name]=dict(line.split('=',1) for line in out.splitlines() if '=' in line)
assert units['aura-camera-ui.service']['MainPID']=='29563' and units['aura-avatar-ui.service']['MainPID']=='29588'
assert all(v['Restart']=='no' and 'boot_ops.py' in v['ExecCondition'] for v in units.values())
print(json.dumps({'armed':True,'state':state,'units':units,'reboots':0,'model_jobs':0}))
