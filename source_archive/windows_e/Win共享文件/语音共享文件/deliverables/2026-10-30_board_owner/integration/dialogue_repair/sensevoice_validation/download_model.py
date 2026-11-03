"""Download only fixed public SenseVoice ASR files to external local storage."""
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request

HERE = Path(__file__).resolve().parent
DIRECTORY = Path('D:/AIModels/ASR-candidates/sensevoice-20261031')
REPOSITORY = 'csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17'
REVISION = '2365baeacb507f821a0c8120fcee3d484dba7a07'
FILES = (
    ('model.int8.onnx', 239233841, 'c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51'),
    ('tokens.txt', 315894, 'f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc'),
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
                  suggested_board_directory='/home/root/aura-public-streaming-validation-20261031/sensevoice-2365baeacb507f82')
    (HERE / 'MODEL_HANDOFF.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
