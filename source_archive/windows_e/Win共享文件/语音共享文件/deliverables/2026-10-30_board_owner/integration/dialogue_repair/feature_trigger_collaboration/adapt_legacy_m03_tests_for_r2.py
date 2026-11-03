"""Copy old tests only to supply the newly required private guard argument.
Every assert and pytest.raises statement stays byte-equivalent in AST; the
independent four-case review file is NEVER adapted or modified.
"""
import ast
import hashlib
import json
from pathlib import Path
H=Path(__file__).resolve().parent
source=H/'tests/test_history_delete_m03.py'
raw=source.read_bytes();before=raw.decode().replace('\r\n','\n')
after=before.replace('H=Path(__file__).resolve().parents[1]','H=Path(__file__).resolve().parents[2]')
assert before.count("preview_turn_id=pending['preview_turn_id'])")==2
after=after.replace("preview_turn_id=pending['preview_turn_id'])",
    "preview_turn_id=pending['preview_turn_id'],validate_live=lambda:None)")
def assertions(text):
    tree=ast.parse(text)
    return [ast.dump(node,include_attributes=False) for node in ast.walk(tree) if isinstance(node,ast.Assert)]
assert assertions(before)==assertions(after)
path=H/'candidate_m03_r2/tests/test_legacy_m03_adapted.py';path.write_bytes(after.encode('utf-8'))
receipt=dict(original_path=str(source),original_sha256=hashlib.sha256(raw).hexdigest(),
    adapted_path=str(path),adapted_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    assert_nodes_unchanged=len(assertions(after)),private_api_fixture_only=True,
    changes='Only fixture root path and validate_live argument for direct internal cached receipt/rollback tests; full live guards separately tested end to end.',
    independent_review_modified=False)
(H/'candidate_m03_r2/LEGACY_TEST_ADAPTER.json').write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps(receipt,ensure_ascii=False))
