"""Download and verify the official VoiceDesign model; reuse an identical tokenizer."""
import fnmatch
import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

from huggingface_hub import snapshot_download

BASE = Path('E:/项目/tmp')
TARGET = BASE / 'Qwen3-TTS-12Hz-1.7B-VoiceDesign'
REPORT = Path('E:/项目/共享文件夹/deliverables/2026-10-06_voice_design_young')
REPO = 'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign'


def digest_file(path, algorithm='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def expected_hash(entry):
    return entry.get('lfs', {}).get('sha256') or entry['blobId']


def verify(entry):
    path = (TARGET / entry['rfilename']).resolve()
    if not path.is_relative_to(TARGET.resolve()) or not path.is_file():
        raise ValueError('Missing model file: ' + entry['rfilename'])
    size = path.stat().st_size
    if size != entry['size']:
        raise ValueError('Wrong model file size: ' + entry['rfilename'])
    if entry.get('lfs'):
        actual = digest_file(path)
    else:
        digest = hashlib.sha1(b'blob ' + str(size).encode() + b'\0')
        digest.update(path.read_bytes())
        actual = digest.hexdigest()
    if actual != expected_hash(entry):
        raise ValueError('Wrong model file hash: ' + entry['rfilename'])
    return {'file': entry['rfilename'], 'bytes': size, 'official_hash': actual,
            'hash_type': 'SHA256' if entry.get('lfs') else 'Git blob SHA1'}


def main(verify_only=False):
    if verify_only:
        metadata = json.loads((REPORT / 'official_model_metadata.json').read_text(encoding='utf-8'))
    else:
        with urllib.request.urlopen('https://huggingface.co/api/models/' + REPO + '?blobs=true', timeout=90) as response:
            metadata = json.load(response)
    revision = metadata['sha']
    patterns = ['*.json', '*.txt', '*.safetensors', 'speech_tokenizer/*']
    selected = [entry for entry in metadata['siblings'] if any(fnmatch.fnmatch(entry['rfilename'], pattern) for pattern in patterns)]
    REPORT.mkdir(exist_ok=True)
    (REPORT / 'official_model_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tokenizer = next(entry for entry in selected if entry['rfilename'] == 'speech_tokenizer/model.safetensors')
    source = BASE / 'Qwen3-TTS-12Hz-1.7B-CustomVoice' / tokenizer['rfilename']
    destination = TARGET / tokenizer['rfilename']
    ignored = []
    if source.exists() and source.stat().st_size == tokenizer['size'] and digest_file(source) == expected_hash(tokenizer):
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)
        verify(tokenizer)
        ignored.append(tokenizer['rfilename'])
        print('REUSED verified official speech tokenizer', flush=True)
    print('DOWNLOADING official VoiceDesign revision ' + revision, flush=True)
    failure = 'Original snapshot transfer was cancelled after stale directory-entry size was misread as stalled. Received bytes were retained and reused; final official HTTPS range transfer verified.' if verify_only else None
    try:
        if not verify_only:
            snapshot_download(REPO, revision=revision, local_dir=TARGET, token=False,
                              allow_patterns=patterns, ignore_patterns=ignored, max_workers=2)
    except Exception as error:
        failure = str(error)
        print('Checking final copies after download helper error', flush=True)
    checked = [verify(entry) for entry in selected]
    result = {'status': 'PASS', 'model': REPO, 'revision': revision, 'model_path': str(TARGET),
              'files': checked, 'download_helper_error': failure}
    (REPORT / 'model_verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('VERIFIED VoiceDesign model: ' + str(len(checked)) + ' files', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true')
    main(parser.parse_args().verify_only)
