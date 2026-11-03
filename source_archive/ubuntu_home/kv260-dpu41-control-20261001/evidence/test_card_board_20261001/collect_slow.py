#!/usr/bin/env python3
"""Reuse the preserved collector with slower UART input and shorter read polling."""
from pathlib import Path

source = Path('/home/ghmd/AMD_Smart/logs/fpga/2026-09-30-kv260-readonly/collect_serial.py')
code = source.read_text()
changes = {
    'select.select([fd], [], [], 0.2)': 'select.select([fd], [], [], 0.01)',
    'range(0, len(payload), 24)': 'range(0, len(payload), 4)',
    'payload[pos:pos+24]': 'payload[pos:pos+4]',
    'time.monotonic() + 0.015': 'time.monotonic() + 0.04',
}
for before, after in changes.items():
    if code.count(before) != 1:
        raise SystemExit('Preserved source differs: ' + before)
    code = code.replace(before, after)
namespace = {'__name__': 'preserved_uart_slow', '__file__': str(source)}
exec(compile(code, str(source), 'exec'), namespace)
namespace['ROOT'] = Path(__file__).resolve().parent
namespace['main']()
