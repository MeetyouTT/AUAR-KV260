"""Run one explicitly selected board script; preserve every result without resending it."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRANSPORT = HERE.parent.parent / '2026-10-18_board_dialogue/board_ssh.py'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--command', default='python3 -B -')
    parser.add_argument('--timeout', type=int, default=40)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    assert source.is_relative_to(HERE) and output.parent == HERE
    assert not output.exists()
    assert args.command in ('python3 -B -', '/usr/bin/python3 -B -I -S -')
    raw = source.read_bytes()
    assert hashlib.sha256(TRANSPORT.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
    spec = importlib.util.spec_from_file_location('maintenance_strict_transport', TRANSPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # The script itself supplies any write-ahead intent and rejects duplicates.
    result = module.ssh(args.command, raw.decode('utf-8'), timeout=args.timeout)
    receipt = {'host_start_utc': start,
               'host_end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'source_path': str(source), 'source_sha256': hashlib.sha256(raw).hexdigest(),
               'board_result': json.loads(result)}
    with output.open('x', encoding='utf-8') as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    board = receipt['board_result']
    print(json.dumps({'output': str(output), 'status': board.get('status', board.get('phase')),
                      'boot_id': board.get('boot_id'), 'board_mutations': board.get('board_mutations')}, ensure_ascii=True))

if __name__ == '__main__':
    main()
