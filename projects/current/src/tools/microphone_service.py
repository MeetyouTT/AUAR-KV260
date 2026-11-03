"""Bounded PCM microphone recognition outside the GUI process."""
import base64
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import queue
import subprocess
import sys

class MicrophoneJobs:
    def __init__(self,python,root):
        self.python=Path(python);self.root=Path(root);self.results=queue.Queue()
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='aura-asr')
        self.process=None;self.log=None;self.pending=False;self.ready=False;self.error=''
        self.executor.submit(self.warmup)

    def request(self,data):
        if self.process is None or self.process.poll() is not None:
            if self.log:self.log.close()
            self.log=(self.root/'asr_worker.log').open('a',encoding='utf-8')
            self.process=subprocess.Popen([str(self.python),'-B','-u',str(Path(__file__).resolve()),'--worker'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,encoding='utf-8',
                bufsize=1,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.process.stdin.write(json.dumps(data)+'\n');self.process.stdin.flush()
        for line in self.process.stdout:
            if not line.startswith('ASR '):continue
            result=json.loads(line[4:])
            if not result.get('ok'):raise ValueError(result.get('error','ASR failed'))
            return result
        raise RuntimeError('Microphone recognizer stopped')

    def warmup(self):
        try:self.request({'type':'warmup'});self.ready=True
        except Exception as exc:self.error=str(exc)

    def submit(self,pcm,generation):
        if self.pending:raise ValueError('上一段声音仍在识别，请稍后')
        if not isinstance(pcm,str) or len(pcm)>900000:raise ValueError('录音最多 20 秒')
        raw=base64.b64decode(pcm,validate=True)
        if not 6400<=len(raw)<=640000 or len(raw)%2:raise ValueError('请说 0.2–20 秒，使用 16kHz 单声道 PCM16')
        self.pending=True;self.executor.submit(self._run,pcm,generation)

    def _run(self,pcm,generation):
        try:self.results.put(dict(self.request({'pcm':pcm}),generation=generation))
        except Exception as exc:self.results.put({'generation':generation,'error':str(exc)})

    def poll(self):
        try:result=self.results.get_nowait();self.pending=False;return result
        except queue.Empty:return None

    def close(self):
        self.executor.shutdown(wait=False,cancel_futures=True)
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
        if self.log:self.log.close()

def worker_main():
    import time
    import numpy as np
    aura=Path(__file__).resolve().parents[1];sys.path.insert(0,str(aura))
    from board.runtime.audio.asr import SherpaOfflineRecognizer,AsrConfig
    sys.stdin.reconfigure(encoding='utf-8');sys.stdout.reconfigure(encoding='utf-8')
    recognizer=SherpaOfflineRecognizer(AsrConfig(prefer_int8=True))
    for line in sys.stdin:
        try:
            data=json.loads(line)
            if data.get('type')=='warmup':
                recognizer.transcribe(np.zeros(16000,dtype=np.float32),16000)
                result={'ok':True,'ready':True}
            else:
                started=time.perf_counter();raw=base64.b64decode(data['pcm'],validate=True)
                samples=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
                text=recognizer.transcribe(samples,16000)
                if not text:raise ValueError('没有识别到说话内容，请再试一次')
                result={'ok':True,'text':text,'recognition_seconds':time.perf_counter()-started}
            print('ASR '+json.dumps(result,ensure_ascii=False),flush=True)
        except Exception as exc:print('ASR '+json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False),flush=True)

if __name__=='__main__':worker_main()
