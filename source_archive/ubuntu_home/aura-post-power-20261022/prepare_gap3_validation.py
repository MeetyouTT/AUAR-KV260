"""Prepare isolated gap-record functional and worst-case snapshot checks."""
import ast
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path('/home/ghmd/aura-gap3-validation-20261023')
PARENT=Path('/home/ghmd/aura-yunet-retry-light-validation-20261022')
CANDIDATE=Path('/home/ghmd/aura-yunet-retry-gap-audit-20261023')
assert not ROOT.exists()
shutil.copytree(PARENT,ROOT,ignore=shutil.ignore_patterns('evidence','__pycache__','*.tar.gz','manifest.json','sources.json'))
for name in ('candidate/aura/board/identity/face_targets.py',
             'candidate/aura/board/identity/face_freshness_metrics.py',
             'tests/test_light.py','tests/test_service.py'):
    (ROOT/name).write_bytes((CANDIDATE/name).read_bytes())
prepare=ROOT/'prepare_sources.py'
tree=ast.parse(prepare.read_text())
pins=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
          and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='PINS')
pins={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in pins}
text=prepare.read_text()
start=text.index('PINS = ');end=text.index('\nEXPECTED_TESTS',start)
text=text[:start]+'PINS = '+repr(pins)+text[end:]
text=text.replace("UPSTREAM = Path('/home/ghmd/aura-yunet-retry-light-20261022')",
                  "UPSTREAM = Path('/home/ghmd/aura-yunet-retry-gap-audit-20261023')")
text=text.replace('EXPECTED_TESTS = 32','EXPECTED_TESTS = 35')
prepare.write_text(text)
for name in ('run_preflight.py','evaluate_preflight.py','test_evaluator.py'):
    p=ROOT/name;text=p.read_text().replace('aura-face-freshness-light-2','aura-face-freshness-light-3')
    text=text.replace('freshness-light2-','freshness-light3-').replace('All light32 tests','All light35 tests')
    if name=='run_preflight.py':
        old="""            if mode == 'on':
                assert event_count == 16
"""
        new="""            if mode == 'on':
                assert event_count == 16
                # Seed gap-only history using real recorder operations in a
                # separate synthetic recorder. The measured service retains
                # its exact 16-rejection counters; this is a worst-case
                # snapshot allocation/serialization fixture, not live data.
                seed=type(recorder)(ttl_ms=1000)
                for gap_index in range(33):
                    stamp=gap_index*1200
                    token=seed.begin(stamp)
                    token.update(input_now_ms=stamp+10,pre_commit_check_now_ms=stamp+10,outcome_code=5)
                    seed.publish(token,stamp+20,0);seed.finish(token)
                recorder.gap_records=seed.snapshot()['gap_records']
                assert len(recorder.gap_records)==32
"""
        assert text.count(old)==1;text=text.replace(old,new)
        old="""    row['closed_cleanly'] = service.closed and (recorder is None or recorder.closed)
    return row
"""
        new="""    row['closed_cleanly'] = service.closed and (recorder is None or recorder.closed)
    if case == 'full_event_health_outer_lock' and mode == 'on':
        snapshot=recorder.snapshot()
        assert len(snapshot['gap_records'])==snapshot['gap_record_capacity']==32
        row['gap_records_before_measurement']=32
        row['snapshot_json_bytes']=len(json.dumps(snapshot,separators=(',',':')).encode())
        row['snapshot_fixture_scope']='real recorded gap values seeded into bounded health fixture'
    return row
"""
        assert text.count(old)==1;text=text.replace(old,new)
    p.write_text(text)
for p in ROOT.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
print(json.dumps({'root':str(ROOT),'pins':pins,'expected_tests':35,'new_native_jobs':0}))
