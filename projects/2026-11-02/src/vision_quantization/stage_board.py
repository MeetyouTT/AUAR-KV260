"""Resume a hash-checked bundle over the existing exclusive 115200 UART."""
import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import time

PRIVATE = Path('/home/ghmd/aura-dpu-vision-20261021')
REMOTE = '/home/root/aura-dpu-vision-20261021/staging/'

RECEIVER = r'''
import base64,hashlib,os,select,sys,termios,time,tty
from pathlib import Path
p=Path(sys.argv[1]);count=int(sys.argv[2]);expected=sys.argv[3];start=int(sys.argv[4]);prefix=sys.argv[5];boot=sys.argv[6]
assert os.uname().machine=='aarch64'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
assert str(p).startswith('/home/root/aura-dpu-vision-20261021/staging/') and '..' not in p.parts
assert not p.exists();tmp=Path(str(p)+'.partial');assert not tmp.is_symlink()
initial=tmp.read_bytes() if tmp.exists() else b''
assert len(initial)==start and hashlib.sha256(initial).hexdigest()==prefix
p.parent.mkdir(parents=True,exist_ok=True)
h=hashlib.sha256(initial);total=start;pending=b'';last=None;old=termios.tcgetattr(0)
try:
 tty.setraw(0);os.write(1,b'AURAVISION_READY\n')
 with tmp.open('ab') as out:
  while total<count:
   until=time.monotonic()+20
   while b'\n' not in pending:
    if time.monotonic()>until:raise RuntimeError('Frame timeout')
    if select.select([0],[],[],.1)[0]:pending+=os.read(0,4096)
   line,pending=pending.split(b'\n',1)
   if not line:continue
   try:
    rawpos,checksum,payload=line.split(b' ',2);pos=int(rawpos);data=base64.b64decode(payload,validate=True)
    assert 0<len(data)<=384 and hashlib.sha256(data).hexdigest().encode()==checksum
    if pos==total:
     assert total+len(data)<=count
     out.write(data);h.update(data);last=(pos,data);total+=len(data)
    else:assert last==(pos,data)
    os.write(1,('AURAVISION_ACK %d\n'%total).encode())
   except Exception:os.write(1,('AURAVISION_NACK %d\n'%total).encode())
  out.flush();os.fsync(out.fileno())
 assert h.hexdigest()==expected
 os.link(str(tmp),str(p));tmp.unlink()
 os.write(1,('AURAVISION_DONE %d %s\n'%(total,h.hexdigest())).encode())
finally:termios.tcsetattr(0,termios.TCSADRAIN,old)
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path)
    p.add_argument('--boot', required=True)
    args = p.parse_args()
    source = args.bundle.resolve()
    if PRIVATE not in source.parents or source.is_symlink():
        p.error('Use a regular bundle inside the private task directory')
    blob = source.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    remote = REMOTE + digest[:16] + '/bundle.tar.gz'
    evidence = PRIVATE / 'uart' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    evidence.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location('wire', '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
    wire = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wire)
    status = {'complete': False, 'destination': remote, 'bytes': len(blob), 'sha256': digest,
              'retries': 0, 'evidence': str(evidence)}
    uart = None
    with (evidence / 'serial.raw').open('xb') as raw:
        try:
            uart = wire.transport_module().UART(raw)
            uart.connect()
            code = 'import json,hashlib\nfrom pathlib import Path\np=Path(%r)\nt=Path(str(p)+".partial")\nassert not p.is_symlink() and not t.is_symlink()\nd=p.read_bytes() if p.exists() else t.read_bytes() if t.exists() else b""\nprint(json.dumps({"complete":p.exists(),"offset":len(d),"sha256":hashlib.sha256(d).hexdigest()}))' % remote
            rc, body, _ = uart.command(wire.wire(code), 'AURAVISIONINFO', 10)
            if rc:
                raise RuntimeError('Could not query private staging state')
            info = json.loads(body)
            offset = info['offset']
            if not 0 <= offset <= len(blob) or hashlib.sha256(blob[:offset]).hexdigest() != info['sha256']:
                raise ValueError('Refuse mismatched staging prefix')
            if info['complete']:
                if offset != len(blob):
                    raise ValueError('Completed staged bundle differs')
            else:
                code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode(%r)))' % base64.b64encode(gzip.compress(RECEIVER.encode(), mtime=0)).decode()
                command = 'python3 -B -c ' + shlex.quote(code) + ' ' + ' '.join(shlex.quote(str(x)) for x in (remote, len(blob), digest, offset, info['sha256'], args.boot))
                uart.line(command)
                if not uart.receive(10, re.compile(rb'(?m)^AURAVISION_READY\r?$')):
                    raise RuntimeError('Receiver did not start')
                started = last = time.monotonic()
                for pos in range(offset, len(blob), 384):
                    chunk = blob[pos:pos + 384]
                    frame = b'\n' + str(pos).encode() + b' ' + hashlib.sha256(chunk).hexdigest().encode() + b' ' + base64.b64encode(chunk) + b'\n'
                    for attempt in range(4):
                        uart.buf = b''
                        uart.write(frame)
                        if uart.receive(1, re.compile(rb'(?m)^AURAVISION_ACK ' + str(pos + len(chunk)).encode() + rb'\r?$')):
                            break
                        status['retries'] += 1
                    else:
                        raise RuntimeError('No frame acknowledgement at ' + str(pos))
                    if time.monotonic() - last >= 15:
                        print(json.dumps({'acknowledged': pos + len(chunk), 'total': len(blob), 'retries': status['retries']}), flush=True)
                        last = time.monotonic()
                if not uart.receive(5, re.compile(rb'(?m)^AURAVISION_DONE ' + str(len(blob)).encode() + b' ' + digest.encode() + rb'\r?$')):
                    raise RuntimeError('Final checksum acknowledgement missing')
                if not uart.receive(5, wire.transport_module().PROMPT):
                    raise RuntimeError('Restored root prompt missing')
                uart.shell_ready = True
            status['complete'] = True
        except Exception as exc:
            status['error'] = str(exc)
        finally:
            if uart:
                if not uart.shell_ready:
                    uart.shell_ready = uart.receive(25, wire.transport_module().PROMPT)
                status['console_echo_restored'] = uart.close()
    (evidence / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    (PRIVATE / 'latest-stage.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status), flush=True)
    raise SystemExit(0 if status['complete'] else 1)


if __name__ == '__main__':
    main()
