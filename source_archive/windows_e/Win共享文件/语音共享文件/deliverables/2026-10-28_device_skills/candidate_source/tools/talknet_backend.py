"""Official TalkNet weights on CPU; one bounded, time-aligned track window."""
import hashlib,json,sys,threading,time
from pathlib import Path
import numpy as np
from common.av_attribution import window

class TalkNetBackend:
    def __init__(self,source,weights,*,threads=2):
        import torch
        source=Path(source);weights=Path(weights)
        if weights.drive.upper()!='D:':raise ValueError('Model weights must remain on D:')
        manifest=json.loads((weights.parent/'manifest.json').read_text(encoding='utf-8'))
        with weights.open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=manifest['sha256']:raise ValueError('TalkNet weight fingerprint changed')
        sys.path.insert(0,str(source))
        try:
            from model.talkNetModel import talkNetModel
            from loss import lossAV
        finally:sys.path.remove(str(source))
        torch.set_num_threads(threads)
        self.torch=torch;self.model=talkNetModel().eval();self.head=lossAV().eval()
        state=torch.load(weights,map_location='cpu',weights_only=True)
        self.model.load_state_dict({k[6:]:v for k,v in state.items() if k.startswith('model.')},strict=True)
        self.head.load_state_dict({k[7:]:v for k,v in state.items() if k.startswith('lossAV.')},strict=True)
        self.lock=threading.Lock();self.model_id='talknet-talkset-'+manifest['sha256'][:16]
    def score(self,meta,pcm,faces,*,now_ms,cancelled):
        meta=window(meta,now_ms);duration=meta['ended_ms']-meta['started_ms']
        if not isinstance(pcm,bytes) or len(pcm)!=duration*32:raise ValueError('Expected aligned 16kHz PCM16')
        if not isinstance(faces,np.ndarray) or faces.dtype!=np.uint8 or faces.shape!=(len(meta['frame_times_ms']),112,112):raise ValueError('Expected timestamped 112px face crops')
        if cancelled.is_set():raise InterruptedError('AV window cancelled')
        if not self.lock.acquire(False):raise BlockingIOError('ASD busy')
        started=time.perf_counter()
        try:
            from python_speech_features import mfcc
            audio=np.frombuffer(pcm,dtype='<i2')
            features=mfcc(audio,16000,numcep=13,winlen=.025,winstep=.010)
            count=min(len(features)//4,int(duration*25/1000))
            features=features[:count*4]
            # Match training's 25 fps with nearest timestamped observations.
            # Never bridge >150 ms or mix a track generation/epoch.
            target=meta['started_ms']+np.arange(count)*40
            observed=np.asarray(meta['frame_times_ms'])
            indices=np.abs(observed[:,None]-target[None,:]).argmin(axis=0)
            video=np.ascontiguousarray(faces[indices])
            torch=self.torch
            with torch.inference_mode():
                a=self.model.forward_audio_frontend(torch.from_numpy(features.astype(np.float32))[None])
                v=self.model.forward_visual_frontend(torch.from_numpy(video.astype(np.float32))[None])
                a,v=self.model.forward_cross_attention(a,v)
                fused=self.model.forward_audio_visual_backend(a,v)
                logits=self.head.FC(fused)
                scores=torch.softmax(logits,dim=-1)[:,1].cpu().numpy()
            if cancelled.is_set():raise InterruptedError('AV result cancelled')
            elapsed=(time.perf_counter()-started)*1000
            if now_ms+elapsed>=meta['deadline_ms']:raise TimeoutError('AV result expired')
            return {'window':meta,'model_id':self.model_id,'score':float(np.mean(scores)),
                'frame_scores':scores.tolist(),'inference_ms':elapsed,'resampled_frames':count,
                'unique_source_frames':len(set(indices.tolist())),'score_semantics':'uncalibrated_softmax',
                'field_calibrated':False,'personal_memory_allowed':False}
        finally:self.lock.release()

