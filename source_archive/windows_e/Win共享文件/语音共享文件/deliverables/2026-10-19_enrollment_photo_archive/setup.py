from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ('aura/board/identity/sampling.py','aura/board/identity/live.py',
             'aura/board/identity/camera_faces.py','aura/config/board_identity.json'):
 target=HERE/'before'/name
 if target.exists():raise RuntimeError('Existing backup must be preserved')
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
old=HERE.parent/'2026-10-19_front_template_selection'
for name in ('prepare.py','preflight.py','activate_camera.py','verify.py','rollback.py','stop_for_reload.py','status.py'):
 raw=(old/name).read_text(encoding='utf-8').replace('/home/root/aura-front-template-20261019',
     '/home/root/aura-enrollment-photos-20261019')
 (HERE/name).write_text(raw,encoding='utf-8')
print('Backed up four files and prepared isolated camera release helpers.')
