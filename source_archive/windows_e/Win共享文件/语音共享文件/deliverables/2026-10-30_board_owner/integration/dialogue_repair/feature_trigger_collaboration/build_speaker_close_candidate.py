import ast
import difflib
import hashlib
import json
from pathlib import Path
H=Path(__file__).resolve().parent
relative='board/runtime/board_speaker_business.py'
base=H/'board_integration_v17/local_runtime_v17'/relative
raw=base.read_bytes();before=raw.decode().replace('\r\n','\n')
anchor="                for job in self.jobs.values():\n                    job['cancelled'].set(); job['pcm'] = None\n                    if job.get('future') is not None:"
assert before.count(anchor)==1
after=before.replace(anchor,anchor.replace('self.jobs.values()','tuple(self.jobs.values())'))
ast.parse(after,feature_version=(3,9))
d=H/'candidate_speaker_close'
for kind,data in [('before',raw),('after',after.encode())]:
    path=d/kind/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
(d/'board_speaker_business.py.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='before/'+relative,tofile='after/'+relative)),encoding='utf-8')
pins=json.loads((H/'board_integration_v17/source_mapping.json').read_bytes())['component_pins']
assert hashlib.sha256(raw).hexdigest()==pins[relative]
(d/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(status='ISOLATED_ONE_LINE_CANDIDATE_NOT_DEPLOYED',
    baseline_startup_sha256='0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a',
    files={relative:dict(before_sha256=pins[relative],sha256=hashlib.sha256(after.encode()).hexdigest(),source=str(d/'after'/relative))},
    purpose='close Future.cancel synchronously invokes done callback mutating the jobs dictionary; reset is unchanged',
    cancellation_and_profile_authority_unchanged=True),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(hashlib.sha256(after.encode()).hexdigest())
