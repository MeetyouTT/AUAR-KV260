"""Root-owned metadata-only sample for the explicitly detached candidate UI."""
import base64
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
from resume_baseline import write_json

SHA='634049541e448dfdf99d96c5356ab479418bcbba435eb7a8a738fb81b6175f76'
CONTROL='/home/root/aura-board-owner-candidate-20261030/ui-capacity-control-20261030'
SCRIPT=r'''
import base64,hashlib,importlib.util,json,os,subprocess,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
raw=base64.b64decode(SOURCE,validate=True);assert hashlib.sha256(raw).hexdigest()==SHA
p=Path(CONTROL)/('metadata-sampler-'+SHA[:16]+'.py')
assert not p.is_symlink()
if p.exists():assert p.read_bytes()==raw
else:
 fd=os.open(str(p),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
owner=json.loads((Path(CONTROL)/'candidate_owner.json').read_text())['owner']
page=os.sysconf('SC_PAGE_SIZE');hz=os.sysconf('SC_CLK_TCK')
def stat(pid):
 try:
  root=Path('/proc')/str(pid);v=root.joinpath('stat').read_text().rsplit(')',1)[1].split()
  if v[0]=='Z':return None
  result=dict(pid=pid,ppid=int(v[1]),birth=v[19],ticks=int(v[11])+int(v[12]),rss_kib=int(v[21])*page//1024)
  if pid==owner['pid']:
   assert v[19]==owner['birth'] and hashlib.sha256(root.joinpath('cmdline').read_bytes()).hexdigest()==owner['cmdline_sha256']
  return result
 except (FileNotFoundError,ProcessLookupError):return None
def proof():
 unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,Job,Restart,SendSIGKILL,TimeoutStopUSec'],text=True).splitlines() if '=' in x)
 assert unit['MainPID']=='0' and unit['ActiveState']=='inactive' and not unit.get('Job')
 assert unit['Restart']=='no' and unit['SendSIGKILL']=='no' and unit['TimeoutStopUSec']=='infinity'
 assert stat(owner['pid']) is not None
 camera=stat(260102);assert camera and camera['birth']=='784437'
 assert subprocess.check_output(['/bin/systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()=='260102'
 return unit
def sample():
 values={int(p.name):v for p in Path('/proc').iterdir() if p.name.isdigit() for v in [stat(int(p.name))] if v}
 group={owner['pid']}
 while True:
  new={pid for pid,v in values.items() if v['ppid'] in group}-group
  if not new:break
  group|=new
 rows={str(pid):dict(values[pid]) for pid in group if pid in values}
 for key,row in rows.items():
  try:
   fields=dict(l.split(':',1) for l in (Path('/proc')/key/'smaps_rollup').read_text().splitlines() if ':' in l)
   row['pss_kib']=int(fields['Pss'].split()[0])
  except (FileNotFoundError,KeyError):row['pss_kib']=None
 cpu=[int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
 memory={k:int(v.split()[0]) for k,v in (l.split(':',1) for l in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemAvailable','CmaFree')}
 return dict(at=time.monotonic(),busy=sum(cpu)-cpu[3]-cpu[4],camera=stat(260102),ui=rows,memory_kib=memory)
proof()
spec=importlib.util.spec_from_file_location('_public_metadata_sample',str(p));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
deadline=time.monotonic()+60;initial=None
while time.monotonic()<deadline:
 proof();short=module.sample(duration=1,interval=.5);states=[r['state'] for r in short['rows'] if 'state' in r]
 if not states:continue
 initial=states[-1]
 if (initial.get('character_pair.state')=='READY' and initial.get('avatar_display.frames',0)>0
     and initial.get('portrait_offload.ready') is True
     and initial.get('local_transcription.service.enabled') is True):break
else:raise ValueError('candidate_ready_not_observed; metadata stays board-local')
assert initial['manual_pan.state']=='FAULT' and initial['manual_pan.pulse_us'] is None
assert initial['handsfree_dialogue.microphone_open'] is False and initial['handsfree_dialogue.enabled'] is False
assert initial['playing'] is False and initial['manual_pan.automatic_following'] is False
a=sample()
done=subprocess.run(['/usr/bin/python3','-B',str(p),'--sample','--seconds','30','--interval','0.5'],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=40)
assert done.returncode==0,done.stderr[-250:]
value=json.loads(done.stdout);b=sample();proof()
dt=b['at']-a['at'];common=set(a['ui'])&set(b['ui'])
assert common and all(a['ui'][k]['birth']==b['ui'][k]['birth'] for k in common)
ticks=sum(b['ui'][k]['ticks']-a['ui'][k]['ticks'] for k in common)
print(json.dumps(dict(status='ACTUAL_DETACHED_GUI_METADATA_ONLY_SAMPLE',owner=owner,elapsed_seconds=dt,
 whole_board_cpu_cores=(b['busy']-a['busy'])/hz/dt,ui_group_cpu_cores=ticks/hz/dt,
 camera_cpu_cores=(b['camera']['ticks']-a['camera']['ticks'])/hz/dt,
 ui_group_pss_mib=sum(v['pss_kib'] or 0 for v in b['ui'].values())/1024,
 resources=[a,b],initial_ready_state=initial,native_state_sample=value,actual_microphone_opened=False,actual_audio_played=False,
 matched_old_local16_business_ab=False,physical_display_scanout_measured=False)))
'''

def main():
    path=HERE/'resume_ui_trial/read_only_state_sampler.py'
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
    prefix='\n'.join(k+'='+repr(v) for k,v in dict(CONTROL=CONTROL,SHA=SHA,SOURCE=base64.b64encode(raw).decode()).items())+'\n'
    value=json.loads(ssh('python3 -B -',prefix+SCRIPT,timeout=105))
    now=datetime.datetime.now(datetime.timezone.utc)
    target=HERE/'resume_ui_trial'/(now.strftime('%Y%m%dT%H%M%S')+'-actual-native-sample.json')
    write_json(target,dict(recorded_utc=now.isoformat(),**value))
    print(json.dumps(dict(output=str(target),**{k:v for k,v in value.items() if k not in ('resources','owner','native_state_sample','initial_ready_state')},native_summary={k:v for k,v in value['native_state_sample'].items() if k!='rows'})))

if __name__=='__main__':main()
