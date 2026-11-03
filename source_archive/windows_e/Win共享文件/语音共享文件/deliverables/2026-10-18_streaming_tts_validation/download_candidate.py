"""Pinned independent speech candidate. All weights and parts stay on D:."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import threading
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = Path('D:/AIModels/cosyvoice3-streaming-validation')
REV = 'ab01740bbbfcc059fd748163787554f7c8977e64'
FILES = [
    ('CosyVoice3-2512_Q8_0.gguf', 943933536, 'be133cb6154ca73cd1d213b1c9496def99ba9c1f7c14cd99f6b350af2eb7963d'),
    ('frontend-onnx/speech_tokenizer_v3.int8.onnx', 244237335, 'd7caa04fbc2f54af196906469471b607ce2594b7e92ac07dddfb315103a74c72'),
    ('frontend-onnx/campplus.int8.onnx', 8654637, '96b05369863f6cad4a3905206bb376915c2d61af0db16508eeaf2910a0c8a80a'),
]

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def main():
    assert ROOT.resolve().is_relative_to(Path('D:/AIModels').resolve())
    ROOT.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = {'status': 'DOWNLOADING', 'revision': REV, 'directory': str(ROOT), 'files': []}
    for filename, size, sha in FILES:
        dest = ROOT / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not (dest.exists() and dest.stat().st_size == size and digest(dest) == sha):
            parts = ROOT / 'download-parts' / Path(filename).name
            parts.mkdir(parents=True, exist_ok=True)
            chunk = 16 * 1024 * 1024
            ranges = [(i, start, min(size, start + chunk) - 1) for i, start in enumerate(range(0, size, chunk))]
            count = [0]
            lock = threading.Lock()
            def fetch(item):
                i, start, end = item
                path = parts / f'{i:04d}.part'
                length = end - start + 1
                if path.exists() and path.stat().st_size == length: return length
                url = f'https://huggingface.co/Lourdle/Fun-CosyVoice3-0.5B-2512-GGUF/resolve/{REV}/{filename}?download=true&range={start}-{end}'
                for attempt in range(4):
                    try:
                        req = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}', 'User-Agent': 'AURA-speech-validation/1'})
                        with urllib.request.urlopen(req, timeout=45) as response:
                            assert response.status == 206
                            assert response.headers['Content-Range'] == f'bytes {start}-{end}/{size}'
                            data = response.read(length + 1)
                            assert len(data) == length
                            path.write_bytes(data)
                        return length
                    except Exception:
                        if attempt == 3: raise
                        time.sleep(attempt + 1)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                for future in concurrent.futures.as_completed([pool.submit(fetch, item) for item in ranges]):
                    count[0] += future.result()
                    progress = {'file': filename, 'bytes': count[0], 'total': size, 'percent': round(count[0] * 100 / size, 1), 'elapsed_s': round(time.monotonic() - started, 1)}
                    (HERE / 'download_progress.json').write_text(json.dumps(progress), encoding='utf-8')
                    print(json.dumps(progress), flush=True)
            partial = dest.with_name(dest.name + '.verified-partial')
            with partial.open('wb') as f:
                for i, _, _ in ranges:
                    with (parts / f'{i:04d}.part').open('rb') as p:
                        for block in iter(lambda: p.read(4 * 1024 * 1024), b''): f.write(block)
            assert partial.stat().st_size == size and digest(partial) == sha
            partial.replace(dest)
        report['files'].append({'path': str(dest), 'size': size, 'sha256': sha})
        (HERE / 'download.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    report.update(status='VERIFIED', elapsed_s=round(time.monotonic() - started, 2))
    (HERE / 'download.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)

if __name__ == '__main__': main()
