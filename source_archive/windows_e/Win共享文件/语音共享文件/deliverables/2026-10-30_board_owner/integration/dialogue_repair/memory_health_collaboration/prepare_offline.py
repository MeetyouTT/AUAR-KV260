"""Freeze only source modules for isolated synthetic diagnostics (no models)."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
INTEGRATION = HERE.parents[1]
sources = {
    'common/board_memory.py': HERE.parent / 'guard_session_candidate/after/common/board_memory.py',
    'common/board_memory_backoff.py': INTEGRATION / 'response_latency/memory_backoff_candidate/after/common/board_memory_backoff.py',
    'board/runtime/board_memory_policy.py': PROJECT / 'aura/board/runtime/board_memory_policy.py',
    'tools/production_memory_presentation.py': HERE.parent / 'ui_budget_candidate/after/tools/production_memory_presentation.py',
}
manifest = {}
for name, source in sources.items():
    target = HERE / 'before' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise RuntimeError('Do not overwrite a frozen baseline')
    shutil.copyfile(source, target)
    manifest[name] = dict(source=str(source), sha256=hashlib.sha256(target.read_bytes()).hexdigest())
(HERE/'baseline_sources.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(frozen_sources=len(manifest), models_copied=0, production_modified=False)))
