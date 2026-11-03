"""Original normal lifecycle, gated on a diagnosed root-selected single source."""
import argparse
import json
from pathlib import Path
import time

import followup_common as common


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('guard', 'window-inspect', 'normal-close', 'start', 'ready'))
    parser.add_argument('--spec', required=True, type=Path)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--window-proof', type=Path)
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    spec = common.validate_spec(json.loads(common.pinned(args.spec, args.spec_sha256)),
                                allow_baseline=args.action in ('guard', 'window-inspect', 'normal-close'))
    remote = common.publisher_remote(spec)
    values = dict(SPEC=spec, ACTION=args.action, TOKEN=None, WINDOW=None)
    if args.action == 'normal-close':
        common.need(args.window_proof is not None, 'exact_window_proof_required')
        proof = json.loads(args.window_proof.read_bytes())
        common.need(proof.get('status') == 'WINDOW_INSPECTED_NO_CLOSE', 'inspected_window_proof_required')
        values.update(TOKEN=proof['review_token'], WINDOW=proof['window']['window_id'])
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_FOLLOWUP_PUBLICATION_VALIDATED_NO_SSH', action=args.action,
                             remote_sha256=common.sha(remote.encode()), startup_sha256=spec['startup_sha256'])))
        return
    result = common.execute_remote(remote, values)
    output = common.HERE / ('actual_' + args.action + '_' + str(time.time_ns()) + '.json')
    common.write_new_json(output, result)
    print(json.dumps(dict(output=str(output), result=result)))


if __name__ == '__main__':
    main()
