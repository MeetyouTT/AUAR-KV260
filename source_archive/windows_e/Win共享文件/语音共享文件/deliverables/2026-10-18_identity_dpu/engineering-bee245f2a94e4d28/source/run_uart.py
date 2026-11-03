"""Run one guarded short probe using the existing exclusive UART transport."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source')
parser.add_argument('--phase', required=True)
args = parser.parse_args()
source = (ROOT/args.source).resolve()
assert source.parent == ROOT and args.phase.replace('-', '').isalnum()
spec = importlib.util.spec_from_file_location('checked_wire', '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
code = source.read_text()
command = wire.wire(code)
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT/'evidence'/(stamp+'-'+args.phase)
out.mkdir(parents=True, mode=0o700)
(out/'source.py').write_text(code)
status = {'source_sha256': hashlib.sha256(code.encode()).hexdigest(), 'evidence': str(out), 'complete': False}
uart = None
try:
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart = wire.transport_module().UART(raw)
            uart.connect()
            rc, body, digest = uart.command(command, 'IDENTITYDPU', 40)
            (out/'response.output').write_bytes(body)
            status.update(exit_code=rc, sha256=digest, complete=(rc == 0))
            if rc == 0:
                value = json.loads(body)
                artifacts = value.pop('artifacts', {})
                for name, artifact in artifacts.items():
                    assert Path(name).name == name
                    data = base64.b64decode(artifact['base64'], validate=True)
                    assert hashlib.sha256(data).hexdigest() == artifact['sha256']
                    (out/name).write_bytes(data)
                (out/'response.json').write_text(json.dumps(value, indent=2)+'\n')
                print(json.dumps(value), flush=True)
            else:
                print(body.decode(errors='replace')[-2000:], flush=True)
        finally:
            if uart:
                status['console_echo_restored'] = uart.close()
except Exception as exc:
    status['error'] = str(exc)
(out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
(ROOT/('latest-'+args.phase+'.json')).write_text(json.dumps(status, indent=2)+'\n')
print(json.dumps(status), flush=True)
raise SystemExit(0 if status['complete'] else 1)
