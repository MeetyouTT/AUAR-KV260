"""Create and independently verify the final release. Run on the Ubuntu workstation."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

pkg,qa,delivery,rar,viv,vit=map(Path,sys.argv[1:7])
implementation_run=sys.argv[7]
out=qa/sys.argv[8]
out.mkdir(exist_ok=False)
if delivery.exists():raise ValueError("Delivery destination already exists")
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def inventory(root):
 result={}
 for p in sorted(root.rglob('*')):
  if p.is_symlink():raise ValueError(str(p))
  if p.is_file():
   rel=p.relative_to(root).as_posix()
   if '\n' in rel or '\\' in rel:raise ValueError(rel)
   result[rel]=sha(p)
 return result
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
events=[]
env=os.environ.copy()
env.update(LC_ALL='C.UTF-8',LANG='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
def run(label,cmd,cwd):
 cmd=[str(x) for x in cmd];log=out/(label+'.log')
 with log.open('xb') as f:pr=subprocess.run(cmd,cwd=str(cwd),env=env,stdout=f,stderr=subprocess.STDOUT)
 events.append({'label':label,'exit_code':pr.returncode,'log_sha256':sha(log),'finished_utc':stamp()})
 if pr.returncode:raise RuntimeError(label+' failed; see '+str(log))
for p in pkg.rglob('*.sh'):
 if p.is_file():p.chmod(0o755)
before=inventory(pkg)
before.pop('checksums.sha256',None)
if not (pkg/'report/validation_summary.md').is_file():raise ValueError('Missing validation report')
(pkg/'checksums.sha256').write_text(''.join(h+'  '+rel+'\n' for rel,h in before.items()),encoding='utf-8')
source=inventory(pkg)
run('source-checksums',['sha256sum','--quiet','-c','checksums.sha256'],pkg)
arc=out/'auar_xuefei_source.rar'
run('rar-create',[rar,'a','-ma5','-m5','-r','-idq',arc,pkg.name],pkg.parent)
if arc.read_bytes()[:8]!=bytes.fromhex('526172211a070100') or not 0<arc.stat().st_size<200000000:raise ValueError('RAR5 signature or size')
run('rar-test',[rar,'t','-idq',arc],out)
extract=out/'expanded';extract.mkdir()
run('rar-extract',[rar,'x','-idq',arc,str(extract)+'/'],out)
if [p.name for p in extract.iterdir()]!=[pkg.name]:raise ValueError('Unexpected RAR roots')
tree=extract/pkg.name
if inventory(tree)!=source:raise ValueError('Extracted paths or bytes differ')
run('extracted-checksums',['sha256sum','--quiet','-c','checksums.sha256'],tree)
for stage in ['software','skill','rtl','prepare']:
 run('extracted-'+stage,[sys.executable,'-B',tree/'build/reproduce.py','--out',out/'regression','--stage',stage,'--vivado',viv/'bin/vivado','--vitis-root',vit],out)
run('extracted-skill-units',[sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],tree/'skill/pynq-contract-testgen')
run('extracted-model-inputs',[sys.executable,'-B',tree/'build/prepare_models.py','check'],tree)
run('extracted-sample',[sys.executable,'-B',tree/'build/check_assets.py'],tree)
run('extracted-board',[sys.executable,'-B',tree/'board/stage.py','board','--index',qa/'index02.json','--audio',qa/'reference-audio.zip','--out',out/'staged-board'],tree)
run('extracted-host',[sys.executable,'-B',tree/'board/stage.py','windows','--index',qa/'index02.json','--out',out/'staged-windows'],tree)
run('extracted-bench',[sys.executable,'-B',tree/'board/stage.py','bench','--index',qa/'index02.json','--out',out/'staged-bench'],tree)
run('extracted-bench-plan',[sys.executable,'-B',out/'staged-bench/bench_identity_stop.py'],out)
if inventory(tree)!=source:raise ValueError('A test changed files in the unpacked source')
staged=json.loads((out/'staged-board/stage_result.json').read_text())
if staged['exact_9a4f'] is not True or staged['audio_members_verified']!=15:raise ValueError('Final board byte gate failed')
validated=tree/'report/evidence/implementation_receipt.json'
receipt=json.loads(validated.read_text())
pins=receipt.get('hardware_source_sha256',{})
if not pins or any(source.get(n)!=v for n,v in pins.items()):
 raise ValueError('Extracted implementation inputs differ from those actually tested')
metrics=receipt.get('metrics',{})
if (receipt.get('status')!='PASS' or receipt.get('stage')!='margin_refinement'
    or metrics.get('wns_ns',-1)<0.020 or metrics.get('whs_ns',-1)<0.030
    or metrics.get('drc_errors',-1)!=0 or metrics.get('routing_errors',-1)!=0
    or metrics.get('original_clock_periods_preserved') is not True
    or metrics.get('original_user_uncertainty_restored') is not True):
 raise ValueError('Final archive does not meet the requested original-budget timing margins')
has=sha(arc)
result={'status':'PASS','created_utc':stamp(),'archive':'auar_xuefei_source.rar','format':'RAR5','sha256':has,'bytes':arc.stat().st_size,
        'single_root':pkg.name,'files':len(source),'uncompressed_file_bytes':sum((pkg/r).stat().st_size for r in source),
        'checksums_records':len(before),'paths_and_bytes_match':True,'hardware_input_sha_match':True,'implementation_stage_status':receipt['status'],'archive_roundtrip_steps':events,
        'source_implementation':str(qa/implementation_run),'timing':metrics,'required_setup_ns':0.020,'required_hold_ns':0.030,'board_staging':staged,'real_board':'NOT_RUN','receipts':str(out)}
# A presentation copy is made only after all archive tests pass.
delivery.mkdir(parents=True,exist_ok=False)
dest=delivery/arc.name
shutil.copyfile(str(arc),str(dest));assert sha(dest)==has
(delivery/'archive_verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
(delivery/'archive.sha256').write_text(has+'  '+arc.name+'\n')
shutil.copyfile(str(tree/'report/validation_summary.md'),str(delivery/'验证摘要.md'))
print(json.dumps(result,ensure_ascii=False),flush=True)
