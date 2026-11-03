"""Host-only strict transport. New outputs stay in this review directory."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRANSPORT = HERE.parents[2] / '2026-10-18_board_dialogue/board_ssh.py'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('script', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source_path, output = args.script.resolve(), args.output.resolve()
    assert source_path.parent == HERE and output.parent == HERE
    assert source_path.name.startswith('collect_') and source_path.suffix == '.py'
    spec = importlib.util.spec_from_file_location('strict_gui_review_ssh', TRANSPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = source_path.read_text(encoding='utf-8')
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw = module.ssh('python3 -B -', source, timeout=75)
    result = {'host_observed_start_utc': start,
              'host_observed_end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'script_path': str(source_path), 'script_sha256': hashlib.sha256(source.encode()).hexdigest(),
              'transport_sha256': hashlib.sha256(TRANSPORT.read_bytes()).hexdigest(),
              'board_result': json.loads(raw)}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'output': str(output), 'board_mutations': False}))

if __name__ == '__main__':
    main()
