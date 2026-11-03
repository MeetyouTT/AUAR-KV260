from common import *
import re
names=['command_guard_validation','perception_freshness_benchmark','llm_voice_runtime_optimization']
for n in names:
    base=W.parent/'skills_work'/n
    assert (base/'readme.md').is_file()
    for p in base.rglob('*'):
        if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in p.parts:copy(p,ROOT/'skill'/n/p.relative_to(base))
def put(n,s):
    p=ROOT/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((s.strip()+'\n').encode('utf8'))
wd=ROOT/'src/windows'
cfg=load(ROOT/'src/software/config/board_avatar_gtk.json')['board_business']
m=load(B/'cpu_optimization_20261102/camera/SOURCE_DISCOVERY.json')['board_result']
map_file=ROOT/'board/config/deployment_files.json'
items=load(map_file) if map_file.exists() else []
def register(path, dest):
    row=dict(source=path,destination=dest)
    if not any(r['destination']==dest for r in items):items.append(row)
register('models/dpu/yolox_nano_person.xmodel',m['config']['yolo']['model'])
register('src/software/models/dpu/yolox_nano_person.prototxt',m['config']['yolo']['model'].replace('.xmodel','.prototxt'))
assert sha(ROOT/'src/software/models/dpu/yolox_nano_person.prototxt')==m['config']['yolo']['model_config_sha256']
register('src/software/board/vision/native/libaura_yolox.so',m['config']['yolo']['native_library'])
register('src/software/tests/fixtures/vision/person_bus.jpg',m['config']['yolo']['reference_image'])
# Preserve the exact original camera native unit's sources. The ARM object makes an offline link possible.
unit='/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1/'
for n in load(B/'cpu_optimization_20261102/camera/NATIVE_UNIT_PROVENANCE.json')['unit_manifest']['files']:
    register('src/camera/native_operator/'+n,unit+n)
drv='/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c'
register('board/firmware_pairing.json',drv+'/candidate-manifest.json')
for p in (ROOT/'board/driver').iterdir():register(p.relative_to(ROOT).as_posix(),drv+'/driver/'+p.name)
reg=load(ROOT/'src/software/config/pan_face.local.json')
print('axis app paths',reg['arguments'].get('app-root'))
# Exact known model paths from recorded release metadata are included only when fingerprint matches.
save(map_file,items)
# Original project pins for portability of the selected TTS pair.
tts=P/'aura/models/tts/OmniVoice'
for n in ['download_identity.json','config.json','tokenizer_config.json','chat_template.jinja']:
    copy(tts/n,wd/'aura/models/tts/OmniVoice'/n)
save(ROOT/'models/host_tts_files.json',[dict(path=p.relative_to(tts).as_posix(),bytes=p.stat().st_size,sha256=h)
    for p,h in [(p,next((x['sha256'] for x in load(tts/'download_identity.json')['files'] if x['path']==p.relative_to(tts).as_posix()),None) or sha(p)) for p in tts.rglob('*') if p.is_file() and p.name!='download_identity.json' and not any(k.startswith('.') for k in p.relative_to(tts).parts)]])
put('src/windows/prepare_weights.py',r'''
"""Stage already downloaded OmniVoice files and verify external GGUF. No network access."""
import argparse, hashlib, json, os, shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def digest(p):
    with p.open('rb') as f:
        h=hashlib.sha256()
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--gguf',required=True,type=Path)
    ap.add_argument('--tts-cache',required=True,type=Path)
    a=ap.parse_args()
    llm=json.loads((ROOT/'models/host_llm.json').read_text())
    if digest(a.gguf)!=llm['sha256']:raise SystemExit('wrong 27B GGUF')
    for r in json.loads((ROOT/'models/host_tts_files.json').read_text()):
        p=a.tts_cache/r['path']
        if not p.is_file() or p.stat().st_size!=r['bytes'] or digest(p)!=r['sha256']:
            raise SystemExit('wrong or missing TTS dependency: '+str(p))
    target=HERE/'aura/models/tts/OmniVoice'
    for r in json.loads((ROOT/'models/host_tts_files.json').read_text()):
        p=a.tts_cache/r['path'];dest=target/r['path'];dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():
            if digest(dest)!=r['sha256']:raise SystemExit('conflicting file: '+str(dest))
            continue
        tmp=dest.with_name(dest.name+'.preparing')
        with tmp.open('xb') as out,p.open('rb') as inp:shutil.copyfileobj(inp,out,1024*1024)
        if digest(tmp)!=r['sha256']:raise RuntimeError('TTS copy failed')
        os.replace(str(tmp),str(dest))
    print('Pinned external GGUF and OmniVoice dependencies ready')
if __name__=='__main__':main()
''')
# Only the first-party project files needed for the Windows model service are selected for this distribution.
# Keep all first-party board business sources separately at src/software.
deps={'tools/model_inference_host.py','tools/model_inference_startup.py','tools/service_instance_lock.py','tools/voice_startup_guard.py','tools/voice_worker_transport.py','tools/dialogue_host_ollama.py','tools/cuda_memory_stats.py','common/model_inference_wire.py','common/gpu_coordination.py','common/inference_output_contract.py','board/runtime/audio/omnivoice_voice.py','board/runtime/audio/selected_voice.py'}
# Retain local imports recursively, including imports in functions and optional control branches.
import ast
aw=wd/'aura'; need=set()
def add_module(n):
    parts=n.split('.')
    for i in range(1,len(parts)+1):
        base=aw.joinpath(*parts[:i])
        for p in [base.with_suffix('.py'),base/'__init__.py']:
            if p.is_file() and p not in need:deps.add(p.relative_to(aw).as_posix())
