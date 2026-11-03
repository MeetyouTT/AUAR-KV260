"""Stage and run the reviewed H01 test overlay during the root's closed-UI window."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
FEATURE = HERE.parent / 'feature_trigger_collaboration'
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

parser = argparse.ArgumentParser()
parser.add_argument('--run', action='store_true')
args = parser.parse_args()
manifest = json.loads((FEATURE / 'candidate_h01/BOARD_STAGE_MANIFEST.json').read_bytes())
assert len(manifest['files']) == 6
payload = []
for relative, item in manifest['files'].items():
    path = FEATURE / relative
    assert path.resolve().is_relative_to(FEATURE.resolve()) and not path.is_symlink()
    raw = path.read_bytes()
    assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']
    payload.append(dict(path=Path(relative).as_posix(), sha256=item['sha256'], data=base64.b64encode(raw).decode()))
stage = '/home/root/aura-h01-closed-validation-20261031/b6c702864cf5ede6'
run_id = str(time.time_ns())
source = r'''
import base64,hashlib,json,os,subprocess,time
from pathlib import Path
stage=Path(STAGE)
assert stage.resolve()==stage and stage.parent==Path('/home/root/aura-h01-closed-validation-20261031')
stage.mkdir(mode=0o700,parents=True,exist_ok=True)
for item in PAYLOAD:
    path=stage/item['path']
    assert path.resolve()==path and path.is_relative_to(stage)
    raw=base64.b64decode(item['data'],validate=True)
    assert hashlib.sha256(raw).hexdigest()==item['sha256']
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==raw
    else:
        with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        path.chmod(0o444)
if not RUN:
    print(json.dumps(dict(status='H01_STAGED_NO_TEST',stage=STAGE)))
else:
    root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
    assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()=='0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
    def unit():
        return dict(row.split('=',1) for row in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','Job'],text=True).splitlines())
    before=unit()
    assert before==dict(MainPID='0',ActiveState='inactive',Job='')
    journal=json.loads((root.parent/'control-production-v1/state.json').read_bytes())
    assert journal['phase']=='NORMAL_CLOSED' and journal['guard_removed'] is False
    output=stage/('ACTUAL_'+RUN_ID+'.json')
    command=['/usr/bin/timeout','--signal=TERM','--kill-after=5','60','/usr/bin/python3','-B',
        str(stage/'candidate_h01/board_runner.py'),'--runtime-root',str(root/'runtime/aura'),
        '--startup-config',str(root/'startup/config.json'),
        '--mapping',str(stage/'board_integration_v17/source_mapping.json'),
        '--worker',str(stage/'board_integration_v17/worker.py'),
        '--candidate-manifest',str(stage/'candidate_h01/SOURCE_MANIFEST.json'),
        '--candidate-root',str(stage/'candidate_h01/after'),
        '--coordinated-slot','root-closed-'+RUN_ID,'--output',str(output)]
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
    try:stdout,stderr=process.communicate(timeout=68)
    except subprocess.TimeoutExpired:
        import signal
        os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate(timeout=5)
    remaining=[]
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            stat=path.read_text().rsplit(')',1)[1].split()
            if int(stat[2])==process.pid:remaining.append(int(path.parent.name))
        except (FileNotFoundError,ProcessLookupError):pass
    assert unit()==before
    result=json.loads(output.read_bytes()) if output.exists() else dict(status='NO_RESULT')
    print(json.dumps(dict(exit_code=process.returncode,process_group_empty=not remaining,
        production_stayed_closed=True,result=result,stderr_sha256=hashlib.sha256(stderr).hexdigest(),
        stderr_bytes=len(stderr))))
'''
header = dict(STAGE=stage, PAYLOAD=payload, RUN=args.run, RUN_ID=run_id)
result = json.loads(ssh('python3 -B -', '\n'.join(key+'='+repr(value) for key,value in header.items())+'\n'+source,
                        timeout=90))
output = HERE / ('h01_closed_' + run_id + '.json')
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
test = result.get('result', {})
print(json.dumps(dict(evidence=str(output), status=test.get('status', result.get('status')),
    passed=test.get('passed'), failed=test.get('failed'), process_group_empty=result.get('process_group_empty'))))
