import sys,json,time,threading,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'candidate_source'),str(HERE.parents[1]/'aura'),'D:/AIModels/talknet-interaction/dependencies']
import tools,common
tools.__path__=[str(HERE/'candidate_source/tools'),str(HERE.parents[1]/'aura/tools')]
common.__path__=[str(HERE/'candidate_source/common'),str(HERE.parents[1]/'aura/common')]
# Check official source blob hashes before importing code.
up=json.loads((HERE/'asd_upstream.json').read_text(encoding='utf-8'))
for row in up['tree']:
 p=HERE/'upstream/TalkNet-ASD'/row['path']
 if p.is_file():
  b=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['sha'],row['path']
from tools.talknet_backend import TalkNetBackend
import numpy as np
backend=TalkNetBackend(HERE/'upstream/TalkNet-ASD',Path('D:/AIModels/talknet-interaction/pretrain_TalkSet.model'))
meta=dict(board_boot_id='fixture',clock_domain='fixture',capture_id='one',turn_generation=1,camera_epoch='one',track_id=1,track_generation=1,started_ms=0,ended_ms=1000,deadline_ms=3000,frame_times_ms=list(range(0,1000,40)))
rows=[]
for name,pcm in [('silence',b'\0\0'*16000),('tone',(np.sin(np.arange(16000)*2*np.pi*220/16000)*1000).astype('<i2').tobytes())]:
 v=backend.score(meta,pcm,np.zeros((25,112,112),dtype=np.uint8),now_ms=1000,cancelled=threading.Event())
 rows.append({'input':name,**{k:v[k] for k in ('model_id','score','inference_ms','field_calibrated','personal_memory_allowed')}})
 print(json.dumps(rows[-1]),flush=True)
(HERE/'asd_actual_probe.json').write_text(json.dumps({'status':'INFERENCE_EXECUTED_NOT_ACCURACY_ACCEPTANCE','rows':rows,'gpu':False,'weights_only':True,'source_hashes_verified':True},indent=2),encoding='utf-8')

