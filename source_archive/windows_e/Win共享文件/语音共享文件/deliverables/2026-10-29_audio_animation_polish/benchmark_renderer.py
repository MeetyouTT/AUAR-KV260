"""Offscreen public render requests, including strict manifest validation."""
import json,os,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path[:0]=[str(A),r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps']
os.environ['OMP_NUM_THREADS']=os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from common import portrait_wire as wire
from tools.portrait_renderer import PortraitRenderer
after='--after' in sys.argv
snapshot=H/'renderer_snapshot' if after else H.parent/'2026-10-27_windows_portrait/renderer_snapshot'
t=time.perf_counter();r=PortraitRenderer(A,snapshot,(423,438),'#FCFCF3');warm=(time.perf_counter()-t)*1000
times=[];checks=[];sequence=0
for generation,state in enumerate(('IDLE','PRESENT','SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW','ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED')):
    values=[]
    for i in range(48):
        sequence+=1
        plan=dict(protocol=wire.PROTOCOL,kind='render',session='public-offscreen-qa',generation=generation*2,
          sequence=sequence,state=state,clock=generation*4+i/16,gain=.8,level=.7,idle_gain=1.,
          emotion='sad' if state=='SPEAKING_LOW' else 'happy' if state=='SPEAKING' else 'neutral',
          characters=30,audio_sample=i*1500,track='answer',width=423,height=438,revision=r.revision)
        header,pixels=r.render(plan);wire.frame(header,pixels,plan);times.append(header['render_ms']);values.append(header['render_ms'])
    checks.append({'state':state,'frames':len(values),'p95_ms':float(np.percentile(values,95))})
result=dict(status='PASS',scope='offscreen composition, not physical fps or live conversation',revision=r.revision,
 warmup_ms=warm,frames=len(times),composition_ms={str(p):float(np.percentile(times,p)) for p in (50,95,99,100)},
 checks=checks,physical_devices_opened=False)
(H/('renderer_after.json' if after else 'renderer_before.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
