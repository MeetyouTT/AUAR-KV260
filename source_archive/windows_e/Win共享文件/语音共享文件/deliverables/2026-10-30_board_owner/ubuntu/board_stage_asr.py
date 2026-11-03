"""Stage only reviewed ASR assets under a fresh independent candidate root.

No baseenv install, service changes, microphone, playback, identity access, or
model downloads: existing Paraformer files plus same-version official wheels.
"""
import hashlib
import json
from pathlib import Path
import shutil
import signal
import time
import urllib.request
import zipfile

BASE = 'http://192.168.50.1:54623'
# Filled from the frozen public manifest served by the Windows whitelist host.
MANIFEST_SHA256 = '93325b10634fe281d61651f5b25d880bbfd2ff531305efc87ea259f39bd2d7e1'
ROOT = Path('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    signal.alarm(48)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(BASE+'/manifest.json',timeout=4) as response:raw=response.read(65537)
    assert len(raw)<=65536 and hashlib.sha256(raw).hexdigest()==MANIFEST_SHA256
    manifest=json.loads(raw)
    assert manifest['purpose']=='same_model_public_asr_candidate'
    assert manifest['candidate_root']==str(ROOT) and manifest['total_bytes']<300*1024*1024
    assert not ROOT.is_symlink() and shutil.disk_usage('/home/root').free>800*1024*1024
    ROOT.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();assets=[]
    for entry in manifest['entries']:
        relative=Path(entry['name'])
        assert not relative.is_absolute() and '..' not in relative.parts
        path=ROOT/relative
        assert ROOT.resolve() in path.resolve().parents and not path.is_symlink()
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            partial=path.with_name(path.name+'.partial')
            with opener.open(BASE+'/assets/'+entry['sha256'],timeout=6) as response, partial.open('xb') as out:
                while True:
                    block=response.read(1024*1024)
                    if not block:break
                    out.write(block)
            assert partial.stat().st_size==entry['bytes'] and sha(partial)==entry['sha256']
            partial.rename(path)
        assert path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256']
        assets.append({k:entry[k] for k in ('name','bytes','sha256')})
    deps=ROOT/'deps'
    deps.mkdir(exist_ok=True)
    for wheel in sorted((ROOT/'wheels').glob('*.whl'),reverse=True):
        with zipfile.ZipFile(str(wheel)) as archive:
            for item in archive.infolist():
                relative=Path(item.filename)
                assert not relative.is_absolute() and '..' not in relative.parts
                target=deps/relative
                assert deps.resolve() in target.resolve().parents
                assert not target.is_symlink() and (item.external_attr>>16)&0o170000!=0o120000
                if item.is_dir():target.mkdir(parents=True,exist_ok=True);continue
                target.parent.mkdir(parents=True,exist_ok=True)
                data=archive.read(item)
                if target.exists():assert target.read_bytes()==data
                else:
                    with target.open('xb') as out:out.write(data)
    signal.alarm(0)
    print(json.dumps(dict(candidate_root=str(ROOT),assets=assets,
        elapsed_seconds=round(time.monotonic()-started,3),production_changed=False,
        baseenv_changed=False,model_loads=0,hardware_actions=0)))


if __name__=='__main__':main()
