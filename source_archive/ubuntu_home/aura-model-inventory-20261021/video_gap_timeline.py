import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-video-cpu-20261023/0dad262102329bfc')
out={}
for unit in ('aura-video-trial-0dad262102329bfc.service','aura-video-restore-0dad262102329bfc.timer'):
 out[unit]=subprocess.check_output(['systemctl','show',unit,'-p','ExecMainStartTimestampMonotonic','-p','ExecMainExitTimestampMonotonic','-p','ActiveEnterTimestampMonotonic']).decode()
out['candidate_run_names']=[p.name for p in (root/'runtime/managed-runs').iterdir()]
out['clone_file_bytes']=sum(p.stat().st_size for p in (root/'runtime/aura').rglob('*') if p.is_file() and not p.is_symlink())
print(json.dumps(out))
