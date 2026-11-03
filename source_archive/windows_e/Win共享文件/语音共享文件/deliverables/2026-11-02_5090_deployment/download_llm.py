"""Pinned, bounded range download; all weight data stays outside shared E root."""
import concurrent.futures, hashlib, json, os, re, subprocess, time
from pathlib import Path
BASE=Path('D:/AIModels/qwen3.8-27b-abliterated')
NAME='Huihui-Qwen3.8-27B-abliterated-UD-IQ4_XS.gguf'
SIZE=14403496864
EXPECTED='d83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9'
REV='1c69098e9c32db6dc06fc48f1d6cc75ad07da89e'
URL=f'https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF/resolve/{REV}/{NAME}'
OUT=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment')
PARTS=BASE/'download-parts-5090'
PARTS.mkdir(exist_ok=True)
prefix=BASE/(NAME+'.partial')
final=BASE/NAME
if final.exists():raise RuntimeError('Inspect existing final model before downloading')
prefix_size=prefix.stat().st_size if prefix.exists() else 0
if not 0<=prefix_size<=SIZE:raise RuntimeError('Invalid initial download size')
planfile=PARTS/'plan.json'
plan={'url':URL,'total_bytes':SIZE,'sha256':EXPECTED,'prefix_bytes':prefix_size,'chunk_bytes':128*1024*1024}
if planfile.exists():
    saved=json.loads(planfile.read_bytes())
    if saved!=plan:raise RuntimeError('Range plan changed; preserve original data for review')
else:planfile.write_text(json.dumps(plan,indent=2),encoding='utf-8')
chunks=[(i,s,min(s+plan['chunk_bytes'],SIZE)-1) for i,s in enumerate(range(prefix_size,SIZE,plan['chunk_bytes']))]
started=time.monotonic()

def fetch(row):
    i,start,end=row
    done=PARTS/f'{i:04d}.done'
    if done.exists() and done.stat().st_size==end-start+1:return done
    tmp=PARTS/f'{i:04d}.partial'
    headers=PARTS/f'{i:04d}.headers'
    result=subprocess.run(['curl.exe','--fail','--location','--silent','--show-error','--retry','4',
        '--retry-delay','2','--connect-timeout','20','--max-time','480','--range',f'{start}-{end}',
        '--max-filesize',str(end-start+1),'--dump-header',str(headers),'--output',str(tmp),
        '--write-out','%{http_code}',URL],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or result.stdout.strip()!='206':
        raise RuntimeError(f'Range {i} failed: curl={result.returncode}, http={result.stdout.strip()}')
    ranges=re.findall(r'(?im)^content-range:\s*bytes\s+(\d+)-(\d+)/(\d+)\s*$',headers.read_text())
    if not ranges or tuple(map(int,ranges[-1]))!=(start,end,SIZE) or tmp.stat().st_size!=end-start+1:
        raise RuntimeError(f'Range {i} response identity or size differs')
    os.replace(tmp,done)
    return done

complete=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    futures={pool.submit(fetch,row):row for row in chunks}
    for future in concurrent.futures.as_completed(futures):
        p=future.result();complete.append(p)
        progress={'status':'DOWNLOADING','completed_chunks':len(complete),'total_chunks':len(chunks),
            'complete_bytes':prefix_size+sum(x.stat().st_size for x in complete),'total_bytes':SIZE,
            'elapsed_seconds':round(time.monotonic()-started,1)}
        (OUT/'llm_download_progress.json').write_text(json.dumps(progress),encoding='utf-8')
        if len(complete)%4==0:print(json.dumps(progress),flush=True)
assembled=BASE/(NAME+'.assembled.partial')
h=hashlib.sha256()
with assembled.open('wb') as target:
    sources=([prefix] if prefix_size else [])+[PARTS/f'{row[0]:04d}.done' for row in chunks]
    for source in sources:
        with source.open('rb') as f:
            for block in iter(lambda:f.read(8*1024*1024),b''):
                target.write(block);h.update(block)
    target.flush();os.fsync(target.fileno())
if assembled.stat().st_size!=SIZE or h.hexdigest()!=EXPECTED:raise RuntimeError('Final model identity differs; all files retained')
os.replace(assembled,final)
report={'status':'VERIFIED','path':str(final),'bytes':SIZE,'sha256':h.hexdigest(),
    'repository':'huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF','revision':REV,
    'elapsed_seconds':round(time.monotonic()-started,1),'verified_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
(OUT/'llm_download_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
