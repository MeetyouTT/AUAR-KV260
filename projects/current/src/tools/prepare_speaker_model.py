"""Provision a fixed official model into an external local directory."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import time

REPO = 'speechbrain/spkrec-ecapa-voxceleb'
REVISION = '0f99f2d0ebe89ac095bcc5903c4dd8f72b367286'
FILES = ('hyperparams.yaml', 'embedding_model.ckpt', 'classifier.ckpt',
         'mean_var_norm_emb.ckpt', 'label_encoder.txt')


def download_ranges(url, target, size):
    """Bounded HTTP ranges for CDN connections that stall on large responses."""
    chunk_size = 1024*1024
    def fetch(start):
        end = min(start+chunk_size, size)-1
        for attempt in range(3):
            try:
                request = urllib.request.Request(url+'?range_start='+str(start),
                                                 headers={'Range': f'bytes={start}-{end}'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{size}':
                        raise ValueError('CDN did not honor exact byte range')
                    data = response.read(end-start+2)
                if len(data) != end-start+1:
                    raise ValueError('Incomplete byte range')
                return start, data
            except Exception:
                if attempt == 2: raise
                time.sleep(1)
    prefix = (target.stat().st_size//chunk_size)*chunk_size if target.exists() else 0
    prefix = min(prefix,size)
    with target.open('r+b' if target.exists() else 'wb') as output, ThreadPoolExecutor(max_workers=12) as pool:
        output.truncate(prefix)
        for index, (start,data) in enumerate(pool.map(fetch, range(prefix,size,chunk_size))):
            output.seek(start); output.write(data); output.flush()
            if index % 8 == 0:
                print(json.dumps({'download':target.name,'bytes_written':start+len(data),'total':size}),flush=True)


def provision(directory):
    directory = Path(directory).resolve()
    workspace = Path(__file__).resolve().parents[3]
    if directory == workspace or workspace in directory.parents:
        raise ValueError('Model files must stay outside the shared workspace')
    directory.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true', timeout=60) as response:
        metadata = json.load(response)
    if metadata['sha'] != REVISION:
        raise ValueError('Unexpected remote revision')
    siblings = {row['rfilename']: row for row in metadata['siblings']}
    hashes = {}
    for name in FILES:
        target = directory/name
        part = directory/(name+'.part')
        row = siblings[name]
        def verified(path):
            if not path.is_file() or path.stat().st_size != row['size']:
                return False
            raw = path.read_bytes()
            if 'lfs' in row:
                return hashlib.sha256(raw).hexdigest() == row['lfs']['sha256']
            return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == row['blobId']
        if not verified(target):
            url = f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}'
            if row['size'] > 1024*1024:
                download_ranges(url, part, row['size'])
            else:
                with urllib.request.urlopen(url, timeout=30) as response, part.open('wb') as output:
                    output.write(response.read())
            if not verified(part):
                raise ValueError('Downloaded file failed upstream hash: '+name)
            part.replace(target)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        print(json.dumps({'verified_file': name, 'bytes': target.stat().st_size}), flush=True)
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    manifest = {'repository': REPO, 'revision': REVISION, 'sha256': hashes,
                'model_id': 'ecapa-voxceleb-'+fingerprint}
    (directory/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(provision(args.directory), indent=2))
