import json,os,subprocess,urllib.request
from pathlib import Path
names=('aura-camera-ui.service','aura-avatar-ui.service','aura-face-zone-editor.service')
units={}
for unit in names:
 p=subprocess.run(['systemctl','show',unit,'-p','MainPID','-p','ControlPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainCode','-p','ExecMainStatus','-p','NRestarts','-p','ExecStart'],capture_output=True,text=True,timeout=3)
 units[unit]=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
procs=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  c=(p/'cgroup').read_text()
  if any('aura-camera-ui.service' in x or 'aura-avatar-ui.service' in x or 'aura-face-zone-editor.service' in x for x in c.splitlines()):
   stat=(p/'stat').read_text().rsplit(')',1)[1].split();procs.append({'pid':int(p.name),'state':stat[0],'ppid':int(stat[1]),'cgroup':c[:400]})
 except OSError:pass
endpoints={};op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for port,path in ((8790,'/health'),(8783,'/api/state')):
 try:
  with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as f:x=json.load(f)
  endpoints[str(port)]={'reachable':True}
  if port==8783:endpoints[str(port)].update(phase=x.get('phase'),manual=x.get('manual_pan'),audio=x.get('audio_output_state'))
  else:
   d=x['dpu_schedule'];endpoints[str(port)].update(pid=x['pid'],owner_fenced=d['owner_fenced'],native_critical=d.get('native_critical'),primary_overruns=d['primary_period_overruns'],capture_hz=x.get('capture_hz'),camera_error=x.get('camera_error'))
 except Exception as e:endpoints[str(port)]={'reachable':False,'error_type':type(e).__name__}
mem=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  if any(os.path.realpath(fd)=='/dev/mem' for fd in (proc/'fd').iterdir()):mem.append(int(proc.name))
 except OSError:pass
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'units':units,'owned_processes':procs,'endpoints':endpoints,
 'camera_nodes':[str(p) for p in Path('/dev').glob('video*')],'mmio_owner_pids':mem},ensure_ascii=False))
