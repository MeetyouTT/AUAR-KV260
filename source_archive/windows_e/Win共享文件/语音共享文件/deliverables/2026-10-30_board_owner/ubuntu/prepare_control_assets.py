"""Freeze an explicit pure-Python candidate for isolated ARM smoke tests."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
FILES=(
    'common/board_memory.py','common/memory_commands.py','common/model_inference_wire.py',
    'common/reply_quality.py','board/runtime/board_dialogue.py','board/runtime/board_dialogue_client.py',
)


def main():
    entries=[]
    for relative in FILES:
        source=PROJECT/'aura'/relative
        data=source.read_bytes()
        entries.append(dict(name='code/'+relative,source=str(source),bytes=len(data),
                            sha256=hashlib.sha256(data).hexdigest(),provenance='reviewed_candidate_source'))
    fingerprint=hashlib.sha256(json.dumps([(e['name'],e['sha256']) for e in entries]).encode()).hexdigest()[:16]
    value=dict(version=1,purpose='synthetic_board_control_smoke',
               candidate_root='/home/root/aura-board-owner-candidate-20261030/control-'+fingerprint,
               entries=entries,total_bytes=sum(e['bytes'] for e in entries))
    (HERE/'control_asset_manifest.local.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    value['entries']=[{k:v for k,v in e.items() if k!='source'} for e in entries]
    public=json.dumps(value,separators=(',',':')).encode()
    print(json.dumps(dict(candidate_root=value['candidate_root'],manifest_sha256=hashlib.sha256(public).hexdigest(),
                          bytes=value['total_bytes'])))


if __name__=='__main__':main()
