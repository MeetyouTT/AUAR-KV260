"""Check the current v23 baseline and prepare only a later root-selected source."""
import argparse
import json
import time

import followup_common as common


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-prepared', action='store_true')
    args = parser.parse_args()
    common.require_current_baseline()
    if common.APPROVED_PAYLOAD_SHA is None:
        common.need(not args.write_prepared, 'root_selection_required_before_prepared_spec')
        print(json.dumps({'status': 'DRY_V24_BASELINE_VALIDATED_SOURCE_SELECTION_PENDING',
            'baseline_spec_sha256': common.BASE_SPEC_SHA, 'device_execution_enabled': False}))
        return
    spec = common.proposed()
    result = {'status': 'DRY_V24_SELECTED_SPEC_VALIDATED_NO_WRITES',
        'spec_sha256': common.sha(common.encoded(spec)), 'startup_sha256': spec['startup_sha256']}
    if args.write_prepared:
        path = common.HERE / ('proposed_spec_' + str(time.time_ns()) + '.json')
        common.write_new_json(path, spec)
        result.update(status='LOCAL_SELECTED_FOLLOWUP_SPEC_PREPARED_NO_SSH', spec=str(path))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
