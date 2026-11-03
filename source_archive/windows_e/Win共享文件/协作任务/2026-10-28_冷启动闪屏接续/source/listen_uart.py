"""Bounded passive console/bridge capture. Never sends UART bytes."""
import argparse,fcntl,glob,json,os,select,termios,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=180);p.add_argument('--label',required=True);p.add_argument('--interfaces',nargs='+',choices=['01','02'],default=['01','02']);a=p.parse_args()
assert 1<=a.seconds<=300 and a.label.replace('-','').isalnum()
root=Path(__file__).resolve().parent/'passive'/a.label;root.mkdir(parents=True,exist_ok=False,mode=0o700)
ports={};start=time.monotonic();report={'uart_bytes_sent':0,'power_down_seen':False,'linux_banner_seen':False,'ports':{}}
try:
 for interface in a.interfaces:
  paths=glob.glob('/dev/serial/by-id/usb-Xilinx_ML_Carrier_Card_*-if'+interface+'-port0');assert len(paths)==1
  resolved=os.path.realpath(paths[0])
  for proc in Path('/proc').iterdir():
   if not proc.name.isdigit() or proc.name==str(os.getpid()):continue
   try:others=list((proc/'fd').iterdir())
   except OSError:continue
   if any(os.path.realpath(q)==resolved for q in others):raise RuntimeError('UART already owned')
  fd=os.open(paths[0],os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  old=termios.tcgetattr(fd);attrs=termios.tcgetattr(fd);attrs[0]=attrs[1]=attrs[3]=0;attrs[2]=termios.CS8|termios.CREAD|termios.CLOCAL;attrs[4]=attrs[5]=termios.B115200;attrs[6][termios.VMIN]=attrs[6][termios.VTIME]=0;termios.tcsetattr(fd,termios.TCSANOW,attrs)
  out=(root/('if'+interface+'.raw')).open('xb');os.fchmod(out.fileno(),0o600)
  ports[fd]=(interface,old,out,bytearray());report['ports'][interface]={'bytes':0}
 while time.monotonic()-start<a.seconds:
  for fd in select.select(list(ports),[],[],.2)[0]:
   interface,old,out,buf=ports[fd]
   try:data=os.read(fd,16384)
   except OSError:continue
   if not data:continue
   out.write(data);out.flush();buf.extend(data);del buf[:-2048]
   with (root/'events.jsonl').open('a') as log:log.write(json.dumps({'elapsed_seconds':round(time.monotonic()-start,6),'interface':interface,'offset':report['ports'][interface]['bytes'],'bytes':len(data)})+'\n')
   report['ports'][interface]['bytes']+=len(data)
   if interface=='01':
    report['power_down_seen']|=b'Power down' in buf
    report['linux_banner_seen']|=b'Linux version' in buf
  report['elapsed_seconds']=round(time.monotonic()-start,2)
  (root/'status.json').write_text(json.dumps(report,indent=2)+'\n')
finally:
 for fd,(interface,old,out,buf) in ports.items():
  try:termios.tcsetattr(fd,termios.TCSANOW,old)
  except OSError:pass
  out.close();os.close(fd)
print(json.dumps(report))
