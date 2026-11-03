"""Pinned public online Paraformer resources; external ASR storage only."""
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request

HERE=Path(__file__).resolve().parent
DIRECTORY=Path('D:/AIModels/ASR-candidates/online-paraformer-20261031')
REVISION='8e40c43232a1c5c66c82111efc5820d3accca11b'
BASE='https://huggingface.co/csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en/resolve/'+REVISION+'/'
FILES=(
 ('encoder.int8.onnx',165462184,'81a70226a8934e6ed92aa1d4fc486b428b5398e2f2619ed4897b7294cab90e9a'),
 ('decoder.int8.onnx',71664561,'f3cca9f77bb9d93c8fcbfb63ae617b6b1ee96818df3aa3b151c40658fe38594f'),
 ('tokens.txt',75756,'59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6'),
)

if __name__=='__main__':
    DIRECTORY.mkdir(parents=True,exist_ok=True)
    assert DIRECTORY.resolve().is_relative_to(Path('D:/AIModels').resolve())
    assert shutil.disk_usage(DIRECTORY).free>sum(r[1] for r in FILES)+512*1024*1024
    rows=[]
    for name,size,expected in FILES:
        target=DIRECTORY/name
        url=BASE+name
        if not target.exists():
            part=target.with_name(name+'.part-'+str(time.time_ns()))
            count=0;digest=hashlib.sha256()
            with urllib.request.urlopen(url,timeout=45) as response,part.open('xb') as output:
                while block:=response.read(1024*1024):
                    count+=len(block)
                    if count>size:raise ValueError('public_model_size_exceeded')
                    output.write(block);digest.update(block)
            assert count==size and digest.hexdigest()==expected
            part.rename(target)
        assert target.stat().st_size==size and hashlib.sha256(target.read_bytes()).hexdigest()==expected
        rows.append(dict(path=str(target),url=url,size=size,sha256=expected))
        print(json.dumps(dict(downloaded=name,verified=True)),flush=True)
    result=dict(status='DOWNLOADED_PINNED_PUBLIC_ASR_NOT_DEPLOYED',revision=REVISION,files=rows,
        language_model_weights_downloaded=False)
    (HERE/'online_paraformer_download_manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
