"""Run only local synthetic regression with an explicit module overlay."""
import importlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
AFTER = HERE/'candidate/after'
if '--candidate-v2' in sys.argv:
    AFTER=HERE/'candidate_v2/after'
    sys.argv.remove('--candidate-v2')
if '--candidate-v3' in sys.argv:
    AFTER=HERE/'candidate_v3/after'
    sys.argv.remove('--candidate-v3')
if len(sys.argv)>1 and sys.argv[1]=='--baseline':
    AFTER = HERE/'candidate/before'
    sys.argv.pop(1)
sys.path.insert(0, str(PROJECT/'aura'))
sys.path.insert(0, str(HERE/'runtime_v16'))
sys.path.insert(0, r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')
for name in ('common', 'tools', 'board.runtime', 'board.runtime.audio'):
    module = importlib.import_module(name)
    module.__path__ = [str(AFTER/name.replace('.', '/'))] + list(module.__path__)
for name in ('tests','tests.framework'):
    module=importlib.import_module(name)
    module.__path__=[str(PROJECT/'aura'/name.replace('.','/'))]+list(module.__path__)

if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--audit':
        import runpy
        sys.argv=[str(HERE/'audit_routes.py'),str(AFTER/'tools/yuki_jobs_candidate.py')]
        runpy.run_path(str(HERE/'audit_routes.py'),run_name='__main__')
        raise SystemExit(0)
    import pytest
    arguments = sys.argv[1:] or [
        str(HERE/'tests/test_feature_routes.py'),
        str(PROJECT/'aura/tests/framework/test_visual_policy.py'),
        str(HERE/'tests/current_profile/test_spoken_identity_query.py'),
        str(PROJECT/'aura/tests/framework/test_board_speaker_business.py'),
        str(HERE/'tests/current_profile/test_board_dialogue_jobs.py'),
        str(PROJECT/'aura/tests/framework/test_board_business.py'),
        str(PROJECT/'aura/tests/framework/test_visual_timeline.py'),
        str(PROJECT/'aura/tests/framework/test_visual_memory_worker.py'),
        '-q', '-p', 'no:cacheprovider', '--import-mode=importlib', '--basetemp='+str(HERE/'test_work'),
        '--junitxml='+str(HERE/'candidate_v2/REGRESSION_TESTS.xml' if AFTER==HERE/'candidate_v2/after' else HERE/'TESTS.xml'),
        '-k','not (SpokenIdentityQueryHTTPTests or '
        'test_board_mode_cannot_bypass_board_kernel_lock_on_windows)',
    ]
    raise SystemExit(pytest.main(arguments))
