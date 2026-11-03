"""Only local public newboot source snapshot + separate reviewed M03 overlay."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
H=Path(__file__).resolve().parent;P=H.parents[4];D=H/'candidate_m03_newboot'
BASE=D/'public_runtime_newboot';AFTER=D/'after'
sys.path[:0]=[str(BASE),str(P/'aura'),r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies']
manifest=json.loads((D/'SOURCE_MANIFEST.json').read_bytes())
mapping=json.loads((D/'source_mapping.newboot.json').read_bytes())
for relative,row in manifest['files'].items():
    assert hashlib.sha256((AFTER/relative).read_bytes()).hexdigest()==row['sha256']
for name in ('common','board.runtime','tools'):
    package=importlib.import_module(name)
    package.__path__=[str(AFTER/name.replace('.','/'))]+list(package.__path__)+[str(P/'aura'/name.replace('.','/'))]
for name in ('tests','tests.framework'):
    package=importlib.import_module(name)
    package.__path__=[str(P/'aura'/name.replace('.','/'))]+list(package.__path__)
loaded={}
for name in ('common.board_memory','common.board_production_bootstrap','board.runtime.board_dialogue',
    'board.runtime.history_delete','board.runtime.board_business','board.runtime.board_speaker_business',
    'board.runtime.board_memory_policy','tools.production_memory_presentation'):
    module=importlib.import_module(name);path=Path(module.__file__).resolve()
    loaded[name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
assert loaded['board.runtime.board_business']['sha256']==manifest['files']['board/runtime/board_business.py']['sha256']
assert loaded['common.board_production_bootstrap']['sha256']==mapping['component_pins']['common/board_production_bootstrap.py']
import pytest
code=pytest.main(sys.argv[1:])
value=dict(pytest_exit_code=code,loaded_modules=loaded,
    baseline_startup_sha256=mapping['startup_sha256'],baseline_boot_id=mapping['boot_id'],
    source_manifest_sha256=hashlib.sha256((D/'SOURCE_MANIFEST.json').read_bytes()).hexdigest(),
    original_sources_and_tests_modified=False,production_or_device_or_model_or_private_database_accessed=False)
(D/'LAST_MODULE_PROOF.json').write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
raise SystemExit(code)
