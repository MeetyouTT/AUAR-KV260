#!/usr/bin/env python3
"""Execute reviewed UART manifests; preserve raw output and verify every frame.

No login guessing, interrupt, reset, or automatic hardware recovery. Commands and
file transfers are explicit manifest entries. A timeout stops further commands.
"""
import base64
import datetime
import fcntl
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

ROOT = Path(__file__).resolve().parents[1]
PORT = '/dev/serial/by-id/usb-Xilinx_ML_Carrier_Card_XFL1EMEBC1R5-if01-port0'
PROMPT = re.compile(rb'root@[^\r\n]+:[^\r\n]*# $')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class UART:
    def __init__(self, raw):
        self.raw = raw
        self.buf = b''
        self.shell_ready = False
        self.echo_restored = False
        resolved = os.path.realpath(PORT)
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit() or int(proc.name) == os.getpid():
                continue
            try:
                files = list((proc / 'fd').iterdir())
            except OSError:
                continue
            for other in files:
                if os.path.realpath(other) == resolved:
                    raise RuntimeError('UART already open by PID ' + proc.name)
        self.fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.old = termios.tcgetattr(self.fd)
        attrs = termios.tcgetattr(self.fd)
        attrs[0] = attrs[1] = attrs[3] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[4] = attrs[5] = termios.B115200
        attrs[6][termios.VMIN] = attrs[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)

    def receive(self, seconds, pattern=None):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if pattern and pattern.search(self.buf):
                return True
            if select.select([self.fd], [], [], .02)[0]:
                part = os.read(self.fd, 32768)
                if part:
                    self.raw.write(part)
                    self.raw.flush()
                    self.buf += part
        return bool(pattern and pattern.search(self.buf))

    def write(self, payload):
        view = memoryview(payload)
        while view:
            if not select.select([], [self.fd], [], 5)[1]:
                raise RuntimeError('UART write timeout')
            count = os.write(self.fd, view[:256])
            view = view[count:]

    def line(self, command):
        if '\n' in command or len(command.encode()) > 3800:
            raise RuntimeError('Command exceeds reviewed canonical UART line limit')
        self.buf = b''
        self.shell_ready = False
        payload = command.encode() + b'\r'
        for pos in range(0, len(payload), 32):
            self.write(payload[pos:pos + 32])
            self.receive(.012)

    def connect(self):
        time.sleep(.4)
        self.write(b'\r')
        if not self.receive(5, PROMPT):
            self.write(b'\r')
            if not self.receive(5, PROMPT):
                raise RuntimeError('Root shell not confirmed; no task command sent')
        self.line("stty -echo; printf '\\nUART_REVIEWED_READY\\n'")
        if not self.receive(5, re.compile(rb'(?m)^UART_REVIEWED_READY\r?$')) or not self.receive(5, PROMPT):
            raise RuntimeError('Console preparation failed')
        self.shell_ready = True

    def command(self, command, marker, timeout):
        code = "import subprocess,sys,base64,gzip,hashlib,time;p=subprocess.run(base64.b64decode(sys.argv[1]).decode(),shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);d=p.stdout;s=base64.b64encode(gzip.compress(d)).decode();print('BEGIN '+sys.argv[2]+' '+str(p.returncode)+' '+str(len(d)),flush=True);time.sleep(.06);[(print('DATA '+sys.argv[2]+' '+str(i//384)+' '+s[i:i+384],flush=True),time.sleep(.045)) for i in range(0,len(s),384)];print('END '+sys.argv[2]+' '+hashlib.sha256(d).hexdigest(),flush=True);time.sleep(.06)"
        wire = 'python3 -B -c ' + shlex.quote(code) + ' ' + shlex.quote(base64.b64encode(command.encode()).decode()) + ' ' + marker
        self.line(wire)
        done = self.receive(timeout, PROMPT)
        self.shell_ready = done
        decoded = self.buf.decode('utf-8', 'replace')
        begin = re.search(r'^BEGIN ' + marker + r' (\d+) (\d+)\r?$', decoded, re.M)
        end = re.search(r'^END ' + marker + r' ([0-9a-f]{64})\r?$', decoded, re.M)
        chunks = re.findall(r'^DATA ' + marker + r' (\d+) ([A-Za-z0-9+/=]+)\r?$', decoded, re.M)
        if not done or not begin or not end or [int(i) for i, _ in chunks] != list(range(len(chunks))):
            raise RuntimeError('Incomplete command response: ' + marker)
        data = gzip.decompress(base64.b64decode(''.join(s for _, s in chunks), validate=True))
        if len(data) != int(begin[2]) or hashlib.sha256(data).hexdigest() != end[1]:
            raise RuntimeError('Command output integrity mismatch')
        return int(begin[1]), data, end[1]

    def transfer(self, entry):
        source = Path(entry['source']).resolve()
        if ROOT not in source.parents and Path('/home/ghmd/kv260-dfx-state-validation-20261003') not in source.parents:
            raise RuntimeError('Transfer source outside reviewed workspaces')
        data = source.read_bytes()
        expected = entry['sha256']
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError('Source hash mismatch')
        dest = entry['destination']
        if not dest.startswith('/home/root/kv260-dfx-state-boardtest-20261004/'):
            raise RuntimeError('Transfer destination outside independent staging')
        receiver = '''import os,sys,termios,tty,time,select,base64,hashlib
from pathlib import Path
p=Path(sys.argv[1]);expected=sys.argv[2];count=int(sys.argv[3]);tmp=Path(str(p)+'.partial')
if p.exists() or tmp.exists():raise RuntimeError('Destination already exists')
p.parent.mkdir(parents=True,exist_ok=True)
fd=sys.stdin.fileno();old=termios.tcgetattr(fd);h=hashlib.sha256();total=0;seq=0;pending=b''
try:
 tty.setraw(fd)
 with tmp.open('xb') as out:
  os.write(1,b'UART_FILE_READY\\n')
  while total<count:
   until=time.monotonic()+20
   while b'\\n' not in pending:
    if time.monotonic()>until:raise RuntimeError('Frame timeout')
    if select.select([fd],[],[],.2)[0]:pending+=os.read(fd,4096)
   line,pending=pending.split(b'\\n',1);index,checksum,payload=line.split(b' ',2)
   payload=base64.b64decode(payload,validate=True)
   if int(index)!=seq or hashlib.sha256(payload).hexdigest().encode()!=checksum:raise RuntimeError('Bad frame')
   if total+len(payload)>count:raise RuntimeError('Unexpected size')
   out.write(payload);h.update(payload);total+=len(payload)
   os.write(1,('UART_FILE_ACK %d\\n'%seq).encode());seq+=1
  out.flush();os.fsync(out.fileno())
 if h.hexdigest()!=expected:raise RuntimeError('Final hash mismatch')
 os.link(str(tmp),str(p));tmp.unlink()
 os.write(1,('UART_FILE_DONE %d %s\\n'%(total,h.hexdigest())).encode())
finally:
 termios.tcsetattr(fd,termios.TCSANOW,old)
'''
        zipped = base64.b64encode(gzip.compress(receiver.encode(), mtime=0)).decode()
        code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(zipped) + ')))'
        self.line('python3 -B -c ' + shlex.quote(code) + ' ' + shlex.quote(dest) + ' ' + expected + ' ' + str(len(data)))
        if not self.receive(10, re.compile(rb'(?m)^UART_FILE_READY\r?$')):
            raise RuntimeError('Transfer receiver did not start')
        acked = 0
        for seq, pos in enumerate(range(0, len(data), 3072)):
            chunk = data[pos:pos + 3072]
            frame = str(seq).encode() + b' ' + hashlib.sha256(chunk).hexdigest().encode() + b' ' + base64.b64encode(chunk) + b'\n'
            self.buf = b''
            self.write(frame)
            if not self.receive(10, re.compile(rb'(?m)^UART_FILE_ACK ' + str(seq).encode() + rb'\r?$')):
                raise RuntimeError('Missing transfer frame acknowledgement ' + str(seq))
            acked += 1
            if acked % 25 == 0:
                print(json.dumps({'transfer': entry['id'], 'frames_acknowledged': acked, 'total_bytes': len(data)}), flush=True)
        if not self.receive(10, re.compile(rb'(?m)^UART_FILE_DONE ' + str(len(data)).encode() + b' ' + expected.encode() + rb'\r?$')):
            raise RuntimeError('Missing final transfer hash proof')
        if not self.receive(5, PROMPT):
            raise RuntimeError('Transfer complete without shell prompt')
        self.shell_ready = True
        return {'frames_acknowledged': acked, 'bytes': len(data), 'sha256': expected}

    def close(self):
        echo_restored = self.echo_restored
        try:
            if self.shell_ready:
                self.line("stty echo; printf '\\nUART_ECHO_RESTORED\\n'")
                echo_restored = self.receive(5, re.compile(rb'(?m)^UART_ECHO_RESTORED\r?$')) and self.receive(5, PROMPT)
        finally:
            termios.tcsetattr(self.fd, termios.TCSANOW, self.old)
            os.close(self.fd)
        return echo_restored

    def poweroff(self):
        # The preceding manifest entry must have completed guarded application
        # unload and service stop. Restore console echo before losing the shell.
        self.line("stty echo; printf '\\nUART_SHUTDOWN_ECHO_READY\\n'")
        if not self.receive(5, re.compile(rb'(?m)^UART_SHUTDOWN_ECHO_READY\r?$')) or not self.receive(5, PROMPT):
            raise RuntimeError('Shutdown echo preparation failed')
        self.echo_restored = True
        self.line('systemctl --no-block poweroff')
        started = time.monotonic()
        powerdown = re.compile(rb'reboot: Power down')
        for n in range(120):
            if self.receive(1, powerdown):
                return {'powerdown_confirmed': True, 'command': 'systemctl --no-block poweroff',
                        'elapsed_seconds': time.monotonic() - started,
                        'console_echo_restored_before_shutdown': True}
            if (n + 1) % 10 == 0:
                print(json.dumps({'waiting_for_clean_powerdown_seconds': n + 1}), flush=True)
        raise RuntimeError('Clean Power down marker not confirmed; do not disconnect board power')


