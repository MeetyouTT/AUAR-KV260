#!/usr/bin/env python3
"""Run only the already prepared bounded cycles and original-baseline recovery."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    run=Path(sys.argv[1]).resolve()
    marker=run/'cycle_controller.started.json'
    if marker.exists():
        raise RuntimeError('No automatic restart or repeat of the cycle controller')
    expected=re.findall(r'r[.]index +([0-9]+).*r[.]score +([0-9.eE+-]+)',(run/'03-baseline-functional.classification.output').read_text())
    assert len(expected)==5
    phases=['c1-remove-official','c2-load-official','c2-functional','c2-remove-official','c3-load-official',
            'c3-functional','c3-remove-official','r1-unload-repaired-module','r2-restore-original-module',
            'r3-restore-official-app','r4-restored-functional','r5-final-state']
    status={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'collector_sha256':hashlib.sha256((run/'collect_serial.py').read_bytes()).hexdigest(),
        'phases':phases,'completed_phases':[],'passed':False}
    marker.write_text(json.dumps(status,indent=2)+'\n')
    try:
        for phase in phases:
            print('START REVIEWED PHASE '+phase,flush=True)
            command=[sys.executable,str(run/'collect_serial.py'),phase]
            subprocess.run(command,cwd=str(run),check=True)
            rows=[json.loads(line) for line in (run/(phase+'.results.jsonl')).read_text().splitlines()]
            entries=[r for r in rows if r.get('type')=='command']
            manifest=json.loads((run/(phase+'.commands.json')).read_text())
            assert [e['id'] for e in entries]==[e['id'] for e in manifest]
            assert all(e['complete'] and e['exit_code']==0 for e in entries)
            if 'functional' in phase:
                actual=re.findall(r'r[.]index +([0-9]+).*r[.]score +([0-9.eE+-]+)',(run/(phase+'.classification.output')).read_text())
                query=json.loads((run/(phase+'.dpu_query.output')).read_text())
                assert actual==expected,'Classification differs'
                assert query['DPU IP Spec']['DPU Core Count']==1 and len(query['kernels'])==1
                kernel=query['kernels'][0]
                assert kernel['fingerprint']=='0x101000056010407' and kernel['cu_addr']=='0xa0010000'
                assert kernel['DPU Frequency (MHz)']==300 and kernel['DPU Arch']=='DPUCZDX8G_ISA1_B4096'
                (run/(phase+'.comparison.json')).write_text(json.dumps({'top5_same':True,'top5':actual,'architecture_and_address_match':True},indent=2)+'\n')
            elif phase!='r5-final-state':
                argv=[sys.executable,str(ROOT/'scripts/review_board_phase.py'),str(run),phase]
                if phase=='r2-restore-original-module':
                    prior=json.loads((run/'r1-unload-repaired-module.review.json').read_text())
                    argv.append(str(prior['commands'][0]['uptime_after']))
                subprocess.run(argv,check=True)
                review=json.loads((run/(phase+'.review.json')).read_text())
                for item in review['commands']:
                    assert item['kernel_interval_isolated'],'New kernel interval not isolated'
                    assert not item['refcount_errors'] and not item['exception_lines'] and not item['other_error_lines'],'New kernel error; stop further actions'
            status['completed_phases'].append(phase)
            (run/'cycle_controller.progress.json').write_text(json.dumps(status,indent=2)+'\n')
            print('REVIEW PASSED '+phase,flush=True)
        status['passed']=True
        print('BOUNDED CYCLES AND RECOVERY FINISHED',flush=True)
    except Exception as error:
        status['error']=str(error)
        print('STOPPED WITHOUT RETRY: '+str(error),flush=True)
        return 1
    finally:
        status['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (run/'cycle_controller.result.json').write_text(json.dumps(status,indent=2)+'\n')
    return 0


if __name__=='__main__':
    sys.exit(main())
