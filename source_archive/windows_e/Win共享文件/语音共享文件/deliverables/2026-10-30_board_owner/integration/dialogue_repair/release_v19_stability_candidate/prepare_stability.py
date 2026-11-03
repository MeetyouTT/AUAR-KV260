"""Prepare the sealed current or proposed minor spec without device access."""
import argparse
import json
from pathlib import Path

import stability_common as common


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--proposed',action='store_true')
    args=parser.parse_args()
    value=common.proposed() if args.proposed else common.baseline()
    digest=common.write_new_json(args.output,value)
    print(json.dumps(dict(status='LOCAL_MINOR_SPEC_PREPARED_NO_SSH',path=str(args.output),sha256=digest,
        source_manifest_sha_requires_apply_receipt=args.proposed),ensure_ascii=True))


if __name__=='__main__':
    main()
