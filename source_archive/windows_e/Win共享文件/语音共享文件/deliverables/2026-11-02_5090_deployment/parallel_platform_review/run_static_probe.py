"""Host wrapper; writes only one exclusive evidence file in this review directory."""
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
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    script, output = args.script.resolve(), args.output.resolve()
    if script.parent != HERE or output.parent != HERE:
        raise ValueError('Only this review directory is allowed')
    if not script.name.startswith('collect_') or not script.name.endswith('_readonly.py'):
        raise ValueError('A reviewed static collector is required')
    source = script.read_text(encoding='utf-8')
    transport_raw = TRANSPORT.read_bytes()
    if hashlib.sha256(transport_raw).hexdigest() != '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373':
        raise ValueError('Trusted transport changed')
    spec = importlib.util.spec_from_file_location('aura_static_review_transport', TRANSPORT)
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    raw = transport.ssh('python3 -B -I -S -', source, timeout=45)
    result = {'host_observed_start_utc': start,
              'host_observed_end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'script_path': str(script),
              'script_sha256': hashlib.sha256(source.encode()).hexdigest(),
              'transport_sha256': hashlib.sha256(transport_raw).hexdigest(),
              'board_result': json.loads(raw)}
    with output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'output': str(output), 'boot_id': result['board_result']['boot_id'],
                      'board_mutations': result['board_result']['board_mutations']}))


if __name__ == '__main__':
    main()
