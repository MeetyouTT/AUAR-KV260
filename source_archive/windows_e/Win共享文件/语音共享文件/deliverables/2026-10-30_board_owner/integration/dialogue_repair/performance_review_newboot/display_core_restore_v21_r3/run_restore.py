"""Root-only restoration of the exact saved core policy. Dry by default."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
R2 = HERE.parent / 'display_query_v21_r2'
POLICY_EVIDENCE = HERE.parent.parent / 'progress_followup_20261031/v21_x_policy_1793506639886502500.json'
POLICY_EVIDENCE_SHA = '6da23a157e61a46abacd1bd01f0ba83986f432a33cde329bd98aea75b3d4cc88'
PINS = {'read_only_guard.py': 'b9d993be6a3318cf5956aabfa073c84d348f93099be244b376b0e9636c9dc630',
    'xcb_screensaver.py': 'b8779b899cab45e0668fefda0ecd0a4d0e99b580b5640cb8dc5985e25f546436',
    'query_display.py': '45dd1797118adf123a52abc37f8c53c27e87a44b14b6ed66448ae64d6c287863',
    'run_query.py': 'cc37d141ce36a4eb9ee5e4099af57598d784ca2d4891c91c0908d96ac4952ce9'}


def pinned_sources():
    sources = {}
    for filename, pin in PINS.items():
        raw = (R2 / filename).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError('FROZEN_R2_CHANGED')
        sources[Path(filename).stem] = raw.decode('utf-8')
    return sources


def local_inputs():
    sources = pinned_sources()
    spec = importlib.util.spec_from_file_location('_r3_frozen_query_runner', R2 / 'run_query.py')
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    common, arguments = previous.local_inputs()
    raw = common.pinned(POLICY_EVIDENCE, POLICY_EVIDENCE_SHA)
    arguments.update(current_policy_evidence=json.loads(raw), current_policy_evidence_sha256=POLICY_EVIDENCE_SHA)
    return common, arguments


def build_remote():
    sources = pinned_sources()
    del sources['run_query']
    sources['restore_core'] = (HERE / 'restore_core.py').read_bytes().decode('utf-8')
    for source in sources.values():
        ast.parse(source, feature_version=(3, 9))
    return '''
import json, signal, sys, types
MODULE_SOURCES = ''' + repr(sources) + '''
for name, source in MODULE_SOURCES.items():
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(source, '<pinned-' + name + '>', 'exec'), module.__dict__)
def expired(signum, frame):
    raise sys.modules['read_only_guard'].Refused('BOUNDED_CORE_RESTORE_TIMEOUT')
signal.signal(signal.SIGALRM, expired)
signal.alarm(85)
try:
    result = sys.modules['restore_core'].execute(ARGUMENTS)
finally:
    signal.alarm(0)
print(json.dumps(result, sort_keys=True))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    common, arguments = local_inputs()
    remote = build_remote()
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_EXACT_CORE_RESTORE_VALIDATED',
            remote_sha256=hashlib.sha256(remote.encode()).hexdigest(),
            current_policy_evidence_sha256=POLICY_EVIDENCE_SHA, device_access=False)))
        return
    arguments['token'] = time.time_ns()
    result = common.execute_remote(remote, dict(ARGUMENTS=arguments), timeout=115)
    output = HERE / ('actual_restore_' + str(arguments['token']) + '.json')
    pin = common.write_new_json(output, result)
    print(json.dumps(dict(output=str(output), sha256=pin, result=result), ensure_ascii=True))


if __name__ == '__main__':
    main()
