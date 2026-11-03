"""Independent hidden parent for the authorized download and verified upgrade."""
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STORAGE=json.loads((ROOT/'aura/config/model_storage.local.json').read_text(encoding='utf-8-sig'))
started={}
for name,script in (
    ('download',Path(STORAGE['weights_directory'])/'download_model.py'),
    ('upgrade',HERE/'complete_27b_upgrade.py')):
    with (HERE/f'model_27b_{name}_stdout.log').open('a',encoding='utf-8') as output, \
         (HERE/f'model_27b_{name}_stderr.log').open('a',encoding='utf-8') as error:
        process=subprocess.Popen([sys.executable,'-B','-u',str(script)],cwd=ROOT,
            stdout=output,stderr=error,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        started[name]={'pid':process.pid,'script':str(script)}
(HERE/'model_27b_background_processes.json').write_text(json.dumps(started,indent=2),encoding='utf-8')
