"""Pinned official Qwen VLM download; all weights and parts stay on D:."""
import hashlib,json,sys,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'aura/tools'))
from prepare_speaker_model import download_ranges
root=Path('D:/AIModels/qwen3-vl-2b-interaction')
assert root.drive.upper()=='D:'
root.mkdir(parents=True,exist_ok=True)
repo='Qwen/Qwen3-VL-2B-Instruct-GGUF'
with urllib.request.urlopen('https://huggingface.co/api/models/'+repo+'?blobs=true',timeout=30) as r:meta=json.load(r)
files={row['rfilename']:row for row in meta['siblings']}
names=['Qwen3VL-2B-Instruct-Q4_K_M.gguf','mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf']
manifest={'repository':repo,'revision':meta['sha'],'files':{}}
for name in names:
 row=files[name];target=root/name;part=root/(name+'.part')
 expected=row['lfs']['sha256'];size=row['size']
 def verify(p):
  if not p.exists() or p.stat().st_size!=size:return False
  with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()==expected
 if not verify(target):
  download_ranges('https://huggingface.co/'+repo+'/resolve/'+meta['sha']+'/'+name,part,size)
  assert verify(part),'Official model hash mismatch'
  part.replace(target)
 manifest['files'][name]={'sha256':expected,'bytes':size,'path':str(target)}
 print(json.dumps({'verified':name,'bytes':size}),flush=True)
(root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(HERE/'vlm_model_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

