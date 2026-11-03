import json,os,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
env=dict(os.environ,DISPLAY=':0')
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=8,env=env)
 return {'exit_code':p.returncode,'stdout':p.stdout[-6000:],'stderr':p.stderr[-1000:]}
print(json.dumps({'xset':run(['xset','q']),'xrandr':run(['xrandr','--current']),
 'units':run(['systemctl','show','xserver-nodm.service','aura-avatar-ui.service','aura-camera-ui.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts']),
 'module_present':Path('/sys/module/aura_dp_retrain_candidate').exists()}))
