import importlib.util,os,sys
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('entry_trace_test_bootstrap',HERE/'test_entry_trace.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
mode=os.environ.get('AURA_ENTRY_TRACE_MODE','candidate')
tests=module.BASE/'tests/framework'
for name in tuple(sys.modules):
 if name=='tests' or name.startswith('tests.'):sys.modules.pop(name)
sys.path.insert(0,str(module.BASE))
raise SystemExit(pytest.main([str(tests/name) for name in ('test_board_dialogue_jobs.py','test_board_dialogue.py')]+
 ['-q','--disable-warnings','--tb=line','--junitxml='+str(HERE/(mode.upper()+'_ORIGINAL_REGRESSION.xml'))]))
