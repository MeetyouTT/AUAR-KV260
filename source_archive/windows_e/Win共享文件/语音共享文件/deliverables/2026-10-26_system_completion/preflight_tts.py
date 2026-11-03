"""Real existing-voice warmup with bounded diagnostics; no audio playback."""
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(AURA))
from tools.selected_voice_service import VoiceWorker

root=HERE/'tts_preflight'
worker=VoiceWorker(root,python=sys.executable,model_path=AURA/'models/tts/OmniVoice',engine='omnivoice')
original=worker._worker_command()
wrapper="import faulthandler,runpy,sys;faulthandler.dump_traceback_later(45,repeat=True);script=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(script,run_name='__main__')"
worker.transport.command=lambda:original[:3]+['-c',wrapper]+original[3:]
started=time.monotonic()
try:
    worker.warmup(timeout=240)
    value={'ready':worker.ready,'error':worker.error,'elapsed_seconds':time.monotonic()-started,
        'health':worker.health(),'model_unchanged':True,'voice_unchanged':True,
        'microphone_opened':False,'playback_started':False}
finally:
    worker.close()
(HERE/'tts_preflight.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value,ensure_ascii=False))
raise SystemExit(0 if value['ready'] else 1)
