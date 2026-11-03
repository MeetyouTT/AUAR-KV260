"""Default dry two-source memory apply with original leases and source closure."""
import argparse
import ast
import json
from pathlib import Path
import time

import summary_common as common


def original_transaction_helpers():
    raw = common.pinned(common.PREVIOUS / 'apply_runtime.py', 'ec675890f012c6e9722c5108f47161cf652d14a96948b48c543b7782a675afe1').decode()
    names = {'exact_file', 'private_directory', 'fsync_directory', 'saved_pause'}
    nodes = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name in names]
    common.need({node.name for node in nodes} == names, 'original_transaction_helpers_required')
    helpers = '\n\n'.join(ast.get_source_segment(raw, node) for node in nodes) + '\n'
    helpers += (common.HERE / 'rollforward.py').read_text(encoding='utf8')
    return helpers


def build_remote(spec):
    common.validate_spec(spec, allow_proposed=True)
    common.need(spec['summary_revision']['state'] == 'PROPOSED', 'proposed_summary_spec_required')
    remote = common.publisher_remote(spec)
    anchor = "\nboot()\nwith open('/run/aura-production-publisher.lock','a') as lock:"
    common.need(remote.count(anchor) == 1, 'unique_frozen_dispatch_anchor_required')
    remote = remote.split(anchor, 1)[0]
    base = common.baseline()
    values = dict(BASE_PINS=base['component_sha256'], BASE_STARTUP=common.startup_for(base),
                  BASE_STARTUP_SHA=common.BASE_STARTUP_SHA, BASE_CONFIG_SHA=common.BASE_CONFIG_SHA,
                  BASE_MANIFEST_SHA=common.BASE_MANIFEST_SHA, BASE_SOURCE_PINS=common.OLD_SOURCE_PINS,
                  BASE_SPEC_SHA=common.BASE_SPEC_SHA, CONFIGURATION_PATH=base['minor_prepared_configuration_path'],
                  REVISION=common.REVISION, SOURCE_PATHS=['common/board_memory.py', 'board/runtime/board_memory_policy.py'],
                  LAUNCHER_SHA='5b15a8cf1813935679e5f4d30eb788e9c8d6ae18826669009d06c92cba152e03')
    remote = ''.join(key + '=' + repr(value) + '\n' for key, value in values.items()) + remote
    remote += '\n' + original_transaction_helpers() + '\n' + (common.HERE / 'apply_runtime.py').read_text(encoding='utf8')
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
        print(json.dumps(dict(status='DRY_SUMMARY_APPLY_VALIDATED_NO_SSH', remote_sha256=common.sha(remote.encode()),
                             changed_components=sorted(common.ALLOWED_PATHS), component_pins=380)))
        return
    result = common.execute_remote(remote, dict(SPEC=spec, ACTION='start', TOKEN=None, WINDOW=None,
                                                  PAYLOAD=common.payload_for(spec)))
    suffix = str(time.time_ns())
    output = common.HERE / ('actual_apply_' + suffix + '.json')
    common.write_new_json(output, result)
    common.need(result.get('status') == 'SUMMARY_MEMORY_SOURCES_APPLIED_UI_STOPPED', 'summary_source_apply_incomplete')
    applied = common.validate_spec(result['spec'])
    path = common.HERE / ('applied_spec_' + suffix + '.json')
    digest = common.write_new_json(path, applied)
    print(json.dumps(dict(status=result['status'], output=str(output), spec=str(path), spec_sha256=digest)))


if __name__ == '__main__':
    main()
