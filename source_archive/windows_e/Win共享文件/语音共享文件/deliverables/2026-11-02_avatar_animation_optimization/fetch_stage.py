from device_host import *
import argparse
def main():
 p=argparse.ArgumentParser();p.add_argument('paths',nargs='+');a=p.parse_args();stage=load(HERE/'candidate_physics/STAGE_INTENT.json')['stage']
 remote='''import sys,tarfile
from pathlib import Path
s=Path(STAGE)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 for name in NAMES:
  p=s/name;assert p.resolve().is_relative_to(s.resolve()) and not p.is_symlink()
  if p.is_dir():
   for q in sorted(p.rglob('*')):
    if q.is_file():t.add(q,arcname=str(q.relative_to(s)),recursive=False)
  else:t.add(p,arcname=name,recursive=False)
'''.replace('STAGE',repr(stage)).replace('NAMES',repr(a.paths))
 r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=7','aura-kv260','python3 -B -'],input=remote.encode(),capture_output=True,timeout=90)
 assert r.returncode==0,r.stderr.decode(errors='replace')[-1500:]
 out=HERE/'board_results';out.mkdir(exist_ok=True);count=0
 with tarfile.open(fileobj=io.BytesIO(r.stdout),mode='r:') as t:
  for m in t:
   rel=Path(m.name);assert m.isfile() and not rel.is_absolute() and '..' not in rel.parts
   path=out/rel;path.parent.mkdir(parents=True,exist_ok=True);raw=t.extractfile(m).read()
   if path.exists():assert path.read_bytes()==raw
   else:path.write_bytes(raw)
   count+=1
 print(json.dumps(dict(files=count,bytes=len(r.stdout),directory=str(out))))
if __name__=='__main__':main()
