"""One-file source candidate only; no devices, inference or production writes."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / 'response_latency/asr_threads_candidate/after/board/runtime/audio/board_asr.py'
BEFORE = '4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3'


def main():
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BEFORE:
        raise ValueError('pinned_asr_source_changed')
    after = raw.replace(b'not 1 <= num_threads <= 3:', b'not 1 <= num_threads <= 4:', 1)
    after = after.replace(b'Use one to three board ASR threads', b'Use one to four board ASR threads', 1)
    if after == raw or after.replace(b'not 1 <= num_threads <= 4:', b'not 1 <= num_threads <= 3:', 1).replace(
            b'Use one to four board ASR threads', b'Use one to three board ASR threads', 1) != raw:
        raise ValueError('unexpected_source_delta')
    ast.parse(after, feature_version=(3, 9))
    name = 'board/runtime/audio/board_asr.py'
    target = HERE / 'after' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(after)
    before = HERE / 'before' / name
    before.parent.mkdir(parents=True, exist_ok=True)
    before.write_bytes(raw)
    record = dict(before_sha256=BEFORE, sha256=hashlib.sha256(after).hexdigest(), bytes=len(after))
    (HERE / 'candidate_manifest.json').write_bytes((json.dumps({name: record}, indent=2)+'\n').encode())
    (HERE / 'extra_source_map.json').write_bytes((json.dumps({name: str(target.resolve())},
        ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    print(json.dumps(record))


if __name__ == '__main__': main()
