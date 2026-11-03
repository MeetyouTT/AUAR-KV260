from inspect_baseline import *
import argparse,base64,tarfile,io,os
def board(script,timeout=45):
 r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=7','aura-kv260','python3 -B -'],input=script.encode(),capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError((r.stderr+r.stdout).decode(errors='replace')[-5000:])
 return r.stdout
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('script');p.add_argument('output');p.add_argument('--timeout',type=int,default=45);args=p.parse_args()
 hand=load(HERE/'DEVICE_HANDOFF.json');assert hand['permission_active'] and hand['exclusive_GUI_maintenance_holder']=='01a19efd-bb40-7f32-a6e4-a5f0cb59ffe8'
 source=(HERE/args.script).read_text(encoding='utf-8')
 if '# IMPORT_DEVICE_READ_HEADER' in source:
  source=source.replace('# IMPORT_DEVICE_READ_HEADER',(HERE/'device_read.py').read_text(encoding='utf8').split('raw=P.read_bytes();')[0])
 raw=board(source,args.timeout)
 v=json.loads(raw);save(HERE/args.output,v)
 print(json.dumps({k:x for k,x in v.items() if k not in ('component_sha256','gui_unit','camera_unit')},ensure_ascii=False)[:12000])
