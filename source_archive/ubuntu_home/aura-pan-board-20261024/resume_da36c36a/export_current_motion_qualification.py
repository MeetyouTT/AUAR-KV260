import json
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a')
refpath=R/'attended-fixed-reference.json';reference=json.loads(refpath.read_text())
trial=R/('fixed-trajectory-'+reference['authorization_id']+'.json');observer=trial.with_suffix('.preview-motion.json')
print(json.dumps({'reference':reference,'control_report':json.loads(trial.read_text()),'observer_report':json.loads(observer.read_text()),
 'paths':{'reference':str(refpath),'control_report':str(trial),'observer_report':str(observer)},'motor_commands':0,'MMIO_opened':False}))
