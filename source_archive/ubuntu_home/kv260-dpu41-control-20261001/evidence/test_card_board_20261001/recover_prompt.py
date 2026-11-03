#!/usr/bin/env python3
"""Recover an idle shell prompt after the user supplied ttyPS1 process evidence."""
import datetime
import json
import os
from pathlib import Path
import re
import select
import sys
import termios
import time

root = Path(__file__).resolve().parent
port = '/dev/serial/by-id/usb-Xilinx_ML_Carrier_Card_XFL1EMEBC1R5-if01-port0'
phase = sys.argv[1] if len(sys.argv) > 1 else '11-prompt-recovery'
mode = sys.argv[2] if len(sys.argv) > 2 else 'interrupt'
if mode not in ('interrupt', 'resume') or not re.fullmatch(r'[A-Za-z0-9-]+', phase):
    raise SystemExit('Invalid phase or mode')
payload = b'\x11\r' if mode == 'resume' else b'\x03\r'
sent = 'Ctrl-Q, CR' if mode == 'resume' else 'Ctrl-C, CR'
raw_path = root / (phase + '.serial.raw')
result_path = root / (phase + '.result.json')
if raw_path.exists() or result_path.exists():
    raise SystemExit('Refusing to overwrite existing evidence')
fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
old = termios.tcgetattr(fd)
attrs = termios.tcgetattr(fd)
attrs[0] = 0
attrs[1] = 0
attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
attrs[3] = 0
attrs[4] = attrs[5] = termios.B115200
attrs[6][termios.VMIN] = attrs[6][termios.VTIME] = 0
data = b''
try:
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    time.sleep(0.4)
    os.write(fd, payload)
    until = time.monotonic() + 8
    while time.monotonic() < until:
        ready, _, _ = select.select([fd], [], [], 0.2)
        if ready:
            data += os.read(fd, 32768)
            if re.search(rb'root@[^\r\n]+:[^\r\n]*# $', data):
                break
finally:
    termios.tcsetattr(fd, termios.TCSANOW, old)
    os.close(fd)
raw_path.write_bytes(data)
ok = bool(re.search(rb'root@[^\r\n]+:[^\r\n]*# $', data))
record = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'port': port, 'sent': sent, 'root_prompt_confirmed': ok,
          'output': data.decode('utf-8', 'replace')}
result_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, ensure_ascii=False))
raise SystemExit(0 if ok else 1)