while deps:
    n=deps.pop();p=aw/n
    if p in need or not p.is_file():continue
    need.add(p)
    for i in range(1,len(Path(n).parts)):
        q=aw.joinpath(*Path(n).parts[:i])/'__init__.py'
        if q.is_file() and q not in need:deps.add(q.relative_to(aw).as_posix())
    for stmt in ast.walk(ast.parse(p.read_bytes())):
        if isinstance(stmt,ast.Import):
            for x in stmt.names:add_module(x.name)
        if isinstance(stmt,ast.ImportFrom):
            if stmt.level:
                parent=list(Path(n).parent.parts)
                base='.'.join(parent[:max(0,len(parent)+1-stmt.level)]+([stmt.module] if stmt.module else []))
            else:base=stmt.module or ''
            add_module(base)
            for x in stmt.names:add_module(base+'.'+x.name)
for p in list(aw.rglob('*.py')):
    if p not in need:
        assert p.resolve().is_relative_to((OUT/'aura/src/windows/aura').resolve())
        p.unlink()
print('Windows service first-party Python source closure:',len(need))
# Model host packaging helper - pip install local preserved source, no copied venv.
put('src/windows/readme.md',r'''
# Windows 推理服务

现役主机是 RTX 5090 Laptop，承担 27B 和 OmniVoice16 推理。板端负责 ASR、声纹、记忆和角色业务。入口为本目录的 start_inference.ps1。请先在完整工程解压副本上运行根目录校验，再在独立运行副本中准备模型和环境。服务会写 sessions、运行锁和状态文件。

1. 准备 Python 3.10.11、与 CUDA 12.8 PyTorch 匹配的 NVIDIA 环境和 Ollama 0.40.13。按 requirements-5090.txt 安装，torch/torchaudio 2.7.0+cu128 取自 PyTorch 的 cu128 wheel 源。omnivoice==0.2.1 使用同目录 omnivoice_source，先用相同解释器执行 python -m pip install --no-deps ./omnivoice_source。其余包使用锁文件中的具体版本。原运行环境为 D:/AURARuntimes/voice-py310。
2. 原 GGUF 位于 D:/AIModels/qwen3.8-27b-abliterated，Ollama 模型库位于 D:/AIModels/Ollama-AURA。models/host_llm.json 指明 Hugging Face 仓库、固定 revision、文件名和 SHA-256。原机可直接复用，新机可按下例将权重下到工程之外。OmniVoice 必须下载指定 revision 的完整模型目录，含 audio_tokenizer。
3. 以下示例使用 Hugging Face CLI 并在 src/windows 目录执行。对工作副本运行 prepare_weights.py 后会按清单校验全部所需 TTS 文件，并将其放入服务期望的位置。27B 留在外部目录。

~~~powershell
hf download huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF Huihui-Qwen3.8-27B-abliterated-UD-IQ4_XS.gguf --revision 1c69098e9c32db6dc06fc48f1d6cc75ad07da89e --local-dir D:/AIModels/qwen3.8-27b-abliterated
hf download k2-fsa/OmniVoice --revision c5fdb5ccb189668d56333f77ba2629f4cd7535f4 --local-dir D:/AIModels/omnivoice-source
python prepare_weights.py --gguf D:/AIModels/qwen3.8-27b-abliterated/Huihui-Qwen3.8-27B-abliterated-UD-IQ4_XS.gguf --tts-cache D:/AIModels/omnivoice-source
~~~

4. 在 aura/config/model_inference.local.json 设置本机解释器，aura/config/model_storage.local.json 对应独立 GGUF/Ollama 路径。原机策略 ollama_runtime.local.json 固定原 GPU UUID 和实测 fit_target。新显卡应按真实 UUID 和容量重新确认配置。原进程使用专用 Ollama 127.0.0.1:11435，模型标签 aura-qwen3.8-27b-abliterated:iq4_xs。首次导入时把 modelfile.txt 复制至 GGUF 所在目录，针对该专用服务执行 ollama create aura-qwen3.8-27b-abliterated:iq4_xs -f modelfile.txt。设置 OLLAMA_HOST=127.0.0.1:11435、OLLAMA_MODELS=D:/AIModels/Ollama-AURA，先确认当前服务归属与模型库，再导入。
5. 准备完毕后执行 .\start_inference.ps1 -Action Start，随后执行 .\start_inference.ps1 -Action Status。业务端点 192.168.50.1:8797，允许板侧 192.168.50.2，状态端点 /health。结束时执行 .\start_inference.ps1 -Action Stop。原机已经运行服务时只做 Status。原始实测和参数见根目录 data/results/performance。本次打包未在另一台 Windows 上冷装并调用模型。
''')
