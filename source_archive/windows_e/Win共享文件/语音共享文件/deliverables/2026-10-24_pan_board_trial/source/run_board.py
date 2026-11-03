#!/usr/bin/env python3
"""Use the established exclusive framed UART and keep raw evidence private."""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--label', required=True)
    parser.add_argument('--timeout', type=int, default=35)
    args = parser.parse_args()
    source = args.source.resolve()
    if ROOT not in source.parents or not args.label.replace('-', '').replace('_', '').isalnum():
        raise RuntimeError('Use an own source and simple evidence label')
    code = source.read_text()
    compile(code, str(source), 'exec')
    spec = importlib.util.spec_from_file_location('pan_wire', '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
    wire = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wire)
    command = wire.wire(code)
    out = ROOT / 'uart' / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + args.label)
    out.mkdir(parents=True)
    status, uart = {}, None
    with (out / 'serial.raw').open('xb') as raw:
        try:
            status['stage'] = 'opening_uart'
            uart = wire.transport_module().UART(raw)
            uart.connect()
            status['stage'] = 'root_confirmed'
            rc, body, digest = uart.command(command, 'AURAPAN', args.timeout)
            status['stage'] = 'command_response_complete'
            status.update(exit_code=rc, response_sha256=digest)
            if rc:
                (out / 'error.txt').write_bytes(body)
                raise RuntimeError('Board command failed; raw details remain in private evidence')
            data = json.loads(body)
            (out / 'response.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        except BaseException as error:
            status.update(error_type=type(error).__name__, error=str(error))
            raise
        finally:
            if uart:
                status['console_echo_restored'] = uart.close()
            (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
            (ROOT / ('latest-' + args.label + '.json')).write_text(json.dumps({'evidence': str(out), **status}, indent=2) + '\n')
    print(json.dumps({'evidence': str(out), 'exit_code': status.get('exit_code'),
                      'console_echo_restored': status.get('console_echo_restored'),
                      'response_keys': list(data)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
