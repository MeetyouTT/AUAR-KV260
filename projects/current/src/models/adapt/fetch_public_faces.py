"""Fetch checksum-pinned public LFW benchmark into a private local directory.

URLs and SHA256 are from scikit-learn's official datasets/_lfw.py.
No project enrollment images, identity database or audio are accessed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request

FILES = {
    'lfw-funneled.tgz': ('5976015', 'b47c8422c8cded889dc5a13418c4bc2abbda121092b3533a83306f90d900100a'),
    'pairsDevTrain.txt': ('5976012', '1d454dada7dfeca0e7eab6f65dc4e97a6312d44cf142207be28d688be92aabfa'),
    'pairsDevTest.txt': ('5976009', '7cb06600ea8b2814ac26e946201cdb304296262aad67d046a16a7ec85d0ff87c'),
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    records = []
    for name, (file_id, expected) in FILES.items():
        path = args.directory / name
        if not path.exists():
            partial = path.with_suffix(path.suffix + '.partial')
            url = 'https://ndownloader.figshare.com/files/' + file_id
            with urllib.request.urlopen(url, timeout=45) as response, partial.open('wb') as f:
                total = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    f.write(block)
                    total += len(block)
                    if total % (32 * 1024 * 1024) < len(block):
                        print(json.dumps({'file': name, 'downloaded_bytes': total}), flush=True)
            if digest(partial) != expected:
                raise ValueError('Public dataset checksum mismatch: ' + name)
            partial.rename(path)
        if digest(path) != expected:
            raise ValueError('Existing public dataset checksum mismatch: ' + name)
        records.append({'file': name, 'sha256': expected, 'bytes': path.stat().st_size})
    destination = args.directory / 'lfw_funneled'
    marker = args.directory / 'extraction_complete.json'
    if not marker.exists():
        count = 0
        with tarfile.open(args.directory / 'lfw-funneled.tgz', 'r:gz') as archive:
            for member in archive:
                relative = Path(member.name)
                if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'lfw_funneled':
                    raise ValueError('Unsafe archive path')
                if member.isdir():
                    continue
                # The pinned official archive also contains eleven pair lists.
                # We use the separately checksum-pinned development splits.
                if member.isfile() and len(relative.parts) == 2 and relative.name in (
                    ['pairs.txt'] + ['pairs_%02d.txt' % i for i in range(1, 11)]
                ):
                    continue
                if not member.isfile() or relative.suffix.lower() != '.jpg' or member.size > 2 * 1024 * 1024:
                    raise ValueError('Unexpected archive entry')
                target = args.directory / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as src, target.open('wb') as dst:
                    dst.write(src.read())
                count += 1
        marker.write_text(json.dumps({'images': count, 'files': records}, indent=2) + '\n')
    print(json.dumps({'status': 'PUBLIC_BENCHMARK_FETCHED', 'files': records,
                      'image_count': len(list(destination.glob('*/*.jpg'))),
                      'redistributed_images': False}), flush=True)


if __name__ == '__main__':
    main()
