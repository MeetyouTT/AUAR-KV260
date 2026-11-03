"""Copy exact local models into shared project and verify every saved byte."""
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OMNI_SOURCE=Path('C:/Users/35870/.codex/visualizations/2026/10/09/01a12110-3ba4-7651-b3d7-2e6560916eb6/models/OmniVoice')
OLLAMA_SOURCE=Path('D:/ollama/models')
ACCEPTED=ROOT/'deliverables/2026-10-11_voice_accepted'
ACCEPTED.mkdir(parents=True,exist_ok=True)
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
rows=[]
def save(source,target,expected=None):
    target.parent.mkdir(parents=True,exist_ok=True)
    expected=expected or digest(source)
    if not target.exists():shutil.copy2(source,target)
    if digest(target)!=expected:raise ValueError('Saved model hash mismatch: '+str(target))
    rows.append({'path':target.relative_to(ROOT).as_posix(),'bytes':target.stat().st_size,'sha256':expected})
    print('VERIFIED '+target.relative_to(ROOT).as_posix(),flush=True)

official=json.loads((OMNI_SOURCE/'download_identity.json').read_text(encoding='utf-8'))
expected={entry['path']:entry['sha256'] for entry in official['files']}
for folder in (OMNI_SOURCE,OMNI_SOURCE/'audio_tokenizer'):
    for source in sorted(folder.iterdir()):
        if not source.is_file() or source.name in {'range_progress.json','.gitattributes'}:continue
        relative=source.relative_to(OMNI_SOURCE).as_posix()
        save(source,ROOT/'aura/models/tts/OmniVoice'/relative,expected.get(relative))

relative=Path('manifests/registry.ollama.ai/library/qwen3/4b-instruct-2507-q4_K_M')
manifest=json.loads((OLLAMA_SOURCE/relative).read_text(encoding='utf-8'))
save(OLLAMA_SOURCE/relative,ROOT/'aura/models/dialogue/ollama'/relative)
for entry in [manifest['config'],*manifest['layers']]:
    relative=Path('blobs')/entry['digest'].replace(':','-')
    save(OLLAMA_SOURCE/relative,ROOT/'aura/models/dialogue/ollama'/relative,entry['digest'].split(':')[1])

report={'status':'PASS','date':'2026-10-11','scope':'Saved shared project model files SHA256 verified; environments must be rebuilt per machine',
        'omnivoice_revision':official['revision'],'ollama_model':'qwen3:4b-instruct-2507-q4_K_M',
        'total_bytes':sum(r['bytes'] for r in rows),'files':rows}
(ACCEPTED/'model_files.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SHARED_MODELS_PASS',report['total_bytes'],flush=True)
