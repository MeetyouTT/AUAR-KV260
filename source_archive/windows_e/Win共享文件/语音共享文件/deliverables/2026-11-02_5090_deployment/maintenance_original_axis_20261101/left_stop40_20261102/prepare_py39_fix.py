"""Preserve the first attempt and prepare the Python 3.9 annotation correction."""
import ast
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
NEW=HERE/'py39_fix'
assert not NEW.exists();NEW.mkdir()
for name in ('before','candidate'):shutil.copytree(HERE/name,NEW/name)
p=NEW/'candidate/continuous_face_control.py';s=p.read_text(encoding='utf-8')
assert s.count('left_target_center_ratio: float | None = None')==1
s=s.replace('from dataclasses import dataclass\n','from dataclasses import dataclass\nfrom typing import Optional\n',1).replace(
    'left_target_center_ratio: float | None = None','left_target_center_ratio: Optional[float] = None',1)
p.write_text(s,encoding='utf-8',newline='')
ast.parse(s)
for name in ('test_left_episode.py','run_pure_suite.py'):
    text=(HERE/name).read_text(encoding='utf-8')
    if name=='test_left_episode.py':
        text=text.replace("ARCHIVE=HERE.parents[2]/'2026-10-31_visual_axis_maintenance'",
                          "ARCHIVE=next(p for p in HERE.parents if (p/'2026-10-31_visual_axis_maintenance').is_dir())/'2026-10-31_visual_axis_maintenance'")
    (NEW/name).write_text(text,encoding='utf-8')
review=json.loads((HERE/'INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
review.update(schema='aura-left-stop40-py39-compatibility-review-2',
    status='STATIC_SOURCE_PASS_PENDING_PURE_TESTS_NOT_PUBLISHED',
    reviewer='primary continuation; original independent review retained one level above',
    compatibility_correction='Only optional field annotation uses typing.Optional for Python 3.9; no decision logic change',
    original_independent_review=''+str(HERE/'INDEPENDENT_REVIEW.json'))
for r in review['records']:
    r['after']=hashlib.sha256((NEW/'candidate'/r['file']).read_bytes()).hexdigest()
    assert hashlib.sha256((NEW/'before'/r['file']).read_bytes()).hexdigest()==r['before']
    r['unchanged']=r['before']==r['after']
assert sum(not r['unchanged'] for r in review['records'])==3
(NEW/'INDEPENDENT_REVIEW.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
changes={r['file']:{'before':r['before'],'after':r['after']} for r in review['records'] if not r['unchanged']}
(NEW/'PATCH_REVIEW.json').write_text(json.dumps(dict(changes=changes,remaining_22_files_unchanged=True,
    left_stop_target=.4,right_stop_target=.45,tolerance=.03,trigger_settings_changed=False,
    hardware_slew_and_source_deadlines_changed=False,compatibility_fix='Optional[float] for existing Python 3.9'),indent=2)+'\n',encoding='utf-8')
print(json.dumps(changes,indent=2))
