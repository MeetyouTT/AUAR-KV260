"""Create the exact proposed spec from public authority and written proof only."""
import argparse
import json
from pathlib import Path
import time

import rebind_common as common


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('authority', 'proof'):
        parser.add_argument('--' + name, required=True, type=Path)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--private-readback-path', required=True)
    args = parser.parse_args()
    authority = json.loads(common.pinned(args.authority, args.authority_sha256))
    proof = json.loads(common.pinned(args.proof, args.proof_sha256))
    binding = dict(authority=authority, authority_sha256=args.authority_sha256,
                   written_proof=proof, written_proof_sha256=args.proof_sha256, face_path=args.private_readback_path)
    spec = common.proposed(binding)
    path = common.HERE / ('proposed_spec_' + str(time.time_ns()) + '.json')
    digest = common.write_new_json(path, spec)
    print(json.dumps(dict(status='LOCAL_REBIND_SPEC_PREPARED_NO_SSH', spec=str(path), spec_sha256=digest,
                         configuration_sha256=spec['configuration_sha256'], startup_sha256=spec['startup_sha256'])))


if __name__ == '__main__':
    main()
