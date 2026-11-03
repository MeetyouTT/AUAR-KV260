"""Run the fixed read-only probe with the existing exclusive UART transport."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('reviewed_wire', '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
source = (root / 'board_probe.py').read_text()
command = wire.wire(source)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
directory = root / 'evidence' / stamp
directory.mkdir(parents=True, mode=0o700)
status = {'source_sha256': hashlib.sha256(source.encode()).hexdigest(), 'complete': False}
uart = None
try:
    with (directory / 'serial.raw').open('xb') as raw:
        try:
            uart = wire.transport_module().UART(raw)
            uart.connect()
            rc, body, digest = uart.command(command, 'VOICEPROBE', 35)
            (directory / 'response.output').write_bytes(body)
            status.update(exit_code=rc, sha256=digest, complete=(rc == 0))
            if rc == 0:
                result = json.loads(body)
                result['verified_host_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                (directory / 'response.json').write_text(json.dumps(result, indent=2) + '\n')
                (root / 'latest-board-probe.json').write_text(json.dumps(result, indent=2) + '\n')
                print(json.dumps(result))
        finally:
            if uart:
                status['console_echo_restored'] = uart.close()
except Exception as error:
    status.update(error_type=type(error).__name__, error=str(error)[:300])
(directory / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
print(json.dumps(status))
raise SystemExit(0 if status['complete'] else 1)
