"""Use the frozen product closure with the bounded ownerless-port wait.

This separate wrapper changes only its generated ownerless probe. The original
minor scripts, source payload, source pins and private data are never rewritten.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time

from ownerless_port_wait import patch_ownerless


HERE=Path(__file__).resolve().parent
ORIGINAL=HERE.parent
MODULE_PINS={
    'minor_common':'4fa91837f57f529d6e67542f7726b3573a213365c8c1d1712a8958bc834cb5da',
    'apply_minor_closed':'81c3a3240f028dc7207e11fff7430ad34beb6603d3e8c1d8c0b58bf347d26df5',
}


def original_modules():
    sys.path.insert(0,str(ORIGINAL))
    modules={}
    for name,pin in MODULE_PINS.items():
        path=ORIGINAL/(name+'.py');raw=path.read_bytes()
        if path.resolve()!=path or path.is_symlink() or hashlib.sha256(raw).hexdigest()!=pin:
            raise ValueError('original_minor_tool_changed')
        loaded=sys.modules.get(name)
        if loaded is not None and Path(loaded.__file__).resolve()!=path:
            raise ValueError('minor_tool_import_collision')
        modules[name]=importlib.import_module(name)
    return modules['minor_common'],modules['apply_minor_closed']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('guard','window-inspect','normal-close','apply','start','ready'))
    parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--spec-sha256',required=True)
    parser.add_argument('--window-proof',type=Path)
    parser.add_argument('--execute-root-only',action='store_true')
    args=parser.parse_args();common,apply=original_modules()
    spec=common.validate_spec(json.loads(common.pinned(args.spec,args.spec_sha256)),
        allow_baseline=args.action in ('guard','window-inspect','normal-close'),allow_proposed=args.action=='apply')
    if args.action=='apply' and spec['minor_state']!='PROPOSED':
        raise ValueError('proposed_minor_spec_required')
    original=apply.build_remote(spec) if args.action=='apply' else common.publisher_remote(spec)
    remote=patch_ownerless(original)
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_PORT_WAIT_TOOL_VALIDATED_NO_SSH',action=args.action,
            remote_sha256=common.sha(remote.encode()),maximum_port_wait_seconds=70,
            startup_sha256=spec['startup_sha256'],product_payload_sha256=common.APPROVED_PAYLOAD_SHA)))
        return
    values=dict(SPEC=spec,ACTION='start' if args.action=='apply' else args.action,TOKEN=None,WINDOW=None)
    if args.action=='normal-close':
        if args.window_proof is None:parser.error('--window-proof is required for exact normal-close')
        proof=json.loads(args.window_proof.read_bytes())
        if proof.get('status')!='WINDOW_INSPECTED_NO_CLOSE':raise ValueError('exact_window_inspection_required')
        values.update(TOKEN=proof['review_token'],WINDOW=proof['window']['window_id'])
    if args.action=='apply':values['PAYLOAD']=common.payload_for(spec)
    result=common.execute_remote(remote,values,timeout=225)
    suffix=str(time.time_ns());output=HERE/('actual_'+args.action+'_'+suffix+'.json')
    common.write_new_json(output,result)
    metadata=dict(output=str(output),result=result)
    if args.action=='apply':
        if result.get('status')!='MINOR_SOURCES_APPLIED_UI_STOPPED':raise ValueError('minor_apply_incomplete')
        completed=common.validate_spec(result['spec']);spec_path=HERE/('applied_spec_'+suffix+'.json')
        digest=common.write_new_json(spec_path,completed)
        metadata=dict(status=result['status'],output=str(output),spec=str(spec_path),spec_sha256=digest)
    print(json.dumps(metadata,ensure_ascii=True))


if __name__=='__main__':
    main()
