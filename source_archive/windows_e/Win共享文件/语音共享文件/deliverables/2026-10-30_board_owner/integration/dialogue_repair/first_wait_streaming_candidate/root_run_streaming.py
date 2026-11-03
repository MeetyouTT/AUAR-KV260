"""Root-only isolated public streaming ASR measurement with the GUI retained."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import argparse,base64,hashlib,importlib.util,json,os,pathlib,subprocess,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
guard_path=pathlib.Path('/home/root/aura-public-asr-thread-abba-20261031/210925ca35fb5acd/probe_asr_abba.py')
assert hashlib.sha256(guard_path.read_bytes()).hexdigest()=='210925ca35fb5acdf90e96c08f9fe4713042637dd777d707c8ccb4134cdecf69'
spec=importlib.util.spec_from_file_location('_public_asr_guard',guard_path)
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True).splitlines() if '=' in x)
assert unit['ActiveState']=='active'
ui=int(unit['MainPID']);camera=guard.get('127.0.0.1',8790,'/health')['pid']
assert type(camera) is int
args=argparse.Namespace(runtime_root=str(root),startup_sha256=EXPECTED,
 boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 ui_pid=ui,ui_birth=guard.proc(ui)['birth'],camera_pid=camera,camera_birth=guard.proc(camera)['birth'],min_available_mib=512)
before=guard.metadata(args)
directory=pathlib.Path('/home/root/aura-public-streaming-asr-20261031/68c9c943840f7d9c')
assert directory.is_dir() and not directory.is_symlink()
raw=base64.b64decode(SOURCE);assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
probe=directory/('probe_'+SOURCE_SHA[:16]+'.py');assert not probe.is_symlink()
if probe.exists():assert probe.read_bytes()==raw
else:
 with probe.open('xb') as out:out.write(raw)
command=['python3','-B',str(probe),
 '--model',str(directory/'model.int8.onnx'),'--model-sha256','68c9c943840f7d9cf3e8a4970ba50f404feb5277f611fa82b7e72267786fa84a',
 '--tokens',str(directory/'tokens.txt'),'--tokens-sha256','6fed8c6c248516f38e7faa19404b57413e8ce259f1cbc1fa4aebc86eac32fdfd',
 '--wav','/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/models/paraformer/test_wavs/0.wav',
 '--wav-sha256','1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c',
 '--baseline-output-sha256','cbe36e837e51a8636d1042b26557822c053c2f9626345d73f760f63078b11b3a',
 '--public-input-confirmed']
environment=dict(os.environ,PYTHONPATH='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
 OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment,timeout=100)
assert len(p.stdout)<262144
try:result=json.loads(p.stdout)
except Exception:result=dict(status='INVALID_PROBE_OUTPUT',exit_code=p.returncode)
after=guard.metadata(args,allow_background=True)
assert before['ui']==after['ui'] and before['camera']==after['camera']
result.update(root_guard_before=before,root_guard_after=after,probe_sha256=SOURCE_SHA,
 production_configuration_changed=False,formal_pipeline_integrated=False,
 background_activity_changed=before['memory']!=after['memory'] or not after['model_idle'],
 actual_capture_or_render_fps_acceptance=False)
print(json.dumps(result))
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe-sha256', required=True)
    args = parser.parse_args()
    raw = (HERE / 'public_streaming_probe.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == args.probe_sha256
    spec = json.loads((HERE.parent.parent / 'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    header = 'EXPECTED=' + repr(spec['startup_sha256']) + '\nSOURCE_SHA=' + repr(args.probe_sha256) + '\nSOURCE=' + repr(base64.b64encode(raw).decode()) + '\n'
    value = json.loads(ssh('python3 -B -', header + REMOTE, timeout=120))
    output = HERE / ('actual_streaming_' + str(time.time_ns()) + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    print(json.dumps(value))
