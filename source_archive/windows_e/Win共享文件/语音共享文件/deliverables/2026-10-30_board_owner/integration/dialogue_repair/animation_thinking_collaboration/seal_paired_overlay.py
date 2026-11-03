"""After the owner builds/tests native code, create a new, coherent overlay.

No deployment, startup mutation, service, model, network or device operation.
The frozen source candidate is not edited; a new paired_overlay is produced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    receipt=json.loads(args.receipt.read_text(encoding='utf-8'))
    manifest=json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    for relative,row in manifest['files'].items():
        if sha(HERE/'candidate'/relative)!=row['after_sha256']:
            raise ValueError('Frozen candidate changed: '+relative)
    if (receipt.get('status')!='ISOLATED_COMPILED_CPU_POLICY_PASSED_NOT_INSTALLED'
        or receipt.get('source_sha256')!=sha(HERE/'candidate/native/yuki_host.cpp')
        or receipt.get('header_sha256')!=sha(HERE/'candidate/native/yuki_host.h')
        or receipt.get('library_sha256')!=sha(args.library)
        or receipt.get('shared_dependencies_identical') is not True
        or receipt.get('native_policy_test',{}).get('status')!='PASS'
        or receipt.get('production_installed') is not False):
        raise ValueError('Matching isolated native build/policy receipt required')
    old_pair=HERE/'before/aura/config/yuki_pair.formal.json'
    baseline=json.loads((HERE/'SOURCE_BASELINE.json').read_text(encoding='utf-8'))
    if sha(old_pair)!=baseline['files']['aura/config/yuki_pair.formal.json']['sha256']:
        raise ValueError('Frozen public pair selection changed')
    selection=json.loads(old_pair.read_text(encoding='utf-8'))
    selection['runtime_pins']['tools/native_yuki.py']=sha(HERE/'candidate/aura/tools/native_yuki.py')
    selection['runtime_pins']['tools/libaura_yuki.so']=receipt['library_sha256']
    # Every non-renderer pin, identity, persona, native_config and presentation
    # entry remains from the verified waist-framing production selection.
    pair_raw=(json.dumps(selection,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
    pair_sha=hashlib.sha256(pair_raw).hexdigest()
    formal=(HERE/'candidate/aura/tools/formal_yuki.py').read_text(encoding='utf-8')
    old_sha=sha(old_pair)
    pattern=r"(?m)^PAIR_CONFIG_SHA256='"+old_sha+r"'$"
    if len(re.findall(pattern,formal))!=1:
        raise ValueError('Formal adapter does not pin the verified before selection')
    formal=re.sub(pattern,"PAIR_CONFIG_SHA256='"+pair_sha+"'",formal)
    out=HERE/'paired_overlay'
    out.mkdir(exist_ok=False)
    for path in (HERE/'candidate/aura').rglob('*.py'):
        destination=out/'aura'/path.relative_to(HERE/'candidate/aura')
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)
    (out/'aura/tools/formal_yuki.py').write_text(formal,encoding='utf-8',newline='\n')
    (out/'aura/config').mkdir(parents=True)
    (out/'aura/config/yuki_pair.formal.json').write_bytes(pair_raw)
    shutil.copyfile(args.library,out/'aura/tools/libaura_yuki.so')
    rows={path.relative_to(out/'aura').as_posix():sha(path) for path in sorted((out/'aura').rglob('*')) if path.is_file()}
    result=dict(schema='aura.animation-thinking-paired-overlay.v1',status='PAIRED_SOURCE_READY_NOT_DEPLOYED',
        files=rows,selection_sha256=pair_sha,base_selection_sha256=old_sha,
        required_startup_change={'character_pair.selection_sha256':pair_sha},
        native_build_receipt_sha256=sha(args.receipt),production_modified=False,
        preserve_user_paused=True,physical_fps_measured=False,visual_preview_passed=False)
    (out/'PAIRING_RECEIPT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],selection_sha256=pair_sha,files=len(rows))))


if __name__=='__main__':
    main()
