"""Pinned existing SFace on Windows CPU; transient 112px faces, no database/I/O."""
import hashlib
import io
import threading
import time
from common.face_features import MODEL_ID,MODEL_SHA,checked_meta

class FaceFeatureHost:
    def __init__(self,path):
        import numpy as np
        import onnxruntime as ort
        from PIL import Image
        if hashlib.sha256(path.read_bytes()).hexdigest()!=MODEL_SHA:raise ValueError('SFace weight mismatch')
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        options.log_severity_level=3
        self.session=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
        self.np,self.Image=np,Image;self.input=self.session.get_inputs()[0].name
        self.lock=threading.Lock();self.processed=0;self.last_ms=None
        self.session.run(None,{self.input:np.zeros((1,3,112,112),np.float32)})

    def feature(self,meta,png):
        checked_meta(meta,png)
        if not self.lock.acquire(blocking=False):raise BlockingIOError('Face feature worker busy')
        try:
            with self.Image.open(io.BytesIO(png)) as image:
                if image.size!=(112,112) or image.format!='PNG':raise ValueError('Expected face PNG')
                pixels=self.np.asarray(image.convert('RGB'),dtype=self.np.float32)
            tensor=self.np.ascontiguousarray(pixels.transpose(2,0,1)[None])
            started=time.perf_counter();vector=self.session.run(None,{self.input:tensor})[0].reshape(-1)
            duration=(time.perf_counter()-started)*1000
            if vector.shape!=(128,) or not self.np.isfinite(vector).all() or self.np.linalg.norm(vector)<=1e-8:
                raise ValueError('Invalid SFace result')
            self.processed+=1;self.last_ms=round(duration,3)
            return {'context':meta,'embedding':[float(v) for v in vector],
                    'inference_ms':self.last_ms,'backend':'WINDOWS_CPU_SFACE_ORT'}
        finally:self.lock.release()

    def health(self):
        return {'ready':True,'model_id':MODEL_ID,'backend':'WINDOWS_CPU_SFACE_ORT',
                'input_size':[112,112],'processed':self.processed,'last_inference_ms':self.last_ms,
                'gpu_used':False,'images_persisted':False}
