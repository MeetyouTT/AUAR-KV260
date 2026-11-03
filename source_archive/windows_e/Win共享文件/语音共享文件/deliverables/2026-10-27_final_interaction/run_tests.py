import importlib,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path[:0]=[str(Path('C:/Users/35870/.codex/visualizations/2026/10/26/01a1772c-f263-75f1-bfa1-9bd865e5caa9/animation-fps-deps')),str(AURA)]
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
sys.dont_write_bytecode=True
import tools
tools.__path__=[str(HERE/'candidate_source/tools'),*tools.__path__]
import tools.board_avatar_affine
import pytest
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(HERE/'test_tmp'),
'--junitxml',str(HERE/'tests.xml'),str(HERE/'test_remote_handoff.py'),
str(AURA/'tests/framework/test_portrait_offload.py'),str(AURA/'tests/framework/test_board_avatar_worker.py')]))

