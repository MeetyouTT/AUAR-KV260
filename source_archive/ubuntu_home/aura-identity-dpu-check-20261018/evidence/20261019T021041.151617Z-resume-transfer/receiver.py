
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
