"""Download pinned CPU wheels outside the workspace; install into a given venv."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

from prepare_speaker_model import download_ranges

EXPECTED_SHA256 = {
    'torch': 'a6b720410350765d3d77c01a5ce098a6c45af446284e45e87a98b8a16e7d564d',
    'torchaudio': '68b58c1dae7bb738df8a36f0d147d2c9c69e56a35ff40dedb84ac30aff2e59e1',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--dependency-plan',type=Path,
                        help='Optional pip dry-run report with fully resolved wheel URLs')
    args = parser.parse_args()
    root = args.root.resolve()
    workspace = Path(__file__).resolve().parents[3]
    if root == workspace or workspace in root.parents:
        raise ValueError('Runtime and downloads must be external')
    wheels = root/'wheels'; wheels.mkdir(parents=True, exist_ok=True)
    python = root/'venv/Scripts/python.exe'
    hashes = {}
    for package in ('torch', 'torchaudio'):
        name = f'{package}-2.5.1+cpu-cp312-cp312-win_amd64.whl'
        path = wheels/name
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_SHA256[package]:
            hashes[name] = EXPECTED_SHA256[package]
            continue
        url = 'https://download.pytorch.org/whl/cpu/'+name.replace('+','%2B')
        request = urllib.request.Request(url+'?probe=1',headers={'Range':'bytes=0-1023'})
        with urllib.request.urlopen(request,timeout=30) as response:
            if response.status != 206: raise ValueError('Expected range support')
            size = int(response.headers['Content-Range'].split('/')[-1])
        if not path.is_file() or path.stat().st_size != size:
            part = wheels/(name+'.part')
            download_ranges(url,part,size)
            part.replace(path)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if hashes[name] != EXPECTED_SHA256[package]:
            raise ValueError('Official wheel hash mismatch: '+name)
    (root/'wheel-sha256.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    packages = [str(wheels/name) for name in hashes] + [
        'speechbrain==1.0.3','huggingface-hub==0.36.0','webrtcvad-wheels==2.0.14']
    if args.dependency_plan:
        plan = json.loads(args.dependency_plan.read_text(encoding='utf-8'))
        packages = []
        for row in plan['install']:
            info = row['download_info']
            packages.append(info['url']+'#sha256='+info['archive_info']['hashes']['sha256'])
    subprocess.run([str(python),'-m','pip','install','--disable-pip-version-check',
                    *(['--no-index'] if args.dependency_plan else []), *packages],check=True)
    with (root/'requirements.lock.txt').open('w',encoding='utf-8') as output:
        subprocess.run([str(python),'-m','pip','freeze'],stdout=output,check=True)


if __name__ == '__main__': main()
