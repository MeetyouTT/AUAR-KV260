#!/usr/bin/env python3
"""Execute a reviewed remote Python file on the known KV260 over UART."""
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    source_path = Path(sys.argv[1]).resolve()
    if ROOT not in source_path.parents:
        raise SystemExit('Remote script must be inside the adaptation directory')
    source = source_path.read_bytes()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'evidence' / (stamp + '-' + source_path.stem)
    out.mkdir()
    (out / 'remote.py').write_bytes(source)
    guard = ("import os;from pathlib import Path;"
             "assert os.uname().machine=='aarch64';"
             "assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100';\n")
    payload = base64.b64encode(gzip.compress(guard.encode() + source, mtime=0)).decode()
    code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(payload) + ')))'
    spec = importlib.util.spec_from_file_location('aura_uart', '/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with (out / 'uart.raw').open('wb') as raw:
        uart = mod.UART(raw)
        try:
            uart.connect()
            rc, data, digest = uart.command('python3 -B -c ' + shlex.quote(code), 'ADAPTATION', int(sys.argv[2]) if len(sys.argv) > 2 else 120)
            (out / 'result.txt').write_bytes(data)
        finally:
            restored = uart.close()
    status = {'evidence': str(out), 'rc': rc, 'output_sha256': digest,
              'source_sha256': hashlib.sha256(source).hexdigest(), 'console_echo_restored': restored}
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    (ROOT / ('CURRENT_' + source_path.stem.upper() + '.json')).write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status), flush=True)
    print(data.decode(errors='replace'), flush=True)
    raise SystemExit(rc)

if __name__ == '__main__':
    main()
