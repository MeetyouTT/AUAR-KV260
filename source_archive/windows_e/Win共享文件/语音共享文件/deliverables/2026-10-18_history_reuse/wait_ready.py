"""Confirm the actual model service loaded this version before profiling it."""
import json
from pathlib import Path
import time
import urllib.request

HERE=Path(__file__).resolve().parent
deadline=time.monotonic()+160;last_error=''
while time.monotonic()<deadline:
    try:
        with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as response:health=json.load(response)
        if (health['ready'] and health.get('latency_options')=={'reply_first':True,'early_sentence':True,'coalesce_chat':True,'reuse_history':True}
                and health['thinking_feedback_ready'] and not health['busy']):
            (HERE/'host_ready.json').write_text(json.dumps(health,indent=2),encoding='utf-8')
            print(json.dumps(health));break
    except Exception as exc:last_error=str(exc)
    time.sleep(.5)
else:raise SystemExit('Model service did not become ready: '+last_error)
