"""Freeze the reviewed default-off observer without claiming a board deployment."""
import ast
import hashlib
import json
from pathlib import Path
import shutil

root=Path('/home/ghmd/aura-yunet-freshness-metrics-20261022')
out=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_yunet_freshness_metrics')
manifest=json.loads((root/'manifest.json').read_text())
assert manifest['validation']['tests_passed']==23
assert not manifest['default_enabled'] and not manifest['retry_or_scheduling_changed']
assert not manifest['validation']['board_overhead_measured']
baseline=Path(manifest['baseline']['path'])
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==manifest['baseline']['sha256']
review_path=Path('/home/ghmd/aura-affinity-review-20261022/freshness-review.json')
review=json.loads(review_path.read_text())
assert not review['blocking_findings']
assert not out.exists()
for name,row in manifest['files'].items():
    raw=(root/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes'],name
out.mkdir(parents=True)
for name in tuple(manifest['files'])+('manifest.json',):
    target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(root/name,target)
shutil.copyfile(review_path,out/'independent-review.json')
shutil.copyfile(Path(__file__),out/'freeze_candidate.py')
release={'status':'REVIEWED_DEFAULT_OFF_LOCAL_CANDIDATE_NOT_BOARD_VERIFIED',
    'software_tests':23,'candidate_source_count':2,'default_enabled':False,
    'production_callers_modified_to_enable':False,'retry_or_schedule_changed':False,
    'baseline_sha256':manifest['baseline']['sha256'],
    'independent_review_passed':True,'board_overhead_measured':False,
    'board_deployed':False,'improvement_proven':False,'windows_receipt_confirmed':False}
(out/'release.json').write_text(json.dumps(release,indent=2)+'\n')
for p in out.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
for p in out.rglob('*.json'):json.loads(p.read_text())
files=sorted(p for p in out.rglob('*') if p.is_file())
(out/'FILES.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '
    +str(p.relative_to(out))+'\n' for p in files))
print(json.dumps({'delivery':str(out),'hashed_files':len(files),'board_deployed':False}))
