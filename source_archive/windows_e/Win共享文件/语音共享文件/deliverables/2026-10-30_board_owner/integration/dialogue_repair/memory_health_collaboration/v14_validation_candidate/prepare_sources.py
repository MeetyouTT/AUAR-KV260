"""Freeze the three exact v13 source modules; no runtime data is copied."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
actual = json.loads((PARENT/'actual_metadata_v13_initial.json').read_text(encoding='utf-8-sig'))
sources = {'common/board_memory.py': PARENT/'before/common/board_memory.py',
    'board/runtime/board_memory_policy.py': PARENT/'after/board/runtime/board_memory_policy.py',
    'common/board_memory_backoff.py': PARENT/'after/common/board_memory_backoff.py'}
manifest = {}
for relative, source in sources.items():
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == actual['source_sha256'][relative]
    for folder in ('before', 'after'):
        target = HERE/folder/relative
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    manifest[relative] = dict(before_sha256=digest, source=str(source))
manifest['startup_sha256'] = actual['startup_sha256']
(HERE/'baseline_sources.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(frozen_v13_sources=3, runtime_data_copied=False)))
