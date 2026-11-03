
import sys,subprocess,hashlib,json,shutil
from pathlib import Path
q,pkg,rar,vit,viv=map(Path,sys.argv[1:])
q.mkdir(exist_ok=False);expanded=q/'expanded';expanded.mkdir()
def inv(root):
 return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
def run(label,cmd,cwd):
 with (q/(label+'.log')).open('xb') as logfile:
  pr=subprocess.run([str(x) for x in cmd],cwd=str(cwd),stdout=logfile,stderr=subprocess.STDOUT)
 if pr.returncode:raise RuntimeError(label+' '+str(pr.returncode))
 return pr.returncode
src=inv(pkg);arc=q/'source-probe.rar'
run('rar-create',[rar,'a','-ma5','-m5','-r','-idq',arc,pkg.name],pkg.parent)
run('rar-test',[rar,'t','-idq',arc],q)
run('rar-extract',[rar,'x','-idq',arc,str(expanded)+'/'],q)
assert [p.name for p in expanded.iterdir()]==[pkg.name]
unpacked=expanded/pkg.name; assert inv(unpacked)==src
assert arc.stat().st_size<200_000_000
result={'phase':'internal pre-final roundtrip','files':len(src),'rar_bytes':arc.stat().st_size,'inventory_match':True}
(q/'archive.json').write_text(json.dumps(result,indent=2)); print(result,flush=True)
for stage in ('software','skill','rtl','prepare'):
 run(stage,[sys.executable,'-B',unpacked/'build/reproduce.py','--out',q/'run','--stage',stage,'--vivado',viv/'bin/vivado','--vitis-root',vit],q)
print('PASS four stages from an actual extraction',flush=True)
