"""Compare a local AURA copy with the required ASR source/model manifest."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aura-root',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,default=Path(__file__).with_name('ASR_REQUIRED_FILES.json'))
    parser.add_argument('--files-only',action='store_true')
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    rows=[]
    for name,expected in manifest['files'].items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Invalid manifest path')
        path=args.aura_root/relative
        row={'path':name,'status':'MISSING'}
        if path.is_file():
            row.update(bytes=path.stat().st_size,sha256=digest(path))
            row['status']='MATCH' if row['bytes']==expected['bytes'] and row['sha256']==expected['sha256'] else 'DIFFERENT'
        rows.append(row)
    packages={}
    for name in ('sherpa-onnx','sherpa-onnx-core','numpy'):
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    files_ok=all(row['status']=='MATCH' for row in rows)
    packages_ok=(packages['sherpa-onnx']==packages['sherpa-onnx-core']=='1.13.8' and bool(packages['numpy']))
    report={'scope':'FILES_AND_INSTALLED_PACKAGE_METADATA_ONLY','aura_root':str(args.aura_root.resolve()),
            'files_match':files_ok,'matched':sum(r['status']=='MATCH' for r in rows),
            'required_files':len(rows),'files':rows,'python':sys.executable,'python_version':platform.python_version(),
            'packages':packages,'package_versions_match':packages_ok,'actual_recognition_and_network_verified':False}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if files_ok and (args.files_only or packages_ok) else 1


if __name__=='__main__':raise SystemExit(main())
