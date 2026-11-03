"""Root serial admission: run the existing ownership check with selected mode."""
import json
from pathlib import Path
import runpy
import sys

HERE=Path(__file__).resolve().parent
INTEGRATION=HERE.parent.parent
PROJECT=HERE.parents[4]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

if __name__=='__main__':
    original=runpy.run_path(str(INTEGRATION/'listening_entry_fix/check_complete_capture_process.py'))['REMOTE']
    assert original.count("optimization='baseline'")==1
    remote=original.replace("optimization='baseline'","optimization=cfg['board_business']['frontend_optimization']")
    remote=remote.replace("print(json.dumps(out))", "out['configured_mode']=cfg['board_business']['frontend_optimization']\nout['actual_mode']=gate.optimization\nassert out['configured_mode']==out['actual_mode']=='combined'\nprint(json.dumps(out))")
    spec=json.loads((INTEGRATION/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    value=json.loads(ssh('env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -',
        'EXPECTED='+repr(spec['startup_sha256'])+'\n'+remote,timeout=90))
    value['startup_sha256']=spec['startup_sha256']
    (HERE/('actual_worker_admission_'+spec['startup_sha256'][:16]+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    (HERE/'actual_worker_admission.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    assert value['passed']
    print(json.dumps({key:value[key] for key in ('passed','configured_mode','actual_mode','worker_shutdown_confirmed','cancel_state','worker_nice','arecord_after_cancel')}))
