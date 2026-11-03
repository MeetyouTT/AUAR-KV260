import os,sys,termios,tty,time,select,base64,hashlib
from pathlib import Path
p=Path(sys.argv[1]); expected=sys.argv[2]; count=int(sys.argv[3]); tmp=p.with_name(p.name+'.partial')
if p.exists() or tmp.exists(): raise SystemExit('Refusing existing image or partial file')
assert os.geteuid()==0 and os.uname().release=='5.15.36-xilinx-v2022.2'
assert Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
assert (p.parent/'baseline/original-zocl.ko').is_file()
assert (p.parent/'baseline/state.json').is_file()
assert Path('/sys/module/zocl/srcversion').read_text().strip()=='0991D1B457855C8987936E6'

saved=__import__('json').loads((p.parent/'baseline/state.json').read_text())
assert saved['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert hashlib.sha256(Path('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko').read_bytes()).hexdigest()=='215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d'
fd=sys.stdin.fileno(); old=termios.tcgetattr(fd); h=hashlib.sha256(); total=0; seq=0; pending=b''
try:
 tty.setraw(fd)
 with tmp.open('xb') as out:
  os.write(1,b'REPAIR_PACKAGE_READY\n')
  while total<count:
   until=time.monotonic()+20
   while b'\n' not in pending:
    if time.monotonic()>until: raise RuntimeError('Frame timeout')
    if select.select([fd],[],[],.2)[0]: pending+=os.read(fd,4096)
   line,pending=pending.split(b'\n',1); index,checksum,data=line.split(b' ',2)
   data=base64.b64decode(data,validate=True)
   if int(index)!=seq or hashlib.sha256(data).hexdigest().encode()!=checksum: raise RuntimeError('Bad frame')
   if total+len(data)>count: raise RuntimeError('Unexpected size')
   out.write(data); h.update(data); total+=len(data)
   os.write(1,('REPAIR_PACKAGE_ACK %d\n'%seq).encode()); seq+=1
  out.flush(); os.fsync(out.fileno())
 if h.hexdigest()!=expected: raise RuntimeError('Final hash mismatch')
 os.link(str(tmp),str(p)); tmp.unlink()
 os.write(1,('REPAIR_PACKAGE_DONE %d %s\n'%(total,h.hexdigest())).encode())
finally:
 termios.tcsetattr(fd,termios.TCSANOW,old)
