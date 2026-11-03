#!/usr/bin/env python3
"""Transfer the pinned shadow bundle to its dedicated native-ops staging path."""
import base64
import argparse
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import sys

ROOT = Path('/home/ghmd/aura-pan-follow-shadow-20261024')
OPS = '/home/root/aura-native-live-20261024/ops/be72669aa53de735'
DEST_ROOT = OPS + '/pan-follow-shadow-live/'
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=ROOT/'shadow-bundle-manifest.json')
    args=parser.parse_args()
    manifest_path=args.manifest.resolve()
    if ROOT not in manifest_path.parents:raise RuntimeError('Manifest outside shadow workspace')
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('ops_root') != OPS or manifest.get('release') not in ('pan-follow-shadow-live','pan-follow-shadow-stream-v2'):
        raise RuntimeError('Unexpected shadow release destination')
    files = list(manifest['files'])
    raw_manifest = manifest_path.read_bytes()
    files.append({'source': str(manifest_path), 'source_rel': 'shadow-bundle-manifest.json',
                  'destination': OPS+'/'+manifest['release']+'/deployment-manifest.json',
                  'bytes': len(raw_manifest), 'sha256': hashlib.sha256(raw_manifest).hexdigest()})
    for row in files:
        source_input = Path(row['source'])
        if source_input.is_symlink():
            raise RuntimeError('Refusing symlink release source')
        source = source_input.resolve()
        if ROOT not in source.parents:
            raise RuntimeError('Refusing source outside isolated shadow workspace')
        data = source.read_bytes()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise RuntimeError('Local release file changed: ' + row['source_rel'])
        destination = Path(row['destination'])
        if '..' in destination.parts or not row['destination'].startswith(OPS + '/'):
            raise RuntimeError('Refusing destination outside owned native-ops directory')

    spec = importlib.util.spec_from_file_location('pan_wire', str(TRANSPORT))
    wire = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wire)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = Path('/home/ghmd/aura-pan-board-20261024/uart-transfer') / (stamp + '-pan-shadow')
    out.mkdir(parents=True)
    (out / 'manifest.json').write_text(json.dumps({'manifest': manifest,
        'transfers': [{k: row[k] for k in ('source_rel','destination','bytes','sha256')} for row in files]}, indent=2) + '\n')
    status = {'complete': False, 'transfers': [], 'console_echo_restored': False}
    with (out / 'serial.raw').open('xb') as raw:
        uart = wire.UART(raw)
        try:
            uart.connect()
            for index, row in enumerate(files):
                data = Path(row['source']).read_bytes()
                payload = """import os,sys,termios,tty,time,select,base64,hashlib
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
finally:termios.tcsetattr(fd,termios.TCSANOW,old)
"""
                code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(
                    base64.b64encode(gzip.compress(payload.encode(), mtime=0)).decode()) + ')))'
                uart.line('python3 -B -c ' + shlex.quote(code) + ' '
                          + shlex.quote(row['destination']) + ' '
                          + row['sha256'] + ' ' + str(len(data)))
                if not uart.receive(10, re.compile(rb'(?m)^UART_FILE_READY\r?$')):
                    raise RuntimeError('Receiver did not start for ' + row['source_rel'])
                acked = 0
                for seq, offset in enumerate(range(0, len(data), 3072)):
                    chunk = data[offset:offset + 3072]
                    frame = (str(seq).encode() + b' ' + hashlib.sha256(chunk).hexdigest().encode()
                             + b' ' + base64.b64encode(chunk) + b'\n')
                    uart.buf = b''
                    uart.write(frame)
                    if not uart.receive(10, re.compile(rb'(?m)^UART_FILE_ACK ' + str(seq).encode() + rb'\r?$')):
                        raise RuntimeError('Missing file frame acknowledgement')
                    acked += 1
                if not uart.receive(10, re.compile(rb'(?m)^UART_FILE_DONE ' + str(len(data)).encode()
                                                     + b' ' + row['sha256'].encode() + rb'\r?$')):
                    raise RuntimeError('Missing final file hash acknowledgement')
                if not uart.receive(5, wire.PROMPT):
                    raise RuntimeError('Transfer shell prompt not restored')
                uart.shell_ready = True
                status['transfers'].append({'file': row['source_rel'],'bytes': len(data),
                                            'frames': acked,'sha256': row['sha256']})
            status['complete'] = True
        finally:
            status['console_echo_restored'] = uart.close()
            (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({'evidence': str(out),'complete': status['complete'],
                      'transferred_files': len(status['transfers']),
                      'console_echo_restored': status['console_echo_restored']}))


if __name__ == '__main__':
    main()
