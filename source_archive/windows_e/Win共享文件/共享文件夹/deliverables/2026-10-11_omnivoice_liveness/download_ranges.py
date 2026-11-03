"""Resume public official HF files in bounded ranges; verify canonical SHA256."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time

import requests
from huggingface_hub import HfApi

REVISION = 'c5fdb5ccb189668d56333f77ba2629f4cd7535f4'
REPO = 'k2-fsa/OmniVoice'


def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024*1024),b''):
            digest.update(data)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=24)
    args = parser.parse_args()
    info = HfApi().model_info(REPO, revision=REVISION, files_metadata=True)
    for item in info.siblings:
        if not item.lfs:
            continue
        name = item.rfilename
        target = args.destination/name
        expected = item.lfs.sha256
        size = item.size
        if target.exists() and file_hash(target)==expected:
            print('VERIFIED existing '+name,flush=True)
            continue
        url = 'https://huggingface.co/'+REPO+'/resolve/'+REVISION+'/'+name+'?download=true'
        # Resolve once, without printing the transient CDN signature.
        response = requests.get(url,headers={'Range':'bytes=0-0'},stream=True,timeout=30)
        response.raise_for_status()
        cdn = response.url
        response.close()
        chunks = args.destination/'.range-parts'/name.replace('/','_')
        chunks.mkdir(parents=True,exist_ok=True)
        block = 4*1024*1024
        offsets = list(range(0,size,block))
        cached_bytes = sum(min(block,size-start) for start in offsets
                           if (chunks/str(start)).exists()
                           and (chunks/str(start)).stat().st_size==min(block,size-start))
        started = time.perf_counter()

        def fetch(start):
            end = min(size-1,start+block-1)
            path = chunks/str(start)
            length = end-start+1
            if path.exists() and path.stat().st_size==length:
                return length
            for attempt in range(3):
                try:
                    source = cdn if attempt == 0 else url
                    with requests.get(source,headers={'Range':f'bytes={start}-{end}'},stream=True,timeout=(20,40)) as r:
                        r.raise_for_status()
                        if r.status_code!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}':
                            raise ValueError('Unexpected range response')
                        tmp=path.with_suffix('.part')
                        with tmp.open('wb') as f:
                            for data in r.iter_content(65536):
                                f.write(data)
                        if tmp.stat().st_size!=length:
                            raise ValueError('Range length mismatch')
                        tmp.replace(path)
                        return length
                except Exception:
                    if attempt==2:
                        raise RuntimeError('Range failed: '+name+' offset '+str(start)) from None
                    time.sleep(1+attempt)
        print('DOWNLOADING '+name+' '+str(size)+' bytes',flush=True)
        completed=0
        pending=offsets
        for round_index in range(3):
            failed=[]
            workers=args.workers if round_index==0 else min(16,args.workers)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                jobs={pool.submit(fetch,start):start for start in pending}
                for task in as_completed(jobs):
                    try:
                        completed+=task.result()
                    except Exception:
                        failed.append(jobs[task])
                        print('RETRY NEEDED '+name+' offset '+str(jobs[task]),flush=True)
                        continue
                    progress=dict(file=name,completed_bytes=completed,total_bytes=size,
                                  cached_bytes=cached_bytes,
                                  retry_round=round_index,
                                  elapsed_seconds=time.perf_counter()-started)
                    (args.destination/'range_progress.json').write_text(json.dumps(progress),encoding='utf-8')
                    if completed==size or completed//block%12==0:
                        downloaded=max(0,completed-cached_bytes)
                        print(f'PROGRESS {completed/size:.1%} new {downloaded/(time.perf_counter()-started)/1048576:.2f} MiB/s',flush=True)
            pending=failed
            if not pending:
                break
        if pending:
            raise RuntimeError('Incomplete ranges: '+name+' count '+str(len(pending)))
        target.parent.mkdir(parents=True,exist_ok=True)
        tmp=target.with_suffix('.part')
        digest=hashlib.sha256()
        with tmp.open('wb') as f:
            for start in offsets:
                data=(chunks/str(start)).read_bytes()
                digest.update(data);f.write(data)
        if digest.hexdigest()!=expected:
            raise ValueError('Official SHA256 mismatch: '+name)
        tmp.replace(target)
        print('VERIFIED '+name+' '+expected,flush=True)
    verified=dict(repository=REPO,revision=REVISION,
                  scope='All listed LFS files verified against official SHA256',
                  files=[dict(path=i.rfilename,bytes=i.size,sha256=i.lfs.sha256)
                         for i in info.siblings if i.lfs])
    (args.destination/'download_identity.json').write_text(json.dumps(verified,indent=2)+'\n',encoding='utf-8')
    print('MODEL WEIGHTS VERIFIED',flush=True)


if __name__=='__main__':
    main()
