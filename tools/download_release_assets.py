"""Download the published resource parts into their SHA256-indexed layout."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fnmatch
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='MeetyouTT/AUAR-KV260'
TAG='archive-20261103'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for data in iter(lambda:source.read(4*1024**2),b''):
            h.update(data)
    return h.hexdigest()


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT.parent/'release_assets')
    parser.add_argument('--index',type=Path,help='Use an already downloaded release_assets_index.json')
    parser.add_argument('--only',help='Download only original part paths matching this glob')
    parser.add_argument('--plan',action='store_true',help='Check the index and show the plan without writing files')
    args=parser.parse_args()
    expected={}
    with (ROOT/'inventory/release_payloads.jsonl').open(encoding='utf-8') as source:
        for line in source:
            row=json.loads(line)
            for part in row['parts']:
                expected[part['path']]=part
    if args.index:
        index=json.loads(args.index.read_text(encoding='utf-8'))
    else:
        url='https://github.com/'+REPOSITORY+'/releases/download/'+TAG+'/release_assets_index.json'
        request=urllib.request.Request(url,headers={'User-Agent':'AUAR-resource-download'})
        with urllib.request.urlopen(request,timeout=60) as response:
            raw=response.read(4*1024**2+1)
        if len(raw)>4*1024**2:
            raise RuntimeError('Unexpectedly large release index')
        index=json.loads(raw)
    if index['repository']!=REPOSITORY or index['release_tag']!=TAG:
        raise RuntimeError('Release index belongs to a different publication')
    parts=index['parts']
    if len(parts)!=len(expected) or {p['path'] for p in parts}!=set(expected):
        raise RuntimeError('Release index does not cover the local resource manifest')
    out=args.out.absolute()
    selected=[]
    for part in parts:
        reference=expected[part['path']]
        if part['sha256']!=reference['sha256'] or part['bytes']!=reference['bytes']:
            raise RuntimeError('Release index differs from the checked-in resource manifest')
        if part['path'].startswith(('/','\\')) or '..' in part['path'].replace('\\','/').split('/'):
            raise RuntimeError('Unsafe part path')
        target=(out/part['path']).resolve()
        target.relative_to(out.resolve())
        if type(part['asset_id']) is not int or part['asset_id']<=0:
            raise RuntimeError('Invalid GitHub asset ID')
        if args.only is None or fnmatch.fnmatchcase(part['path'],args.only):
            selected.append(part)
    if not selected:
        raise RuntimeError('No resource parts match the requested selection')
    if args.plan:
        print(json.dumps({'parts':len(selected),'bytes':sum(p['bytes'] for p in selected),'output':str(out),'writes_performed':False},ensure_ascii=False,indent=2))
        return

    def download(part):
        target=out/part['path']
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if target.stat().st_size!=part['bytes'] or digest(target)!=part['sha256']:
                raise RuntimeError('Existing file differs; choose a fresh output directory: '+part['path'])
            return {'path':part['path'],'status':'already_verified'}
        temporary=target.with_name(target.name+'.download')
        offset=temporary.stat().st_size if temporary.exists() else 0
        if offset>part['bytes']:
            raise RuntimeError('Partial download exceeds its declared size')
        if offset<part['bytes']:
            headers={'User-Agent':'AUAR-resource-download','Accept':'application/octet-stream'}
            if offset:
                headers['Range']='bytes='+str(offset)+'-'
            url='https://api.github.com/repos/'+REPOSITORY+'/releases/assets/'+str(part['asset_id'])
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as response:
                if offset and (response.status!=206 or not response.headers.get('Content-Range','').startswith('bytes '+str(offset)+'-')):
                    raise RuntimeError('Server did not accept resume; preserve the partial file and choose a fresh output directory')
                mode='ab' if temporary.exists() else 'xb'
                with temporary.open(mode) as output:
                    while True:
                        data=response.read(4*1024**2)
                        if not data:
                            break
                        output.write(data)
        if temporary.stat().st_size!=part['bytes'] or digest(temporary)!=part['sha256']:
            raise RuntimeError('Downloaded resource SHA256 mismatch: '+part['path'])
        if target.exists():
            raise RuntimeError('Output appeared while downloading; existing file preserved')
        temporary.rename(target)
        return {'path':part['path'],'status':'downloaded_and_verified'}

    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(download,selected):
            print(json.dumps(result,ensure_ascii=False),flush=True)
    print(json.dumps({'status':'PASS','verified_parts':len(selected),'output':str(out)},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
