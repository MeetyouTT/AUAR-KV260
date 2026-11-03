"""Validate parent provenance and freeze explicit software-only merge artifacts."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
RETRY = Path('/home/ghmd/aura-yunet-retry-integration-20261022')
LIGHT = Path('/home/ghmd/aura-freshness-light-20261022')
FACE = 'board/identity/face_targets.py'
METRICS = 'board/identity/face_freshness_metrics.py'
PINNED_RETRY = {
    FACE:'863a9c94c02f4d303b4444f6ab2e8de1253b528cb28d1091d9e8b98981887f31',
    'board/vision/dpu_vision_runtime.py':'e3b2d11140838fdf0eb548f8def033da5930ec46dfa72ae27f098c03e801c9d3',
    'board/vision/dpu_yunet.py':'23ea72f8380e7205fafb0d1b28b692a4780f1c9a51e221d04609843bbf0c309b'}
PINNED_LIGHT = {FACE:'2f68d7ae75f67b2b1c67e7513296d6a6e907e02bcc0a5867d0f09c8fd1075577',
    METRICS:'206f565044a94a7f3f8369d25a1f98e587107b5f025d16f3c2cab6c19fe4a160'}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def method(path, name):
    node = next(n for n in ast.walk(ast.parse(path.read_text()))
        if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.dump(node, include_attributes=False)

def difference(old, new, old_label, new_label):
    return ''.join(difflib.unified_diff(old.read_text().splitlines(True) if old else [],
        new.read_text().splitlines(True), fromfile=old_label, tofile=new_label))

def main():
    baseline_pins = json.loads((ROOT/'baseline-manifest.json').read_text())
    for relative, pin in baseline_pins.items():
        assert sha(ROOT/'baseline/aura'/relative) == pin['sha256'], relative+' baseline changed'
    parents = {}
    for name, parent, pins in (('retry',RETRY,PINNED_RETRY),('light',LIGHT,PINNED_LIGHT)):
        for relative, digest in pins.items():
            assert sha(parent/'candidate/aura'/relative) == digest, name+'/'+relative+' parent changed'
        parents[name] = {'root':str(parent),'source_sha256':pins}
    candidate = ROOT/'candidate/aura'
    for relative in ('board/vision/dpu_vision_runtime.py','board/vision/dpu_yunet.py',
            'board/vision/dpu_vision_schedule.py','board/vision/pipeline_metrics.py','board/vision/thread_sched_metrics.py'):
        assert (candidate/relative).read_bytes() == (RETRY/'candidate/aura'/relative).read_bytes(), relative
    for name in ('retry_health','_process_with_retry','work'):
        assert method(candidate/FACE,name) == method(RETRY/'candidate/aura'/FACE,name), name+' retry method changed'
    for name in ('_freshness_call','_freshness_failed','close'):
        assert method(candidate/FACE,name) == method(LIGHT/'candidate/aura'/FACE,name), name+' light method changed'
    init = next(n for n in ast.walk(ast.parse((candidate/FACE).read_text()))
        if isinstance(n,ast.FunctionDef) and n.name=='__init__')
    defaults = dict(zip((a.arg for a in init.args.kwonlyargs),init.args.kw_defaults))
    assert all(isinstance(defaults[key],ast.Constant) and defaults[key].value is False
        for key in ('freshness_metrics','slot_retry'))
    for path in ROOT.rglob('*.py'): ast.parse(path.read_text())
    assert re.findall(r'Ran (\d+) tests[^\n]*\n\nOK',(ROOT/'test-results.txt').read_text()) == ['82']
    assert re.findall(r'Ran (\d+) tests[^\n]*\n\nOK',(ROOT/'regression-results.txt').read_text()) == ['67','66']
    (ROOT/'parents.json').write_text(json.dumps(parents,ensure_ascii=False,indent=2)+'\n')
    sources = {}
    baseline_diff = []
    for path in sorted(candidate.rglob('*.py')):
        relative = str(path.relative_to(candidate)); old = ROOT/'baseline/aura'/relative
        old = old if old.exists() else None
        changed = old is None or old.read_bytes()!=path.read_bytes()
        sources[relative] = {'candidate_sha256':sha(path),'baseline_sha256':sha(old) if old else None,'changed':changed}
        if changed:baseline_diff.append(difference(old,path,'baseline/'+relative,'candidate/'+relative))
    assert sum(row['changed'] for row in sources.values()) == 4
    (ROOT/'candidate-vs-baseline.diff').write_text(''.join(baseline_diff))
    (ROOT/'merge-vs-retry.diff').write_text(difference(RETRY/'candidate/aura'/FACE,candidate/FACE,'retry/'+FACE,'merge/'+FACE)
        +difference(None,candidate/METRICS,'/dev/null','merge/'+METRICS))
    (ROOT/'merge-vs-light.diff').write_text(''.join(difference(LIGHT/'candidate/aura'/p,candidate/p,'light/'+p,'merge/'+p)
        for p in (FACE,METRICS)))
    manifest = {'schema':'aura-yunet-retry-light-merge-1','software_only':True,'board_verified':False,
        'board_cost_gate_passed':False,'production_enabled':False,'performance_claim':None,
        'freshness_schema':'aura-face-freshness-light-2','test_counts':{'retry':39,'light_adapted':32,'combined':11,
            'total_special':82,'identity':67,'timing':66},'sources':sources}
    paths = [ROOT/name for name in ('README.md','parents.json','baseline-manifest.json','candidate-vs-baseline.diff',
        'merge-vs-retry.diff','merge-vs-light.diff','run_tests.py','run_regressions.py','verify_merge.py',
        'test-results.txt','regression-results.txt')]
    for directory in ('baseline','candidate','tests'): paths.extend(sorted((ROOT/directory).rglob('*.py')))
    manifest['files'] = {str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in paths}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'verified':True,'special_tests':82,'identity':67,'timing':66,'source_files':len(sources),
        'changed_from_baseline':4,'artifact_files':len(paths),'board_cost_gate_passed':False,'manifest_sha256':sha(ROOT/'manifest.json')}))

if __name__ == '__main__': main()
