"""Export allowlisted code/metrics only; never export real camera images/UART."""
import hashlib,json,shutil
from pathlib import Path
J=Path(__file__).resolve().parent;A=Path('/home/ghmd/Win共享文件/语音共享文件/aura')
D=A.parent/'deliverables/2026-10-20_camera_preview_pan_audit'
def put(name,data):
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==data,name
 else:
  with p.open('xb') as f:f.write(data)
def js(name,value):put(name,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
provenance={}
def evidence(phase):
 status=json.loads((J/('latest-'+phase+'.json')).read_text());assert status['complete'],phase
 path=Path(status['evidence'])
 provenance[phase]={k:status[k] for k in ['source_sha256','sha256','exit_code']}
 return json.loads((path/'response.json').read_text())
audit=evidence('camera-stack-audit')
samples=[]
for row in audit['samples']:
 health={k:row['health'].get(k) for k in ['pid','capture_frames','capture_hz','detection_hz','capture_age_ms','observation_age_ms','preview_frames','preview_hz','camera_error','detector_error','preview_error']}
 ui={k:v for k,v in row['ui'].items() if k!='manual_pan'}
 samples.append({'mono':row['mono'],'ui':ui,'runtime':row['runtime'],'health':health,'camera':row['camera'],'modules':row['modules']})
js('evidence/audit-summary.json',{'boot':audit['boot'],'units':audit['units'],'samples':samples,'load':audit['system']['load'],'memory':audit['system']['mem'],'space':audit['system']['space']})
processes=evidence('camera-screen-probe')
rows=[r for r in processes['processes'] if ' -c ' not in r['cmd'] or r['pid']=='207278']
js('evidence/process-ownership.json',{'processes':rows,'device_owners':processes['device_owners'],'kernel_relevant':processes['kernel_relevant']})
js('evidence/source-hashes-and-errors.json',evidence('camera-source-audit'))
js('evidence/voice-audio-baseline.json',evidence('camera-repair-baseline'))
js('evidence/deployment-result.json',evidence('camera-repair-result-ready')['deployment'])
js('evidence/screen-check.json',evidence('camera-repair-screen'))
js('evidence/cycle-check.json',evidence('camera-repair-cycles'))
fine=json.loads((J/'latest-camera-repair-fine-mode.json').read_text())
js('evidence/fine-preference-not-executed.json',{'complete':fine['complete'],'exit_code':fine['exit_code'],'scope':'ASSERTED_PANEL_OPEN_BEFORE_ANY_UI_ACTION','reason':'Panel was closed; preference action not executed; no motion'})
put('board-avatar-preview.patch',(J/'camera-repair/board-avatar-preview.patch').read_bytes())
put('board-runtime/tools/board_avatar_gtk.py',(J/'camera-repair/board_avatar_gtk.py').read_bytes())
for rel in ['tools/pan_controls.py','docs/BOARD_PAN_MANUAL.md']:
 put('shared-runtime/'+rel,(A/rel).read_bytes())
put('validation/check_camera_pan_native.py',(J/'check_camera_pan_native.py').read_bytes())
put('validation/framework-tests.txt',(J/'camera-repair/framework-tests.txt').read_bytes())
put('validation/native-gtk-result.json',(J/'camera-repair/native-gtk-v1/result.json').read_bytes())
put('validation/native-gtk-pass.log',(J/'camera-repair/native-gtk-v1.log').read_bytes())
put('validation/native-gtk-baseline.log',(J/'camera-repair/native-gtk-baseline.log').read_bytes())
for name in ['initial.png','expired-cleared.png','source-recovered.png','pan-open-0.png','remap-4.png']:
 put('validation/synthetic-only/'+name,(J/'camera-repair/native-gtk-v1'/name).read_bytes())
for name in ['board_camera_stack_audit.py','board_camera_source_audit.py','board_camera_screen_probe.py','board_camera_uncover_probe.py','board_camera_expand_probe.py','board_camera_repair_deploy.py','board_camera_repair_screen_check.py','board_camera_repair_cycle_check.py']:
 put('validation/sources/'+name,(J/name).read_bytes())
js('evidence/provenance.json',provenance)
manifest={str(p.relative_to(D)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(D.rglob('*')) if p.is_file() and p.name!='files.json'}
js('files.json',{'schema_version':1,'files':manifest,'excludes':['actual camera images','actual full screen images','identity database','model weights','serial.raw']})
print(json.dumps({'delivery':str(D),'files':len(manifest),'bytes':sum(v['bytes'] for v in manifest.values())}))
