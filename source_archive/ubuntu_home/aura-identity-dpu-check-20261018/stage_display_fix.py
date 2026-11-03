"""Transfer only the reviewed display patch to an isolated board directory."""
import base64
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
D=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_display_startup_fix')
files={}
for folder in ('src','tests'):
 for p in sorted((D/folder).iterdir()):
  if p.is_file() and p.name!='xorg.conf.original':
   data=p.read_bytes()
   files[p.name]={'sha256':hashlib.sha256(data).hexdigest(),'base64':base64.b64encode(data).decode()}
packed=gzip.compress(json.dumps(files,sort_keys=True).encode(),mtime=0)
payload=base64.b64encode(packed).decode()
release='/home/root/aura-display-startup-fix-20261020/'+hashlib.sha256(packed).hexdigest()[:12]
spec=importlib.util.spec_from_file_location('wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
out=ROOT/'evidence'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-display-fix-stage')
out.mkdir(parents=True,mode=0o700)
status={'release':release,'complete':False,'commands':[]}
commands=[]
part=release+'/bundle.part'
common='import base64,gzip,hashlib,json,os\nfrom pathlib import Path\np=Path('+repr(part)+')\nassert Path("/sys/block/mmcblk1/device/cid").read_text().strip()=="0353445345333247805558c00401a100"\n'
commands.append(common+"p.parent.mkdir(parents=True,exist_ok=True)\nassert not p.exists()\nprint(json.dumps({'offset':0}))")
for start in range(0,len(payload),1400):
 chunk=payload[start:start+1400]
 commands.append(common+'assert (p.stat().st_size if p.exists() else 0)=='+str(start)+'\nwith p.open("ab") as f:f.write('+repr(chunk.encode())+');f.flush();os.fsync(f.fileno())\nprint(json.dumps({"offset":p.stat().st_size}))')
commands.append(common+'assert hashlib.sha256(p.read_bytes()).hexdigest()=='+repr(hashlib.sha256(payload.encode()).hexdigest())+'\nfiles=json.loads(gzip.decompress(base64.b64decode(p.read_bytes())))\nresult={}\nfor name,item in files.items():\n assert Path(name).name==name\n data=base64.b64decode(item["base64"]);assert hashlib.sha256(data).hexdigest()==item["sha256"]\n if name.endswith(".py"):compile(data,name,"exec")\n with (p.parent/name).open("xb") as f:f.write(data);f.flush();os.fsync(f.fileno())\n result[name]=item["sha256"]\nprint(json.dumps({"files":result}))')
encoded=[wire.wire(c) for c in commands]
uart=None
raw=None
try:
 raw=(out/'serial.raw').open('xb')
 if raw:
  uart=wire.transport_module().UART(raw);uart.connect()
  for i,command in enumerate(encoded):
   rc,data,sha=uart.command(command,'DF'+str(i).zfill(3),40)
   (out/('step-'+str(i)+'.output')).write_bytes(data)
   status['commands'].append({'step':i,'rc':rc,'sha256':sha})
   assert rc==0,data.decode(errors='replace')[-1000:]
   result=json.loads(data)
   print(json.dumps({'step':i,'total':len(encoded),'offset':result.get('offset')}),flush=True)
  assert result['files']=={n:d['sha256'] for n,d in files.items()}
  status['files']=result['files'];status['complete']=True
finally:
 try:
  if uart:status['console_echo_restored']=uart.close()
 finally:
  if raw:raw.close()
  (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
  (ROOT/'latest-display-fix-stage.json').write_text(json.dumps(dict(status,evidence=str(out)),indent=2)+'\n')
print(json.dumps(status),flush=True)
