"""Create a paired, reviewable motion overlay after a matching native build.
No service/configuration/device operation; frozen before/source stay unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--current-source-mapping',type=Path,required=True,
        help='Final v23 or newer actual source_mapping, never a proposed spec')
    args=parser.parse_args()
    manifest=json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    for relative,row in manifest['files'].items():
        if sha(HERE/'candidate'/relative)!=row['after_sha256']:raise ValueError('Frozen motion source changed')
    receipt=json.loads(args.receipt.read_text(encoding='utf-8'))
    native=HERE/'candidate/native'
    if (receipt.get('status')!='ISOLATED_COMPILED_CPU_POLICY_PASSED_NOT_INSTALLED'
        or receipt.get('source_sha256')!=sha(native/'yuki_host.cpp')
        or receipt.get('header_sha256')!=sha(native/'yuki_host.h')
        or receipt.get('motion_header_sha256')!=sha(native/'gentle_motion.hpp')
        or receipt.get('library_sha256')!=sha(args.library)
        or receipt.get('native_policy_test',{}).get('status')!='PASS'
        or receipt.get('native_policy_test',{}).get('eye_regression_passed') is not True
        or receipt.get('added_motion_channels') != 2
        or receipt.get('shared_dependencies_identical') is not True
        or receipt.get('production_installed') is not False):
        raise ValueError('Matching motion + eye regression receipt required')
    base=json.loads((HERE/'BASELINE_V22.json').read_text(encoding='utf-8'))
    current=json.loads(args.current_source_mapping.read_text(encoding='utf-8'))
    if current['startup_sha256']==base['startup_sha256']:
        raise ValueError('Wait for final v23 actual source mapping before pairing')
    for name,expected in base['pair_pins'].items():
        if current['component_pins'].get(name)!=expected:raise ValueError('Current pair source requires rebase: '+name)
    tested=json.loads((HERE/'LOCAL_TEST_RESULTS.json').read_text(encoding='utf-8'))
    for name,expected in tested['loaded_dependency_pins'].items():
        if current['component_pins'].get(name)!=expected:raise ValueError('Retest current facial dependency: '+name)
    original=HERE/'before/aura/config/yuki_pair.formal.json'
    if sha(original)!=base['pair_pins']['config/yuki_pair.formal.json']:
        raise ValueError('Before pair does not match reviewed v22')
    selection=json.loads(original.read_text(encoding='utf-8'))
    selection['runtime_pins']['tools/libaura_yuki.so']=sha(args.library)
    raw=(json.dumps(selection,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    pair_sha=hashlib.sha256(raw).hexdigest()
    formal=(HERE/'before/aura/tools/formal_yuki.py').read_text(encoding='utf-8')
    pattern="(?m)^PAIR_CONFIG_SHA256='"+sha(original)+"'$"
    if len(re.findall(pattern,formal))!=1:raise ValueError('Before formal pair constant differs')
    formal=re.sub(pattern,"PAIR_CONFIG_SHA256='"+pair_sha+"'",formal)
    out=HERE/'motion_overlay';out.mkdir(exist_ok=False)
    for relative in ('tools/formal_yuki.py','tools/formal_native_yuki.py','tools/native_yuki.py'):
        source=HERE/'before/aura'/relative
        destination=out/'aura'/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
    (out/'aura/tools/formal_yuki.py').write_text(formal,encoding='utf-8',newline='\n')
    (out/'aura/config').mkdir();(out/'aura/config/yuki_pair.formal.json').write_bytes(raw)
    shutil.copyfile(args.library,out/'aura/tools/libaura_yuki.so')
    rows={path.relative_to(out/'aura').as_posix():sha(path) for path in sorted((out/'aura').rglob('*')) if path.is_file()}
    result=dict(schema='aura.minimal-head-motion-paired-overlay.v3',status='MOTION_PAIRED_READY_NOT_DEPLOYED',
        files=rows,selection_sha256=pair_sha,base_selection_sha256=sha(original),
        actual_binding_target='GUI config/board_avatar_gtk.json: character_pair.selection_sha256; recompute GUI component pin in startup',
        changed_inner_pin='tools/libaura_yuki.so',feature_route_files_included=False,
        native_build_receipt_sha256=sha(args.receipt),production_modified=False,
        actual_rebase_startup_sha256=current['startup_sha256'],
        actual_rebase_source_mapping_sha256=sha(args.current_source_mapping),
        visual_preview_passed=False,physical_fps_acceptance_passed=False,preserve_user_paused=True)
    (out/'PAIRING_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],selection_sha256=pair_sha,files=len(rows))))


if __name__=='__main__':main()
