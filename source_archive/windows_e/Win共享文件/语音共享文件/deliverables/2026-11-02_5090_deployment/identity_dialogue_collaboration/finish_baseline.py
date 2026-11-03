"""Add an exact pinned dependency from the earlier sealed public candidate."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[2]/'2026-10-30_board_owner/integration/dialogue_repair/feature_trigger_collaboration/identity_cooperation_v90/after/tools/provisional_voice.py'
# The deployment lives under deliverables, so parents[2] is that directory.
if not SOURCE.is_file():
    SOURCE=HERE.parents[1]/'2026-10-30_board_owner/integration/dialogue_repair/feature_trigger_collaboration/identity_cooperation_v90/after/tools/provisional_voice.py'
expected='6219b84a9f40dedca6238aadf1523de7ec6d9060d7fc40d8c34f7eccf5b12a8f'
assert SOURCE.is_file() and hashlib.sha256(SOURCE.read_bytes()).hexdigest()==expected
target=HERE/'baseline/tools/provisional_voice.py';assert not target.exists();target.write_bytes(SOURCE.read_bytes())
path=HERE/'SOURCE_MANIFEST.json';manifest=json.loads(path.read_text(encoding='utf-8'))
manifest['baseline_files']['tools/provisional_voice.py']={'source':str(SOURCE),'sha256':expected,'bytes':target.stat().st_size}
manifest['baseline_missing'].remove('tools/provisional_voice.py')
path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PINNED_DEPENDENCY_ADDED')
