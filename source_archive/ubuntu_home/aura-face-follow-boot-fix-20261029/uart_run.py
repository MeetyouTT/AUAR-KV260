#!/usr/bin/env python3
"""Run one reviewed Python probe with UART exclusivity and complete evidence."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
source = Path(sys.argv[1]).resolve()
assert ROOT in source.parents
spec = importlib.util.spec_from_file_location('startup_wire', '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
data = source.read_bytes()
command = wire.wire(data.decode('utf-8'))
if '--validate-only' in sys.argv[2:]:
    print(json.dumps({'source': str(source), 'command_bytes': len(command.encode()), 'board_accessed': False}))
    raise SystemExit(0)
out = ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'+source.stem)
out.mkdir(parents=True, exist_ok=False)
status = {'source': source.name, 'source_sha256': hashlib.sha256(data).hexdigest(), 'complete': False,
          'host_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
with (out/'serial.raw').open('xb') as raw:
    uart = None
    try:
        uart = wire.transport_module().UART(raw)
        uart.connect()
        rc, body, digest = uart.command(command, 'FOLLOW01', 110)
        (out/'response.output').write_bytes(body)
        status.update(exit_code=rc, response_sha256=digest, response_bytes=len(body))
        if rc:
            raise RuntimeError('Board command failed; private response retained')
        result = json.loads(body)
        (out/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        status['complete'] = True
    except Exception as exc:
        status['error'] = str(exc)
    finally:
        if uart is not None:
            try:
                status['console_echo_restored'] = uart.close()
            except Exception as exc:
                status['console_close_error'] = str(exc)
status['finished_host_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(out/'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(ROOT/'LATEST.json').write_text(json.dumps({'evidence': str(out), **status}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'evidence': str(out), **status}, ensure_ascii=False, indent=2))
raise SystemExit(0 if status.get('complete') and status.get('console_echo_restored') else 1)
