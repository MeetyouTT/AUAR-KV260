"""Use existing guarded UART transport and preserve integrity evidence."""
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

job = Path(__file__).parent
spec = importlib.util.spec_from_file_location('reviewed_uart', '/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
source = (job/'board_readonly.py').read_bytes()
compile(source, 'board_readonly.py', 'exec')
payload = base64.b64encode(gzip.compress(source, mtime=0)).decode()
code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(payload) + ')))'
command = 'python3 -B -c ' + shlex.quote(code)
out = job/'board-readonly'
out.mkdir(exist_ok=True)
status = {'started_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': hashlib.sha256(source).hexdigest(), 'complete': False}
uart = None
try:
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart = transport.UART(raw)
            uart.connect()
            status['root_shell_confirmed'] = True
            rc, data, digest = uart.command(command, 'IDENTITYREADONLY', 35)
            (out/'result.json').write_bytes(data)
            status.update(exit_code=rc, output_sha256=digest, complete=(rc == 0))
            if rc == 0:
                print(data.decode())
            else:
                print('Read-only command failed; see private local output')
        finally:
            if uart is not None:
                status['console_echo_restored'] = uart.close()
except Exception as exc:
    status['error'] = str(exc)
finally:
    status['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (out/'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(status, ensure_ascii=False))
raise SystemExit(0 if status['complete'] else 1)
