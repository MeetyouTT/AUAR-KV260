import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parents[1]/'2026-10-29_audio_animation_polish'))
from board_guard import ssh
script=r'''
import hashlib,json,urllib.request
from pathlib import Path
pid=1333
proc=Path('/proc')/str(pid)
stat=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()
with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/status',timeout=1.5) as response:s=json.load(response)
i=s['modules']['identity']
print(json.dumps(dict(pid=pid,start_ticks=stat[19],cmdline_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),
  backend=i.get('backend'),model_id=i.get('model_id'),db_version=i.get('db_version'),state=i.get('state'),
  service_epoch=s['service_epoch'],camera_epoch=s.get('preview',{}).get('camera_epoch'),source_kind=s['source_kind'])))
'''
result=json.loads(ssh('python3 -B -',script,timeout=15))
(H/'camera_process_metadata.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
