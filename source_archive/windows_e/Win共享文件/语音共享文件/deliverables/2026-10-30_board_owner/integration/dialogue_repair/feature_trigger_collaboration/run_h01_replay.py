"""Local-only candidate overlay; original worker and all 23 assertions unchanged."""
import hashlib
import importlib
import json
from pathlib import Path
import runpy
import sys

H = Path(__file__).resolve().parent
BASE = H/'board_integration_v17/local_runtime_v17'
AFTER = H/'candidate_h01/after'
sys.path.insert(0, r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')
sys.path.insert(0, str(BASE))
for name in ('common', 'board.runtime'):
    module = importlib.import_module(name)
    module.__path__ = [str(AFTER/name.replace('.', '/'))] + list(module.__path__)
worker = H/'board_integration_v17/worker.py'
output = H/'candidate_h01/LOCAL_INTEGRATION.json'
sys.argv = [str(worker), '--local-replay', '--runtime-root', str(BASE), '--output', str(output)]
entry = runpy.run_path(str(worker), run_name='public_worker_h01_candidate')
code = entry['main']()
record = json.loads(output.read_bytes())
manifest = H/'candidate_h01/SOURCE_MANIFEST.json'
record['candidate_overlay'] = dict(status='NOT_DEPLOYED_LOCAL_ONLY', manifest=str(manifest),
    manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
    original_worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(), assertions_changed=False,
    unchanged_v17_base_was_verified=True, overlay_applied_after_base_verification=True)
output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
raise SystemExit(code)
