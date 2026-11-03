from device_host import *
import argparse
def main():
 p=argparse.ArgumentParser();p.add_argument('script');p.add_argument('label');p.add_argument('arguments',nargs='*');p.add_argument('--timeout',type=int,default=55);a=p.parse_args()
 stage=load(HERE/'candidate_physics/STAGE_INTENT.json')['stage']
 source=(HERE/a.script).read_text(encoding='utf8')
 if '# IMPORT_DEVICE_READ_HEADER' in source:source=source.replace('# IMPORT_DEVICE_READ_HEADER',(HERE/'device_read.py').read_text(encoding='utf8').split('raw=P.read_bytes();')[0])
 raw=source.encode();encoded=base64.b64encode(raw).decode()
 remote='''from pathlib import Path
import json,base64,subprocess,hashlib
s=Path(STAGE);p=s/NAME;raw=base64.b64decode(DATA)
if p.exists():assert p.read_bytes()==raw,'Stage script changed; choose a new filename'
else:
 with p.open('xb') as f:f.write(raw)
r=subprocess.run(['python3','-B',str(p)]+ARGS,capture_output=True,timeout=TIMEOUT)
if r.returncode:raise RuntimeError((r.stderr+r.stdout).decode(errors='replace')[-5000:])
print(r.stdout.decode())
'''.replace('STAGE',repr(stage)).replace('NAME',repr(a.script)).replace('DATA',repr(encoded)).replace('ARGS',repr(a.arguments)).replace('TIMEOUT',str(a.timeout))
 save(HERE/'validation'/('INTENT_'+a.label+'.json'),dict(stage=stage,script=a.script,script_sha256=hashlib.sha256(raw).hexdigest(),args=a.arguments))
 result=json.loads(board(remote,timeout=a.timeout+12));save(HERE/'validation'/(a.label+'.json'),result)
 print(json.dumps({k:v for k,v in result.items() if k not in ('samples','records','steps','verified_original_native_inputs')},ensure_ascii=False))
if __name__=='__main__':main()
