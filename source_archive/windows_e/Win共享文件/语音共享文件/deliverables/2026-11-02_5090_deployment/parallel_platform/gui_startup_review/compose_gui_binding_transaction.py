"""Compose self-contained board transaction locally; does not contact the board."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
collector=(HERE/'collect_gui_candidate_precheck24.py').read_text(encoding='utf-8')
prefix=collector.split("print(json.dumps({'schema':'aura-selected-gui-binding-candidate-precheck-24-1',",1)[0]
assert prefix != collector and prefix.rstrip().endswith("'motion_command_emitted')}")
source=prefix+'\n'+(HERE/'gui_binding_transaction_tail.py.txt').read_text(encoding='utf-8')
ast.parse(source)
target=HERE/'apply_gui_selected_binding.py'
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
print(json.dumps({'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                  'board_operations':False}))
