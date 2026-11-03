"""Open the existing vision page in the sampled boot; no motion or display-mode command."""
import json,subprocess,time,urllib.request
from pathlib import Path

BOOT='c006a771-c3e4-4d4f-97d7-ade3dd774619'
def get(port,path):
    with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
def pid(unit):
    return subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True,timeout=3).strip()
def idle(u):
    assert u['phase']=='IDLE' and u['audio_output_state']=='IDLE_READY'
    assert u['playing'] is False
    assert u['manual_pan']['automatic_following'] is False
    assert u['handsfree_dialogue']['enabled'] is False and u['handsfree_dialogue']['microphone_open'] is False
def filtered(u):
    return {'page':u.get('ui_page'),'preview':u.get('ui_runtime',{}).get('preview_metrics',{}),
        'pan_state':u['manual_pan']['state'],'automatic_following':u['manual_pan']['automatic_following']}
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert pid('aura-avatar-ui.service')=='15092' and pid('aura-camera-ui.service')=='1333'
u=get(8783,'/api/state');idle(u)
d={'boot_id':BOOT,'original_page':u['ui_page'],'before':filtered(u),'page_command_sent':False}
if u['ui_page']!='vision':
    req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps({'type':'ui_page','page':'vision'}).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    with urllib.request.urlopen(req,timeout=4) as r:assert json.load(r)['ok']
    d['page_command_sent']=True
time.sleep(1)
a=get(8783,'/api/state');idle(a);assert a['ui_page']=='vision';d['first']=filtered(a)
time.sleep(2)
b=get(8783,'/api/state');idle(b);assert b['ui_page']=='vision';d['after']=filtered(b)
assert pid('aura-avatar-ui.service')=='15092' and pid('aura-camera-ui.service')=='1333'
d['physical_refresh_verified']=False
print(json.dumps(d))
