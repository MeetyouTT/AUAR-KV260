"""Run one reviewed local read-only script using the existing strict SSH helper.

Writes evidence only into this parallel_platform directory. Never uploads a file to the board.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRANSPORT = HERE.parents[1] / '2026-10-18_board_dialogue' / 'board_ssh.py'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('script', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    script = args.script.resolve()
    output = args.output.resolve()
    assert script.parent == HERE and output.parent == HERE
    assert script.name.startswith('collect_') and script.name.endswith('_readonly.py')
    spec = importlib.util.spec_from_file_location('aura_strict_readonly_ssh', TRANSPORT)
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    source = script.read_text(encoding='utf-8')
    observed_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw = transport.ssh('python3 -B -', source, timeout=90)
    result = {'host_observed_start_utc': observed_start,
              'host_observed_end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'script_path': str(script),
              'script_sha256': hashlib.sha256(source.encode('utf-8')).hexdigest(),
              'transport_path': str(TRANSPORT),
              'transport_sha256': hashlib.sha256(TRANSPORT.read_bytes()).hexdigest(),
              'board_result': json.loads(raw)}
    with output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'output': str(output), 'boot_id': result['board_result'].get('boot_id'),
                      'board_mutations': result['board_result'].get('board_mutations')}))

if __name__ == '__main__':
    main()
