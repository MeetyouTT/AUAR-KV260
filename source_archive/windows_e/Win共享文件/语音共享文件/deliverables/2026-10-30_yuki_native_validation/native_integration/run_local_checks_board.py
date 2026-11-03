from pathlib import Path
import json,subprocess
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration');rows=[]
for name in ('host/test_mailbox.py','host/test_preparation.py','test_ui_worker.py'):
    p=subprocess.run(['python3',str(phase/name)],capture_output=True,text=True,timeout=30)
    rows.append(dict(script=name,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
report=dict(status='PASS' if all(row['returncode']==0 for row in rows) else 'FAIL',tests=rows,production_deployed=False)
(phase/'results/adapter-tests.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
assert report['status']=='PASS'
