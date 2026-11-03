import json
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r8/runs/ui-11787894628582/trial.json')
r=json.loads(p.read_text());assert r['status']=='CONTINUOUS_FACE_ZONE_STOPPED'
x=r['result'];trace=x['command_trace'];print(json.dumps({'status':r['status'],'parameters':r['control_parameters'],'telemetry':r.get('telemetry'),'result':{k:x.get(k) for k in ('state','reason','elapsed_s','commands_accepted','motion_target_changes','segments','range_us','fatal','stopped')},'input':r['input_summary'],'commands':trace[-12:]}))
