"""Download only four pinned public ASR resources to external model storage."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request

HERE = Path(__file__).resolve().parent
DIRECTORY = Path('D:/AIModels/ASR-candidates/streaming-transducer-20261031')
BASE = 'https://huggingface.co/csukuangfj/k2fsa-zipformer-bilingual-zh-en-t/resolve/e2382758de9a0219b4efe682b95af30b399db3b8/'
FILES = (
    ('exp/32/encoder-epoch-99-avg-1.int8.onnx', 42980793, 'db6f51551762e40e549166fe041ea3e45464370b595e9ad23f06478ec3794fbb'),
    ('exp/32/decoder-epoch-99-avg-1.onnx', 13877276, '89be509a83175261695bdef5fd1c7b9ab1129a663d1284e7ba9f8507b21e0906'),
    ('exp/32/joiner-epoch-99-avg-1.int8.onnx', 3228485, 'bdda356d6f9b8c2d7cee9ee0e26075fa537490f7fd06520be408d287073667b9'),
    ('data/lang_char_bpe/tokens.txt', 56317, 'a8e0e4ec53810e433789b54a5c0134a7eaa2ffca595a6334d54c00da858841d3'),
)

def main():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    assert DIRECTORY.resolve().is_relative_to(Path('D:/AIModels').resolve())
    receipts = []
    for relative, size, expected in FILES:
        target = DIRECTORY/relative.rsplit('/', 1)[-1]
        url = BASE+relative
        if not target.exists():
            part = target.with_name(target.name+'.part-'+str(time.time_ns()))
            count = 0
            digest = hashlib.sha256()
            with urllib.request.urlopen(url, timeout=45) as response, part.open('xb') as output:
                while block := response.read(1024*1024):
                    count += len(block)
                    if count > size:
                        raise ValueError('public_model_size_exceeded')
                    output.write(block)
                    digest.update(block)
            assert count == size and digest.hexdigest() == expected
            part.rename(target)
        assert target.stat().st_size == size and hashlib.sha256(target.read_bytes()).hexdigest() == expected
        receipts.append(dict(path=str(target), url=url, size=size, sha256=expected))
        print(json.dumps(dict(downloaded=target.name, verified=True)), flush=True)
    value = dict(status='DOWNLOADED_PINNED_PUBLIC_ASR_NOT_DEPLOYED', files=receipts,
                 revision='e2382758de9a0219b4efe682b95af30b399db3b8', language_model_weights_downloaded=False)
    output = HERE/'transducer_download_manifest.json'
    output.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    main()
