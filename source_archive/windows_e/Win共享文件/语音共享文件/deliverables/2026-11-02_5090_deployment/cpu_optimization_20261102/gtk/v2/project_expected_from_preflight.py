"""Local deterministic metadata projection. No SSH, device or service actions."""
import argparse
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

TARGETS=('board/interaction/ui_services.py','tools/board_camera_preview.py')
CONTRACT_KEY='board/interaction/ui_contract.py'
OLD={'board/interaction/ui_services.py':'b55ee295e2cb5494f387fbaa4aa081fd1d6bffd57588c018c5f31daae56bd711',
     'tools/board_camera_preview.py':'6e697c16f7ae264dff56b6b35f38da4b531ea13026b69a7c8bdbfb1960a6afcd'}
CONTRACT='7f67e4bdfe4a95396fbe6445759c80f8ea79cf51d2d991269213409a83daec86'
REVIEWED_TRANSACTION='e1b5384bc2abe2aaf957792a316ddca3a1d854aafcc4b06290e75a1b3393e3ed'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def valid_sha(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None
def absolute_board_path(value):
    return type(value) is str and PurePosixPath(value).is_absolute() and '..' not in PurePosixPath(value).parts

def build_expected(preflight,handoff,transaction_root,maintenance_window_confirmed):
    assert maintenance_window_confirmed is True,'Root current exclusive maintenance window is required'
    p=preflight['board_result'];h=handoff['board_result']
    assert h['current_chat_board_writes_and_probes_frozen'] is True
    assert h['handoff_status']=='IDLE_GUI_CAMERA_LISTENING_TRANSFERRED_TO_CPU_WINDOW'
    assert p['boot_id']==h['boot_id']
    pins=p['component_sha256'];assert len(pins)==p['components_verified']==380
    assert all(valid_sha(digest) for digest in pins.values())
    assert valid_sha(p['startup_sha256']) and absolute_board_path(p['startup_path'])
    assert absolute_board_path(transaction_root)
    identity_pins=h['identity_own_source_pins'];assert len(identity_pins)==5
    source_keys=set(identity_pins)|set(TARGETS)|{CONTRACT_KEY}
    for name,digest in identity_pins.items():assert pins[name]==digest,('Identity source changed after handoff',name)
    for name,digest in OLD.items():assert pins[name]==digest,('Target not original',name)
    assert pins[CONTRACT_KEY]==CONTRACT
    owners=p['owners'];assert set(owners)=={'camera','gui_supervisor','gui_gtk'}
    for value in owners.values():
        assert set(value)=={'pid','birth_ticks','command_sha256'}
        assert type(value['pid']) is int and value['pid']>0
        assert type(value['birth_ticks']) is str and value['birth_ticks'].isdigit() and valid_sha(value['command_sha256'])
    pan=p['pan_component_sha256']
    assert set(pan)=={name for name in pins if name.startswith('config/pan_')}
    assert all(pins[name]==digest for name,digest in pan.items())
    external=p['pan_external_sha256']
    assert len(external)>=26 and all(absolute_board_path(path) and valid_sha(digest) for path,digest in external.items())
    binding=p['selected_readback'];assert valid_sha(binding['sha256']) and absolute_board_path(binding['path'])
    assert type(binding['source_count']) is int and 1<=binding['source_count']<=512
    # Deliberately no pan READY/readback-zero/wide-platform requirement:
    # this projection preserves the observed benchmark-platform FAULT/null state.
    return {'maintenance_writers_frozen':True,'boot_id':p['boot_id'],
        'startup_path':p['startup_path'],'startup_sha256':p['startup_sha256'],
        'owners':copy.deepcopy(owners),
        'source_sha256':{name:pins[name] for name in sorted(source_keys)},
        'selected_readback_sha256':binding['sha256'],'selected_readback_source_count':binding['source_count'],
        'pan_component_sha256':copy.deepcopy(pan),'pan_external_sha256':copy.deepcopy(external),
        'transaction_root':transaction_root}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preflight',type=Path,required=True)
    parser.add_argument('--handoff',type=Path,required=True)
    parser.add_argument('--transaction-root',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--maintenance-window-confirmed',action='store_true')
    args=parser.parse_args()
    script=Path(__file__).parent/'transaction_preview_projection.py'
    assert sha(script.read_bytes())==REVIEWED_TRANSACTION,'Re-review changed transaction schema'
    p_raw=args.preflight.read_bytes();h_raw=args.handoff.read_bytes()
    expected=build_expected(json.loads(p_raw),json.loads(h_raw),args.transaction_root,args.maintenance_window_confirmed)
    encoded=(json.dumps(expected,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf-8')
    assert args.output.parent.is_dir()
    with args.output.open('xb') as stream:stream.write(encoded)
    # Check original local evidence was not rewritten during projection.
    assert args.preflight.read_bytes()==p_raw and args.handoff.read_bytes()==h_raw
    receipt={'status':'LOCAL_EXPECTED_PROJECTED','output':str(args.output),'expected_sha256':sha(encoded),
        'preflight_sha256':sha(p_raw),'handoff_sha256':sha(h_raw),'transaction_script_sha256':REVIEWED_TRANSACTION,
        'boot_id':expected['boot_id'],'startup_sha256':expected['startup_sha256'],
        'source_pin_count':len(expected['source_sha256']),'pan_component_count':len(expected['pan_component_sha256']),
        'pan_external_count':len(expected['pan_external_sha256']),'selected_source_count':expected['selected_readback_source_count'],
        'board_contacted':False,'candidate_or_transaction_changed':False}
    with args.output.with_name(args.output.stem+'_PROJECTION.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
    print(json.dumps(receipt))

if __name__=='__main__':main()
