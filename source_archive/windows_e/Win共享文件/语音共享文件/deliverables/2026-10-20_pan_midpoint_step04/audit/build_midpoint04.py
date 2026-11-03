"""Generate a new, finite calibration transaction from the reviewed wide bench."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

J = Path(__file__).parent
D = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_midpoint_step04')
D.mkdir(exist_ok=False)
old = D.parent/'2026-10-20_pan_visible_direction_wide/wide_sweep_bench.py'
s = old.read_text()
assert hashlib.sha256(s.encode()).hexdigest() == '85e66459ccdd8cf3009a6666d879de87c3afe843548936d216996767a9640815'
changes = {
    "'VISIBLE_FIXED_SWEEP_BENCH'": "'FINITE_MIDPOINT_STEP_BENCH'",
    "'duration_s': 3.0, 'target_us': pulse} for pulse in (1580, 1420, 1490)": "'duration_s': 2.0, 'target_us': pulse} for pulse in (1470,)",
    "'duration_s': 9": "'duration_s': 2",
    'One wide fixed sweep 1580us then 1420us then 1490us, 3s each, hardware slew limited': 'One finite 1470us step from initial 1490us, 2s, hardware slew limited',
    'VISIBLE1420-1580-9S': 'MIDPOINT1470-2S',
    "initial['ack_seq'] == 137 and initial['epoch'] == 4": "initial['ack_seq'] == 208 and initial['epoch'] == 5",
    'session, epoch = 0x20261020, 5': 'session, epoch = 0x20261020, 6',
}
for a,b in changes.items():
    assert s.count(a) == (2 if a == 'VISIBLE1420-1580-9S' else 1), a
    s = s.replace(a,b)
raw = s.encode()
sha = hashlib.sha256(raw).hexdigest()
(D/'midpoint_step_bench.py').write_bytes(raw)
compile(raw, str(D/'midpoint_step_bench.py'), 'exec')
plan = json.loads(subprocess.check_output([sys.executable, '-B', str(D/'midpoint_step_bench.py')], text=True))
assert plan['stages'] == [{'duration_s': 2.0, 'target_us': 1470}] and plan['duration_s'] == 2
assert plan['lease_ms'] == 100 and not plan['automatic_following']
r = subprocess.run([sys.executable,'-B',str(D/'midpoint_step_bench.py'),'--execute'],capture_output=True,text=True)
assert r.returncode == 2
r = subprocess.run([sys.executable,'-B',str(D/'midpoint_step_bench.py'),'--execute','--confirmation','MIDPOINT1470-2S','--output',str(D/'must-not-be-created.json')],capture_output=True,text=True)
assert r.returncode != 0 and not (D/'must-not-be-created.json').exists()
(D/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
(D/'host-checks.json').write_text(json.dumps({'syntax':True,'default_plan_no_hardware':True,'single_1470us_2s':True,'confirmation_required':True,'non_board_rejected':True,'initial_epoch':5,'initial_ack':208,'new_epoch':6,'finally_stop_preserved':True,'source_sha256':sha},indent=2)+'\n')
(D/'field-input.json').write_text(json.dumps({'user_exact':'看清了，现在还有点向右偏转，再转一下','prior_wide_movement_visible':True,'current_test_point_us':1490,'new_target_us':1470,'basis':'Earlier user reported increasing pulse worsened right bias; decrease for this finite correction','mechanical_reference_calibrated':False,'image_space_polarity_confirmed':False,'servo_settling_mode_confirmed':False},ensure_ascii=False,indent=2)+'\n')

w = (J/'board_wide_visible_execute2.py').read_text()
start = w.index("RAW=gzip.decompress(base64.b64decode('")+len("RAW=gzip.decompress(base64.b64decode('")
end = w.index("'))",start)
w = w[:start]+base64.b64encode(gzip.compress(raw,mtime=0)).decode()+w[end:]
w = w.replace('85e66459ccdd8cf3009a6666d879de87c3afe843548936d216996767a9640815',sha)
for a,b in {
    'visible-direction-wide-01':'midpoint-step-04',
    'wide_sweep_bench.py':'midpoint_step_bench.py',
    'User explicitly requested larger movement; one bounded 1420..1580us sweep,9s,final1490us':'User saw the larger movement, reported residual right bias and requested another correction; one 1470us hold for2s from1490us',
    'VISIBLE1420-1580-9S':'MIDPOINT1470-2S',
    '动作再大一点':'看清了，现在还有点向右偏转，再转一下',
    'Execute one user-requested wider finite sweep after preparation and a start cue.':'Execute one user-requested finite 1470us correction after preparation and a start cue.',
}.items():
    assert a in w,a
    w = w.replace(a,b)
compile(w,'board_midpoint04_execute.py','exec')
(J/'board_midpoint04_execute.py').write_text(w)
wsha = hashlib.sha256(w.encode()).hexdigest()
prepared = '/home/root/aura-pan-follow-20261020/prepared-midpoint-04/execute.py'
prep = '''"""Prepare frozen finite step; no hardware access or actuation."""
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r
raw=gzip.decompress(base64.b64decode(%r))
assert hashlib.sha256(raw).hexdigest()==%r
compile(raw,'execute.py','exec')
p=Path(%r);p.parent.mkdir(parents=True,exist_ok=False)
with p.open('xb') as out:out.write(raw)
print(json.dumps({'status':'PREPARED_NO_ACTUATION','sha256':%r,'bench_sha256':%r}),flush=True)
''' % ('3e1add36-b917-4289-91dc-699348528782',base64.b64encode(gzip.compress(w.encode(),mtime=0)).decode(),wsha,prepared,wsha,sha)
(J/'board_midpoint04_prepare.py').write_text(prep)
launch = (J/'board_wide_visible_launch2.py').read_text().replace('prepared-wide-visible-02','prepared-midpoint-04').replace('visible-direction-wide-01','midpoint-step-04').replace('c00674778ad1ebd4fb3c3cd4f08aeaa60bb396344eb1942eca50b7db2bf5db57',wsha).replace('wide sweep','finite step')
(J/'board_midpoint04_launch.py').write_text(launch)
export = (J/'board_wide_visible_export.py').read_text().replace('visible-direction-wide-01','midpoint-step-04').replace('wide_sweep_bench.py','midpoint_step_bench.py')
(J/'board_midpoint04_export.py').write_text(export)
for p in ['board_midpoint04_prepare.py','board_midpoint04_launch.py','board_midpoint04_export.py']:
    compile((J/p).read_bytes(),p,'exec')
print(json.dumps({'delivery':str(D),'bench_sha256':sha,'launcher_sha256':wsha,'host_checks':'PASS','no_actuation':True}))
