#!/usr/bin/env python3
"""Finish one explicit source build with offline audit and paired bundle checks."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    expected = Path(sys.argv[1]).resolve()
    assert ROOT/'evidence' in expected.parents
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT/'evidence'/(stamp+'-source-finalization')
    out.mkdir()
    state = dict(state='waiting_for_implementation', evidence=str(out),
                 implementation=str(expected), board_modified=False,
                 physical_actuation_enabled=False, release_complete=False)

    def save():
        text = json.dumps(state, indent=2)+'\n'
        (out/'status.json').write_text(text)
        (ROOT/'CURRENT_SOURCE_RELEASE.json').write_text(text)
        print(json.dumps(state), flush=True)

    save()
    try:
        deadline = time.monotonic()+4*3600
        while True:
            build = json.loads((ROOT/'CURRENT_SOURCE_IMPLEMENTATION.json').read_text())
            assert Path(build['evidence']).resolve()==expected, 'Selected build changed'
            if build['state']=='finished':
                assert build['implementation_passed'], 'Source implementation failed'
                break
            assert time.monotonic()<deadline, 'Source implementation wait timeout'
            time.sleep(10)
        for phase, script in [('auditing', 'audit_joint.py'), ('sealing', 'prepare_candidate_bundle.py')]:
            state['state'] = phase
            save()
            with (out/(phase+'.log')).open('wb') as log:
                p = subprocess.run([sys.executable, str(ROOT/'scripts'/script), '--source-platform'],
                                   cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            state[phase+'_rc'] = p.returncode
            assert p.returncode==0, phase+' failed; inspect '+str(out/(phase+'.log'))
        bundle = json.loads((ROOT/'CURRENT_CANDIDATE_BUNDLE.json').read_text())
        assert bundle['implementation_built_from_generated_project']
        assert bundle['bitstream_and_handoff_from_same_project'] and bundle['board_test_ready']
        assert bundle['source_bitstream_sha256']
        state.update(state='finished', release_complete=True,
                     bundle_evidence=bundle['evidence'], build_id=bundle['build_id'],
                     board_test_ready=True, deployable=False,
                     finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save()
        return 0
    except Exception as error:
        state.update(state='failed', error=str(error),
                     finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        save()
        raise


if __name__=='__main__':
    raise SystemExit(main())
