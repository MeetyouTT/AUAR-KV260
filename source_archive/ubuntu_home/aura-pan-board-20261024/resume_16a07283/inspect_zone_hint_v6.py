import json,subprocess
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');p=R/'face-zone-display-status.json'
unit=subprocess.check_output(['systemctl','show','aura-face-zone-editor.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','Result'],text=True).strip()
logs=subprocess.run(['journalctl','-u','aura-face-zone-editor.service','-n','20','--no-pager','-o','cat'],capture_output=True,text=True).stdout
print(json.dumps({'unit':unit,'display':json.loads(p.read_text()) if p.exists() else None,
 'error_lines':[x for x in logs.splitlines() if any(t in x for t in ('Traceback','Error','Exception','face_zone_editor.py','Failed'))]}))
