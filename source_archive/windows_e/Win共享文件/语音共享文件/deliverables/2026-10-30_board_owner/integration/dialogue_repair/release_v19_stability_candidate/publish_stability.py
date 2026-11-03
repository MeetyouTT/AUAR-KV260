"""Exact current/minor normal publication. Default validates locally only."""
import argparse
import json
from pathlib import Path
import time

import stability_common as common


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('guard','window-inspect','normal-close','start','ready'))
    parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--spec-sha256',required=True)
    parser.add_argument('--window-proof',type=Path)
    parser.add_argument('--execute-root-only',action='store_true')
    args=parser.parse_args()
    spec=common.validate_spec(json.loads(common.pinned(args.spec,args.spec_sha256)),
        allow_baseline=args.action in ('guard','window-inspect','normal-close'))
    remote=common.publisher_remote(spec)
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_MINOR_PUBLICATION_VALIDATED_NO_SSH',action=args.action,
            remote_sha256=common.sha(remote.encode()),startup_sha256=spec['startup_sha256'])))
        return
    values=dict(SPEC=spec,ACTION=args.action,TOKEN=None,WINDOW=None)
    if args.action=='normal-close':
        if args.window_proof is None:
            parser.error('--window-proof is required for exact normal-close')
        proof=json.loads(args.window_proof.read_bytes())
        if proof.get('status')!='WINDOW_INSPECTED_NO_CLOSE':
            raise ValueError('exact_window_inspection_required')
        values.update(TOKEN=proof['review_token'],WINDOW=proof['window']['window_id'])
    result=common.execute_remote(remote,values,timeout=225)
    output=common.HERE/('actual_'+args.action+'_'+str(time.time_ns())+'.json')
    common.write_new_json(output,result)
    print(json.dumps(dict(output=str(output),result=result),ensure_ascii=True))


if __name__=='__main__':
    main()
