"""Two actual audio/content checks; expand only if both are intelligible."""
import json
import os
from pathlib import Path
import subprocess
import sys
from probe_streaming import request,TEXTS
from probe_cuda_variants import transcribe,normalize,distance

BASE=Path(__file__).resolve().parent
HERE=Path(os.environ['AURA_TTS_TRIAL_DIR'])
report={'status':'RUNNING','cases':[]}
for i,text in enumerate(TEXTS):
    row=request(text,chunk_tokens=25,name=f'quick-{i}')
    row['asr_text']=transcribe(row['wav'])
    row['character_error_rate']=distance(normalize(text),normalize(row['asr_text']))/len(normalize(text))
    report['cases'].append(row)
    (HERE/'quick_content.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
report['passed_content']=all(r['character_error_rate']<=.15 for r in report['cases'])
report['status']='CONTENT_SCREEN_PASSED' if report['passed_content'] else 'CONTENT_SCREEN_REJECTED'
(HERE/'quick_content.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if report['passed_content']:
    for script in ('probe_streaming.py','check_audio.py','probe_pipeline.py'):
        subprocess.run([sys.executable,'-B','-u',str(BASE/script)],check=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
        if script=='check_audio.py' and any(r['character_error_rate']>.15 for r in json.loads((HERE/'audio_content.json').read_text(encoding='utf-8'))['cases']):break
