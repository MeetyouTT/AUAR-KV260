"""Derive a fresh read-only preflight after the recorded single-component update."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
receipt = json.loads((HERE / 'identity_query_applied.json').read_text(encoding='utf-8'))['board_result']
assert receipt['status'] == 'IDENTITY_QUERY_V2_UPDATED_GUI_STILL_STOPPED'
assert receipt['component_count_verified'] == 380 and receipt['camera_owner_unchanged']
source = (OUT / 'parallel_platform/collect_preflight_readonly.py').read_text(encoding='utf-8')
old = "STARTUP_SHA = '07c5aa3b1c8da060e5a7d8520021bce7f167a8cf303b48a0a24f8e2a8b63035d'"
assert source.count(old) == 1
source = source.replace(old, "STARTUP_SHA = '" + receipt['startup_after_sha256'] + "'")
anchor = 'samples = [sample()]'
assert source.count(anchor) == 1
extra = """# This current maintenance preflight also verifies the actual GUI-selected binding.
assert gui['ActiveState'] == 'inactive' and gui['SubState'] == 'dead'
ui = document(runtime / 'aura/config/board_avatar_gtk.json')
selected = ui['board_business']['face_readback']
assert selected['sha256'] == '4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'
assert digest(selected['path']) == selected['sha256']
selected_document = document(selected['path'])
assert len(selected_document['source_sha256']) == 24
assert all(digest(path) == sha for path, sha in selected_document['source_sha256'].items())
assert digest('/sys/firmware/fdt') == 'd68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca'

"""
source = source.replace(anchor, extra + anchor)
target = HERE / 'collect_current_preflight_readonly.py'
with target.open('x', encoding='utf-8', newline='\n') as handle:
    handle.write(source)
print(json.dumps({'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}))
