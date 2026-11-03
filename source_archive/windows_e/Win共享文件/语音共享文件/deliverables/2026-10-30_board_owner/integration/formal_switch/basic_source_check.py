"""Small offline source contract; no benchmark or runtime/device imports."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'manifest.json').read_bytes())
parsed=0
for relative, expected in manifest['files'].items():
    raw=(ROOT/'overlay'/relative).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected
    if relative.endswith('.py'):
        ast.parse(raw, feature_version=(3,9))
        parsed+=1
path=ROOT/'overlay/aura/tools/formal_yuki.py'
spec=importlib.util.spec_from_file_location('formal_offline_check',path)
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
class Pair:
    ready=False
    def require_ready(self):
        if not self.ready:raise ValueError('not ready')
class Original:
    def __init__(self):self.monitor_enabled=True
    def _listen(self):return 'original'
pair=Pair()
instance=module.paired_recording_type(Original,pair)()
assert instance.monitor_enabled is False
assert instance.monitor_state=='PAUSED'
try:instance._listen()
except ValueError:pass
else:raise AssertionError('not-ready input was admitted')
pair.ready=True
assert instance._listen()=='original'
selected=ROOT.parent/'resume_windows_character_profile/voice_source_manifest.json'
source_pins=json.loads(selected.read_bytes())['source_files']
for name in ('common/character_profile.py','config/character_profile.local.json','board/runtime/character.py',
             'common/spoken_input.py','common/voice_wake.py','common/voice_enrollment.py',
             'common/binding_intent.py','common/memory_commands.py'):
    if name in source_pins:assert manifest['files']['aura/'+name]==source_pins[name]
result=dict(status='PASS_OFFLINE_SOURCE_AND_STARTUP_MONITOR_CONTRACT',files=len(manifest['files']),
    python39_ast_files=parsed,performance_test=False,actual_runtime_test=False,
    services_called=False,devices_opened=False,models_called=False,database_accessed=False,
    source_zip_sha256=hashlib.sha256((ROOT/'formal_yuki.overlay.zip').read_bytes()).hexdigest(),
    manifest_sha256=hashlib.sha256((ROOT/'manifest.json').read_bytes()).hexdigest())
(ROOT/'basic_source_check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,sort_keys=True))
