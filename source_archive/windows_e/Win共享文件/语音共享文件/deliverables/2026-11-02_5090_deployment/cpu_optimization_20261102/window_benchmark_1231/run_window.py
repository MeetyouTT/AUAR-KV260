import argparse,datetime,hashlib,importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('script',type=Path);p.add_argument('output',type=Path)
p.add_argument('--expected',type=Path);p.add_argument('--include-gtk',action='store_true')
p.add_argument('--timeout',type=int,default=25);p.add_argument('--site',action='store_true')
p.add_argument('--args',default='');a=p.parse_args()
assert not a.output.exists()
source=a.script.read_text(encoding='utf-8');code=''
if a.expected:code+='EXPECTED = '+repr(json.loads(a.expected.read_text(encoding='utf-8')))+'\n'
if a.include_gtk:
    raw=(ROOT/'gtk/v2/transaction_preview_projection.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='e1b5384bc2abe2aaf957792a316ddca3a1d854aafcc4b06290e75a1b3393e3ed'
    code+='GTK_SOURCE = '+repr(raw.decode())+'\n'
code+=source
compile(code,'<cpu-window>','exec')
helper=ROOT.parent.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('cpu_window_ssh',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
command='/usr/bin/python3 -B -I '+('' if a.site else '-S ')+'- '+a.args
result=json.loads(module.ssh(command,code,timeout=a.timeout))
with a.output.open('x',encoding='utf-8') as f:json.dump({'host_started_utc':start,'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256_lf':hashlib.sha256(code.encode()).hexdigest(),'board_result':result},f,indent=2);f.write('\n')
print(json.dumps({'output':str(a.output),'status':result.get('status'),'startup_sha256':result.get('startup_sha256'),'components_verified':result.get('components_verified')}))
