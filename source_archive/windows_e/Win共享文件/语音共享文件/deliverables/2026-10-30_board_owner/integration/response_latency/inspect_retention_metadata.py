"""Read only grouped task states and fixed error enums; no event or summary contents."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
REMOTE=r'''
import collections,json,pathlib,sqlite3
p=pathlib.Path('/home/root/.local/share/aura-board-business/timeline.sqlite3')
assert p.is_file() and not p.is_symlink() and p.resolve()==p
allowed={'dialogue_preempted','lease_expired','source_changed','scope_cleared','candidate_rejected',
 'model_failed','database_busy','cancelled','deadline_exceeded','clock_unverified','compaction_failed'}
states={'leased','committed','failed','cancelled','expired'}
db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=.15)
try:
 db.execute('PRAGMA query_only=ON')
 counts=collections.Counter()
 for state,error,count in db.execute('SELECT status,error_code,COUNT(*) FROM bm_tasks GROUP BY status,error_code'):
  state=state if state in states else 'other'
  error='none' if error is None else error if error in allowed else 'other'
  counts[(state,error)]+=count
 print(json.dumps(dict(metadata_only=True,read_only=True,task_counts=[dict(state=s,error_code=e,count=n) for (s,e),n in sorted(counts.items())])))
finally:db.close()
'''
if __name__=='__main__':
    value=json.loads(ssh('python3 -B -',REMOTE,timeout=10))
    (HERE/'retention_task_counts.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
