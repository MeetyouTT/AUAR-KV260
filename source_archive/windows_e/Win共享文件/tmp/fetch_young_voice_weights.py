"""Bounded range download of the public, fixed-revision official VoiceDesign weight."""
import concurrent.futures
import hashlib
import json
import os
import threading
import time
import urllib.request
from pathlib import Path

BASE = Path('E:/项目/tmp')
TARGET = BASE / 'Qwen3-TTS-12Hz-1.7B-VoiceDesign/model.safetensors'
METADATA = Path('E:/项目/共享文件夹/deliverables/2026-10-06_voice_design_young/official_model_metadata.json')
CHUNK = 32 * 1024 * 1024
LOCK = threading.Lock()


def main():
    metadata = json.loads(METADATA.read_text(encoding='utf-8'))
    entry = next(row for row in metadata['siblings'] if row['rfilename'] == 'model.safetensors')
    total = entry['size']
    expected_hash = entry['lfs']['sha256']
    url = 'https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign/resolve/' + metadata['sha'] + '/model.safetensors'
    if TARGET.exists():
        with TARGET.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() == expected_hash:
                print('VERIFIED existing VoiceDesign weight', flush=True)
                return
        raise ValueError('Existing weight differs from official metadata')
    parts = BASE / 'qwen-young-voice-weight-parts'
    parts.mkdir(exist_ok=True)
    count = (total + CHUNK - 1) // CHUNK
    done = [0]
    print(f'DOWNLOADING official weight: {total / 2**20:.1f} MiB, {count} parts', flush=True)

    def download(index):
        start = index * CHUNK
        end = min(total, start + CHUNK) - 1
        size = end - start + 1
        destination = parts / f'{index:04d}.part'
        if not destination.exists() or destination.stat().st_size != size:
            temporary = destination.with_suffix('.working')
            for attempt in range(4):
                try:
                    if destination.exists() and destination.stat().st_size == size:
                        break
                    offset = temporary.stat().st_size if temporary.exists() else 0
                    if offset > size:
                        raise ValueError('Retained range exceeded its expected size')
                    if offset == size:
                        os.replace(temporary, destination)
                        break
                    range_start = start + offset
                    request = urllib.request.Request(url + '?download=true&part=' + str(index),
                                                     headers={'Range': f'bytes={range_start}-{end}'})
                    deadline = time.monotonic() + 240
                    with urllib.request.urlopen(request, timeout=90) as response:
                        if response.status != 206 or response.headers.get('Content-Range') != f'bytes {range_start}-{end}/{total}':
                            raise ValueError('Range response did not match requested bytes')
                        received = offset
                        with temporary.open('ab' if offset else 'wb') as stream:
                            while block := response.read(1024 * 1024):
                                received += len(block)
                                if received > size or time.monotonic() > deadline:
                                    raise ValueError('Range exceeded size or time bound')
                                stream.write(block)
                    if received != size:
                        raise ValueError('Incomplete range')
                    os.replace(temporary, destination)
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(1 + attempt)
        with LOCK:
            done[0] += 1
            if done[0] % 8 == 0 or done[0] == count:
                print(f'PROGRESS official VoiceDesign: {done[0]}/{count} parts', flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(download, range(count)))
    assembly = TARGET.with_suffix('.assembling')
    digest = hashlib.sha256()
    with assembly.open('wb') as stream:
        for index in range(count):
            with (parts / f'{index:04d}.part').open('rb') as source:
                while block := source.read(8 * 1024 * 1024):
                    digest.update(block)
                    stream.write(block)
    if assembly.stat().st_size != total or digest.hexdigest() != expected_hash:
        raise ValueError('Official weight SHA256 did not match')
    os.replace(assembly, TARGET)
    print('VERIFIED official VoiceDesign weight SHA256', flush=True)


if __name__ == '__main__':
    main()
