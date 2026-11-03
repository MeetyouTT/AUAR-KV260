"""Only expand the pinned board ASR opt-in thread ceiling; default stays two."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PIN='d8dbe7cc387a290ad0a218e84ae2ef97cd471e50b074743e41f04bc02b454366'
def sha(raw):return hashlib.sha256(raw).hexdigest()

def main():
    original=(ROOT.parent/'source_before/board/runtime/audio/board_asr.py').read_bytes()
    if sha(original)!=PIN:raise ValueError('Current production ASR pin changed')
    source=original.decode('utf-8')
    before="if type(num_threads) is not int or not 1 <= num_threads <= 2:\n            raise ValueError('Use one or two board ASR threads')"
    after="if type(num_threads) is not int or not 1 <= num_threads <= 3:\n            raise ValueError('Use one to three board ASR threads')"
    if source.count(before)!=1:raise ValueError('Exact ASR thread guard changed')
    candidate=source.replace(before,after,1)
    if candidate.replace(after,before,1).encode('utf-8')!=original:raise ValueError('Unexpected ASR delta')
    ast.parse(candidate,feature_version=(3,9))
    output=ROOT/'after/board/runtime/audio/board_asr.py'
    output.parent.mkdir(parents=True,exist_ok=True);raw=candidate.encode('utf-8');output.write_bytes(raw)
    manifest=dict(schema='aura.asr-three-thread-source-candidate.v1',hardware_executed=False,
        files={'board/runtime/audio/board_asr.py':dict(sha256=sha(raw),bytes=len(raw),before_sha256=PIN)},
        default_threads=2,accepted_threads=[1,2,3],reverse_exact_bytes=True)
    encoded=(json.dumps(manifest,indent=2)+'\n').encode('utf-8')
    (ROOT/'overlay_manifest.json').write_bytes(encoded)
    (ROOT/'extra_source_map.json').write_text(json.dumps({'aura/board/runtime/audio/board_asr.py':str(output)},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(source_sha256=sha(raw),manifest_sha256=sha(encoded))))

if __name__=='__main__':main()