def main():
    manifest = Path(sys.argv[1]).resolve()
    if ROOT / 'manifests' not in manifest.parents:
        raise SystemExit('Manifest must be inside reviewed workspace')
    entries = json.loads(manifest.read_text())
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'evidence' / (stamp + '-' + manifest.stem)
    out.mkdir(parents=True)
    (out / 'manifest.json').write_bytes(manifest.read_bytes())
    status = {'manifest': str(manifest), 'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
              'started_utc': utc(), 'port': PORT, 'complete': False, 'results': []}
    uart = None
    raw = (out / 'serial.raw').open('xb')
    try:
        uart = UART(raw)
        uart.connect()
        status['root_shell_confirmed'] = True
        for index, entry in enumerate(entries):
            result = {'id': entry['id'], 'started_utc': utc(), 'entry': entry}
            if entry.get('type') == 'poweroff':
                if index == 0 or entries[index - 1].get('id') != 'prepare-coldboot':
                    raise RuntimeError('Poweroff requires preceding guarded preparation')
                result.update(uart.poweroff())
                result['exit_code'] = 0
            elif entry.get('type') == 'transfer':
                result.update(uart.transfer(entry))
                result['exit_code'] = 0
            else:
                rc, data, sha = uart.command(entry['command'], 'KS%03d' % index, entry.get('timeout', 60))
                (out / (entry['id'] + '.output')).write_bytes(data)
                result.update(exit_code=rc, output_sha256=sha, bytes=len(data))
            result['finished_utc'] = utc()
            status['results'].append(result)
            (out / 'status.json').write_text(json.dumps(status, indent=2, ensure_ascii=False) + '\n')
            print(json.dumps({k: v for k, v in result.items() if k != 'entry'}, ensure_ascii=False), flush=True)
            if result['exit_code'] != 0:
                raise RuntimeError('Command failed; subsequent entries stopped: ' + entry['id'])
        status['complete'] = True
    except Exception as exc:
        status['error'] = str(exc)
        print('Stopped:', str(exc), flush=True)
    finally:
        if uart is not None:
            try:
                status['console_echo_restored'] = uart.close()
            except Exception as exc:
                status['console_close_error'] = str(exc)
        raw.close()
        status['finished_utc'] = utc()
        (out / 'status.json').write_text(json.dumps(status, indent=2, ensure_ascii=False) + '\n')
        (ROOT / 'CURRENT_UART.json').write_text(json.dumps({'evidence': str(out), 'complete': status['complete']}, indent=2) + '\n')
    print('Evidence:', str(out), flush=True)
    raise SystemExit(0 if status['complete'] else 1)


if __name__ == '__main__':
    main()
