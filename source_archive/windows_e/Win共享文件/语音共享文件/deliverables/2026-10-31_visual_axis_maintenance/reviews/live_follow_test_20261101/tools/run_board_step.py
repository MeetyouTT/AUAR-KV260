"""Execute a reviewed board Python step through the existing pinned-host SSH helper."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parents[1]
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('step')
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()
    assert args.step.replace('_', '').isalnum() and 1 <= args.timeout <= 150
    source = HERE / 'remote' / (args.step + '.py')
    raw = source.read_bytes()
    if b'# USE_CAMERA_BINDING_RULES' in raw[:100]:
        raw = raw.split(b'\n', 1)[0] + b'\n' + (HERE / 'remote/_camera_binding_rules.py').read_bytes() + b'\n' + raw.split(b'\n', 1)[1]
    if raw.startswith(b'# USE_SESSION_COMMON'):
        raw = (HERE / 'remote/_session_common.py').read_bytes() + b'\n' + raw
    result = ssh('python3 -B -', raw.decode('utf-8'), timeout=args.timeout)
    value = json.loads(result)
    envelope = dict(step=args.step, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    source_sha256=hashlib.sha256(raw).hexdigest(), result=value)
    encoded = (json.dumps(envelope, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    target = HERE / 'evidence' / (args.step + '_' + str(time.time_ns()) + '.json')
    with target.open('xb') as handle:
        handle.write(encoded)
    print(json.dumps(dict(evidence=str(target), sha256=hashlib.sha256(encoded).hexdigest(), result=value),
                     ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
