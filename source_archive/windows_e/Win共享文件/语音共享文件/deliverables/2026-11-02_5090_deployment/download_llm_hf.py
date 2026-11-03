import hashlib,json,os,time
from pathlib import Path
BASE=Path('D:/AIModels/qwen3.8-27b-abliterated')
OUT=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment')
os.environ['HF_HOME']='D:/AIModels/huggingface-cache'
os.environ['HF_XET_CACHE']='D:/AIModels/huggingface-cache/xet'
os.environ['HF_HUB_DISABLE_XET']='1'
os.environ['HF_HUB_DOWNLOAD_TIMEOUT']='60'
from huggingface_hub import hf_hub_download
from huggingface_hub.utils import tqdm as HFTqdm
class Progress(HFTqdm):
    def __init__(self,*args,**kwargs):
        self.report_time=0
        kwargs['file']=open(os.devnull,'w')
        kwargs['disable']=False
        super().__init__(*args,**kwargs)
    def update(self,n=1):
        result=super().update(n)
        now=time.monotonic()
        if now-self.report_time>=3:
            data=dict(status='DOWNLOADING_HTTP',complete_bytes=self.n,total_bytes=self.total,
                elapsed_seconds=round(now-started,1))
            temporary=OUT/'llm_download_progress.tmp'
            temporary.write_text(json.dumps(data),encoding='utf-8')
            os.replace(temporary,OUT/'llm_download_progress.json')
            self.report_time=now
        return result
name='Huihui-Qwen3.8-27B-abliterated-UD-IQ4_XS.gguf'
revision='1c69098e9c32db6dc06fc48f1d6cc75ad07da89e'
started=time.monotonic()
print(json.dumps({'status':'OFFICIAL_HF_HTTP_DOWNLOAD','revision':revision,'path':str(BASE/name)}),flush=True)
p=Path(hf_hub_download(repo_id='huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF',filename=name,revision=revision,local_dir=BASE,tqdm_class=Progress))
h=hashlib.sha256()
with p.open('rb') as f:
    for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
expected='d83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9'
if p.stat().st_size!=14403496864 or h.hexdigest()!=expected:raise RuntimeError('Downloaded model identity differs')
report=dict(status='VERIFIED',path=str(p),bytes=p.stat().st_size,sha256=h.hexdigest(),revision=revision,
    repository='huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF',elapsed_seconds=round(time.monotonic()-started,1),
    verified_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())
(OUT/'llm_download_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
