import base64,hashlib,json,urllib.request
from pathlib import Path
unit=hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()
assert unit=='a29082bae1d382d7a43505d5a1d3a51fa2203081423755900e9d72836385e343'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:'+str(port)+path,timeout=3) as response:return json.load(response)
h=get(8790,'/health');s=h['dpu_schedule'];i=h['identity'];ui=get(8783,'/api/state')
render=ui.get('avatar_renderer') or {};presentation=render.get('presentation') or {}
gui=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/runtime/aura')
p=gui/'tools/render_performance.py';raw=p.read_bytes()
out={'read_only':True,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'unit_sha256':unit,'camera_pid':h['pid'],'capture_hz':h['capture_hz'],'yolo_hz':h['detection_hz'],
 'identity_backend':i['backend'],'identity_ready':i['ready'],'feature_inference':i.get('feature_inference'),
 'face_backend':i['face_targets']['backend'],'optional':s['optional'],'recovery':s['yunet_recovery'],
 'fault_events':s['optional_diagnostics']['fault_events'],'thread_observer':s['optional_diagnostics'].get('thread_sched_observer'),
 'gaps':i['face_targets']['freshness_metrics']['counters']['observed_gap_intervals'],
 'ui':{k:ui.get(k) for k in ('phase','playing','paused','audio_output_state')},
 'renderer_keys':list(render),'presentation_keys':list(presentation),
 'renderer_performance_log':presentation.get('performance_log'),
 'render_performance_source':{'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}}
print(json.dumps(out))
