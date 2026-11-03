"""Read original motion CLI/config contracts. Never imports or runs board code."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
transport = HERE.parents[1] / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('axis_contract_readonly_transport', transport)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SCRIPT = r'''
import hashlib,json
from pathlib import Path
app=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura')
release=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
older=Path('/home/root/aura-axis-priority-20261101-3c94e7a0')
observed=Path('/home/root/aura-face-follow-test-20261101-bebd3e7d-r2')
files=[older/'bench_finite_step_deadline_fix.py',older/'bench_observed_80us_6s.py',
 app/'board/motion/manual.py',app/'board/motion/manual_live_config.py',
 app/'tools/face_pan_controls.py',app/'tools/pan_controls.py',
 app/'config/pan_manual.local.json',app/'config/pan_face.local.json',
 app/'config/pan_direction.current.json',
 observed/'visible-expected-state.json',observed/'visible-expected-state-powered.json',
 observed/'visible-expected-state-observed.json',
 observed/'current-direction-human.json',
 observed/'original-entry/human-evidence.json',
 observed/'original-entry/manual-release/release.json',
 release/'candidate-manifest.json',release/'bench_identity_stop.py']
out={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'fdt_sha256':hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest(),
 'startup_sha256':hashlib.sha256((app.parent.parent/'startup/config.json').read_bytes()).hexdigest(),
 'read_only':True,'files':{}}
for p in files:
 if not p.is_file() or p.is_symlink():
  out['files'][str(p)]={'regular':False};continue
 raw=p.read_bytes()
 assert len(raw)<100000
 out['files'][str(p)]={'regular':True,'sha256':hashlib.sha256(raw).hexdigest(),
  'bytes':len(raw),'text':raw.decode('utf-8')}
tx=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1')
out['transaction_json_files']=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
 'bytes':p.stat().st_size} for p in sorted(tx.glob('*.json')) if p.is_file() and not p.is_symlink()]
print(json.dumps(out,ensure_ascii=False))
'''

start = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = json.loads(module.ssh('python3 -B -', SCRIPT, timeout=40))
target = HERE / 'current_motion_contracts_readonly_01.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump({'host_start_utc': start, 'host_end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'script_sha256': hashlib.sha256(SCRIPT.encode()).hexdigest(), 'board_result': result},
              stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'output':str(target),'boot_id':result['boot_id'],
 'startup_sha256':result['startup_sha256'],
 'files':{p:{k:v for k,v in value.items() if k!='text'} for p,value in result['files'].items()},
 'transaction_json_files':result['transaction_json_files']},ensure_ascii=False))
