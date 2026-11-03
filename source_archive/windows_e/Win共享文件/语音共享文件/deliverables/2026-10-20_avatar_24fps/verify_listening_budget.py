import json,base64,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'listening_budget_candidate.json').read_text())
job=r'''
import json,sys,ctypes as C
from pathlib import Path
import numpy as np
from PIL import Image
import gi
gi.require_version('Gst','1.0');from gi.repository import Gst
Gst.init(None);root=Path(sys.argv[1]);lib=C.CDLL(str(root/'aura/tools/libaura_pixels.so'));lib.aura_rgb565_copy.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_void_p]
def decode(raw,w,h):
 a=np.frombuffer(raw,dtype='<u2').reshape(h,-1)[:,:w].astype(np.int32);return np.stack((((a>>11)&31)*255//31,((a>>5)&63)*255//63,(a&31)*255//31),axis=-1)
rows=[]
paths=list(Path('/home/root/aura-render24-20261020/candidate-45f9f5cd2aaa').glob('*.png'))
for path in paths:
 image=Image.open(path).convert('RGB');w,h=image.size;raw=image.tobytes();stride=(w*2+3)&~3;out=C.create_string_buffer(stride*h);lib.aura_rgb565_copy(raw,w,h,out)
 expected=(np.asarray(image,dtype=np.uint16)[:,:,0]>>3)<<11;expected|=(np.asarray(image,dtype=np.uint16)[:,:,1]>>2)<<5;expected|=np.asarray(image,dtype=np.uint16)[:,:,2]>>3
 actual=np.frombuffer(out.raw,dtype='<u2').reshape(h,-1)[:,:w];assert np.array_equal(expected,actual),'RGB565 kernel mismatch'
 pipe=Gst.parse_launch('appsrc name=input format=time caps="video/x-raw,format=RGB,width=%d,height=%d,framerate=24/1" ! videoconvert ! video/x-raw,format=RGB16 ! appsink name=output sync=false'%(w,h));pipe.set_state(Gst.State.PLAYING)
 istride=(w*3+3)&~3;inp=np.zeros((h,istride),dtype=np.uint8);inp[:,:w*3]=np.frombuffer(raw,dtype=np.uint8).reshape(h,w*3)
 buf=Gst.Buffer.new_allocate(None,inp.size,None);buf.fill(0,inp.tobytes());pipe.get_by_name('input').emit('push-buffer',buf);sample=pipe.get_by_name('output').emit('try-pull-sample',3*Gst.SECOND);assert sample,'Reference conversion missing'
 ref=sample.get_buffer().extract_dup(0,sample.get_buffer().get_size());pipe.set_state(Gst.State.NULL)
 diff=np.abs(decode(ref,w,h)-decode(out.raw,w,h));row={'image':path.name,'mean':float(diff.mean()),'p99':float(np.percentile(diff,99)),'max':int(diff.max())};rows.append(row)
 assert row['mean']<=1.5 and row['p99']<=9 and row['max']<=9,row
print(json.dumps({'passed':True,'quality':rows,'cases':len(rows),'kernel_exact':True}))
'''
remote=r'''
import subprocess,json,base64,os
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);stage=Path(c['stage']);q=stage/'quality.py';q.write_bytes(base64.b64decode(JOB));env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root/'aura'),PATH='/usr/sbin:/usr/bin:/sbin:/bin')
results={}
r=subprocess.run(['python3','-B',str(q),str(root)],env=env,capture_output=True,text=True,timeout=45);results['quality']={'code':r.returncode,'out':r.stdout,'error':r.stderr}
tests=['test_board_avatar_worker','test_handsfree_dialogue','test_automatic_conversation','test_voice_barge_in','test_gstreamer_audio','test_persistent_audio','test_long_conversation','test_voice_channel','test_channel_jobs']
paths=['tests/framework/'+n+'.py' for n in tests if (root/'aura/tests/framework'/(n+'.py')).is_file()]
r=subprocess.run(['python3','-B','-m','pytest','-q','-p','no:cacheprovider',*paths],cwd=root/'aura',env=env,capture_output=True,text=True,timeout=130);results['tests']={'code':r.returncode,'out':r.stdout,'error':r.stderr}
r=subprocess.run(['python3','-B',c['startup']+'/launcher.py','--config',c['startup']+'/config.json','--preflight'],env=env,capture_output=True,text=True,timeout=35);results['preflight']={'code':r.returncode,'out':r.stdout,'error':r.stderr}
results['passed']=all(v['code']==0 for v in results.values());(stage/'verification.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))
'''.replace('CANDIDATE',repr(c),1).replace('JOB',repr(base64.b64encode(job.encode()).decode()),1)
r=json.loads(ssh('python3 -B -',remote,timeout=240));(HERE/'listening_budget_verification.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
