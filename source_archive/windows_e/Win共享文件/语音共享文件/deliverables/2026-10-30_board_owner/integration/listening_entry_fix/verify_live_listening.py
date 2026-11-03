"""Read-only formal listening checks; exports operating metadata only."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import collections,hashlib,http.client,json,os,pathlib,subprocess,time
def state():
 conn=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
 try:
  conn.request('GET','/api/state');r=conn.getresponse();raw=r.read(1048577)
  assert r.status==200 and len(raw)<=1048576
  return json.loads(raw)
 finally:conn.close()
def select(v,keys):return {k:v[k] for k in keys if k in v}
def sample():
 v=state();b=v.get('board_business',{});h=v.get('handsfree_dialogue',{})
 return dict(monotonic=time.monotonic(),playing=v.get('playing'),
  listening=select(h,('enabled','state','microphone_open','visual_required','conversation_entered','reason',
                     'entry_mode','wake_word_required','wake_words','speech_detection','conversation_mode','voice_barge_in')),
  diagnostics=v.get('safe_capture_diagnostics',{}),
  pan=select(v.get('manual_pan',{}),('automatic_following','state','pulse_us')),
  business=dict(started=b.get('started'),closed=b.get('closed'),writer_held=b.get('writer',{}).get('held'),
   receipt_verified=b.get('receipt',{}).get('verified'),speaker_ready=b.get('speaker',{}).get('ready'),
   retention=select(b.get('retention',{}),('enabled','running'))),
  native=select(v.get('avatar_display',{}),('kind','visible','frames','target_fps')),
  character=select(v.get('character_pair',{}),('state','production_selected')))
samples=[sample()]
time.sleep(2);samples.append(sample())
time.sleep(10);samples.append(sample())
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
launch=json.loads((root/'runtime/launch.json').read_bytes());gtk=launch['pid']
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SendSIGKILL','-p','TimeoutStopUSec','-p','Restart'],text=True).splitlines() if '=' in x)
def thread_nice(pid):
 rows=[]
 for task in (pathlib.Path('/proc')/str(pid)/'task').iterdir():
  try:rows.append(dict(tid=int(task.name),nice=os.getpriority(os.PRIO_PROCESS,int(task.name))))
  except ProcessLookupError:pass
 return rows
threads=thread_nice(gtk)
arecord=[];frontend_workers=[];recorders=[]
for path in pathlib.Path('/proc').iterdir():
 if not path.name.isdigit():continue
 try:
  stat=(path/'stat').read_text();fields=stat[stat.rfind(')')+2:].split()
  if (path/'comm').read_text().strip()=='arecord':
   recorders.append(dict(pid=int(path.name),ppid=int(fields[1]),nice=os.getpriority(os.PRIO_PROCESS,int(path.name))))
  if int(fields[1])==gtk and (path/'comm').read_text().strip()=='python3' and b'board_frontend_process' in (path/'cmdline').read_bytes():
   frontend_workers.append(dict(pid=int(path.name),nice=os.getpriority(os.PRIO_PROCESS,int(path.name))))
 except (OSError,ValueError):pass
camera=260102
startup_raw=(root/'startup/config.json').read_bytes();startup=json.loads(startup_raw)
cfg=json.loads((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())
capture_process=cfg['board_business'].get('frontend_capture_process',False)
assert type(capture_process) is bool
worker_ids={row['pid'] for row in frontend_workers}
owners=worker_ids if capture_process else {gtk}
arecord=[row for row in recorders if row['ppid'] in owners]
worker_thread_counts={str(pid):dict(collections.Counter(str(row['nice']) for row in thread_nice(pid))) for pid in worker_ids}
out=dict(root=str(root),startup_sha256=hashlib.sha256(startup_raw).hexdigest(),
 source_manifest_sha256=hashlib.sha256((root/'production_source_manifest.json').read_bytes()).hexdigest(),
 component_pins=len(startup['component_sha256']),board_boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),camera_pid=camera,
 samples=samples,unit=unit,gtk_pid=gtk,gtk_leader_nice=os.getpriority(os.PRIO_PROCESS,gtk),
 capture_related_high_priority_tids=[row['tid'] for row in threads if row['nice']==-10],
 gtk_thread_nice_counts=dict(collections.Counter(str(row['nice']) for row in threads)),
 frontend_capture_process=capture_process,frontend_worker_thread_nice_counts=worker_thread_counts,
 owned_arecord=arecord,owned_frontend_workers=frontend_workers,camera_thread_nice_counts=dict(collections.Counter(str(row['nice']) for row in thread_nice(camera))),
 physical_microphone_opened=True,raw_audio_saved_or_transferred=False,operator_dialogue_acceptance=False)
good=lambda s:(s['listening'].get('enabled') is True and s['listening'].get('microphone_open') is True
 and s['diagnostics'].get('error_code')=='none' and s['diagnostics'].get('capture_state')=='RECORDING'
 and s['diagnostics'].get('input_queue',{}).get('capacity_frames')==8
 and s['pan']==dict(state='FAULT',pulse_us=None,automatic_following=False))
out['continuous_capture_passed']=(all(good(s) for s in samples)
 and len({s['diagnostics'].get('counters',{}).get('armed') for s in samples})==1
 and all(b['diagnostics']['audio_frontend']['frames']>a['diagnostics']['audio_frontend']['frames'] for a,b in zip(samples,samples[1:])))
if capture_process:
 out['priority_scope_passed']=(out['gtk_leader_nice']==0 and set(out['gtk_thread_nice_counts'])=={'0'}
  and len(frontend_workers)==1 and frontend_workers[0]['nice']==-10
  and all(set(counts)=={'-10'} for counts in worker_thread_counts.values())
  and len(arecord)==1 and arecord[0]['nice']==-10 and set(out['camera_thread_nice_counts'])=={'0'})
else:
 out['priority_scope_passed']=(out['gtk_leader_nice']==0 and len(out['capture_related_high_priority_tids'])>=2
  and len(arecord)==1 and arecord[0]['nice']==0 and set(out['camera_thread_nice_counts'])=={'0'})
print(json.dumps(out))
'''

if __name__=='__main__':
    value=json.loads(ssh('python3 -B -',REMOTE,timeout=30))
    (HERE/'actual_live_listening.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
