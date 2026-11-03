"""Produce matched startup16 and startup24 overlays, no production config IO."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    baseline=json.loads((HERE/'BASELINE.json').read_text(encoding='utf-8'))
    for relative,expected in baseline['files'].items():
        if sha(HERE/'before/aura'/relative)!=expected:raise ValueError('Before source changed')
    source=HERE/'candidate/aura'
    for path in source.rglob('*.py'):ast.parse(path.read_text(encoding='utf-8'))
    original=HERE/'before/aura/config/yuki_pair.formal.json'
    pair=json.loads(original.read_text(encoding='utf-8'))
    formal=(source/'tools/formal_yuki.py').read_text(encoding='utf-8')
    old_sha=sha(original);pattern="(?m)^PAIR_CONFIG_SHA256='"+old_sha+"'$"
    if len(re.findall(pattern,formal))!=1:raise ValueError('Expected original formal pair constant')
    variants={}
    for fps in (16,24):
        out=HERE/('paired_'+str(fps));out.mkdir(exist_ok=False)
        selection=json.loads(json.dumps(pair))
        selection['native_config']['fps']=fps
        selection['runtime_pins']['tools/native_yuki.py']=sha(source/'tools/native_yuki.py')
        raw=(json.dumps(selection,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
        pair_sha=hashlib.sha256(raw).hexdigest()
        for path in source.rglob('*.py'):
            destination=out/'aura'/path.relative_to(source)
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,destination)
        (out/'aura/tools/formal_yuki.py').write_text(re.sub(pattern,"PAIR_CONFIG_SHA256='"+pair_sha+"'",formal),encoding='utf-8',newline='\n')
        (out/'aura/config').mkdir();(out/'aura/config/yuki_pair.formal.json').write_bytes(raw)
        rows={path.relative_to(out/'aura').as_posix():sha(path) for path in sorted((out/'aura').rglob('*')) if path.is_file()}
        receipt=dict(schema='aura.native-rate-startup-pair.v1',status='LOCAL_PAIRED_RATE_CANDIDATE_NOT_DEPLOYED',
            fps=fps,files=rows,selection_sha256=pair_sha,native_library_unchanged_sha256=baseline['native_library_sha256'],
            gui_config_changes={'stable_avatar_fps':fps,'native_yuki.fps':fps,'character_pair.selection_sha256':pair_sha},
            actual_config_target='GUI config/board_avatar_gtk.json; startup binds GUI and source component hashes',
            production_modified=False,live_fps_improvement_proven=False,audio_queue_unchanged_frames=8,
            head_motion_included=False,feature_route_files_included=False)
        (out/'PAIRING_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        variants[str(fps)]=receipt
    (HERE/'RATE_VARIANTS.json').write_text(json.dumps(variants,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({fps:dict(selection_sha256=row['selection_sha256'],files=len(row['files'])) for fps,row in variants.items()}))


if __name__=='__main__':main()
