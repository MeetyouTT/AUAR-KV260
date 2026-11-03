"""Wake the confirmed boot once if DPMS is Off; preserve configured idle timeout."""
import json,os,subprocess,time,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='c006a771-c3e4-4d4f-97d7-ade3dd774619'
assert subprocess.check_output(['systemctl','show','xserver-nodm.service','-p','MainPID','--value'],text=True,timeout=3).strip()=='1084'
def run(args):
    p=subprocess.run(args,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=4)
    assert p.returncode==0
    return p.stdout
before=run(['xset','q']);d={'before_xset':before,'wake_command_sent':False}
if 'Monitor is Off' in before:
    d['wake_output']=run(['xset','dpms','force','on']);d['wake_command_sent']=True
time.sleep(.3)
d['after_xset']=run(['xset','q'])
d['connector']={k:(Path('/sys/class/drm/card0-DP-1')/k).read_text().strip() for k in ['status','enabled','dpms']}
d['drm_state']=Path('/sys/kernel/debug/dri/0/state').read_text()
d['services']=run(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts'])
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
d['ui']={'page':u['ui_page'],'automatic_following':u['manual_pan']['automatic_following'],'preview':u.get('ui_runtime',{}).get('preview_metrics',{})}
d['physical_panel_verified']=False
print(json.dumps(d))
