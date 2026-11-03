import ast,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'uart_sender_source.py').read_bytes();assert hashlib.sha256(s).hexdigest()=='759b12bd12669663f33dae15ef4eb18a28de05f6319b3eb9c684e5119ab8130b'
b=(R/'action_sources/07-transfer_receiver.py').read_bytes();assert hashlib.sha256(b).hexdigest()=='0822fabbafacb2d7c8dc66f0ac8ab19b0ec69a0b41ca5199407615c5342ef22f'
tree=ast.parse(s.decode())
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='board_code' for target in node.targets):node.value=ast.copy_location(ast.Str(s=b.decode()),node.value)
exec(compile(tree,'reviewed_m3_uart_sender','exec'))
