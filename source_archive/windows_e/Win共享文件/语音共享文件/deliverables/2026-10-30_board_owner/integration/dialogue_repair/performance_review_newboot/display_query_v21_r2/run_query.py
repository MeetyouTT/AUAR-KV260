"""Root-only passive XCB query. The default command validates locally without SSH."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
R1 = HERE.parent / 'display_restore_v21'
PINS = {'display_restore.py': 'b8ddcd3ab3e996de62ce91747d5a21b6fbaed70bf909de6c7c2a685d079a3d70',
        'run_display_restore.py': '46fce37054e60a635fa75eae492ff95de921320b36a6c1f7ad9ffb72ae9b83b4'}


def local_inputs():
    modules = {}
    for filename, pin in PINS.items():
        path = R1 / filename
        if hashlib.sha256(path.read_bytes()).hexdigest() != pin:
            raise ValueError('FROZEN_R1_CHANGED')
        name = path.stem
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules[name] = module
    old = modules['run_display_restore']
    return old.local_inputs(old.EVIDENCE / 'spec.json', old.SPEC_SHA, old.EVIDENCE / 'ready.json', old.READY_SHA)


def build_remote():
    sources = {name: (HERE / (name + '.py')).read_bytes().decode('utf-8')
               for name in ('read_only_guard', 'xcb_screensaver', 'query_display')}
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
    raise sys.modules['read_only_guard'].Refused('BOUNDED_READONLY_QUERY_TIMEOUT')
signal.signal(signal.SIGALRM, expired)
signal.alarm(85)
try:
    result = sys.modules['query_display'].execute(ARGUMENTS)
finally:
    signal.alarm(0)
print(json.dumps(result, sort_keys=True))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'observe'))
    parser.add_argument('--expected-policy', choices=('temporary', 'original'), default='temporary')
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    common, arguments = local_inputs()
    arguments.update(action=args.action, expected_policy=args.expected_policy, token=time.time_ns())
    remote = build_remote()
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_XCB_READONLY_VALIDATED', action=args.action,
            remote_sha256=hashlib.sha256(remote.encode()).hexdigest(), source_components=380,
            device_access=False, policy_modified=False)))
        return
    result = common.execute_remote(remote, dict(ARGUMENTS=arguments), timeout=115)
    output = HERE / ('actual_' + args.action + '_' + str(arguments['token']) + '.json')
    pin = common.write_new_json(output, result)
    print(json.dumps(dict(output=str(output), sha256=pin, result=result), ensure_ascii=True))


if __name__ == '__main__':
    main()
