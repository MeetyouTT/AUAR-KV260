"""Pin existing Paraformer resources and official same-version ARM wheels.

Downloads runtime wheels only. Never downloads a model or copies a virtualenv.
"""
import hashlib
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
VERSION = '1.13.8'
MODELS = {
    'model.int8.onnx': 'f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945',
    'tokens.txt': '59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6',
    'test_wavs/0.wav': '1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    entries = []
    source = PROJECT / 'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14'
    for relative, expected in MODELS.items():
        path = source / relative
        assert path.is_file() and not path.is_symlink() and digest(path) == expected
        entries.append(dict(name='models/paraformer/' + relative, source=str(path),
                            sha256=expected, bytes=path.stat().st_size, provenance='existing_project_resource'))
    wheelroot = HERE / 'wheels'
    wheelroot.mkdir(exist_ok=True)
    for package in ('sherpa-onnx', 'sherpa-onnx-core'):
        with urllib.request.urlopen('https://pypi.org/pypi/' + package + '/' + VERSION + '/json', timeout=20) as r:
            metadata = json.load(r)
        candidates = [item for item in metadata['urls'] if
                      ('cp39-cp39-manylinux2014_aarch64' in item['filename'] if package == 'sherpa-onnx'
                       else item['filename'].endswith('py3-none-manylinux2014_aarch64.whl'))]
        assert len(candidates) == 1
        item = candidates[0]
        path = wheelroot / item['filename']
        expected = item['digests']['sha256']
        assert not path.is_symlink()
        if not path.exists():
            partial = path.with_suffix(path.suffix+'.partial')
            with urllib.request.urlopen(item['url'], timeout=45) as r, partial.open('xb') as out:
                while True:
                    chunk = r.read(1024*1024)
                    if not chunk: break
                    out.write(chunk)
            assert partial.stat().st_size == item['size'] and digest(partial) == expected
            partial.rename(path)
        assert path.stat().st_size == item['size'] and digest(path) == expected
        entries.append(dict(name='wheels/' + path.name, source=str(path), sha256=expected,
                            bytes=path.stat().st_size, provenance=item['url']))
    # Only explicitly selected new source enters this ASR candidate.
    path = PROJECT / 'aura/board/runtime/audio/board_asr.py'
    entries.append(dict(name='code/board/runtime/audio/board_asr.py',source=str(path),
                        sha256=digest(path),bytes=path.stat().st_size,provenance='new_candidate_source'))
    manifest = dict(version=1, purpose='same_model_public_asr_candidate',
                    candidate_root='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8',
                    entries=entries, total_bytes=sum(item['bytes'] for item in entries))
    target = HERE / 'asr_asset_manifest.local.json'
    target.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(manifest=str(target),total_bytes=manifest['total_bytes'],
                          resources=[{k:v for k,v in item.items() if k!='source'} for item in entries]),ensure_ascii=False))


if __name__ == '__main__': main()
