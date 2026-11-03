"""Root-run CPU-only equivalence probe on public synthetic BGR patterns.

Pass the candidate source path, or prepend CANDIDATE_SOURCE to run via stdin.
This file never opens a camera, Native/DPU owner, DB, GPIO, socket or service.
It prints only numeric/hash results. No image is saved or emitted.
"""
import ast
import hashlib
import json
from pathlib import Path
import sys
import threading
import time

import cv2
import numpy as np

if 'CANDIDATE_SOURCE' in globals():
    source=CANDIDATE_SOURCE
else:
    source=Path(sys.argv[1]).read_text(encoding='utf-8')
digest=hashlib.sha256(source.encode('utf-8')).hexdigest()
assert digest=='7d4773b8ff527773eefc90aa2443dd4bfae801f07c6fcde672af65dd22ff8f66'
tree=ast.parse(source)
provider=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='_PreviewJpeg')
space={'threading':threading}
exec(compile(ast.Module(body=[provider],type_ignores=[]),'<candidate-preview-provider>','exec'),space)
PreviewJpeg=space['_PreviewJpeg']

class Codec:
    IMWRITE_JPEG_QUALITY=cv2.IMWRITE_JPEG_QUALITY
    def __init__(self):self.calls=0;self.lock=threading.Lock()
    def imencode(self,*args):
        with self.lock:self.calls+=1
        return cv2.imencode(*args)

patterns=[]
for value,name in ((0,'black'),(255,'white')):
    pixels=np.full((480,640,3),value,dtype=np.uint8);patterns.append((name,pixels))
gradient=np.empty((480,640,3),np.uint8)
gradient[:,:,0]=np.arange(640,dtype=np.uint16)%256
gradient[:,:,1]=(np.arange(480,dtype=np.uint16)%256)[:,None]
gradient[:,:,2]=127
patterns.append(('gradient',gradient))
bars=np.empty((480,640,3),np.uint8)
colors=((255,0,0),(0,255,0),(0,0,255),(255,255,255),(0,0,0),(40,220,60),(0,190,255),(127,127,127))
for index,color in enumerate(colors):bars[:,index*80:(index+1)*80]=color
patterns.append(('color-bars',bars))
random=np.random.RandomState(7733).randint(0,256,(480,640,3)).astype(np.uint8)
patterns.append(('seeded-public-noise',random))
rows=[]
for name,pixels in patterns:
    # Match the actual preview's private painted copy, including annotations.
    painted=pixels.copy()
    cv2.rectangle(painted,(30,60),(180,280),(40,220,60),2)
    cv2.putText(painted,'person #42 0.95',(30,54),cv2.FONT_HERSHEY_SIMPLEX,.6,(40,220,60),2)
    ok,expected=cv2.imencode('.jpg',painted,[cv2.IMWRITE_JPEG_QUALITY,72])
    assert ok and expected.nbytes<=256*1024
    codec=Codec();frame=PreviewJpeg(painted,codec,threading.Lock())
    assert codec.calls==0
    started=time.monotonic_ns();actual,outcome,error=frame.resolve()
    elapsed_ms=(time.monotonic_ns()-started)/1e6
    assert outcome=='encoded' and error is None and actual==expected.tobytes()
    cached,outcome,error=frame.resolve()
    assert cached==actual and outcome=='cached' and error is None and codec.calls==1
    assert frame._image is None
    rows.append({'pattern':name,'byte_equal':True,'jpeg_bytes':len(actual),
        'jpeg_sha256':hashlib.sha256(actual).hexdigest(),'codec_calls':codec.calls,'resolve_wall_ms':elapsed_ms})
print(json.dumps({'candidate_sha256':digest,'cv2_version':cv2.__version__,'patterns':rows,
    'all_passed':True,'scope':'CPU-only public synthetic patterns; not a production throughput benchmark',
    'camera_device_opened':False,'native_or_model_opened':False,'board_files_written':False}))
