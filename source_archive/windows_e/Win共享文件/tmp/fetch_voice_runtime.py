"""Fetch official Windows CUDA wheels with bounded, resumable range requests."""
import concurrent.futures
import hashlib
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'qwen-audition-wheels'
ROOT.mkdir(exist_ok=True)
CHUNK = 32 * 1024 * 1024
TIMEOUT = 120
LOCK = threading.Lock()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(value for name, value in attrs if name == 'href')


def published(package):
    page = 'https://download.pytorch.org/whl/cu128/' + package + '/'
    with urllib.request.urlopen(page, timeout=TIMEOUT) as response:
        parser = Links()
        parser.feed(response.read().decode())
    for href in parser.links:
        full = urllib.parse.urljoin(page, href)
        parsed = urllib.parse.urlsplit(full)
        filename = urllib.parse.unquote(parsed.path.rsplit('/', 1)[-1])
        if filename == package + '-2.8.0+cu128-cp312-cp312-win_amd64.whl':
            expected = urllib.parse.parse_qs(parsed.fragment).get('sha256', [None])[0]
            if not expected or not re.fullmatch('[a-f0-9]{64}', expected):
                raise ValueError('No official SHA256 was supplied')
            url = urllib.parse.urlunsplit(('https', 'download.pytorch.org', parsed.path, '', ''))
            return filename, url, expected
    raise ValueError('Official wheel was not found: ' + package)


def fetch(package):
    filename, url, expected = published(package)
    target = ROOT / filename
    if target.exists():
        if hashlib.file_digest(target.open('rb'), 'sha256').hexdigest() == expected:
            print('VERIFIED existing ' + filename, flush=True)
            return {'file': str(target), 'sha256': expected, 'source': url}
        raise ValueError('Existing wheel does not match official hash')
    req = urllib.request.Request(url, headers={'Range': 'bytes=0-0'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
        if response.status != 206 or not match:
            raise ValueError('Official CDN did not advertise byte range support')
        total = int(match[3])
    parts = ROOT / (filename + '.parts')
    parts.mkdir(exist_ok=True)
    count = (total + CHUNK - 1) // CHUNK
    done = [0]
    print(f'DOWNLOADING {filename}: {total / 2**20:.1f} MiB in {count} parts', flush=True)

    def part(index):
        start = index * CHUNK
        end = min(total, start + CHUNK) - 1
        size = end - start + 1
        dst = parts / f'{index:04d}.part'
        if not dst.exists() or dst.stat().st_size != size:
            temporary = dst.with_suffix('.working')
            for attempt in range(4):
                try:
                    # Stable per-part URL prevents intermediary caches reusing a different range.
                    part_url = url + '?part=' + str(index)
                    request = urllib.request.Request(part_url, headers={'Range': f'bytes={start}-{end}'})
                    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                        expected_range = f'bytes {start}-{end}/{total}'
                        if response.status != 206 or response.headers.get('Content-Range') != expected_range:
                            raise ValueError('Mismatched CDN range: ' + str(response.headers.get('Content-Range')))
                        read = 0
                        with temporary.open('wb') as stream:
                            while block := response.read(1024 * 1024):
                                read += len(block)
                                if read > size:
                                    raise ValueError('Range exceeded expected size')
                                stream.write(block)
                    if read != size:
                        raise ValueError('Incomplete range')
                    os.replace(temporary, dst)
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(1 + attempt)
        with LOCK:
            done[0] += 1
            if done[0] % 8 == 0 or done[0] == count:
                print(f'PROGRESS {package}: {done[0]}/{count} parts', flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(part, range(count)))
    assembly = target.with_suffix('.assembling')
    digest = hashlib.sha256()
    with assembly.open('wb') as stream:
        for index in range(count):
            with (parts / f'{index:04d}.part').open('rb') as source:
                while block := source.read(8 * 1024 * 1024):
                    digest.update(block)
                    stream.write(block)
    if assembly.stat().st_size != total or digest.hexdigest() != expected:
        raise ValueError('Downloaded wheel does not match official SHA256')
    os.replace(assembly, target)
    print('VERIFIED ' + filename, flush=True)
    return {'file': str(target), 'sha256': expected, 'size': total, 'source': url}


if __name__ == '__main__':
    records = [fetch(name) for name in ('torch', 'torchaudio')]
    (ROOT / 'official_downloads.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
