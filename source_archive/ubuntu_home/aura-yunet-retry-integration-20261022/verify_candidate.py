"""Verify pinned local sources, record explicit software-only artifact hashes."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
EXPECTED_CHANGED = {'board/identity/face_targets.py', 'board/vision/dpu_yunet.py',
    'board/vision/dpu_vision_runtime.py'}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def assignments(tree, name):
    return [ast.dump(node, include_attributes=False) for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
            and target.id == name for target in node.targets)]

def main():
    baseline = json.loads((ROOT/'baseline-manifest.json').read_text())
    entries = {}
    differences = []
    changed = set()
    for relative, pinned in sorted(baseline.items()):
        old, new = ROOT/'baseline/aura'/relative, ROOT/'candidate/aura'/relative
        assert sha(old) == pinned['sha256'], relative+' baseline changed'
        assert sha(Path(pinned['source'])) == pinned['sha256'], relative+' original pin changed'
        old_tree, new_tree = ast.parse(old.read_text()), ast.parse(new.read_text())
        identical = old.read_bytes() == new.read_bytes()
        if not identical:
            changed.add(relative)
            differences.extend(difflib.unified_diff(old.read_text().splitlines(True),
                new.read_text().splitlines(True), fromfile='baseline/'+relative, tofile='candidate/'+relative))
        if relative.endswith('face_targets.py'):
            assert assignments(old_tree, 'next_at') == assignments(new_tree, 'next_at'), 'worker interval changed'
            init = next(n for n in ast.walk(new_tree) if isinstance(n, ast.FunctionDef) and n.name == '__init__')
            defaults = dict(zip((arg.arg for arg in init.args.kwonlyargs), init.args.kw_defaults))
            assert isinstance(defaults['slot_retry'], ast.Constant) and defaults['slot_retry'].value is False
        entries[relative] = {'baseline_sha256':sha(old), 'candidate_sha256':sha(new), 'changed':not identical}
    assert changed == EXPECTED_CHANGED, changed
    for path in ROOT.rglob('*.py'):
        ast.parse(path.read_text())
    special = (ROOT/'test-results.txt').read_text()
    regression = (ROOT/'regression-results.txt').read_text()
    assert re.search(r'Ran 39 tests[^\n]*\n\nOK', special), 'special tests did not pass'
    assert re.findall(r'Ran (\d+) tests[^\n]*\n\nOK', regression) == ['67', '66'], 'regressions did not pass'
    (ROOT/'candidate.diff').write_text(''.join(differences))
    manifest = {'schema':'aura-yunet-retry-candidate-1', 'software_only':True,
        'board_verified':False, 'production_enabled':False, 'performance_claim':None,
        'special_tests':39, 'identity_regressions':67, 'timing_regressions':66,
        'sources':entries, 'conservative_deadline_ms':200, 'retry_backoff_ms':25,
        'max_retries':2, 'max_cpu_preparations_per_round':3}
    (ROOT/'candidate-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    artifacts = [ROOT/name for name in ('README.md', 'baseline-manifest.json', 'candidate-manifest.json',
        'candidate.diff', 'run_tests.py', 'run_regressions.py', 'verify_candidate.py',
        'test-results.txt', 'regression-results.txt')]
    for directory in ('baseline', 'candidate', 'tests'):
        artifacts.extend(sorted((ROOT/directory).rglob('*.py')))
    files = {str(path.relative_to(ROOT)):{'bytes':path.stat().st_size,'sha256':sha(path)}
        for path in sorted(artifacts)}
    (ROOT/'artifact-manifest.json').write_text(json.dumps({'files':files}, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'verified':True,'special_tests':39,'identity_regressions':67,
        'timing_regressions':66,'changed_sources':len(changed),'artifacts':len(files),
        'board_verified':False,'production_enabled':False}, ensure_ascii=False))

if __name__ == '__main__': main()
