"""Read-only camera/UI/process audit; never opens camera device or MMIO."""
import json,subprocess,time,urllib.request
from pathlib import Path
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def run(args):
 try:return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=3)[-10000:]
 except Exception as e:return type(e).__name__
def get(port,path):
 try:
  with opener.open('http://127.0.0.1:%s%s'%(port,path),timeout=1) as r:return json.load(r)
 except Exception as e:return {'error':type(e).__name__}
def sample():
 u=get(8783,'/api/state');c=get(8790,'/health');s=get(8790,'/v1/ui/status')
 v=u.get('ui_runtime') or {};snap=v.get('snapshot') or {};mods=s.get('modules',{})
 return {'mono':time.monotonic(),'ui':{k:u.get(k) for k in ['phase','playing','ui_page','ui_layer','sequence','ui_tick_ms','avatar_display','manual_pan']},
 'runtime':{k:v.get(k) for k in ['connection','error','preview_error','raw_preview','frame_visible','frame_reference','preview_metrics','pending_count']},
 'health':{k:v for k,v in c.items() if not any(t in k for t in ['identity','person','name','path','url','token'])},
 'camera':{k:s.get(k) for k in ['board_boot_id','service_epoch','sequence','preview','error']},
 'modules':{k:{a:b for a,b in val.items() if a in ['state','detail','detection_hz','people_count','count_kind']} for k,val in mods.items() if k in ['camera','vision','npu','pl','motion']}}
v={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'units':{},'samples':[]}
for unit in ['aura-avatar-ui.service','aura-camera-ui.service']:
 v['units'][unit]=run(['systemctl','show',unit,'-p','ActiveState,SubState,MainPID,ExecStart,WorkingDirectory,NRestarts,MemoryCurrent,CPUUsageNSec,TasksCurrent'])
v['processes_before']=run(['ps','-eo','pid,ppid,stat,pcpu,pmem,rss,nlwp,etimes,wchan:25,args','--sort=-pcpu'])[:15000]
v['system']={'load':Path('/proc/loadavg').read_text(),'mem':run(['free','-m']),'space':run(['df','-h','/run','/dev/shm','/home/root']),'devices':run(['ls','-l','/dev/video0','/dev/video1']),
 'kernel':run(['dmesg','--level=err,warn'])[-6000:], 'listeners':run(['ss','-lntp'])}
for i in range(4):
 v['samples'].append(sample())
 if i<3:time.sleep(2)
v['threads']=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  cmd=(p/'cmdline').read_bytes()
  if not any(x in cmd for x in [b'/tools/board_avatar_pan.py',b'/tools/board_camera_motion.py']):continue
  if b'python' not in cmd:continue
  v['threads'].append({'pid':p.name,'status':(p/'status').read_text(),'tasks':[{'tid':t.name,'name':(t/'comm').read_text().strip(),'wait':(t/'wchan').read_text().strip()} for t in (p/'task').iterdir()]})
 except OSError:pass
for u in v['units']:
 v[u+'-log']=run(['journalctl','-u',u,'-n','50','--no-pager','-o','cat'])
print(json.dumps(v),flush=True)
