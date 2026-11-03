#!/usr/bin/env python3
"""Passively capture a physical KV260 restart; never transmit UART bytes."""
import datetime
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import termios
import time

ROOT = Path(__file__).resolve().parents[1]
PORT = '/dev/serial/by-id/usb-Xilinx_ML_Carrier_Card_XFL1EMEBC1R5-if01-port0'


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'evidence' / (stamp + '-coldboot-observation')
    out.mkdir(parents=True, exist_ok=False)
    status = {'started_utc': stamp, 'port': PORT, 'read_only': True, 'uart_bytes_sent': 0,
              'fresh_boot_marker_seen': False, 'root_prompt_seen': False, 'complete': False,
              'port_opens': [], 'disconnects': []}
    fd = None
    old = None
    buf = b''
    started = time.monotonic()
    next_progress = 0

    def close_port():
        nonlocal fd, old
        if fd is not None:
            try:
                termios.tcsetattr(fd, termios.TCSANOW, old)
            except OSError:
                pass  # The USB interface can disappear during DC power removal.
            os.close(fd)
            fd = None
            old = None

    try:
        with (out / 'serial.raw').open('xb') as raw:
            while time.monotonic() - started < 240:
                elapsed = time.monotonic() - started
                if elapsed >= next_progress:
                    print(json.dumps({'elapsed_seconds': round(elapsed), 'boot_seen': status['fresh_boot_marker_seen'],
                                      'root_seen': status['root_prompt_seen'], 'transmit_bytes': 0}), flush=True)
                    next_progress += 15
                if fd is None:
                    if not Path(PORT).exists():
                        time.sleep(.2)
                        continue
                    try:
                        fd = os.open(PORT, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        old = termios.tcgetattr(fd)
                        attrs = termios.tcgetattr(fd)
                        attrs[0] = attrs[1] = attrs[3] = 0
                        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
                        attrs[4] = attrs[5] = termios.B115200
                        attrs[6][termios.VMIN] = attrs[6][termios.VTIME] = 0
                        termios.tcsetattr(fd, termios.TCSANOW, attrs)
                        status['port_opens'].append({'elapsed_seconds': elapsed, 'device': os.path.realpath(PORT)})
                    except OSError as exc:
                        if fd is not None:
                            os.close(fd)
                            fd = None
                        if exc.errno not in (errno.ENOENT, errno.ENODEV, errno.EIO):
                            raise
                        time.sleep(.2)
                        continue
                try:
                    if not select.select([fd], [], [], .2)[0]:
                        continue
                    data = os.read(fd, 32768)
                except OSError as exc:
                    if exc.errno not in (errno.EIO, errno.ENODEV, errno.ENXIO):
                        raise
                    status['disconnects'].append({'elapsed_seconds': elapsed, 'errno': exc.errno})
                    close_port()
                    continue
                if not data:
                    continue
                raw.write(data)
                raw.flush()
                buf += data
                if not status['fresh_boot_marker_seen'] and re.search(
                        rb'U-Boot|Starting kernel|Booting Linux on physical CPU|Linux version 5\.15', buf):
                    status['fresh_boot_marker_seen'] = True
                    status['first_boot_marker_elapsed_seconds'] = time.monotonic() - started
                    print('Fresh boot output observed; still transmitting zero bytes', flush=True)
                if status['fresh_boot_marker_seen'] and re.search(rb'root@[^\r\n]+:[^\r\n]*# ', buf):
                    status['root_prompt_seen'] = True
                    status['root_prompt_elapsed_seconds'] = time.monotonic() - started
                    status['complete'] = True
                    break
            if not status['complete']:
                status['error'] = 'Fresh boot/root prompt not observed within 240 seconds; no UART input sent'
    except Exception as exc:
        status['error'] = '%s: %s' % (type(exc).__name__, exc)
    finally:
        close_port()
        status['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        status['serial_bytes'] = len(buf)
        status['serial_sha256'] = hashlib.sha256(buf).hexdigest()
        (out / 'status.json').write_text(json.dumps(status, indent=2, ensure_ascii=False) + '\n')
        (ROOT / 'CURRENT_BOOT_OBSERVATION.json').write_text(json.dumps({'evidence': str(out), **status}, indent=2) + '\n')
    print(json.dumps({'complete': status['complete'], 'evidence': str(out), 'error': status.get('error'),
                      'serial_bytes': len(buf), 'uart_bytes_sent': 0}), flush=True)
    raise SystemExit(0 if status['complete'] else 1)


if __name__ == '__main__':
    main()
