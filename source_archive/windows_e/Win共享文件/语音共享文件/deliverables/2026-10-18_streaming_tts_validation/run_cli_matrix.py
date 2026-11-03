"""Use verified CLI settings; keep one original-service downtime for two variants."""
import json
import os
from pathlib import Path
import subprocess
import sys

BASE=Path(__file__).resolve().parent
HERE=Path(os.environ['AURA_TTS_TRIAL_DIR'])
for name,flash in (('f16_no_flash',False),('f16_flash',True)):
    folder=HERE/name;folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,AURA_TTS_TRIAL_DIR=str(folder),AURA_TTS_QUICK_CONTENT='1',AURA_TTS_VARIANTS='0',AURA_TTS_EXPECT_FLASH=str(int(flash)))
    env['AURA_TTS_EXTRA_ARGS']=json.dumps(['--llm-kv-cache-type','f16','--dit-kv-cache-type','f16','--llm-flash-attn',str(int(flash)),'--flow-flash-attn',str(int(flash))])
    with (folder/'controller.log').open('w',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,'-B','-u',str(BASE/'run_candidate.py')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps({'variant':name,'returncode':result.returncode,'output':str(folder)}),flush=True)
