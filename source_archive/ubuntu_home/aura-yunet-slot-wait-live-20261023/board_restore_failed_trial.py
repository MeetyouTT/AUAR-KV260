"""Recover only this unaccepted, pinned trial and its owned starting GUI."""
import hashlib,json,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/home/root/aura-slot-wait-release-20261023/9d649227aade936c')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
for name,sha in {'handoff.py':'ebca155e86eb1519870038532337f626788ee5c6b6755ec69537ddf1c5f52dc1',
                 'live_checks.py':'c095d94c2b7e956948fb1324b78dea3717971a924be598a4fd553a2d4e52a965'}.items():
 assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
if sys.argv[1:]==['--run']:
 sys.path.insert(0,str(ROOT))
 from handoff import BoardOps,PREF,atomic_json
 d=json.loads((ROOT/'report.json').read_text());assert not d['accepted']
 ops=BoardOps(Path('/home/root/aura-coordinated-switch-20261023/slot-wait-295705'));ops.verify()
 out={'scope':'RESTORE_UNACCEPTED_SLOT_WAIT_TRIAL','passed':False,'complete':False}
 try:
  ops.assert_guard_armed()
  ops.service('stop','aura-slot-wait-release-9d649227aade936c.service')
  state=ops.service('show','aura-avatar-ui.service','-p','ActiveState','--value').strip()
  if state=='active':ops.assert_idle_or_stopped()
  assert state in ('active','activating','inactive','failed')
  # This is the GUI started by the unaccepted transition. A startup timeout
  # must not let its process keep the USB device open during restoration.
  ops.service('stop','aura-avatar-ui.service')
  value=hashlib.sha256(PREF.read_bytes()).hexdigest()
  if value not in ops.meta['allowed_preference_hashes']:
   ops.meta['allowed_preference_hashes'].append(value);ops.save_meta()
  out['restoration']=ops.restore();assert out['restoration']['restored']
  ops.disarm();out.update(passed=True,camera_pid=ops.pid('aura-camera-ui.service'),
                         audio_pid=ops.pid('aura-avatar-ui.service'),guard_inactive=True)
 except Exception as e:out['error']=type(e).__name__+': '+str(e)[:400]
 finally:
  out['complete']=True;atomic_json(ROOT/'failed-trial-restoration.json',out)
  d=json.loads((ROOT/'report.json').read_text());d.update(complete=True,passed=False,accepted=False,
    phase='REJECTED_STARTUP_CONTENTION_RESTORED' if out['passed'] else 'REJECTED_RESTORATION_INCOMPLETE',
    error='Candidate has repeated pre-execute busy cancellations and freshness gaps',
    recovery_after_rejection=out,guard_left_armed=not out['passed'])
  atomic_json(ROOT/'report.json',d)
 print(json.dumps(out))
else:
 assert sys.argv[1:]==[]
 source=Path(__file__).resolve();result=subprocess.run(['systemd-run',
  '--unit=aura-reject-slot-wait-9d649227','--property=RuntimeMaxSec=360',
  '/usr/bin/python3','-B',str(source),'--run'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
 assert result.returncode==0,result.stdout.decode(errors='replace')[-300:]
 print(json.dumps({'started':True,'report':str(ROOT/'failed-trial-restoration.json')}))
