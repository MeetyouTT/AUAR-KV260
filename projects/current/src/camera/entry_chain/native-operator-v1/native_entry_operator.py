"""Pinned extension over the existing camera/face entry, preserving its owner."""
import hashlib,json,runpy,sys
from pathlib import Path

OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
ROOT=OPS/'pan-face-edge-v5/native-operator-v1'


def main():
    manifest=json.loads((ROOT/'runtime-manifest.json').read_text())
    for name,digest in manifest['files'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Native operator runtime source changed')
    settings=json.loads((ROOT/'settings.json').read_text())
    meta=json.loads((OPS/'meta.json').read_text())
    sys.path.insert(0,str(Path(meta['candidate_root'])/'aura'));sys.path.insert(0,str(ROOT))
    from identity_recovery import install
    install(settings,ROOT)
    entry=OPS/'native_entry_pan_face_v5.py';sys.argv=[str(entry)]
    runpy.run_path(str(entry),run_name='__main__')


if __name__=='__main__':main()
