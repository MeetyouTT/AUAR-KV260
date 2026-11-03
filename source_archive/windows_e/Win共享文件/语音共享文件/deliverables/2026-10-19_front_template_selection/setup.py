"""Back up the active sampling implementation and prepare isolated release tools."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ('aura/board/identity/sampling.py','aura/board/identity/live.py',
             'aura/tests/framework/test_enrollment_sampling.py'):
 target=HERE/'before'/name
 if target.exists():raise RuntimeError('Preserve existing source backup')
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
old=HERE.parent/'2026-10-19_identity_query_routing'
for name in ('prepare.py','preflight.py','status.py','stop_for_reload.py'):
 raw=(old/name).read_text(encoding='utf-8').replace('/home/root/aura-spoken-identity-routing-20261019',
      '/home/root/aura-front-template-20261019')
 (HERE/name).write_text(raw,encoding='utf-8')
print('Saved sampling/live/tests sources; prepared isolated candidate helpers.')
