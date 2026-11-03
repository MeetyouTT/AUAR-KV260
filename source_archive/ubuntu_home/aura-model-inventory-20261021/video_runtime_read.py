import hashlib,json,subprocess,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=4) as r:u=json.load(r)
runtime=u.get('ui_runtime') or {}
out={'ui_page':u.get('ui_page'),'ui_layer':u.get('ui_layer'),'runtime_keys':list(runtime),
 'runtime_preview':{k:runtime.get(k) for k in ('frame_visible','frame_reference','preview_metrics','page','layer')},
 'tools':subprocess.run(['sh','-c','command -v perf; command -v gst-launch-1.0; command -v gst-inspect-1.0'],capture_output=True,text=True).stdout,
 'perf_paranoid':Path('/proc/sys/kernel/perf_event_paranoid').read_text().strip() if Path('/proc/sys/kernel/perf_event_paranoid').exists() else None}
out['queue_threads']=[]
for task in Path('/proc/450593/task').iterdir():
 try:
  name=(task/'comm').read_text().strip()
  if name.startswith('queue'):out['queue_threads'].append({'tid':task.name,'name':name,'wchan':(task/'wchan').read_text().strip()})
 except OSError:pass
print(json.dumps(out))
