"""Resume verified-range transfers; weights and all partial data stay on D:."""
import concurrent.futures, hashlib, json, os, re, subprocess, threading, time, uuid
from pathlib import Path
BASE=Path('D:/AIModels/qwen3.8-27b-abliterated')
OUT=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment')
NAME='Huihui-Qwen3.8-27B-abliterated-UD-IQ4_XS.gguf'
SIZE=14403496864
EXPECTED='d83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9'
REV='1c69098e9c32db6dc06fc48f1d6cc75ad07da89e'
PARTS=BASE/'download-parts-5090'
plan=json.loads((PARTS/'plan.json').read_bytes())
URL=plan['url']
prefix=BASE/(NAME+'.partial')
final=BASE/NAME
started=time.monotonic()
stop=threading.Event()
chunks=[(i,s,min(s+plan['chunk_bytes'],SIZE)-1) for i,s in enumerate(range(plan['prefix_bytes'],SIZE,plan['chunk_bytes']))]

def length(p):
    try:
        with p.open('rb') as f:return os.fstat(f.fileno()).st_size
    except OSError:return 0

def atomic(p,data):
    tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');os.replace(tmp,p)

def recover_tail(i,start,end,part):
    tail=PARTS/f'{i:04d}.tail';header=PARTS/f'{i:04d}.resume-headers'
    got=length(tail)
    if not got:return
    raw=header.read_text(encoding='iso-8859-1') if header.exists() else ''
    ranges=re.findall(r'(?im)^content-range:\s*bytes\s+(\d+)-(\d+)/(\d+)\s*$',raw)
    statuses=re.findall(r'(?im)^HTTP/\S+\s+(\d{3})\b',raw)
    first=start+length(part)
    if (statuses and statuses[-1]=='206' and ranges
            and tuple(map(int,ranges[-1]))==(first,end,SIZE) and got<=end-first+1):
        with part.open('ab') as target,tail.open('rb') as source:
            for block in iter(lambda:source.read(4*1024*1024),b''):target.write(block)
            target.flush();os.fsync(target.fileno())
        tail.unlink()
        atomic(PARTS/f'{i:04d}.tail-recovery.json',dict(recovered_bytes=got,range_start=first,range_end=end))
    else:
        # Keep ambiguous bytes and their headers; resume from the proven part.
        tag='.retained-'+uuid.uuid4().hex
        tail.replace(tail.with_name(tail.name+tag))
        if header.exists():header.replace(header.with_name(header.name+tag))

def fetch(row):
    i,start,end=row
    done=PARTS/f'{i:04d}.done';part=PARTS/f'{i:04d}.partial'
    if length(done)==end-start+1:return
    recover_tail(i,start,end,part)
    failures=0
    while not stop.is_set():
        offset=length(part)
        if offset>end-start+1:raise RuntimeError(f'Invalid retained range size {i}')
        if offset==end-start+1:os.replace(part,done);return
        first=start+offset
        tail=PARTS/f'{i:04d}.tail';header=PARTS/f'{i:04d}.resume-headers'
        result=subprocess.run(['curl.exe','--fail','--location','--silent','--show-error',
            '--connect-timeout','20','--max-time','120','--range',f'{first}-{end}',
            '--max-filesize',str(max(end-first+1,4096)),'--dump-header',str(header),
            '--output',str(tail),'--write-out','%{http_code}',URL],
            capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
        ranges=re.findall(r'(?im)^content-range:\s*bytes\s+(\d+)-(\d+)/(\d+)\s*$',header.read_text() if header.exists() else '')
        got=length(tail)
        valid=(result.stdout.strip()=='206' and ranges and tuple(map(int,ranges[-1]))==(first,end,SIZE)
            and 0<got<=end-first+1)
        if valid:
            # A timed-out range still contains a valid contiguous prefix. The
            # next request starts at its new end; the final SHA is mandatory.
            with part.open('ab') as target,tail.open('rb') as source:
                for block in iter(lambda:source.read(4*1024*1024),b''):target.write(block)
                target.flush();os.fsync(target.fileno())
            tail.unlink();failures=0
        else:
            failures+=1
            atomic(PARTS/f'{i:04d}.last-error.json',dict(curl_code=result.returncode,http_status=result.stdout.strip(),range_start=first,range_end=end,attempt=failures))
            if failures>=12:raise RuntimeError(f'Range {i} made no progress after twelve attempts; see range last-error metadata')
            stop.wait(min(30,2**failures))
        if time.monotonic()-started>48*3600:raise TimeoutError('48 hour transfer budget reached; partial data retained')
    raise InterruptedError('Transfer stopped after a peer range failed')

def reporter():
    while not stop.wait(3):
        total=plan['prefix_bytes'];complete=0
        for i,_,_ in chunks:
            done=PARTS/f'{i:04d}.done';part=PARTS/f'{i:04d}.partial';tail=PARTS/f'{i:04d}.tail'
            if done.exists():total+=length(done);complete+=1
            else:total+=length(part)+length(tail)
        atomic(OUT/'llm_download_progress.json',dict(status='DOWNLOADING_RESUMABLE_RANGES',complete_bytes=total,
            total_bytes=SIZE,complete_ranges=complete,total_ranges=len(chunks),elapsed_seconds=round(time.monotonic()-started,1)))

try:
    if final.exists():
        sources=[final]
    else:
        if length(prefix)!=plan['prefix_bytes']:raise RuntimeError('Initial prefix changed')
        monitor=threading.Thread(target=reporter,daemon=True);monitor.start()
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            futures=[pool.submit(fetch,row) for row in chunks]
            try:
                for future in concurrent.futures.as_completed(futures):future.result()
            except BaseException:stop.set();raise
        stop.set();monitor.join()
        sources=[prefix]+[PARTS/f'{i:04d}.done' for i,_,_ in chunks]
    h=hashlib.sha256()
    assembling=not final.exists()
    target=(BASE/(NAME+'.assembled.partial')).open('wb') if assembling else None
    try:
        for source in sources:
            with source.open('rb') as f:
                for block in iter(lambda:f.read(8*1024*1024),b''):
                    if target:target.write(block)
                    h.update(block)
        if target:target.flush();os.fsync(target.fileno())
    finally:
        if target:target.close()
    if h.hexdigest()!=EXPECTED:raise RuntimeError('Final model SHA256 differs; all data retained')
    if assembling:os.replace(BASE/(NAME+'.assembled.partial'),final)
    if length(final)!=SIZE:raise RuntimeError('Final model size differs')
    report=dict(status='VERIFIED',path=str(final),bytes=SIZE,sha256=h.hexdigest(),revision=REV,
        repository='huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF',elapsed_seconds=round(time.monotonic()-started,1),
        verified_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())
    atomic(OUT/'llm_download_verification.json',report)
    atomic(OUT/'llm_download_progress.json',dict(status='VERIFIED',complete_bytes=SIZE,total_bytes=SIZE))
    print(json.dumps(report),flush=True)
except BaseException as error:
    stop.set()
    atomic(OUT/'llm_download_failure.json',dict(error_type=type(error).__name__,message=str(error),partial_data_retained=True))
    raise
