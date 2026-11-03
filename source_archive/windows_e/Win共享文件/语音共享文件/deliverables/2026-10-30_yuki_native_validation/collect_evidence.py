from pathlib import Path
import hashlib
import json
import os
import subprocess
import zipfile
root = Path('/home/root/aura-yuki-validation-20261030')
original = json.loads((root / 'input-sha256.json').read_text())
selected = {p:h for p,h in original.items() if p.startswith(('source/', 'deps/', 'inputs/'))}
changed = [p for p,h in selected.items() if hashlib.sha256((root/p).read_bytes()).hexdigest() != h]
workers = []
for p in Path('/proc').iterdir():
    if not p.name.isdigit() or int(p.name) == os.getpid(): continue
    try:
        command = (p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        if str(root) in command: workers.append({'pid':int(p.name),'command':command[:350]})
    except OSError: pass
current = subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','ExecStart','-p','DropInPaths'],text=True)
baseline = json.loads((root/'cpu-run-result.json').read_text())['before_ui']
report = {'protected_files_checked':len(selected),'protected_files_changed':changed,
          'ui_state_matches_baseline':current==baseline,'ui_service':current,
          'validation_workers':workers,'production_deployed':False,
          'binary_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                          [root/'build/yuki_runtime_audit',root/'build/yuki_runtime_mask_candidate',root/'build/yuki_frame_export']}}
(root/'final-state.json').write_text(json.dumps(report,indent=2))
names = ['cpu-audit.json','cpu-run-result.json','build.log','build-exception.json',
         'resume-launcher.log','candidate.log','candidate-cpu-audit.json','candidate-result.json',
         'capture.log','capture-result.json','gpu-render-r2.log','gpu-render-r2-result.json',
         'candidate-frames.json','final-state.json','static-reference-frames.json',
         'static-reference-result.json','static-reference-run.log']
with zipfile.ZipFile(root/'evidence-final.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in names:
        p=root/name
        if p.exists():archive.write(p,name)
    for directory in ['candidate-captures','static-reference-captures']:
        for p in sorted((root/directory).glob('*')):
            if p.is_file():archive.write(p,p.relative_to(root).as_posix())
print(json.dumps({k:v for k,v in report.items() if k not in ('ui_service','binary_hashes')},ensure_ascii=False))
print('evidence_zip_bytes',(root/'evidence-final.zip').stat().st_size)
