"""Freeze the two current frontend models and new local adapter, no downloads."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]


def main():
    resources={
        'models/gtcrn_simple.onnx':Path('D:/AIModels/audio-frontend-eval-20261021/gtcrn_simple.onnx'),
        'models/silero_vad_v5.onnx':Path('D:/AIModels/audio-frontend-eval-20261021/silero_vad_v5.onnx'),
        'code/board_asr_frontend.py':PROJECT/'aura/board/runtime/audio/board_asr_frontend.py',
    }
    entries=[]
    for name,path in resources.items():
        data=path.read_bytes();assert not path.is_symlink()
        entries.append(dict(name=name,source=str(path),bytes=len(data),
                            sha256=hashlib.sha256(data).hexdigest(),provenance='existing_model_or_new_candidate_source'))
    fingerprint=entries[-1]['sha256'][:16]
    value=dict(version=1,purpose='same_model_frontend_candidate',
        candidate_root='/home/root/aura-board-owner-candidate-20261030/frontend-'+fingerprint,
        entries=entries,total_bytes=sum(e['bytes'] for e in entries))
    (HERE/'frontend_asset_manifest.local.json').write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    value['entries']=[{k:v for k,v in e.items() if k!='source'} for e in entries]
    encoded=json.dumps(value,separators=(',',':')).encode()
    print(json.dumps(dict(candidate_root=value['candidate_root'],manifest_sha256=hashlib.sha256(encoded).hexdigest(),
                          bytes=value['total_bytes'])))


if __name__=='__main__':main()
