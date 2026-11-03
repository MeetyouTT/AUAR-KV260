#!/usr/bin/env python3
"""Host-side UART collector. Executes only the separately reviewed command manifest.

All evidence files are written on the Ubuntu host. No board files are created.
An unexpected prompt or timeout stops collection without sending Ctrl-C/reset.
"""
import datetime
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shlex
import sys
import termios
import time

ROOT = Path(__file__).resolve().parent
PORT = '/dev/serial/by-id/usb-Xilinx_ML_Carrier_Card_XFL1EMEBC1R5-if01-port0'

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    phase = sys.argv[1]
    entries = json.loads((ROOT / (phase + '.commands.json')).read_text())
    raw_path = ROOT / (phase + '.serial.raw')
    result_path = ROOT / (phase + '.results.jsonl')
    if raw_path.exists() or result_path.exists():
        raise SystemExit('Refusing to overwrite existing evidence: ' + phase)
    resolved_port = os.path.realpath(PORT)
    if not Path(PORT).exists():
        raise RuntimeError('Board UART not connected: ' + PORT)
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            fds = list((proc / 'fd').iterdir())
        except (OSError, PermissionError):
            continue
        for candidate_fd in fds:
            try:
                if os.path.realpath(candidate_fd) == resolved_port:
                    raise RuntimeError('UART already open by PID ' + proc.name)
            except OSError:
                continue
    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    old = termios.tcgetattr(fd)
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    with raw_path.open('xb') as raw, result_path.open('x') as results:
        def receive(deadline, pattern):
            buf = b''
            while time.monotonic() < deadline:
                ready, _, _ = select.select([fd], [], [], 0.01)
                if ready:
                    try:
                        part = os.read(fd, 32768)
                    except BlockingIOError:
                        continue
                    if part:
                        raw.write(part)
                        raw.flush()
                        buf += part
                        if pattern.search(buf):
                            return buf, True
            return buf, False

        try:
            prompt = re.compile(rb'root@[^\r\n]+:[^\r\n]*# $')
            time.sleep(0.4)  # Allow FTDI line settings to settle before the first byte.
            os.write(fd, b'\r')
            initial, ready = receive(time.monotonic() + 3, prompt)
            if not ready:
                os.write(fd, b'\r')
                extra, ready = receive(time.monotonic() + 3, prompt)
                initial += extra
            results.write(json.dumps({'type': 'connection', 'utc': utc(), 'port': PORT,
                                      'settings': '115200 8N1 no flow control',
                                      'ready': ready, 'output': initial.decode('utf-8', 'replace')}, ensure_ascii=False) + '\n')
            results.flush()
            if not ready:
                raise RuntimeError('Root shell not confirmed; no inventory commands sent')
            for index, entry in enumerate(entries):
                command = entry['command']
                marker = f'KV{index:03d}'
                # Capture stdout in board RAM, then send numbered chunks slowly.
                # No temporary files, hardware writes, or board-side installations.
                code = "import subprocess,sys,base64,gzip,hashlib,time; p=subprocess.run(base64.b64decode(sys.argv[1]).decode(),shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT); d=p.stdout; s=base64.b64encode(gzip.compress(d)).decode(); print('BEGIN '+sys.argv[2]+' '+str(p.returncode)+' '+str(len(d)),flush=True); time.sleep(.08); [(print('DATA '+sys.argv[2]+' '+str(i//96)+' '+s[i:i+96],flush=True),time.sleep(.04)) for i in range(0,len(s),96)]; print('END '+sys.argv[2]+' '+hashlib.sha256(d).hexdigest(),flush=True); time.sleep(.08)"
                wire = 'python3 -B -c ' + shlex.quote(code) + ' ' + shlex.quote(base64.b64encode(command.encode()).decode()) + ' ' + marker
                started = utc()
                # Pace input too; collect the terminal echo while sending.
                echoed = b''
                payload = wire.encode() + b'\r'
                for pos in range(0, len(payload), 4):
                    os.write(fd, payload[pos:pos+4])
                    part, _ = receive(time.monotonic() + 0.04, re.compile(rb'(?!)'))
                    echoed += part
                buf, done = receive(time.monotonic() + entry.get('timeout', 45), prompt)
                buf = echoed + buf
                decoded = buf.decode('utf-8', 'replace')
                begin = re.search(r'^BEGIN ' + marker + r' (\d+) (\d+)\r?$', decoded, re.M)
                end = re.search(r'^END ' + marker + r' ([0-9a-f]{64})\r?$', decoded, re.M)
                chunks = re.findall(r'^DATA ' + marker + r' (\d+) ([A-Za-z0-9+/=]+)\r?$', decoded, re.M)
                output = None
                integrity = False
                try:
                    if begin and end and [int(i) for i, _ in chunks] == list(range(len(chunks))):
                        data = gzip.decompress(base64.b64decode(''.join(s for _, s in chunks), validate=True))
                        integrity = len(data) == int(begin[2]) and hashlib.sha256(data).hexdigest() == end[1]
                        if integrity:
                            output = data.decode('utf-8', 'replace')
                            (ROOT / (phase + '.' + entry['id'] + '.output')).write_bytes(data)
                except Exception as exc:
                    print('Integrity decode:', repr(exc), flush=True)
                record = {'type': 'command', 'id': entry['id'], 'command': command,
                          'wire_command': wire, 'started_utc': started, 'finished_utc': utc(),
                          'complete': done and integrity, 'integrity_sha256': end[1] if integrity else None,
                          'exit_code': int(begin[1]) if begin else None,
                          'output': output, 'serial_output': decoded}
                results.write(json.dumps(record, ensure_ascii=False) + '\n')
                results.flush()
                print(json.dumps({'id': entry['id'], 'exit_code': record['exit_code'],
                                  'complete': record['complete'], 'bytes': len(buf)}, ensure_ascii=False), flush=True)
                if not record['complete'] or record['exit_code'] != 0:
                    raise RuntimeError('Collection stopped: incomplete or unsuccessful command')
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, old)
            os.close(fd)
    print('Evidence:', str(result_path), flush=True)

if __name__ == '__main__':
    main()
