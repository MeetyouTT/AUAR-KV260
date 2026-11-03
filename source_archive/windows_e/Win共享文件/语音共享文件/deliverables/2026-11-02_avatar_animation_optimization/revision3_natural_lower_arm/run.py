from common import *
import argparse
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['probe','run','fetch']);p.add_argument('name');p.add_argument('label',nargs='?',default='');p.add_argument('args',nargs='*');p.add_argument('--timeout',type=int,default=50);a=p.parse_args()
 if a.mode=='probe':
  source=(HERE/a.name).read_text(encoding='utf8');result=json.loads(board(source,a.timeout));save(HERE/'validation'/(a.label+'.json'),result)
 elif a.mode=='run':
  s=load(HERE/'STAGE_INTENT.json')['stage'];raw=(HERE/a.name).read_bytes()
  if b'# IMPORT_DEVICE_READ_HEADER' in raw:raw=raw.replace(b'# IMPORT_DEVICE_READ_HEADER',(BASE/'device_read.py').read_bytes().split(b'raw=P.read_bytes();')[0])
  script='STAGE='+repr(s)+'\nNAME='+repr(a.name)+'\nDATA='+repr(base64.b64encode(raw).decode())+'\nARGS='+repr(a.args)+'\nTIMEOUT='+str(a.timeout)+'\n'+'''from pathlib import Path
import json,base64,subprocess
s=Path(STAGE);p=s/NAME;raw=base64.b64decode(DATA);p.parent.mkdir(parents=True,exist_ok=True)
if p.exists():assert p.read_bytes()==raw,'New code requires a new immutable stage filename'
else:p.write_bytes(raw)
r=subprocess.run(['python3','-B',str(p)]+ARGS,capture_output=True,timeout=TIMEOUT)
if r.returncode:raise RuntimeError((r.stderr+r.stdout).decode(errors='replace')[-5000:])
print(r.stdout.decode())
'''
  result=json.loads(board(script,a.timeout+12));save(HERE/'validation'/(a.label+'.json'),result)
 else:
  names=[a.name]+([a.label] if a.label else [])+a.args;s=load(HERE/'STAGE_INTENT.json')['stage']
  script='STAGE='+repr(s)+'\nNAMES='+repr(names)+'\n'+'''from pathlib import Path
import tarfile,sys
s=Path(STAGE)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 for name in NAMES:
  p=s/name;assert p.resolve().is_relative_to(s.resolve()) and not p.is_symlink()
  if p.is_dir():
   for q in sorted(p.rglob('*')):
    if q.is_file():t.add(q,arcname=str(q.relative_to(s)),recursive=False)
  else:t.add(p,arcname=name,recursive=False)
'''
  data=board(script,90);dest=HERE/'board_results';count=0
  with tarfile.open(fileobj=io.BytesIO(data)) as t:
   for m in t:
    rel=Path(m.name);assert m.isfile() and not rel.is_absolute() and '..' not in rel.parts
    p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True);raw=t.extractfile(m).read()
    if p.exists():assert p.read_bytes()==raw
    else:p.write_bytes(raw)
    count+=1
  result=dict(status='FETCHED',files=count,bytes=len(data));print(json.dumps(result));return
 print(json.dumps({k:v for k,v in result.items() if k not in ('component_sha256','samples','state_after','verified_original_native_inputs','steps')},ensure_ascii=False)[:10000])
if __name__=='__main__':main()
