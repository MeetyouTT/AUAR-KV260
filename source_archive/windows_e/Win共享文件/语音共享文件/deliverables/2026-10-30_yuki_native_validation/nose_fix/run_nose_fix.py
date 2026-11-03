from pathlib import Path
import hashlib
import json
import subprocess
import time
import zipfile

ROOT=Path('/home/root/aura-yuki-validation-20261030')


def ui():
    return subprocess.check_output(['systemctl','show','aura-avatar-ui.service',
                                     '-p','MainPID','-p','ActiveState','-p','ExecStart','-p','DropInPaths'],text=True)


report={'before_ui':ui(),'production_deployed':False,'steps':[]}
started=time.monotonic()
with (ROOT/'nose-fix-run.log').open('w') as log:
    commands=[
        ['nice','-n','15','python3',str(ROOT/'nose_fix/test_color_protection.py')],
        ['nice','-n','15','python3',str(ROOT/'probe_build/gles2_capture.py'),str(ROOT/'candidate-frames.json'),str(ROOT/'nose-fix-captures')],
        ['nice','-n','15','python3',str(ROOT/'probe_build/gles2_capture.py'),str(ROOT/'static-reference-frames.json'),str(ROOT/'nose-fix-static')]]
    for argv in commands:
        log.write(json.dumps(argv)+'\n');log.flush()
        stage=time.monotonic()
        p=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=90)
        report['steps'].append({'argv':argv,'returncode':p.returncode,'elapsed_seconds':time.monotonic()-stage})
        if p.returncode:break
report['after_ui']=ui();report['ui_unchanged']=report['before_ui']==report['after_ui']
report['elapsed_seconds']=time.monotonic()-started
report['renderer_sha256']=hashlib.sha256((ROOT/'probe_build/gles2_capture.py').read_bytes()).hexdigest()
report['ok']=len(report['steps'])==3 and all(s['returncode']==0 for s in report['steps'])
original=json.loads((ROOT/'input-sha256.json').read_text())
checked={p:h for p,h in original.items() if p.startswith(('source/','deps/','inputs/'))}
report['protected_files_checked']=len(checked)
report['protected_files_changed']=[p for p,h in checked.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
(ROOT/'nose-fix-run-result.json').write_text(json.dumps(report,indent=2))
with zipfile.ZipFile(ROOT/'nose-fix-evidence.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in ['nose-fix-run.log','nose-fix-run-result.json']:
        archive.write(ROOT/name,name)
    for directory in ['nose-fix-tests','nose-fix-captures','nose-fix-static']:
        folder=ROOT/directory
        if folder.exists():
            for path in sorted(folder.glob('*')):
                if path.is_file():archive.write(path,path.relative_to(ROOT).as_posix())
print(json.dumps({k:v for k,v in report.items() if k not in ('before_ui','after_ui')}))
print((ROOT/'nose-fix-run.log').read_text()[-2500:])
