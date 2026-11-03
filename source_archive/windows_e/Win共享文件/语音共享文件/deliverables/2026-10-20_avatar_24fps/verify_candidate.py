import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text())
job=r'''
import sys,time,json,statistics,gc
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(sys.argv[1]);stage=root.parent;sys.path.insert(0,str(root/'aura'))
from tools.board_avatar_gtk import create_runtime_core
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
from tools.board_avatar_affine import configure_board_rendering,resize_rgb
from tools.native_pixels import NativePixels
start=time.monotonic();core=create_runtime_core(create_demo_core);core.MAX_CACHED_SEQUENCES=12
for state in ('IDLE','PRESENT','LISTENING','THINKING','ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED'):core.sequence(state);core.sop(state)
facials=RealtimeFacials(core);native=NativePixels(root/'aura/tools/libaura_pixels.so','white',threads=2);quality=[];timings={}
startup=time.monotonic()-start
for state in ('IDLE','LISTENING','THINKING','SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW','ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED'):
 for i,t in enumerate((0.,.3,1.31,1.42,3.4)):
  configure_board_rendering(core,'white');core.blend_frames=Image.blend;core.native_pixels=None
  ref=facials.apply(core.frame_at(state,t),t,.7,.6)['image'];ref=Image.frombytes('RGB',(423,438),resize_rgb(ref,(423,438)))
  native.configure(core);native.lib.aura_pixels_threads(3);got=facials.apply(core.frame_at(state,t),t,.7,.6)['image']
  diff=np.abs(np.asarray(ref).astype(int)-np.asarray(got).astype(int))
  row={'state':state,'t':t,'mean':float(diff.mean()),'p99':float(np.percentile(diff,99)),'max':int(diff.max())};quality.append(row)
  assert row['mean']<1.5 and row['p99']<=10,row
  if i==3:got.save(stage/(state+'.png'))
 native.configure(core);native.lib.aura_pixels_threads(3);rows=[];cpu=[]
 for i in range(96):
  now=4+i/24;beg=time.perf_counter();facials.apply(core.frame_at(state,now),now,.7,.6)
  rows.append((time.perf_counter()-beg)*1000);cpu.append(native.cpu_times()['total'])
 rows.sort();cpu.sort();timings[state]={'p50_ms':statistics.median(rows),'p95_ms':rows[int(len(rows)*.95)],'p99_ms':rows[int(len(rows)*.99)],'max_ms':max(rows),'cpu_p50_ms':statistics.median(cpu),'cpu_p99_ms':cpu[int(len(cpu)*.99)]}
assert native.cached_bytes<=native.limit
native.close()
result={'startup_seconds':startup,'quality':quality,'states':timings,'cache_limit_bytes':native.limit,'retained_bytes':native.cached_bytes,'all_passed':True}
(stage/'pixel_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''
remote=r'''
import base64,json,os,subprocess
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);job=stage/'verify_pixels.py';job.write_bytes(base64.b64decode(JOB))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(Path(c['runtime'])/'aura'),PATH='/usr/sbin:/usr/bin:/sbin:/bin')
result={}
r=subprocess.run(['python3','-B',str(job),c['runtime']],env=env,capture_output=True,text=True,timeout=220)
(stage/'pixels.log').write_text(r.stdout+r.stderr);result['pixels']={'code':r.returncode,'out':r.stdout,'error':r.stderr}
tests=['test_board_avatar_worker','test_handsfree_dialogue','test_automatic_conversation','test_gstreamer_audio','test_long_conversation','test_voice_channel','test_channel_jobs']
paths=['tests/framework/'+n+'.py' for n in tests if (Path(c['runtime'])/'aura/tests/framework'/(n+'.py')).is_file()]
r=subprocess.run(['python3','-B','-m','pytest','-q','-p','no:cacheprovider',*paths],cwd=Path(c['runtime'])/'aura',env=env,capture_output=True,text=True,timeout=130)
(stage/'tests.log').write_text(r.stdout+r.stderr);result['tests']={'code':r.returncode,'out':r.stdout+r.stderr}
r=subprocess.run(['python3','-B',str(Path(c['startup'])/'launcher.py'),'--config',str(Path(c['startup'])/'config.json'),'--preflight'],env=env,capture_output=True,text=True,timeout=40)
result['preflight']={'code':r.returncode,'out':r.stdout+r.stderr}
result['passed']=all(v['code']==0 for v in result.values())
(stage/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('CANDIDATE',repr(c),1).replace('JOB',repr(base64.b64encode(job.encode()).decode()),1)
r=json.loads(ssh('python3 -B -',remote,timeout=420));(HERE/'verification.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({'passed':r['passed'],'pixels_code':r['pixels']['code'],'pixels_error':r['pixels']['error'],'tests':r['tests'],'preflight':r['preflight']}))
