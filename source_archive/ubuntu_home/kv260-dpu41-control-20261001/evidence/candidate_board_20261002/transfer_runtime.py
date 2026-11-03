#!/usr/bin/env python3
"""Reuse the successful framed UART transfer for the verified runtime archive."""
import ast
from pathlib import Path

source = Path('/home/ghmd/kv260-dpu41-control-20261001/evidence/test_card_board_20261001/transfer_image.py')
code = source.read_text()
changes = {
    "'downloads/pytorch-resnet-dog.jpg'": "'downloads/kv260-benchmark-b4096-dpu41-runtime.tar.gz'",
    'f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a': '74470f03231a21ddd4b4525f299688b498910c23b3e85f658791c9b34ee3c80d',
    "'/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'": "'/home/root/kv260-test-20261001/kv260-benchmark-b4096-dpu41-runtime.tar.gz'",
    '18-image-transfer.serial.raw': '03-runtime-transfer.serial.raw',
    '18-image-transfer.result.json': '03-runtime-transfer.result.json',
    'range(0,len(payload),768)': 'range(0,len(payload),3072)',
    'payload[pos:pos+768]': 'payload[pos:pos+3072]',
    'Board receiver ready; transferring image': 'Board receiver ready; transferring runtime archive',
}
for before, after in changes.items():
    if code.count(before) != 1:
        raise SystemExit('Preserved transfer source differs: ' + before)
    code = code.replace(before, after)
code = code.replace('IMAGE_', 'PACKAGE_')
tree = ast.parse(code, filename=str(source))
found = 0
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id == 'board_code' for n in node.targets):
        board = ast.literal_eval(node.value)
        old = "tmp=p.with_suffix('.jpg.partial')"
        if board.count(old) != 1:
            raise SystemExit('Unexpected temporary file logic')
        board = board.replace(old, "tmp=p.with_name(p.name+'.partial')")
        start = board.index(' listing=')
        end = board.index(" os.write(1,('PACKAGE_DONE", start)
        board = board[:start] + board[end:]
        compile(board, 'board_runtime_receiver', 'exec')
        node.value = ast.copy_location(ast.Str(s=board), node.value)
        found += 1
if found != 1:
    raise SystemExit('Unexpected board receiver definition')
namespace = {'__name__': '__main__', '__file__': __file__}
exec(compile(tree, str(source), 'exec'), namespace)
