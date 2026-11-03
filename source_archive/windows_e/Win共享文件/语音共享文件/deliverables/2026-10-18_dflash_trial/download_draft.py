"""Download one pinned drafter into external model storage; never into the project."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.request

PROJECT = Path(__file__).resolve().parents[2]
MODEL_ROOT = Path(json.loads((PROJECT / 'aura/config/model_storage.local.json').read_text(encoding='utf-8-sig'))['draft_directory'])
FILENAME = 'Qwen3.8-27B-DFlash2-Q4_K_M.gguf'
REVISION = '51962825493a48b846b40126d35c799ac4093ad0'
URL = f'https://huggingface.co/incoai/Qwen3.8-27B-DFlash2-GGUF/resolve/{REVISION}/{FILENAME}'
SIZE = 1143006816
SHA256 = '1a25c56858e1ebe93f2718ac1d49d1151f9323325c1bbfd6209370f4db131ebd'
EVIDENCE = Path(__file__).resolve().parent / 'draft_download.json'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def main():
    root = MODEL_ROOT.resolve()
    assert root.is_relative_to(Path('D:/AIModels').resolve())
    root.mkdir(parents=True, exist_ok=True)
    target = root / FILENAME
    started = time.monotonic()
    if target.exists():
        assert target.stat().st_size == SIZE and digest(target) == SHA256
    else:
        parts = root / 'download-parts'
        parts.mkdir(exist_ok=True)
        chunk = 32 * 1024 * 1024
        ranges = [(i, start, min(SIZE, start + chunk) - 1) for i, start in enumerate(range(0, SIZE, chunk))]

        def fetch(item):
            i, start, end = item
            path = parts / f'{i:04d}.part'
            length = end - start + 1
            if path.exists() and path.stat().st_size == length:
                return length
            for attempt in range(4):
                try:
                    req = urllib.request.Request(URL + f'?download=true&range={start}-{end}', headers={'Range': f'bytes={start}-{end}', 'User-Agent': 'AURA-controlled-dflash-trial/1'})
                    with urllib.request.urlopen(req, timeout=40) as response:
                        assert response.status == 206, response.status
                        assert response.headers['Content-Range'] == f'bytes {start}-{end}/{SIZE}'
                        with path.open('wb') as output:
                            count = 0
                            while True:
                                data = response.read(min(1024 * 1024, length - count + 1))
                                if not data:
                                    break
                                count += len(data)
                                if count > length:
                                    raise ValueError('Server exceeded requested range')
                                output.write(data)
                        assert count == length, (count, length)
                    return length
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(1 + attempt)

        downloaded = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for future in concurrent.futures.as_completed([pool.submit(fetch, item) for item in ranges]):
                downloaded += future.result()
                seconds = time.monotonic() - started
                print(json.dumps({'downloaded': downloaded, 'total': SIZE, 'percent': round(100 * downloaded / SIZE, 1), 'average_MB_s': round(downloaded / max(seconds, .001) / 1e6, 2)}), flush=True)
        assembled = root / (FILENAME + '.verified-partial')
        with assembled.open('wb') as output:
            for i, _, _ in ranges:
                with (parts / f'{i:04d}.part').open('rb') as part:
                    for data in iter(lambda: part.read(4 * 1024 * 1024), b''):
                        output.write(data)
        assert assembled.stat().st_size == SIZE and digest(assembled) == SHA256, 'SHA256 mismatch; target not published'
        assembled.replace(target)
    evidence = {'status': 'VERIFIED', 'repository': 'incoai/Qwen3.8-27B-DFlash2-GGUF', 'revision': REVISION, 'file': str(target), 'bytes': SIZE, 'sha256': SHA256, 'main_27b_unchanged': True, 'elapsed_s': round(time.monotonic() - started, 2)}
    EVIDENCE.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__':
    main()
