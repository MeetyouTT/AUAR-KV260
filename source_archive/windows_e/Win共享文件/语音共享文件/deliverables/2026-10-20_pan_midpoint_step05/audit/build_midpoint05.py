"""Prepare a further finite 1450us correction without hardware access."""
import base64,gzip,hashlib,json,subprocess,sys
from pathlib import Path
J=Path(__file__).parent
D=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_midpoint_step05')
D.mkdir(exist_ok=False)
old=(J/'board_midpoint04_execute.py').read_text()
OLD='c4b129b1555889b9678c13cfd3bea16b50e0d0c09cd8e782999e37eaae464111'
assert hashlib.sha256(old.encode()).hexdigest()==OLD
source=(D.parent/'2026-10-20_pan_midpoint_step04/midpoint_step_bench.py').read_text()
bc=[("1490 us is an initialization", "1470 us is an initialization"),
    ("'initial_pulse_us': 1490", "'initial_pulse_us': 1470"),
    ("for pulse in (1470,)","for pulse in (1450,)"),
    ('One finite 1470us step from initial 1490us','One finite 1450us step from initial 1470us'),
    ('MIDPOINT1470-2S','MIDPOINT1450-2S'),
    ("initial['ack_seq'] == 208 and initial['epoch'] == 5 and initial['width_us'] == 1490","initial['ack_seq'] == 46 and initial['epoch'] == 6 and initial['width_us'] == 1470"),
    ("initial['target_us'] == 1490","initial['target_us'] == 1470"),
    ('session, epoch = 0x20261020, 6','session, epoch = 0x20261020, 7'),
    ('io.write(0x3c, 1490)','io.write(0x3c, 1470)'),
    ("state['reference_us'] == 1490 and state['width_us'] == 1490","state['reference_us'] == 1470 and state['width_us'] == 1470")]
for a,b in bc:
    assert a in source,a
    source=source.replace(a,b)
raw=source.encode();sha=hashlib.sha256(raw).hexdigest()
(D/'midpoint_step_bench.py').write_bytes(raw)
compile(raw,'midpoint_step_bench.py','exec')
plan=json.loads(subprocess.check_output([sys.executable,'-B',str(D/'midpoint_step_bench.py')],text=True))
assert plan['stages']==[{'duration_s':2.0,'target_us':1450}] and plan['initial_pulse_us']==1470 and plan['lease_ms']==100
r=subprocess.run([sys.executable,'-B',str(D/'midpoint_step_bench.py'),'--execute'],capture_output=True,text=True);assert r.returncode==2
r=subprocess.run([sys.executable,'-B',str(D/'midpoint_step_bench.py'),'--execute','--confirmation','MIDPOINT1450-2S','--output',str(D/'not-created.json')],capture_output=True,text=True);assert r.returncode!=0 and not (D/'not-created.json').exists()
(D/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
(D/'host-checks.json').write_text(json.dumps({'syntax':True,'default_no_hardware':True,'single_1450us_2s':True,'confirmation_required':True,'non_board_rejected':True,'initial_epoch':6,'initial_ack':46,'new_epoch':7,'finally_stop_preserved':True,'source_sha256':sha},indent=2)+'\n')
(D/'field-input.json').write_text(json.dumps({'user_exact':'还是朝右','preceding_target_us':1470,'new_target_us':1450,'direction_basis':'Earlier increase worsened user-view right bias','mechanical_reference_calibrated':False},ensure_ascii=False,indent=2)+'\n')
wc=[('midpoint-step-04','midpoint-step-05'),
    ('9b12dd9c4357b011e202ec2635f81db967ca17ad59f752460c303e3edac0ec88',sha),
    ('one 1470us hold for2s from1490us','one 1450us hold for2s from1470us'),
    ('MIDPOINT1470-2S','MIDPOINT1450-2S'),
    ('看清了，现在还有点向右偏转，再转一下','还是朝右'),
    ("'previous_test_point_us':1490","'previous_test_point_us':1470"),
    ('finite 1470us correction','finite 1450us correction')]
def replace_payload(w,bench):
    marker="RAW=gzip.decompress(base64.b64decode('"
    i=w.index(marker)+len(marker);e=w.index("'))",i)
    packed=bytearray(gzip.compress(bench,mtime=0));packed[9]=255
    return w[:i]+base64.b64encode(packed).decode()+w[e:]
w=replace_payload(old,raw)
for a,b in wc:
    assert a in w,a
    w=w.replace(a,b)
wsha=hashlib.sha256(w.encode()).hexdigest()
(J/'board_midpoint05_execute.py').write_text(w)
prep='''"""Prepare finite correction from reviewed previous launcher; no hardware IO."""
import base64,gzip,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='3e1add36-b917-4289-91dc-699348528782'
old=Path('/home/root/aura-pan-follow-20261020/prepared-midpoint-04/execute.py').read_text()
assert hashlib.sha256(old.encode()).hexdigest()==%r
w=old;marker="RAW=gzip.decompress(base64.b64decode('"
i=w.index(marker)+len(marker);e=w.index("'))",i)
s=gzip.decompress(base64.b64decode(w[i:e])).decode()
for a,b in %r:
 assert a in s,a
 s=s.replace(a,b)
bench=s.encode();assert hashlib.sha256(bench).hexdigest()==%r
packed=bytearray(gzip.compress(bench,mtime=0));packed[9]=255
w=w[:i]+base64.b64encode(packed).decode()+w[e:]
for a,b in %r:
 assert a in w,a
 w=w.replace(a,b)
raw=w.encode();assert hashlib.sha256(raw).hexdigest()==%r
compile(raw,'execute.py','exec')
p=Path('/home/root/aura-pan-follow-20261020/prepared-midpoint-05/execute.py');p.parent.mkdir(parents=True,exist_ok=False)
with p.open('xb') as stream:stream.write(raw)
print(json.dumps({'status':'PREPARED_NO_ACTUATION','sha256':%r,'bench_sha256':%r}),flush=True)
'''%(OLD,bc,sha,wc,wsha,wsha,sha)
(J/'board_midpoint05_prepare.py').write_text(prep)
launch=(J/'board_midpoint04_launch.py').read_text().replace('midpoint-04','midpoint-05').replace('midpoint-step-04','midpoint-step-05').replace(OLD,wsha)
(J/'board_midpoint05_launch.py').write_text(launch)
(J/'board_midpoint05_export.py').write_text((J/'board_midpoint04_export.py').read_text().replace('midpoint-step-04','midpoint-step-05'))
for n in ['execute','prepare','launch','export']:compile((J/('board_midpoint05_'+n+'.py')).read_bytes(),n,'exec')
print(json.dumps({'bench_sha256':sha,'launcher_sha256':wsha,'host_checks':'PASS','preparation_no_actuation':True}))
