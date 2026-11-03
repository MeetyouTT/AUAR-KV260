"""Prepare only the root-selected, locally pinned summary policy revision."""
import json
import time

import summary_common as common


def main():
    spec = common.proposed()
    path = common.HERE / ('proposed_spec_' + str(time.time_ns()) + '.json')
    digest = common.write_new_json(path, spec)
    print(json.dumps(dict(status='LOCAL_SELECTED_SUMMARY_SPEC_PREPARED_NO_SSH', spec=str(path), spec_sha256=digest,
                         startup_sha256=spec['startup_sha256'])))


if __name__ == '__main__':
    main()
