"""Validate or run the guarded, resumable same-boot configuration transaction."""
import argparse
import ast
import json
from pathlib import Path
import time

import rebind_common as common


def build_remote(spec):
    common.validate_spec(spec, allow_proposed=True)
    common.need(spec['camera_rebind']['state'] == 'PROPOSED', 'proposed_rebind_spec_required')
    remote = common.publisher_remote(spec)
    anchor = "\nboot()\nwith open('/run/aura-production-publisher.lock','a') as lock:"
    common.need(remote.count(anchor) == 1, 'unique_frozen_dispatch_anchor_required')
    remote = remote.split(anchor, 1)[0]
    base = common.baseline()
    values = dict(BASE_PINS=base['component_sha256'], BASE_STARTUP=common.literal('EXPECTED_STARTUP'),
                  BASE_GUI=common.literal('EXPECTED_GUI'), BASE_STARTUP_SHA=common.BASE_STARTUP_SHA,
                  BASE_CONFIG_SHA=common.BASE_CONFIG_SHA, BASE_MANIFEST_SHA=common.BASE_MANIFEST_SHA,
                  OLD_EXTERNAL_PATH=base['minor_prepared_configuration_path'], REVISION=common.REVISION,
                  CONFIG_RELATIVE=common.CONFIG_RELATIVE,
                  LAUNCHER_SHA='5b15a8cf1813935679e5f4d30eb788e9c8d6ae18826669009d06c92cba152e03')
    prefix = ''.join(key + '=' + repr(value) + '\n' for key, value in values.items())
    remote = prefix + remote + '\n' + (common.HERE / 'rollforward.py').read_text(encoding='utf8')
    remote += '\n' + (common.HERE / 'apply_runtime.py').read_text(encoding='utf8')
    ast.parse(remote, feature_version=(3, 9))
    return remote


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True, type=Path)
    parser.add_argument('--spec-sha256', required=True)
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    spec = common.validate_spec(json.loads(common.pinned(args.spec, args.spec_sha256)), allow_proposed=True)
    remote = build_remote(spec)
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_REBIND_APPLY_VALIDATED_NO_SSH', remote_sha256=common.sha(remote.encode()),
                             changed_components=[common.CONFIG_RELATIVE], component_pins=380)))
        return
    result = common.execute_remote(remote, dict(SPEC=spec, ACTION='start', TOKEN=None, WINDOW=None))
    suffix = str(time.time_ns())
    output = common.HERE / ('actual_apply_' + suffix + '.json')
    common.write_new_json(output, result)
    common.need(result.get('status') == 'CAMERA_OWNER_REBOUND_UI_STOPPED', 'rebind_incomplete')
    applied = common.validate_spec(result['spec'])
    path = common.HERE / ('applied_spec_' + suffix + '.json')
    digest = common.write_new_json(path, applied)
    print(json.dumps(dict(status=result['status'], output=str(output), spec=str(path), spec_sha256=digest)))


if __name__ == '__main__':
    main()
