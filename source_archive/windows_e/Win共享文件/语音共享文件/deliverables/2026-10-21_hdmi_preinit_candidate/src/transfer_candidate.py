"""Transfer only the completed candidate archive to an isolated board directory."""
import base64
import gzip
import hashlib
import importlib.util
import json
import re
import shlex
import termios
import time
from datetime import datetime, timezone
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
BOOT = '5cd17bb7-30da-4a4f-bf18-8167508de1f4'
RECEIVER = r'''
import base64,hashlib,os,select,sys,termios,time,tty
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==sys.argv[4]
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
p=Path(sys.argv[1]);count=int(sys.argv[2]);expected=sys.argv[3]
assert str(p).startswith('/home/root/aura-hdmi-preinit-20261021/') and p.name=='Image.gz'
assert '..' not in p.parts and not p.exists() and not p.is_symlink()
p.parent.mkdir(parents=True,exist_ok=True);assert not p.parent.is_symlink()
tmp=Path(str(p)+'.partial');assert not tmp.exists() and not tmp.is_symlink()
h=hashlib.sha256();total=0;pending=b'';last=None;fd=0;old=termios.tcgetattr(fd)
try:
 tty.setraw(fd);os.write(1,b'AURA_SLOW_READY\n');time.sleep(.2)
 attrs=termios.tcgetattr(fd);attrs[4]=attrs[5]=termios.B230400
 termios.tcsetattr(fd,termios.TCSADRAIN,attrs)
 for _ in range(3):os.write(1,b'AURA_FAST_READY\n');time.sleep(.2)
 with tmp.open('xb') as out:
  while total<count:
   until=time.monotonic()+20
   while b'\n' not in pending:
    if time.monotonic()>until:raise RuntimeError('Frame timeout')
    if select.select([fd],[],[],.1)[0]:pending+=os.read(fd,8192)
   line,pending=pending.split(b'\n',1)
   if not line:continue
   try:
    rawpos,checksum,payload=line.split(b' ',2);pos=int(rawpos);data=base64.b64decode(payload,validate=True)
    assert 0<len(data)<=3072 and hashlib.sha256(data).hexdigest().encode()==checksum
    if pos==total:
     assert total+len(data)<=count
     out.write(data);h.update(data);last=(pos,data);total+=len(data)
    else:assert last==(pos,data),'Unexpected offset'
    os.write(1,('AURA_ACK %d\n'%total).encode())
   except Exception:os.write(1,('AURA_NACK %d\n'%total).encode())
  out.flush();os.fsync(out.fileno())
 assert h.hexdigest()==expected,'Final hash mismatch'
 os.link(str(tmp),str(p));tmp.unlink()
 os.write(1,('AURA_DONE %d %s\n'%(total,h.hexdigest())).encode());time.sleep(.3)
finally:termios.tcsetattr(fd,termios.TCSADRAIN,old)
'''


def main():
    build = json.loads((PACKAGE/'evidence/kernel-build.json').read_text())
    assert build['completed'] and not build['board_deployed']
    source = PACKAGE/'artifacts/Image.gz'
    blob = source.read_bytes()
    data = gzip.decompress(blob)
    assert hashlib.sha256(data).hexdigest() == build['image_sha256']
    digest = hashlib.sha256(blob).hexdigest()
    dest = '/home/root/aura-hdmi-preinit-20261021/'+build['source_sha256'][:16]+'/Image.gz'
    spec = importlib.util.spec_from_file_location('reviewed_uart', '/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
    mod = importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    encoded = base64.b64encode(gzip.compress(RECEIVER.encode(),mtime=0)).decode()
    code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(encoded)+')))'
    command = 'python3 -B -c '+shlex.quote(code)+' '+shlex.quote(dest)+' '+str(len(blob))+' '+digest+' '+BOOT
    assert len(command.encode()) < 3800
    out = Path('/home/ghmd/aura-identity-dpu-check-20261018/evidence')/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-hdmi-kernel-transfer')
    out.mkdir(parents=True)
    status = dict(complete=False,source=str(source),destination=dest,evidence=str(out),
                  bytes=len(blob),sha256=digest,temporary_baud=230400,
                  frame_bytes=3072,retries=0,active_boot_files_changed=False)
    uart = None
    def speed(value):
        a=termios.tcgetattr(uart.fd);a[4]=a[5]=value
        termios.tcsetattr(uart.fd,termios.TCSANOW,a)
    try:
        with (out/'serial.raw').open('xb') as raw:
            try:
                uart=mod.UART(raw);uart.connect();uart.line(command)
                assert uart.receive(10,re.compile(rb'(?m)^AURA_SLOW_READY\r?$'))
                speed(termios.B230400)
                assert uart.receive(5,re.compile(rb'(?m)^AURA_FAST_READY\r?$'))
                start=last=time.monotonic()
                for pos in range(0,len(blob),3072):
                    chunk=blob[pos:pos+3072]
                    frame=b'\n'+str(pos).encode()+b' '+hashlib.sha256(chunk).hexdigest().encode()+b' '+base64.b64encode(chunk)+b'\n'
                    for attempt in range(4):
                        uart.buf=b'';uart.write(frame)
                        if uart.receive(2,re.compile(rb'(?m)^AURA_ACK '+str(pos+len(chunk)).encode()+rb'\r?$')):break
                        if b'U-Boot' in uart.buf or b'Booting Linux' in uart.buf:
                            raise RuntimeError('Board rebooted during transfer; stop sending')
                        status['retries']+=1
                    else:raise RuntimeError('No acknowledgement at offset '+str(pos))
                    if time.monotonic()-last>15:
                        status.update(acknowledged_bytes=pos+len(chunk),elapsed_s=round(time.monotonic()-start,1))
                        (PACKAGE/'evidence/transfer.json').write_text(json.dumps(status,indent=2)+'\n')
                        print(json.dumps({k:status[k] for k in ['acknowledged_bytes','bytes','retries','elapsed_s']}),flush=True)
                        last=time.monotonic()
                assert uart.receive(5,re.compile(rb'(?m)^AURA_DONE '+str(len(blob)).encode()+b' '+digest.encode()+rb'\r?$'))
                speed(termios.B115200);uart.buf=b''
                assert uart.receive(5,mod.PROMPT),'Restored prompt missing'
                uart.shell_ready=True
                status.update(complete=True,acknowledged_bytes=len(blob),elapsed_s=round(time.monotonic()-start,1))
            finally:
                if uart:
                    if not uart.shell_ready:
                        # The receiver restores the original speed on its 20s
                        # idle timeout. Do not send CR into a possible reboot.
                        uart.receive(22)
                    speed(termios.B115200)
                    if not uart.shell_ready:uart.shell_ready=uart.receive(4,mod.PROMPT)
                    status['console_echo_restored']=uart.close()
    except Exception as exc:
        status['error']=str(exc)
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    (PACKAGE/'evidence/transfer.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)
    if not status['complete']:raise SystemExit(1)


if __name__=='__main__':main()
