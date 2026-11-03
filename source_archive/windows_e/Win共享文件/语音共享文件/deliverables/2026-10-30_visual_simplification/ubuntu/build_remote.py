"""Build reviewable task scripts; never opens a device or executes a deployment."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase',choices=('stage','deploy'))
    parser.add_argument('--baseline',type=Path)
    args = parser.parse_args()
    if args.phase == 'stage':
        assert args.baseline
        b = json.loads(args.baseline.read_text())
        # Load pure guard functions without invoking board access.
        module = types.ModuleType('board_state')
        module.capture = lambda:None
        sys.modules['board_state'] = module
        namespace = {'__name__':'guard_builder'}
        exec((HERE/'workflow_common.py').read_text(),namespace)
        signature = namespace['signature'](b)
        stub = (HERE.parent/'board/device_observer.py').read_text()
        stage = '/home/root/aura-board-vision-20261030/'+hashlib.sha256(stub.encode()).hexdigest()[:16]+'-r3-ubuntu'
        sources = {name:(HERE/name).read_text() for name in (
            'board_state.py','workflow_common.py','runtime_clone.py','test_runtime_clone.py')}
        sources['device_observer.py'] = stub
        prefix = ('EXPECTED_SIGNATURE='+repr(signature)+'\nSTAGE='+repr(stage)+'\n'
                  +'SOURCES='+repr(sources)+'\n')
        output = HERE/'stage_visual.py'
        script = prefix+(HERE/'stage_body.py').read_text()
    else:
        entries = sorted(HERE.glob('evidence/*-stage_visual/result.json'))
        assert entries
        candidate = json.loads(entries[-1].read_text())
        assert candidate['status'] == 'STAGED' and candidate['arm_tests'] == 9
        ops = {name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
               for name in ('board_state.py','workflow_common.py','runtime_clone.py')}
        rollback = (HERE/'rollback_owned.py').read_text()
        prefix = ('STAGE='+repr(candidate['stage'])+'\n'
                  +'EXPECTED_CANDIDATE='+repr(candidate)+'\n'
                  +'OPS_SHA256='+repr(ops)+'\n'
                  +'ROLLBACK_SOURCE='+repr(rollback)+'\n'
                  +'ROLLBACK_SHA256='+repr(hashlib.sha256(rollback.encode()).hexdigest())+'\n')
        output = HERE/'deploy_visual.py'
        script = prefix+(HERE/'deploy_body.py').read_text()
    compile(script,str(output),'exec')
    output.write_text(script)
    print(json.dumps(dict(script=str(output),bytes=len(script.encode()),
                          sha256=hashlib.sha256(script.encode()).hexdigest(),board_accessed=False)))


if __name__ == '__main__':
    main()
