from common import *
import datetime
remote='/home/ghmd/auar-engineering-delivery-XpV7MC'
tag=datetime.datetime.now(datetime.timezone.utc).strftime('r%H%M%S')
session=remote+'/'+tag
save(W/'last_pack.json',{'session':session,'tag':tag})
with subprocess.Popen(['ssh','-o','BatchMode=yes','aura-ubuntu','mkdir -p '+session+'/input && tar -xf - -C '+session+'/input'],stdin=subprocess.PIPE)as p:
    with tarfile.open(fileobj=p.stdin,mode='w|')as tar:tar.add(ROOT,arcname='aura')
    p.stdin.close()
    if p.wait():raise RuntimeError('archive input transfer failed')
print('Pack input transferred',flush=True)
src=r"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,platform,shutil
q=Path.cwd(); rar=q.parent/'rar-tool/usr/bin/rar'; archive=q/'auar_kv260_engineering.rar'; ext=q/'extracted';logs=q/'logs';logs.mkdir();ext.mkdir()
def run(name,args,cwd=None,env=None):
    with (logs/(name+'.log')).open('wb')as out:
        p=subprocess.run([str(x) for x in args],cwd=str(cwd or q),env=env,stdout=out,stderr=subprocess.STDOUT)
    if p.returncode:
        print(name,'failed', (logs/(name+'.log')).read_text(errors='replace')[-1000:],flush=True);sys.exit(p.returncode)
    print(name+' PASS',flush=True)
env=dict(os.environ,LANG='C.UTF-8',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1')
run('create_rar',[rar,'a','-ma5','-m4','-mt2','-idq',archive,'aura'],q/'input')
size=archive.stat().st_size
if size>=200000000:raise RuntimeError('RAR size limit: '+str(size))
run('test_rar',[rar,'t','-idq',archive])
run('extract_rar',[rar,'x','-idq',archive,str(ext)+'/'])
aff=min(os.sched_getaffinity(0));prefix=['taskset','-c',str(aff),sys.executable,'-B']
run('extracted_single_core',prefix+['build/scripts/reproduce.py','--out',q/'qa'],ext/'aura',env)
run('stage_rootfs',prefix+['board/scripts/stage.py','--out',q/'rootfs'],ext/'aura',env)
run('host_unit',prefix+['-m','unittest','test_production_runtime','-v'],ext/'aura/src/windows/deliverables/2026-10-30_board_owner/integration/production_model_host',env)
run('release_after_read',prefix+['build/scripts/verify.py'],ext/'aura',env)
r={'package':archive.name,'format':'RAR5','bytes':size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'contents':sum(p.is_file() for p in (ext/'aura').rglob('*')),'roots':['aura'],'python':platform.python_version(),'cpu_affinity':1,'rar_test':'PASS','verify_after_unpack':'PASS','rootfs_stage_without_audio':'PASS','suite':json.loads((q/'qa/summary.json').read_text())}
(q/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print('ready',size,flush=True)
"""
r=subprocess.run(['ssh','-o','BatchMode=yes','aura-ubuntu','cd '+session+' && python3 -'],input=src.encode(),stdout=None,stderr=None)
if r.returncode:sys.exit(r.returncode)
dest=OUT/'auar_kv260_engineering.rar'
temp=OUT/('archive_'+tag+'.partial')
def get(rempath,local):subprocess.run(['scp','-q','aura-ubuntu:'+session+'/'+rempath,str(local)],check=True)
get('receipt.json',QA/'release_receipt.json')
receipt=load(QA/'release_receipt.json')
get('auar_kv260_engineering.rar',temp)
if sha(temp)!=receipt['sha256'] or temp.stat().st_size!=receipt['bytes']:raise RuntimeError('RAR transfer verification failed')
temp.replace(dest)
for n in ['stage_rootfs','host_unit','extracted_single_core','release_after_read']:get('logs/'+n+'.log',QA/(n+'.txt'))
for n in ['motion_fixture','skill_a','skill_b','skill_c','pynq_unit','pynq_examples']:get('qa/'+n+'.log',QA/(n+'.txt'))
print('E drive RAR verified',receipt['sha256'])
