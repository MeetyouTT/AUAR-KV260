"""Download an official public ASR test candidate outside the shared project."""
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request

HERE = Path(__file__).resolve().parent
NAME = 'sherpa-onnx-streaming-zipformer-small-ctc-zh-int8-2025-04-01'
URL = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/' + NAME + '.tar.bz2'
TARGET = Path('D:/AIModels/ASR-candidates/streaming-ctc-20261031')

if __name__ == '__main__':
    TARGET.mkdir(parents=True, exist_ok=True)
    archive = TARGET / (NAME + '.tar.bz2')
    count = 0
    if archive.exists():
        assert not archive.is_symlink()
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'b3b309f7ce4a737195fcc6963ea19b0653a7d3401580af5ae0d3e284cbb71f0b'
        count = archive.stat().st_size
    else:
        with urllib.request.urlopen(URL, timeout=30) as response, archive.open('xb') as output:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                count += len(block)
                if count > 50 * 1024 * 1024:
                    raise RuntimeError('public_asr_archive_exceeds_bound')
                output.write(block)
    wanted = {'model.int8.onnx': 40 * 1024 * 1024, 'tokens.txt': 1024 * 1024,
              'bbpe.model': 1024 * 1024, 'test_wavs/0.wav': 2 * 1024 * 1024}
    rows = {}
    with tarfile.open(archive, 'r:bz2') as source:
        for relative, limit in wanted.items():
            member = source.getmember('./' + NAME + '/' + relative)
            if not member.isfile() or not 0 < member.size <= limit:
                raise RuntimeError('public_asr_member_invalid')
            content = source.extractfile(member).read(limit + 1)
            if len(content) != member.size:
                raise RuntimeError('public_asr_member_size_changed')
            target = TARGET / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as output:
                output.write(content)
            rows[relative] = dict(path=str(target), sha256=hashlib.sha256(content).hexdigest(), bytes=len(content))
    manifest = dict(status='OFFICIAL_PUBLIC_ASR_CANDIDATE_ONLY', source_url=URL,
                    directory=str(TARGET), archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    archive_bytes=count, files=rows, production_configuration_changed=False,
                    board_model_loaded=False, llm_model_changed=False)
    with (HERE / 'download_manifest.json').open('x', encoding='utf-8') as output:
        json.dump(manifest, output, indent=2)
        output.write('\n')
    print(json.dumps(manifest))
