import hashlib,json,subprocess
from pathlib import Path
startup=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup')
cfg=json.loads((startup/'config.json').read_bytes());runtime=Path(cfg['runtime'])
out=dict(schema='aura-named-reply-display-startup-readonly-1',control_writes=0)
out['stage_log']=(runtime/'stage.log').read_text(errors='replace')[-16000:]
out['launcher_source']=(startup/'launcher.py').read_text(errors='replace')
r=subprocess.run(['journalctl','-b','--unit=aura-avatar-ui.service','--no-pager','-o','cat','-n','40'],capture_output=True,text=True,timeout=5)
out['journal']=r.stdout
out['drm']={p.name:{n:(p/n).read_text(errors='replace')[:1500] for n in ('status','enabled','modes') if (p/n).is_file()} for p in Path('/sys/class/drm').glob('card*-*')}
print(json.dumps(out))
