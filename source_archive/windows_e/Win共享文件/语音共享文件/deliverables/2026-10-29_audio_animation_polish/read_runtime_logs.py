"""Bounded audio stderr and performance metadata; no microphone data."""
import json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
b=json.loads((H/'baseline.json').read_text(encoding='utf-8'))
process=next(row for row in b['processes'] if '--evidence-root' in row['arguments'])
args=process['arguments'];evidence=args[args.index('--evidence-root')+1]
script=r'''
import json,re,urllib.request
from pathlib import Path
root=Path(EVIDENCE)
audio=root/'audio_worker.log'
lines=audio.read_bytes()[-32768:].decode('utf-8',errors='replace').splitlines() if audio.exists() else []
audio_lines=[line[:500] for line in lines if re.search(r'underrun|xrun|late|warning|error|discarding|playback|capture',line,re.I)][-60:]
performance=root/'render_performance.jsonl'
records=[]
if performance.exists():
 for line in performance.read_bytes()[-65536:].decode('utf-8',errors='ignore').splitlines():
  try:records.append(json.loads(line))
  except ValueError:pass
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:s=json.load(response)
print(json.dumps({'audio_worker_log_bytes':audio.stat().st_size if audio.exists() else None,
 'audio_warnings':audio_lines,'render_performance':records[-10:],
 'avatar_renderer':s.get('avatar_renderer'),'display':s.get('avatar_display'),
 'portrait_offload':s.get('portrait_offload'),'phase':s.get('phase')},ensure_ascii=True))
'''.replace('EVIDENCE',repr(evidence))
data=json.loads(ssh('python3 -B -',script,timeout=20))
(H/'runtime_logs.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(data,ensure_ascii=True))
