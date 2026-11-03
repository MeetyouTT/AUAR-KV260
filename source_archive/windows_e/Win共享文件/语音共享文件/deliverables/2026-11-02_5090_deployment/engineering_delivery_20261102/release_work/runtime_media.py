from common import *
import re
ext=SH/'5090主机迁移包_20261101/external_dependencies'
models={}
def add(k,p,pin=None):
    h=sha(p)
    if pin is not None and h!=pin:raise ValueError((p,h,pin))
    models[k]=(p,h)
small=ext/'ASR-candidates/paraformer-small-20261031'
for n,h in [('model.int8.onnx','3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec'),('tokens.txt','4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa')]:
    add('asr/'+n,small/n,h)
speaker=ext/'speaker/board-onnx'
for n,h in load(speaker/'manifest.json')['sha256'].items():add('speaker/'+n,speaker/n,h)
add('speaker/manifest.json',speaker/'manifest.json',load(ROOT/'src/software/config/board_avatar_gtk.json')['board_business']['speaker']['manifest_sha256'])
front=ext/'audio-frontend'
for n in ['silero_vad_v5.onnx','gtcrn_simple.onnx','SILERO_LICENSE','SHERPA_LICENSE','GTCRN_LICENSE']:add('frontend/'+n,front/n)
for p in [*front.glob('sherpa*.whl'),*(front/'board-ort-candidate-20261030').glob('*.whl'),*(ext/'speaker/board-webrtcvad').glob('*.whl')]:add('wheels_arm64/'+p.name,p)
meta=[dict(path=n,sha256=h,bytes=p.stat().st_size)for n,(p,h) in sorted(models.items())]
save(ROOT/'models/board_audio_dependencies.json',meta)
dest=OUT/'auar_board_audio_dependencies.zip'
with zipfile.ZipFile(dest.with_suffix('.part'),'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3)as z:
    for n,(p,h) in models.items():z.write(p,'board_audio/'+n)
    z.write(ROOT/'models/board_audio_dependencies.json','board_audio/manifest.json')
dest.with_suffix('.part').replace(dest)
with zipfile.ZipFile(dest) as z:
    for r in meta:
        with z.open('board_audio/'+r['path'])as f:
            h=hashlib.sha256()
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
            if h.hexdigest()!=r['sha256']:raise ValueError(r['path'])
save(QA/'board_audio_archive.json',dict(path=dest.name,bytes=dest.stat().st_size,sha256=sha(dest),model_and_wheel_files=len(meta),extracted_hashes='PASS'))
print('Board runtime archive verified',dest.stat().st_size)
