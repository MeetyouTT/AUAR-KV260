"""Bounded read-only CPU/scheduling profile; only numeric process metadata."""
import argparse
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import hashlib,http.client,json,os,pathlib,subprocess,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()==SPEC['startup_sha256']
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
leader=int(subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','--value','-p','MainPID'],text=True).strip())
assert leader>1
camera=CAMERA
hz=os.sysconf('SC_CLK_TCK');page=os.sysconf('SC_PAGE_SIZE')
def stat(path):
 raw=path.read_text();p=raw[raw.rfind(')')+2:].split()
 return dict(ppid=int(p[1]),ticks=int(p[11])+int(p[12]),nice=int(p[16]),threads=int(p[17]),
  start=int(p[19]),rss_mib=int(p[21])*page/1048576,processor=int(p[36]))
def sample():
 allp={}
 for path in pathlib.Path('/proc').iterdir():
  if not path.name.isdecimal():continue
  try:allp[int(path.name)]=stat(path/'stat')
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 owned={leader,camera};again=True
 while again:
  new={pid for pid,s in allp.items() if s['ppid'] in owned};again=bool(new-owned);owned.update(new)
 result={}
 for pid in sorted(owned):
  if pid not in allp:continue
  path=pathlib.Path('/proc')/str(pid);item=allp[pid];item['tasks']={}
  try:
   command=(path/'cmdline').read_bytes()
   role='supervisor' if pid==leader else 'camera' if pid==camera else 'worker'
   for token,label in ((b'board_frontend_process.py','audio_frontend'),(b'gstreamer_audio_worker.py','audio_playback'),
                       (b'board_avatar_gtk','gui'),(b'arecord','microphone')):
    if token in command:role=label;break
   item['role']=role
   for task in (path/'task').iterdir():
    try:
     row=stat(task/'stat');sched=[int(x) for x in (task/'schedstat').read_text().split()]
     row.update(runtime_ns=sched[0],runqueue_wait_ns=sched[1],slices=sched[2]);item['tasks'][int(task.name)]=row
    except (FileNotFoundError,ProcessLookupError):pass
   result[pid]=item
  except (FileNotFoundError,ProcessLookupError):pass
 cpus={}
 for line in pathlib.Path('/proc/stat').read_text().splitlines():
  parts=line.split()
  if parts and parts[0].startswith('cpu'):cpus[parts[0]]=[int(x) for x in parts[1:9]]
 gauges={}
 for kind,pattern,name in [('temperature','/sys/class/thermal/thermal_zone*/temp','temp_millic'),
                           ('frequency','/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq','khz')]:
  import glob
  for index,entry in enumerate(sorted(glob.glob(pattern))):
   try:gauges[kind+'_'+str(index)+'_'+name]=int(pathlib.Path(entry).read_text())
   except (ValueError,OSError):pass
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
 try:c.request('GET','/api/state');response=c.getresponse();state=json.loads(response.read(1048576))
 finally:c.close()
 state_meta=dict(playing=state.get('playing'),listening=state.get('handsfree_dialogue',{}).get('state'),
  capture_error=state.get('safe_capture_diagnostics',{}).get('error_code'),
  underruns=state.get('audio_output',{}).get('underrun_packets'),
  speech_active=state.get('safe_capture_diagnostics',{}).get('capture',{}).get('speech_active'),
  speech_starts=state.get('safe_capture_diagnostics',{}).get('counters',{}).get('speech_starts'),
  submitted=state.get('safe_capture_diagnostics',{}).get('counters',{}).get('submitted'))
 return dict(at=time.monotonic(),processes=result,cpus=cpus,gauges=gauges,state=state_meta)
a=sample();time.sleep(8);b=sample();elapsed=b['at']-a['at'];processes=[]
for pid,s in b['processes'].items():
 old=a['processes'].get(pid)
 if not old or old['start']!=s['start']:continue
 tasks=[]
 for tid,v in s['tasks'].items():
  before=old['tasks'].get(tid)
  if not before or before['start']!=v['start']:continue
  tasks.append(dict(tid=tid,nice=v['nice'],processor=v['processor'],
   cpu_core_percent=round((v['runtime_ns']-before['runtime_ns'])/1e9/elapsed*100,2),
   runqueue_wait_ms=round((v['runqueue_wait_ns']-before['runqueue_wait_ns'])/1e6,2),
   scheduler_slices=v['slices']-before['slices']))
 processes.append(dict(pid=pid,role=s['role'],nice=s['nice'],rss_mib=round(s['rss_mib'],2),threads=s['threads'],
  cpu_core_percent=round((s['ticks']-old['ticks'])/hz/elapsed*100,2),tasks=sorted(tasks,key=lambda x:-x['cpu_core_percent'])))
cpu={}
for name,values in b['cpus'].items():
 delta=[y-x for x,y in zip(a['cpus'][name],values)];total=sum(delta)
 cpu[name]=dict(busy_percent=round((total-delta[3]-delta[4])/max(1,total)*100,2),
               iowait_percent=round(delta[4]/max(1,total)*100,2))
print(json.dumps(dict(startup_sha256=SPEC['startup_sha256'],board_boot_id=SPEC['boot_id'],
 duration_seconds=elapsed,processes=processes,cpu=cpu,gauges_before=a['gauges'],gauges_after=b['gauges'],
 state_before=a['state'],state_after=b['state'],read_only=True,source_or_configuration_changed=False,
 private_text_or_PCM_accessed=False)))
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('label');args=parser.parse_args()
    assert args.label.replace('_','').isalnum()
    spec=json.loads((HERE.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    live=json.loads((HERE.parent/'listening_entry_fix/actual_live_listening.json').read_text(encoding='utf-8'))
    result=json.loads(ssh('python3 -B -','SPEC='+repr(spec)+'\nCAMERA='+repr(live['camera_pid'])+'\n'+REMOTE,timeout=25))
    path=HERE/(args.label+'.json');path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
