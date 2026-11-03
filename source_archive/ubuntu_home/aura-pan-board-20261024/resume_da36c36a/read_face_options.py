import json,subprocess,urllib.request
from pathlib import Path
cmd=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
import re
c=Path(re.search(r'--config (/[^ ;]+)',cmd).group(1));root=json.loads(c.read_text());a=Path(root['runtime'])/'aura'
f=json.loads((a/'config/pan_face.local.json').read_text());m=json.loads((a/'config/pan_manual.local.json').read_text())
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as h:s=json.load(h)
follow=s['manual_pan'].get('face_follow') or {}
print(json.dumps({'config':{'mode':f.get('mode'),'duration_s':f.get('duration_s'),
 'automatic_following_enabled':f.get('automatic_following_enabled'),'left_button_pulse_sign':f.get('left_button_pulse_sign'),
 'manifest_sha256':f.get('manifest_sha256'),'component_pins':len(root['component_sha256'])},
 'manual':{k:m.get(k) for k in ('enabled','boot_id','fdt_sha256','manual_minimum_us','manual_maximum_us','maximum_step_us','maximum_duration_s','automatic_following_enabled','center_reference_us','center_reference_source')},
 'page':s.get('ui_page'),'native_canvas':s.get('native_canvas'),'ui_runtime':s.get('ui_runtime'),
 'follow':{k:follow.get(k) for k in ('state','phase','reason','commands_accepted','pulse_us','readback')},
 'unit':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','NRestarts','-p','ActiveState'],text=True)},ensure_ascii=False))
