import json,base64,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'interaction_fix_candidate.json').read_text())
job=r'''
import sys,time,statistics,json,importlib.util
from pathlib import Path
import numpy as np
root=Path(ROOT);sys.path.insert(0,str(root/'aura'))
from tools.demo_script import create_demo_core
from tools.native_pixels import NativePixels
from tools.idle_body_compositor import IdleBodyTrack
from tools.realtime_facials import RealtimeFacials
core=create_demo_core('reuse');native=NativePixels(root/'aura/tools/libaura_pixels.so',threads=3);native.configure(core)
new=IdleBodyTrack(core);old=IdleBodyTrack(core);old.player.blend_frames=__import__('PIL.Image',fromlist=['Image']).blend
core.sequence('IDLE');old.sample(0);new.sample(0)
times={'old':[],'new':[]};worst=0
for i in range(40):
 t=i*.125+.011
 for name,track in (('old',old),('new',new)):
  at=time.monotonic();meta,matrix=track.sample(t);times[name].append((time.monotonic()-at)*1000)
  if name=='old':before=np.asarray(meta['image']).astype('int16');before_matrix=matrix
  else:
   worst=max(worst,int(np.max(np.abs(before-np.asarray(meta['image']).astype('int16')))))
   assert np.array_equal(before_matrix,matrix)
assert worst<=1,worst
f=RealtimeFacials(core)
def fail(unused):raise AssertionError('Unneeded idle body sampled during action/listening')
f.body.sample=fail
for state in ('LISTENING','THINKING','ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED'):
 meta=core.frame_at(state,0.);meta['display_state']=state;f.apply(meta,0.,0.,0.)
print(json.dumps({'passed':True,'max_pixel_difference':worst,'samples':40,'median_ms':{k:statistics.median(v) for k,v in times.items()}}));native.close()
'''.replace('ROOT',repr(c['runtime']),1)
remote="import base64,subprocess,json,os\nr=subprocess.run(['python3','-B','-c',base64.b64decode(%r).decode()],capture_output=True,text=True,timeout=100,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'));print(json.dumps(dict(code=r.returncode,out=r.stdout,error=r.stderr)))"%base64.b64encode(job.encode()).decode()
r=json.loads(ssh('python3 -B -',remote,timeout=115));(HERE/'interaction_fix_tests.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
