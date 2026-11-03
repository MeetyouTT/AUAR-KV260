"""Download only fixed public Paraformer Small ASR files to external local storage."""
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request

HERE = Path(__file__).resolve().parent
DIRECTORY = Path('D:/AIModels/ASR-candidates/paraformer-small-20261031')
REPOSITORY = 'csukuangfj/sherpa-onnx-paraformer-zh-small-2024-03-09'
REVISION = '63ddc3cd0f2810b68289a7b3876e62ef5d53d6df'
FILES = (
    ('model.int8.onnx', 81828675, '3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec'),
    ('tokens.txt', 75352, '4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa'),
)


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    for directory in (DIRECTORY, *DIRECTORY.parents):
        assert not directory.is_symlink() and not directory.is_junction()
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    assert DIRECTORY.resolve().is_relative_to(Path('D:/AIModels').resolve())
    assert shutil.disk_usage(DIRECTORY).free > sum(x[1] for x in FILES) + 512 * 1024 * 1024
    rows = []
    for name, size, expected in FILES:
        target = DIRECTORY / name
        assert not target.is_symlink() and not target.is_junction()
        url = 'https://huggingface.co/' + REPOSITORY + '/resolve/' + REVISION + '/' + name
        if not target.exists():
            part = target.with_name(name + '.part-' + str(time.time_ns()))
            count, value = 0, hashlib.sha256()
            with urllib.request.urlopen(url, timeout=45) as response, part.open('xb') as output:
                while block := response.read(1024 * 1024):
                    count += len(block)
                    if count > size:
                        raise ValueError('pinned_public_model_size_exceeded')
                    output.write(block)
                    value.update(block)
            assert count == size and value.hexdigest() == expected
            part.rename(target)
        assert target.stat().st_size == size and digest(target) == expected
        rows.append(dict(name=name, path=str(target), size=size, sha256=expected, url=url))
        print(json.dumps(dict(resource=name, verified=True)), flush=True)
    result = dict(status='MODEL_READY_EXTERNAL_STORAGE_NOT_DEPLOYED', repository=REPOSITORY,
                  revision=REVISION, files=rows, language_model_downloaded=False,
                  board_accessed=False, production_changed=False,
                  board_operator_thread='01a18bcd-1167-71a0-ba0b-d809148d39d9',
                  suggested_board_directory='/home/root/aura-public-streaming-validation-20261031/paraformer-small-63ddc3cd0f2810b6')
    (HERE / 'MODEL_HANDOFF.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
