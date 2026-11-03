"""Prepare the pinned read-only single-task diagnostic. Root execution is explicit."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parents[2]
PUBLISHER = REPAIR / 'release_v23_memory_summary_candidate'
PINS = {'spec.json': '8376770e832d82add3ae207da3228c46c34ada89b95830cdd7536f8291224ec2',
        'ready.json': 'ab81bbc36ad34cbdcbc36a5830a36b2937e7975c40bd44accc7fb258c9a70aaa',
        'installed.json': '0c60f434447bf3704b326ff98a4af76d3a9eb44730db92f816a701bdd8f581ea',
        'source_mapping.json': 'b053291dd3af5f5bc6e441288b5db91521226b903958bcbf3ca939a6541945d6'}


def inputs():
    import hashlib
    need = lambda value: None if value else (_ for _ in ()).throw(ValueError('PINNED_LOCAL_INPUT_CHANGED'))
    for name, pin in {'summary_common.py': '7b7227447bee67e38ed4371fc4d58979bdf56f2f36c3745c8fdd934e012d6a25',
                      'seal_summary.py': '99a5906d2412216df0a45ccd9cc9fcb122c35c1b976bf2b9d48638eb7cfb1ef2'}.items():
        need(hashlib.sha256((PUBLISHER / name).read_bytes()).hexdigest() == pin)
    sys.path.insert(0, str(PUBLISHER))
    import summary_common as common
    import seal_summary
    values = {name: json.loads(common.pinned(PUBLISHER / 'memory_summary_evidence' / name, pin))
              for name, pin in PINS.items()}
    spec, ready, installed, mapping = [values[name] for name in PINS]
    seal_summary.validate_mapping(mapping, spec, ready, installed)
    arguments = dict(spec=spec, ready=ready, installed=installed, mapping=mapping,
                     previous_spec_sha256=common.BASE_SPEC_SHA, guard_source=seal_summary.build_remote(spec))
    source = (HERE / 'worker.py').read_text(encoding='utf8')
    ast.parse(source, feature_version=(3, 9))
    return common, arguments, source


REMOTE = '''
import json, subprocess, sys
contract = {'__name__': '_diagnostic_output_contract'}
exec(compile(WORKER_SOURCE, '<diagnostic-contract>', 'exec'), contract)
result = contract['empty_result']()
process = None
try:
    process = subprocess.Popen(['/usr/bin/python3', '-B', '-c', WORKER_SOURCE],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        output, unused = process.communicate(json.dumps(ARGUMENTS, ensure_ascii=True).encode('ascii'), timeout=45)
        if process.returncode != 0 or len(output) > 32768:
            raise ValueError()
        result = contract['validate_output'](contract['parse'](output))
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=3)
        result = contract['empty_result']('OWNED_CHILD_WINDOW_EXPIRED')
except BaseException:
    if process is not None and process.poll() is None:
        process.kill()
        process.communicate(timeout=3)
    result = contract['empty_result']('OUTPUT_CONTRACT_REFUSED')
print(json.dumps(contract['validate_output'](result), ensure_ascii=True, allow_nan=False))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    common, arguments, source = inputs()
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_SINGLE_DIAGNOSTIC_VALIDATED', component_count=380,
                              maximum_model_calls=1, hard_window_seconds=45, device_accessed=0)))
        return
    handoff = json.loads((HERE / 'HANDOFF.json').read_bytes())
    for name, item in handoff['files'].items():
        common.pinned(HERE / name, item['sha256'])
    result = common.execute_remote(REMOTE, dict(WORKER_SOURCE=source, ARGUMENTS=arguments), timeout=65)
    definition = importlib.util.spec_from_file_location('_local_fixed_output_contract', HERE / 'worker.py')
    contract = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(contract)
    contract.validate_output(result)
    common.write_new_json(HERE / ('actual_once_' + str(time.time_ns()) + '.json'), result)
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))


if __name__ == '__main__':
    main()
