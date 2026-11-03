"""Resume the owned engineering bundle with checked prefix and retryable frames."""
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import termios
import time

ROOT = Path(__file__).parent
bundle = json.loads((ROOT/'engineering-bundle.json').read_text())
blob = Path(bundle['source']).read_bytes()
assert hashlib.sha256(blob).hexdigest() == bundle['sha256']
state = json.loads((ROOT/'latest-transfer-state.json').read_text())
info = json.loads((Path(state['evidence'])/'response.json').read_text())['engineering.zip.partial']
offset = info['bytes']
assert not info['symlink'] and 0 < offset < len(blob)
assert hashlib.sha256(blob[:offset]).hexdigest() == info['sha256']
receiver = r'''
import base64,hashlib,os,select,sys,termios,time,tty
from pathlib import Path
assert os.uname().machine=='aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
p=Path(sys.argv[1]);count=int(sys.argv[2]);expected=sys.argv[3];start=int(sys.argv[4]);prefix=sys.argv[5]
assert str(p).startswith('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/')
assert '..' not in p.parts and not p.exists()
tmp=Path(str(p)+'.partial');assert not tmp.is_symlink() and tmp.stat().st_size==start
initial=tmp.read_bytes();assert hashlib.sha256(initial).hexdigest()==prefix
h=hashlib.sha256(initial);total=start;pending=b'';last=None;fd=0;old=termios.tcgetattr(fd)
try:
 tty.setraw(fd);os.write(1,b'SFACE_SLOW_READY\n');time.sleep(.2)
 attrs=termios.tcgetattr(fd);attrs[4]=attrs[5]=termios.B230400
 termios.tcsetattr(fd,termios.TCSADRAIN,attrs)
 for _ in range(3):os.write(1,b'SFACE_FAST_READY\n');time.sleep(.2)
 with tmp.open('ab') as out:
  while total<count:
   until=time.monotonic()+20
   while b'\n' not in pending:
    if time.monotonic()>until:raise RuntimeError('Frame timeout')
    if select.select([fd],[],[],.1)[0]:pending+=os.read(fd,4096)
   line,pending=pending.split(b'\n',1)
   if not line:continue
   try:
    rawpos,checksum,payload=line.split(b' ',2);pos=int(rawpos);data=base64.b64decode(payload,validate=True)
    assert 0<len(data)<=384 and hashlib.sha256(data).hexdigest().encode()==checksum
    if pos==total:
     assert total+len(data)<=count
     out.write(data);h.update(data);last=(pos,data);total+=len(data)
    else:assert last==(pos,data),'Unexpected offset'
    os.write(1,('SFACE_ACK %d\n'%total).encode())
   except Exception:os.write(1,('SFACE_NACK %d\n'%total).encode())
  out.flush();os.fsync(out.fileno())
 assert h.hexdigest()==expected,'Final hash mismatch'
 os.link(str(tmp),str(p));tmp.unlink()
 os.write(1,('SFACE_DONE %d %s\n'%(total,h.hexdigest())).encode());time.sleep(.3)
finally:termios.tcsetattr(fd,termios.TCSADRAIN,old)
'''
spec = importlib.util.spec_from_file_location('reviewed_uart', '/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
encoded = base64.b64encode(gzip.compress(receiver.encode(), mtime=0)).decode()
code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(encoded)+')))'
command = 'python3 -B -c '+shlex.quote(code)+' '+shlex.quote(bundle['destination'])+' '+str(len(blob))+' '+bundle['sha256']+' '+str(offset)+' '+info['sha256']
assert len(command.encode()) < 3800
out = ROOT/'evidence'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-resume-transfer')
out.mkdir(parents=True)
(out/'receiver.py').write_text(receiver)
status = {'complete': False, 'evidence': str(out), 'starting_offset': offset,
          'prefix_sha256': info['sha256'], 'bytes': len(blob), 'sha256': bundle['sha256'],
          'temporary_baud': 230400, 'frame_bytes': 384, 'retries': 0}
uart = None


def speed(value):
    attrs = termios.tcgetattr(uart.fd)
    attrs[4] = attrs[5] = value
    termios.tcsetattr(uart.fd, termios.TCSANOW, attrs)


try:
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart = mod.UART(raw)
            uart.connect()
            uart.line(command)
            assert uart.receive(10, re.compile(rb'(?m)^SFACE_SLOW_READY\r?$')), 'Receiver did not start'
            speed(termios.B230400)
            assert uart.receive(5, re.compile(rb'(?m)^SFACE_FAST_READY\r?$')), 'Baud handshake failed'
            start = last = time.monotonic()
            for pos in range(offset, len(blob), 384):
                chunk = blob[pos:pos+384]
                frame = b'\n'+str(pos).encode()+b' '+hashlib.sha256(chunk).hexdigest().encode()+b' '+base64.b64encode(chunk)+b'\n'
                for attempt in range(4):
                    uart.buf = b''
                    uart.write(frame)
                    if uart.receive(1, re.compile(rb'(?m)^SFACE_ACK '+str(pos+len(chunk)).encode()+rb'\r?$')):
                        break
                    status['retries'] += 1
                else:
                    raise RuntimeError('No acknowledgement at offset '+str(pos))
                time.sleep(.002)
                if time.monotonic()-last > 15:
                    status['acknowledged_bytes'] = pos+len(chunk)
                    print(json.dumps({'bytes': pos+len(chunk), 'total': len(blob), 'retries': status['retries'], 'elapsed_s': round(time.monotonic()-start, 1)}), flush=True)
                    (out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
                    last = time.monotonic()
            assert uart.receive(5, re.compile(rb'(?m)^SFACE_DONE '+str(len(blob)).encode()+b' '+bundle['sha256'].encode()+rb'\r?$')), 'Final checksum acknowledgement missing'
            speed(termios.B115200)
            uart.buf = b''
            if not uart.receive(3, mod.PROMPT):
                uart.write(b'\r')
                assert uart.receive(5, mod.PROMPT), 'Restored prompt missing'
            uart.shell_ready = True
            status.update(complete=True, acknowledged_bytes=len(blob), elapsed_s=time.monotonic()-start)
        finally:
            if uart:
                speed(termios.B115200)
                if not uart.shell_ready:
                    for _ in range(6):
                        uart.write(b'\r')
                        if uart.receive(5, mod.PROMPT):
                            uart.shell_ready = True
                            break
                status['console_echo_restored'] = uart.close()
except Exception as exc:
    status['error'] = str(exc)
(out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
(ROOT/'latest-resume-transfer.json').write_text(json.dumps(status, indent=2)+'\n')
print(json.dumps(status), flush=True)
raise SystemExit(0 if status['complete'] else 1)
