"""Generate one further finite 1430us correction; generation never opens hardware."""
import ast,base64,gzip,hashlib,json,subprocess,sys
from pathlib import Path
J=Path(__file__).parent
D=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_midpoint_step06')
D.mkdir(exist_ok=False)
old=(J/'board_midpoint05_execute.py').read_text()
OLD='94a843513215de9fde852f2f509e807c69c0cb23a5b8bc9895704650eed7de8a'
assert hashlib.sha256(old.encode()).hexdigest()==OLD
source=(D.parent/'2026-10-20_pan_midpoint_step05/midpoint_step_bench.py').read_text()
assert hashlib.sha256(source.encode()).hexdigest()=='d0a83fabfc1a66825fe2425ac54f292945941da934a8bd1a9b58526a58c1ddee'
bc=[('1470 us is an initialization','1450 us is an initialization'),
    ("'initial_pulse_us': 1470","'initial_pulse_us': 1450"),
    ('for pulse in (1450,)','for pulse in (1430,)'),
    ('One finite 1450us step from initial 1470us','One finite 1430us step from initial 1450us'),
    ('MIDPOINT1450-2S','MIDPOINT1430-2S'),
    ("initial['ack_seq'] == 46 and initial['epoch'] == 6 and initial['width_us'] == 1470","initial['ack_seq'] == 46 and initial['epoch'] == 7 and initial['width_us'] == 1450"),
    ("initial['reference_us'] == 1490 and initial['target_us'] == 1470","initial['reference_us'] == 1470 and initial['target_us'] == 1450"),
    ('session, epoch = 0x20261020, 7','session, epoch = 0x20261020, 8'),
    ('io.write(0x3c, 1470)','io.write(0x3c, 1450)'),
    ("state['reference_us'] == 1470 and state['width_us'] == 1470","state['reference_us'] == 1450 and state['width_us'] == 1450")]
for a,b in bc:
    assert a in source,a
    source=source.replace(a,b)
raw=source.encode();sha=hashlib.sha256(raw).hexdigest()
(D/'midpoint_step_bench.py').write_bytes(raw)
compile(raw,'midpoint_step_bench.py','exec')
plan=json.loads(subprocess.check_output([sys.executable,'-B',str(D/'midpoint_step_bench.py')],text=True))
assert plan['stages']==[{'duration_s':2.0,'target_us':1430}] and plan['initial_pulse_us']==1450 and plan['lease_ms']==100
r=subprocess.run([sys.executable,'-B',str(D/'midpoint_step_bench.py'),'--execute'],capture_output=True,text=True);assert r.returncode==2
r=subprocess.run([sys.executable,'-B',str(D/'midpoint_step_bench.py'),'--execute','--confirmation','MIDPOINT1430-2S','--output',str(D/'not-created.json')],capture_output=True,text=True);assert r.returncode!=0 and not (D/'not-created.json').exists()
(D/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
(D/'host-checks.json').write_text(json.dumps({'syntax':True,'default_no_hardware':True,'single_1430us_2s':True,'confirmation_required':True,'non_board_rejected':True,'initial_epoch':7,'initial_ack':46,'new_epoch':8,'finally_stop_preserved':True,'source_sha256':sha},indent=2)+'\n')
(D/'field-input.json').write_text(json.dumps({'user_exact':'还有点偏右','preceding_target_us':1450,'new_target_us':1430,'prior_1450us_residual_right_bias_reported':True,'mechanical_reference_calibrated':False},ensure_ascii=False,indent=2)+'\n')
wc=[('midpoint-step-05','midpoint-step-06'),
    ('d0a83fabfc1a66825fe2425ac54f292945941da934a8bd1a9b58526a58c1ddee',sha),
    ('one 1450us hold for2s from1470us','one 1430us hold for2s from1450us'),
    ('MIDPOINT1450-2S','MIDPOINT1430-2S'),
    ('还是朝右','还有点偏右'),
    ("'previous_test_point_us':1470","'previous_test_point_us':1450"),
    ('finite 1450us correction','finite 1430us correction')]
marker="RAW=gzip.decompress(base64.b64decode('"
i=old.index(marker)+len(marker);e=old.index("'))",i)
packed=bytearray(gzip.compress(raw,mtime=0));packed[9]=255
w=old[:i]+base64.b64encode(packed).decode()+old[e:]
for a,b in wc:
    assert a in w,a
    w=w.replace(a,b)
wsha=hashlib.sha256(w.encode()).hexdigest()
(J/'board_midpoint06_execute.py').write_text(w)
tree=ast.parse((J/'build_midpoint05.py').read_text())
template=next(n.value.left.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prep' for t in n.targets))
template=template.replace('prepared-midpoint-05','prepared-midpoint-06').replace('prepared-midpoint-04','prepared-midpoint-05')
(J/'board_midpoint06_prepare.py').write_text(template%(OLD,bc,sha,wc,wsha,wsha,sha))
launch=(J/'board_midpoint05_launch.py').read_text().replace('prepared-midpoint-05','prepared-midpoint-06').replace('midpoint-step-05','midpoint-step-06').replace(OLD,wsha)
(J/'board_midpoint06_launch.py').write_text(launch)
(J/'board_midpoint06_export.py').write_text((J/'board_midpoint05_export.py').read_text().replace('midpoint-step-05','midpoint-step-06'))
for n in ['execute','prepare','launch','export']:compile((J/('board_midpoint06_'+n+'.py')).read_bytes(),n,'exec')
print(json.dumps({'bench_sha256':sha,'launcher_sha256':wsha,'host_checks':'PASS','preparation_no_actuation':True}))
