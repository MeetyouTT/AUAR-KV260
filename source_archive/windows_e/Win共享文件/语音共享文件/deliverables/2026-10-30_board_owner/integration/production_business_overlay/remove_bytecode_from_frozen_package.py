"""Create a separate source-only revision; never overwrite frozen inputs."""
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent


def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    original=HERE/'production_business.overlay.zip';original_manifest=HERE/'production_business.manifest.json'
    assert sha(original.read_bytes())=='84f61727a69e79254335de8e279fba0e5bdc176ed232d5be3eb1fb51e42aab6c'
    assert sha(original_manifest.read_bytes())=='6925a7262db0a34d4e129f5a1976e82f08d6b10c552e4eb577f33685a143f8c1'
    manifest=json.loads(original_manifest.read_bytes())
    removed={name:row for name,row in manifest['files'].items() if '__pycache__' in Path(name).parts and name.endswith('.pyc')}
    assert len(removed)==71 and set(removed)<=manifest['overlay_files'].keys()
    payload={}
    with zipfile.ZipFile(original) as z:
        for name in z.namelist():
            raw=z.read(name);assert sha(raw)==manifest['overlay_files'][name]['sha256']
            if name not in removed:payload[name]=raw
    dest=HERE/'production_business.source_only.overlay.zip'
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(payload.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100600<<16
            z.writestr(info,raw)
    manifest['files']={name:row for name,row in manifest['files'].items() if name not in removed}
    manifest['overlay_files']={name:row for name,row in manifest['overlay_files'].items() if name not in removed}
    manifest['overlay_sha256']=sha(dest.read_bytes())
    manifest['source_only_revision']=2
    manifest['source_cache_exclusions']=removed
    manifest['original_overlay_sha256']=sha(original.read_bytes())
    raw=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    (HERE/'production_business.source_only.manifest.json').write_bytes(raw)
    print(json.dumps({'files':len(manifest['files']),'delta_files':len(payload),'removed_bytecode':len(removed),
        'overlay_sha256':sha(dest.read_bytes()),'manifest_sha256':sha(raw),'all_noncache_bytes_unchanged':True}))


if __name__=='__main__':main()
