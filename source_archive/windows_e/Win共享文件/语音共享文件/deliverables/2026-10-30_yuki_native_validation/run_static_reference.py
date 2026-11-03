from pathlib import Path
import json
import subprocess
root = Path('/home/root/aura-yuki-validation-20261030')
before = subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True)
result={'experimental':True,'production_accepted':False,'steps':[]}
with (root/'static-reference-run.log').open('w') as log:
    for argv in [
        ['nice','-n','15',str(root/'build/yuki_frame_export'),str(root/'inputs/ems/yuk_0.ems.json'),str(root/'inputs/ems/yuk_0.ems.resx.json'),str(root/'probe_build/scenario-static-reference.json'),str(root/'static-reference-frames.json'),'--resource-root',str(root/'inputs/ems')],
        ['nice','-n','15','python3',str(root/'probe_build/gles2_capture.py'),str(root/'static-reference-frames.json'),str(root/'static-reference-captures')]]:
        p=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=60)
        result['steps'].append({'argv':argv,'returncode':p.returncode})
        if p.returncode:break
after = subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True)
result['ui_unchanged']=before==after
(root/'static-reference-result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
print((root/'static-reference-run.log').read_text()[-2500:])
