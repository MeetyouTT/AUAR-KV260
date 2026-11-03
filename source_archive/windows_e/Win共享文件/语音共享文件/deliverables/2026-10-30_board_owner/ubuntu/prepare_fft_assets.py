"""Freeze FFT adapter source, optionally the existing official ARM ORT wheel."""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--with-ort17',action='store_true');args=parser.parse_args()
    resources={
        'code/board/runtime/audio/board_asr_frontend.py':PROJECT/'aura/board/runtime/audio/board_asr_frontend.py',
        'code/board/runtime/audio/board_gtcrn_fft.py':PROJECT/'aura/board/runtime/audio/board_gtcrn_fft.py',
    }
    if args.with_ort17:
        path=Path('D:/AIModels/audio-frontend-eval-20261021/onnxruntime-1.17.3-cp39-cp39-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl')
        assert hashlib.sha256(path.read_bytes()).hexdigest()=='3ff2dc012bd930578aff5232afd2905bf16620815f36783a941aafabf94b3702'
        resources['wheels/'+path.name]=path
    entries=[]
    for name,path in resources.items():
        data=path.read_bytes();assert not path.is_symlink()
        entries.append(dict(name=name,source=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                            provenance='candidate_source_or_existing_official_runtime_wheel'))
    fingerprint=hashlib.sha256(json.dumps([(e['name'],e['sha256']) for e in entries]).encode()).hexdigest()[:16]
    value=dict(version=1,purpose='same_model_gtcrn_fft_candidate',
        candidate_root='/home/root/aura-board-owner-candidate-20261030/fft-'+fingerprint,
        entries=entries,total_bytes=sum(e['bytes'] for e in entries))
    (HERE/'fft_asset_manifest.local.json').write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    value['entries']=[{k:v for k,v in e.items() if k!='source'} for e in entries]
    raw=json.dumps(value,separators=(',',':')).encode()
    print(json.dumps(dict(candidate_root=value['candidate_root'],manifest_sha256=hashlib.sha256(raw).hexdigest(),
                          bytes=value['total_bytes'],isolated_ort17=args.with_ort17)))


if __name__=='__main__':main()
