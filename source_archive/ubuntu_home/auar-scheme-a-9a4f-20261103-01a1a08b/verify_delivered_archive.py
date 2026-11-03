
from pathlib import Path
import os,json,subprocess,sys,hashlib,datetime
q=Path(sys.argv[1]);w=q/'immediate-source-delivery';src=w/'expanded/auar_xuefei';dest=Path.home()/'下载/AUAR_工程包_9a4f';out=w/'rerun';out.mkdir(exist_ok=False)
viv=Path(sys.argv[2]);vit=Path(sys.argv[3]);receipts={}
actual=hashlib.sha256((dest/'auar_xuefei_source.rar').read_bytes()).hexdigest()
assert actual==json.loads((dest/'archive_verification.json').read_text())['sha256']
for name in ['software','skill','rtl','prepare']:
 prog=[sys.executable,'-B',str(src/'build/reproduce.py'),'--stage',name,'--out',str(out),'--vivado',str(viv/'bin/vivado'),'--vitis-root',str(vit)]
 with (w/('rerun-'+name+'.log')).open('xb') as log:r=subprocess.run(prog,cwd=str(w),stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError('Failed '+name)
 receipts[name]=json.loads((out/(name+'.receipt.json')).read_text())['status']
assert set(receipts.values())=={'PASS'}
rtl=json.loads((out/'rtl/result.json').read_text());assert len(rtl['tests'])==4
for test in rtl['tests']:assert len(test['stages'])==3 and all(s['exit_code']==0 for s in test['stages'])
m={'source_archive_sha256':actual,'stages_from_this_exact_extracted_archive':receipts,'rtl_exit_codes':{test['test']:{s['stage']:s['exit_code'] for s in test['stages']} for test in rtl['tests']},'fresh_project_validated':True,'outputs':str(out),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
tmp=dest/'Tcl复验写入中.tmp';tmp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');os.replace(str(tmp),str(dest/'Tcl解包复验.json'));print(json.dumps(m),flush=True)
