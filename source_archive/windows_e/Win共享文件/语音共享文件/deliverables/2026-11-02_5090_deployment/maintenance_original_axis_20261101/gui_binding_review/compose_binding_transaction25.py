"""Compose the root-only, single selected-config transaction from reviewed originals."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1]
collector = (HERE/'collect_gui_binding_precheck25.py').read_text(encoding='utf-8')
needle = "print(json.dumps({'schema':'aura-selected-restored-gui-binding-candidate-precheck-25-1',"
assert collector.count(needle) == 1
prefix = collector.split(needle, 1)[0]
assert prefix.rstrip().endswith("'motion_command_emitted')}")
tail = (OUT/'parallel_platform/gui_startup_review/gui_binding_transaction_tail.py.txt').read_text(encoding='utf-8')

def change(before, after, expected=1):
    global tail
    assert tail.count(before) == expected, (before, tail.count(before))
    tail = tail.replace(before, after)

change('original 24-pin RAM-only collector', 'restored-camera 25-pin RAM-only collector')
change('--apply-selected-current-binding', '--apply-selected-restored-camera-binding')
change('args.apply_selected_current_binding', 'args.apply_selected_restored_camera_binding')
change('gui-selected-1333-24pins-v1', 'gui-selected-79866-25pins-v1')
change("EXPECTED_CANDIDATE_SHA='4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'", "EXPECTED_CANDIDATE_SHA='9ab2533d2c3000d61095f54de2e8199f53461ac085e2f58230ab36149be6af1f'")
change("6c9928fa49db7ef34ecc4d8854f3a456468fa72aa1faf7cdf1b7466cf2d2148a", "c8df0795664d21d52eab3a4f1cf55e0d1a721577d547c512e83ee1931d80871d")
change("'candidate_source_files_verified':24", "'candidate_source_files_verified':25")
change("'original_source_pins_preserved':23", "'original_source_pins_preserved':24")
change("'pid':1333,'birth_ticks':'2359'", "'pid':79866,'birth_ticks':'2265436'")
change("'schema':'aura-gui-selected-binding-transaction-1'", "'schema':'aura-gui-restored-camera-binding-transaction-2'")
change('The failed GUI and unchanged camera', 'The normally stopped GUI and restored camera')
change('units();owner()', 'units();owner();platform()', expected=4)
source = prefix + '\n' + tail
tree = ast.parse(source)
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'run':
        assert not any(isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in ('start', 'stop', 'restart', 'loadapp', 'unloadapp') for a in node.args for n in ast.walk(a))
target = HERE/'apply_gui_binding25.py'
with target.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(source)
print(json.dumps({'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                  'root_only_apply_flag': '--apply-selected-restored-camera-binding'}))
