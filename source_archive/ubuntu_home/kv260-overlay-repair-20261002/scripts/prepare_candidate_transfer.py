#!/usr/bin/env python3
"""Adapt the preserved acknowledged UART sender for the sealed driver archive."""
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    run = Path(sys.argv[1]).resolve()
    meta = json.loads((run / "run.json").read_text())
    archive = json.loads((ROOT / "bundle/archive_manifest.json").read_text())
    preserved = Path("/home/ghmd/kv260-dpu41-control-20261001/evidence/test_card_board_20261001/transfer_image.py")
    code = preserved.read_text()
    replacements = {
        "source = root.parent.parent / 'downloads/pytorch-resnet-dog.jpg'": "source = Path(" + repr(str(ROOT / archive["path"])) + ")",
        "f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a": archive["sha256"],
        "'/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'": repr(meta["board_work_directory"] + "/candidate.tar.gz"),
        "18-image-transfer.serial.raw": "06-candidate-transfer.serial.raw",
        "18-image-transfer.result.json": "06-candidate-transfer.result.json",
        "range(0,len(payload),768)": "range(0,len(payload),3072)",
        "payload[pos:pos+768]": "payload[pos:pos+3072]",
        "Board receiver ready; transferring image": "Board receiver ready; transferring sealed driver archive",
    }
    for before, after in replacements.items():
        if code.count(before) != 1:
            raise RuntimeError("Preserved transfer sender differs: " + before)
        code = code.replace(before, after)
    code = code.replace("IMAGE_", "REPAIR_PACKAGE_")
    tree = ast.parse(code)
    found = 0
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(v, ast.Name) and v.id == "board_code" for v in node.targets):
            board = ast.literal_eval(node.value)
            board = board.replace("tmp=p.with_suffix('.jpg.partial')", "tmp=p.with_name(p.name+'.partial')")
            start = board.index(" listing=")
            end = board.index(" os.write(1,('REPAIR_PACKAGE_DONE", start)
            board = board[:start] + board[end:]
            anchor = "p.parent.mkdir(parents=True,exist_ok=True)"
            guard = """assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
assert (p.parent/'baseline/original-zocl.ko').is_file()
assert (p.parent/'baseline/state.json').is_file()
assert Path('/sys/module/zocl/srcversion').read_text().strip()=='0991D1B457855C8987936E6'
"""
            if board.count(anchor) != 1:
                raise RuntimeError("Receiver directory logic differs")
            board = board.replace(anchor, guard)
            compile(board, "reviewed_driver_archive_receiver", "exec")
            node.value = ast.copy_location(ast.Str(s=board), node.value)
            found += 1
    if found != 1:
        raise RuntimeError("Unexpected receiver definition")
    # Retain the exact reviewed receiver and original sender source for replay.
    target = run / "transfer_candidate.py"
    if target.exists():
        raise RuntimeError("Refusing to overwrite transfer runner")
    target.write_text("import ast\nSOURCE=" + repr(code) + "\n" +
        "tree=ast.parse(SOURCE)\n" +
        "BOARD=" + repr(board) + "\n" +
        "for node in tree.body:\n" +
        " if isinstance(node,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='board_code' for v in node.targets):\n" +
        "  node.value=ast.copy_location(ast.Str(s=BOARD),node.value)\n" +
        "exec(compile(tree,'preserved_uart_sender','exec'))\n")
    (run / "transfer_preparation.json").write_text(json.dumps({"preserved_source":str(preserved),
        "preserved_source_sha256":hashlib.sha256(preserved.read_bytes()).hexdigest(),"runner_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256":archive["sha256"],"archive_bytes":archive["bytes"],"receiver_bytes_per_frame":3072,"executed_on_board":False},indent=2)+"\n")
    print(json.dumps({"runner":str(target),"archive_bytes":archive["bytes"],"executed_on_board":False}))


if __name__ == "__main__":
    main()
