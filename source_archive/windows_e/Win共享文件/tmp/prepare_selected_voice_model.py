"""Download and verify the fixed-revision official Qwen Base model."""
import concurrent.futures
import fnmatch
import hashlib
import json
import os
import shutil
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path('E:/项目/tmp')
TARGET = BASE / 'Qwen3-TTS-12Hz-1.7B-Base'
REPORT = Path('E:/项目/共享文件夹/deliverables/2026-10-06_voice_selected_soft_young')
REPO = 'Qwen/Qwen3-TTS-12Hz-1.7B-Base'
CHUNK = 32 * 1024 * 1024
LOCK = threading.Lock()


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git_blob_sha1(path):
    size = path.stat().st_size
    digest = hashlib.sha1(b'blob ' + str(size).encode() + b'\0')
    with path.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def verify(path, entry):
    if not path.is_file() or path.stat().st_size != entry['size']:
        return False
    return (sha256(path) == entry['lfs']['sha256']) if entry.get('lfs') else (git_blob_sha1(path) == entry['blobId'])


def url_for(revision, relative, suffix=''):
    path = urllib.parse.quote(relative, safe='/')
    return f'https://huggingface.co/{REPO}/resolve/{revision}/{path}' + suffix


def range_download(entry, revision):
    relative = entry['rfilename']
    target = TARGET / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if verify(target, entry):
        print('VERIFIED existing ' + relative, flush=True)
        return
    total = entry['size']
    expected = entry['lfs']['sha256']
    parts = BASE / 'qwen-selected-voice-weight-parts'
    parts.mkdir(exist_ok=True)
    count = (total + CHUNK - 1) // CHUNK
    done = [0]
    print(f'DOWNLOADING {relative}: {total / 2**20:.1f} MiB, {count} parts', flush=True)

    def part(index):
        start = index * CHUNK
        end = min(total, start + CHUNK) - 1
        size = end - start + 1
        destination = parts / f'{index:04d}.part'
        if destination.exists() and destination.stat().st_size == size:
            with LOCK:
                done[0] += 1
            return
        temporary = destination.with_suffix('.working')
        for attempt in range(4):
            try:
                offset = temporary.stat().st_size if temporary.exists() else 0
                if offset > size:
                    raise ValueError('Retained range exceeds expected size')
                if offset == size:
                    os.replace(temporary, destination)
                    break
                range_start = start + offset
                request = urllib.request.Request(
                    url_for(revision, relative, '?download=true&part=' + str(index)),
                    headers={'Range': f'bytes={range_start}-{end}'})
                deadline = time.monotonic() + 240
                with urllib.request.urlopen(request, timeout=90) as response:
                    expected_range = f'bytes {range_start}-{end}/{total}'
                    if response.status != 206 or response.headers.get('Content-Range') != expected_range:
                        raise ValueError('Mismatched range response')
                    received = offset
                    with temporary.open('ab' if offset else 'wb') as stream:
                        while block := response.read(1024 * 1024):
                            received += len(block)
                            if received > size or time.monotonic() > deadline:
                                raise ValueError('Range exceeded bounds')
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
                print(f'PROGRESS Base: {done[0]}/{count} parts', flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(part, range(count)))
    assembly = target.with_suffix('.assembling')
    digest = hashlib.sha256()
    with assembly.open('wb') as output:
        for index in range(count):
            with (parts / f'{index:04d}.part').open('rb') as source:
                while block := source.read(8 * 1024 * 1024):
                    digest.update(block)
                    output.write(block)
    if assembly.stat().st_size != total or digest.hexdigest() != expected:
        raise ValueError('Final Base model SHA256 mismatch')
    os.replace(assembly, target)
    print('VERIFIED Base model weight SHA256', flush=True)


def main():
    REPORT.mkdir(exist_ok=True)
    with urllib.request.urlopen('https://huggingface.co/api/models/' + REPO + '?blobs=true', timeout=90) as response:
        metadata = json.load(response)
    revision = metadata['sha']
    (REPORT / 'official_base_model_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    patterns = ['*.json', '*.txt', '*.safetensors', 'speech_tokenizer/*']
    entries = [entry for entry in metadata['siblings'] if any(fnmatch.fnmatch(entry['rfilename'], pattern) for pattern in patterns)]
    for entry in entries:
        relative = entry['rfilename']
        target = TARGET / relative
        if verify(target, entry):
            continue
        reused = False
        for model in ('Qwen3-TTS-12Hz-1.7B-VoiceDesign', 'Qwen3-TTS-12Hz-1.7B-CustomVoice'):
            source = BASE / model / relative
            if verify(source, entry):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                reused = True
                print('REUSED verified ' + relative, flush=True)
                break
        if reused:
            continue
        if entry.get('lfs') and entry['size'] > 128 * 1024 * 1024:
            range_download(entry, revision)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + '.tmp')
            with urllib.request.urlopen(url_for(revision, relative), timeout=90) as response:
                temporary.write_bytes(response.read())
            if not verify(temporary, entry):
                raise ValueError('Downloaded file failed verification: ' + relative)
            os.replace(temporary, target)
            print('VERIFIED ' + relative, flush=True)
    checked = []
    for entry in entries:
        path = TARGET / entry['rfilename']
        if not verify(path, entry):
            raise ValueError('Final model verification failed: ' + entry['rfilename'])
        checked.append({'file': entry['rfilename'], 'bytes': entry['size'],
                        'hash': entry.get('lfs', {}).get('sha256') or entry['blobId'],
                        'hash_type': 'SHA256' if entry.get('lfs') else 'Git blob SHA1'})
    report = {'status': 'PASS', 'model': REPO, 'revision': revision,
              'model_path': str(TARGET), 'files': checked}
    (REPORT / 'base_model_verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS: verified Base model ' + revision, flush=True)


if __name__ == '__main__':
    main()
