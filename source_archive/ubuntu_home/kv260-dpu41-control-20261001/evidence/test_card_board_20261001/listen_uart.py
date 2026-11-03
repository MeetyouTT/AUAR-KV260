#!/usr/bin/env python3
"""Listen for a marker written to ttyPS1 from the user's authenticated SSH session."""
import datetime
import json
import os
from pathlib import Path
import select
import termios
import time

root = Path(__file__).resolve().parent
port = '/dev/serial/by-id/usb-Xilinx_ML_Carrier_Card_XFL1EMEBC1R5-if01-port0'
raw_path = root / '13-uart-link.serial.raw'
result_path = root / '13-uart-link.result.json'
if raw_path.exists() or result_path.exists():
    raise SystemExit('Refusing to overwrite existing evidence')
fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
old = termios.tcgetattr(fd)
attrs = termios.tcgetattr(fd)
attrs[0] = attrs[1] = attrs[3] = 0
attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
attrs[4] = attrs[5] = termios.B115200
attrs[6][termios.VMIN] = attrs[6][termios.VTIME] = 0
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
data = b''
marker = b'KV260_UART_LINK_CHECK'
try:
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    print('Listening for KV260_UART_LINK_CHECK for up to 180 seconds', flush=True)
    until = time.monotonic() + 180
    while time.monotonic() < until:
        ready, _, _ = select.select([fd], [], [], 0.2)
        if ready:
            data += os.read(fd, 32768)
            if marker in data:
                break
finally:
    termios.tcsetattr(fd, termios.TCSANOW, old)
    os.close(fd)
raw_path.write_bytes(data)
ok = marker in data
record = {'started_utc': started, 'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'port': port, 'sent': 'none', 'marker_received': ok,
          'output': data.decode('utf-8', 'replace')}
result_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, ensure_ascii=False), flush=True)
raise SystemExit(0 if ok else 1)
