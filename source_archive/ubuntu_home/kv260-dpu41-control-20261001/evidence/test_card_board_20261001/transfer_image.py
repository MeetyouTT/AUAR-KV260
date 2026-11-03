#!/usr/bin/env python3
"""Transfer the fixed JPEG to an independent board directory using acknowledged UART frames."""
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shlex
import termios
import time

root = Path(__file__).resolve().parent
source = root.parent.parent / 'downloads/pytorch-resnet-dog.jpg'
expected = 'f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a'
dest = '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg'
payload = source.read_bytes()
if hashlib.sha256(payload).hexdigest() != expected:
    raise SystemExit('Unexpected source image hash')
raw_path = root / '18-image-transfer.serial.raw'
result_path = root / '18-image-transfer.result.json'
if raw_path.exists() or result_path.exists():
    raise SystemExit('Refusing to overwrite existing evidence')
board_code = '''import os,sys,termios,tty,time,select,base64,hashlib
from pathlib import Path
p=Path(sys.argv[1]); expected=sys.argv[2]; count=int(sys.argv[3]); tmp=p.with_suffix('.jpg.partial')
if p.exists() or tmp.exists(): raise SystemExit('Refusing existing image or partial file')
p.parent.mkdir(parents=True,exist_ok=True)
fd=sys.stdin.fileno(); old=termios.tcgetattr(fd); h=hashlib.sha256(); total=0; seq=0; pending=b''
try:
 tty.setraw(fd)
 with tmp.open('xb') as out:
  os.write(1,b'IMAGE_READY\\n')
  while total<count:
   until=time.monotonic()+20
   while b'\\n' not in pending:
    if time.monotonic()>until: raise RuntimeError('Frame timeout')
    if select.select([fd],[],[],.2)[0]: pending+=os.read(fd,4096)
   line,pending=pending.split(b'\\n',1); index,checksum,data=line.split(b' ',2)
   data=base64.b64decode(data,validate=True)
   if int(index)!=seq or hashlib.sha256(data).hexdigest().encode()!=checksum: raise RuntimeError('Bad frame')
   if total+len(data)>count: raise RuntimeError('Unexpected size')
   out.write(data); h.update(data); total+=len(data)
   os.write(1,('IMAGE_ACK %d\\n'%seq).encode()); seq+=1
  out.flush(); os.fsync(out.fileno())
 if h.hexdigest()!=expected: raise RuntimeError('Final hash mismatch')
 os.link(str(tmp),str(p)); tmp.unlink()
 listing=p.parent/'samoyed.list'; text=str(p)+'\\n'
 if listing.exists():
  if listing.read_text()!=text: raise RuntimeError('Existing list differs')
 else:
  with listing.open('x') as f: f.write(text)
 os.write(1,('IMAGE_DONE %d %s\\n'%(total,h.hexdigest())).encode())
finally:
 termios.tcsetattr(fd,termios.TCSANOW,old)
'''
wire = 'python3 -B -c ' + shlex.quote(board_code) + ' ' + shlex.quote(dest) + ' ' + expected + ' ' + str(len(payload))
port = '/dev/serial/by-id/usb-Xilinx_ML_Carrier_Card_XFL1EMEBC1R5-if01-port0'
fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
old = termios.tcgetattr(fd)
attrs = termios.tcgetattr(fd)
attrs[0] = attrs[1] = attrs[3] = 0
attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
attrs[4] = attrs[5] = termios.B115200
attrs[6][termios.VMIN] = attrs[6][termios.VTIME] = 0
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
record = {'started_utc': started, 'source': str(source), 'destination': dest,
          'bytes': len(payload), 'expected_sha256': expected, 'board_code': board_code,
          'complete': False, 'frames_acknowledged': 0}
buffer = b''
with raw_path.open('xb') as raw:
 def read_for(seconds, pattern=None):
  global buffer
  end = time.monotonic() + seconds
  while time.monotonic() < end:
   if pattern and pattern.search(buffer): return True
   if select.select([fd], [], [], .01)[0]:
    part = os.read(fd,32768)
    raw.write(part); raw.flush(); buffer += part
  return bool(pattern and pattern.search(buffer))
 def write_all(data):
  view = memoryview(data)
  while view:
   if not select.select([], [fd], [], 5)[1]: raise RuntimeError('UART write timeout')
   n = os.write(fd, view[:256]); view = view[n:]
 try:
  termios.tcsetattr(fd,termios.TCSANOW,attrs)
  time.sleep(.4); write_all(b'\r')
  prompt = re.compile(rb'root@[^\r\n]+:[^\r\n]*# $')
  if not read_for(5,prompt): raise RuntimeError('Root prompt not confirmed')
  buffer = b''
  # Multiline quoted input is paced at approximately 100 bytes/s.
  for line in wire.splitlines():
   data = line.encode()+b'\r'
   for pos in range(0,len(data),4):
    write_all(data[pos:pos+4]); read_for(.04)
  if not read_for(10,re.compile(rb'(?m)^IMAGE_READY\r?$')):
   raise RuntimeError('Image receiver did not start')
  print('Board receiver ready; transferring image',flush=True)
  for index,pos in enumerate(range(0,len(payload),768)):
   chunk=payload[pos:pos+768]
   frame=str(index).encode()+b' '+hashlib.sha256(chunk).hexdigest().encode()+b' '+base64.b64encode(chunk)+b'\n'
   buffer=b''; write_all(frame)
   if not read_for(10,re.compile(rb'(?m)^IMAGE_ACK '+str(index).encode()+rb'\r?$')):
    raise RuntimeError('Missing frame acknowledgement '+str(index))
   record['frames_acknowledged']=index+1
   if (index+1)%100==0: print('Frames acknowledged:',index+1,flush=True)
  done=re.compile(rb'(?m)^IMAGE_DONE '+str(len(payload)).encode()+b' '+expected.encode()+rb'\r?$')
  if not read_for(10,done): raise RuntimeError('Missing final hash confirmation')
  if not read_for(5,prompt): raise RuntimeError('Receiver finished without shell prompt')
  record['complete']=True
 except Exception as exc:
  record['error']=str(exc)
  print('Transfer stopped:',exc,flush=True)
 finally:
  termios.tcsetattr(fd,termios.TCSANOW,old); os.close(fd)
  record['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
  result_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='board_code'},ensure_ascii=False),flush=True)
raise SystemExit(0 if record['complete'] else 1)
