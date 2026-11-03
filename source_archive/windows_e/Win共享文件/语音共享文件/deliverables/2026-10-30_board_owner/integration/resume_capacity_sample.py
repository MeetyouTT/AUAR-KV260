"""Bounded metadata-only board camera/display resource sample."""
import argparse
import datetime
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
from resume_baseline import write_json

SCRIPT=r'''
import hashlib,importlib.util,json,os,subprocess,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256(Path(PROBE).read_bytes()).hexdigest()==PROBE_SHA
spec=importlib.util.spec_from_file_location('_metadata_probe',PROBE)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
hz=os.sysconf('SC_CLK_TCK');page=os.sysconf('SC_PAGE_SIZE')
camera=int(subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True))
ui=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
assert camera>0 and ui>0
def stat(pid):
 try:
  a=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
  return dict(pid=pid,ppid=int(a[1]),ticks=int(a[11])+int(a[12]),birth=int(a[19]),rss_mib=int(a[21])*page/1048576)
 except (FileNotFoundError,ProcessLookupError):return None
def sample():
 allp={int(p.name):v for p in Path('/proc').iterdir() if p.name.isdigit() for v in [stat(int(p.name))] if v is not None}
 group={ui}
 while True:
  newer={pid for pid,v in allp.items() if v['ppid'] in group}-group
  if not newer:break
  group|=newer
 cpu=[int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
 return dict(at=time.monotonic(),busy=sum(cpu)-cpu[3]-cpu[4],camera=allp.get(camera),
  ui={str(pid):allp[pid] for pid in group if pid in allp},context=mod.production_context())
rows=[sample()];end=time.monotonic()+SECONDS
while time.monotonic()<end:
 time.sleep(min(1,max(0,end-time.monotonic())));rows.append(sample())
a,b=rows[0],rows[-1];elapsed=b['at']-a['at']
assert a['camera'] and b['camera'] and a['camera']['birth']==b['camera']['birth']
common=set(a['ui'])&set(b['ui'])
assert all(a['ui'][k]['birth']==b['ui'][k]['birth'] for k in common)
ui_ticks=sum(b['ui'][k]['ticks']-a['ui'][k]['ticks'] for k in common)
people=[r['context'].get('camera',{}).get('people_count') for r in rows]
ages=[r['context'].get('identity',{}).get('faces',{}).get('source_age_ms') for r in rows]
valid_ages=[v for v in ages if type(v) in (int,float)]
def delta(section,key):
 x=a['context'].get(section,{}).get(key);y=b['context'].get(section,{}).get(key)
 return (y-x) if type(x) in (int,float) and type(y) in (int,float) and y>=x else None
faces_a=a['context'].get('identity',{}).get('faces',{}).get('processed')
faces_b=b['context'].get('identity',{}).get('faces',{}).get('processed')
pushed=delta('display','pushed')
print(json.dumps(dict(status='READ_ONLY_RESOURCE_SAMPLE',label=LABEL,seconds=round(elapsed,3),camera_pid=camera,ui_pid=ui,
 cpu_units='cores;4 cores total',whole_board_cpu_cores=round((b['busy']-a['busy'])/hz/elapsed,4),
 camera_cpu_cores=round((b['camera']['ticks']-a['camera']['ticks'])/hz/elapsed,4),
 ui_cpu_cores=round(ui_ticks/hz/elapsed,4),person_counts=people,
 face_processed_delta=faces_b-faces_a if type(faces_a) is int and type(faces_b) is int else None,
 native_display_handoff_fps=round(pushed/elapsed,4) if pushed is not None else None,
 face_source_age_ms=ages,face_age_at_most250_fraction=sum(v<=250 for v in valid_ages)/len(valid_ages) if valid_ages else None,
 samples=rows,production_database_opened=False,microphone_opened=False,physical_display_scan_measured=False)))
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('label',choices=('baseline100','candidate200','restored100'))
    parser.add_argument('--seconds',type=int,default=10,choices=(10,20,30));args=parser.parse_args()
    gate=json.loads((HERE.parent/'coordination/runtime_windows.json').read_text(encoding='utf-8-sig'))
    if gate['performance_window'].get('state')!='BUSINESS_ACCEPTANCE_EXCLUSIVE':raise RuntimeError('Root window required')
    staged=json.loads((HERE/'resume_performance/staged.json').read_text(encoding='utf-8'))
    values=dict(BOOT='8100a7fd-0c6a-46c4-82b8-f874988a1521',PROBE=staged['root']+'/probe.py',
        PROBE_SHA=staged['pins']['probe.py'],SECONDS=args.seconds,LABEL=args.label)
    prefix='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
    now=datetime.datetime.now(datetime.timezone.utc)
    value=json.loads(ssh('python3 -B -',prefix+SCRIPT,timeout=45))
    path=HERE/'resume_camera_budget'/(now.strftime('%Y%m%dT%H%M%S')+'-'+args.label+'-resources.json')
    write_json(path,dict(started_utc=now.isoformat(),**value))
    print(json.dumps(dict(output=str(path),**{k:v for k,v in value.items() if k!='samples'})))


if __name__=='__main__':main()
