"""Stage already downloaded OmniVoice files and verify external GGUF. No network access."""
import argparse, hashlib, json, os, shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
INPUTS=HERE/'model_inputs'
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
    llm=json.loads((INPUTS/'host_llm.json').read_text())
    if digest(a.gguf)!=llm['sha256']:raise SystemExit('wrong 27B GGUF')
    for r in json.loads((INPUTS/'host_tts_files.json').read_text()):
        p=a.tts_cache/r['path']
        if not p.is_file() or p.stat().st_size!=r['bytes'] or digest(p)!=r['sha256']:
            raise SystemExit('wrong or missing TTS dependency: '+str(p))
    target=HERE/'aura/models/tts/OmniVoice'
    for r in json.loads((INPUTS/'host_tts_files.json').read_text()):
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
