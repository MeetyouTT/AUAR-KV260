#!/usr/bin/env python3
"""Integrity-checked, exclusive UART staging; temporary 460800 baud, then 115200.

Only new files under /home/root/aura-adaptation-20261006 are permitted.
The receiver restores terminal settings on error and on its 20-second timeout.
No FPGA application, camera or system service is changed.
"""
import base64, datetime, gzip, hashlib, importlib.util, json, re, shlex, sys, termios, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/home/root/aura-adaptation-20261006/'
RECEIVER = r'''
import base64,hashlib,os,select,sys,termios,time,tty
from pathlib import Path
assert os.uname().machine=='aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
p=Path(sys.argv[1]);expected=sys.argv[2];count=int(sys.argv[3]);tmp=Path(str(p)+'.partial')
assert str(p).startswith('/home/root/aura-adaptation-20261006/') and '..' not in p.parts
assert not p.exists() and not tmp.exists(),'Destination already exists'
p.parent.mkdir(parents=True,exist_ok=True)
fd=0;old=termios.tcgetattr(fd);h=hashlib.sha256();total=seq=0;pending=b''
try:
 tty.setraw(fd)
 os.write(1,b'ADAPT_SLOW_READY\n');time.sleep(.2)
 attrs=termios.tcgetattr(fd);attrs[4]=attrs[5]=termios.B460800
 termios.tcsetattr(fd,termios.TCSADRAIN,attrs)
 for _ in range(3):os.write(1,b'ADAPT_FAST_READY\n');time.sleep(.3)
 with tmp.open('xb') as out:
  while total<count:
   until=time.monotonic()+20
   while b'\n' not in pending:
    if time.monotonic()>until:raise RuntimeError('Frame timeout')
    if select.select([fd],[],[],.1)[0]:pending+=os.read(fd,8192)
   line,pending=pending.split(b'\n',1);index,checksum,payload=line.split(b' ',2)
   payload=base64.b64decode(payload,validate=True)
   assert int(index)==seq and hashlib.sha256(payload).hexdigest().encode()==checksum,'Bad frame'
   assert total+len(payload)<=count
   out.write(payload);h.update(payload);total+=len(payload)
   os.write(1,('ADAPT_ACK %d\n'%seq).encode());seq+=1
  out.flush();os.fsync(out.fileno())
 assert h.hexdigest()==expected,'Final hash mismatch'
 os.link(str(tmp),str(p));tmp.unlink()
 os.write(1,('ADAPT_DONE %d %s\n'%(total,h.hexdigest())).encode());time.sleep(.3)
finally:
 termios.tcsetattr(fd,termios.TCSADRAIN,old)
'''

def speed(uart,value):
    attrs=termios.tcgetattr(uart.fd)
    attrs[4]=attrs[5]=value
    termios.tcsetattr(uart.fd,termios.TCSANOW,attrs)

def transfer(uart,source,dest):
    source=Path(source).resolve()
    assert ROOT in source.parents
    assert dest.startswith(REMOTE) and '..' not in Path(dest).parts
    data=source.read_bytes();digest=hashlib.sha256(data).hexdigest()
    code='import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(base64.b64encode(gzip.compress(RECEIVER.encode(),mtime=0)).decode())+')))'
    uart.line('python3 -B -c '+shlex.quote(code)+' '+shlex.quote(dest)+' '+digest+' '+str(len(data)))
    if not uart.receive(10,re.compile(rb'(?m)^ADAPT_SLOW_READY\r?$')):
        raise RuntimeError('Receiver did not start: '+dest)
    speed(uart,termios.B460800)
    if not uart.receive(5,re.compile(rb'(?m)^ADAPT_FAST_READY\r?$')):
        raise RuntimeError('Fast baud confirmation failed')
    started=time.monotonic();last=started
    for seq,pos in enumerate(range(0,len(data),768)):
        chunk=data[pos:pos+768]
        uart.buf=b''
        uart.write(str(seq).encode()+b' '+hashlib.sha256(chunk).hexdigest().encode()+b' '+base64.b64encode(chunk)+b'\n')
        if not uart.receive(10,re.compile(rb'(?m)^ADAPT_ACK '+str(seq).encode()+rb'\r?$')):
            raise RuntimeError('Missing ACK '+str(seq))
        if time.monotonic()-last>=15:
            print(json.dumps({'file':source.name,'bytes':min(pos+768,len(data)),'total':len(data),'elapsed_s':round(time.monotonic()-started,1)}),flush=True)
            last=time.monotonic()
    if not uart.receive(5,re.compile(rb'(?m)^ADAPT_DONE '+str(len(data)).encode()+b' '+digest.encode()+rb'\r?$')):
        raise RuntimeError('Missing final checksum')
    speed(uart,termios.B115200)
    uart.buf=b''
    if not uart.receive(5,re.compile(rb'(?m)^root@[^\r\n]+[#$] ')):
        uart.write(b'\r')
        if not uart.receive(5,re.compile(rb'(?m)^root@[^\r\n]+[#$] ')):
            raise RuntimeError('Restored-baud root prompt missing')
    uart.shell_ready=True
    return {'source':str(source),'destination':dest,'bytes':len(data),'sha256':digest,'elapsed_s':time.monotonic()-started}

def main():
    manifest=Path(sys.argv[1]).resolve();assert ROOT in manifest.parents
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out=ROOT/'evidence'/(stamp+'-transfer');out.mkdir()
    status={'results':[],'complete':False,'temporary_baud':460800,'restored_baud':115200,'frame_bytes':768,'evidence':str(out)}
    spec=importlib.util.spec_from_file_location('aura_uart','/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    uart=None
    with (out/'uart.raw').open('wb') as raw:
        try:
            uart=mod.UART(raw);uart.connect()
            for entry in json.loads(manifest.read_text()):
                assert hashlib.sha256(Path(entry['source']).read_bytes()).hexdigest()==entry['sha256']
                status['results'].append(transfer(uart,entry['source'],entry['destination']))
                (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
                print(json.dumps(status['results'][-1]),flush=True)
            status['complete']=True
        except Exception as exc:
            status['error']=str(exc)
        finally:
            if uart:
                speed(uart,termios.B115200)
                if not uart.shell_ready:
                    # Allow the receiver's bounded timeout/finally to restore baud.
                    for _ in range(6):
                        uart.write(b'\r')
                        if uart.receive(5,mod.PROMPT):uart.shell_ready=True;break
                status['console_echo_restored']=uart.close()
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    (ROOT/'CURRENT_TRANSFER.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)
    raise SystemExit(0 if status['complete'] else 1)
if __name__=='__main__':main()
