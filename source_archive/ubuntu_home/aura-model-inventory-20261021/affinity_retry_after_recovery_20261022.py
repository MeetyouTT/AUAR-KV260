import hashlib,json,subprocess,urllib.request
from pathlib import Path
base=Path('/home/root/aura-dpu-vision-20261021')
records=sorted((base/'affinity-live').glob('*/deployment-result.json'),key=lambda p:p.stat().st_mtime);assert len(records)==1
r=json.loads(records[-1].read_text());assert r['complete'] and r['rollback_verified'] and not r['passed']
assert r['error']=='AssertionError: USB warning during copy-only candidate'
assert r['affinity_shutdown']['clean_selected_thread_restoration_and_close']
recovery=json.loads(Path('/home/root/aura-audio-recovery-20261021/dda47b13d83c2110/result.json').read_text())
assert recovery['complete'] and recovery['warning_recovered_in_short_sample']
assert recovery['after']['journal_query_complete'] and recovery['after']['xhci_warning_count']==0
assert recovery['guard_timer_active']=='inactive'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
assert h['pid']==recovery['after']['camera']['pid']
assert h['identity']['face_targets']['backend']=='DPU_YUNET_INT8'
assert not h['dpu_schedule']['optional']['yunet']['disabled'] and not h['dpu_schedule']['optional']['yunet']['overruns']
unit=Path('/etc/systemd/system/aura-camera-ui.service');assert hashlib.sha256(unit.read_bytes()).hexdigest()=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
p=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/c98cdd3015a36636/source.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c98cdd3015a366369671b9cfa018d845dccf2a02de6bda794b7d3bb21500d009'
launch=base/'affinity-launches/c98cdd3015a36636/launch-result.json';archive=launch.with_name('launch-result-attempt1.json')
assert not archive.exists();archive.write_bytes(launch.read_bytes())
out=subprocess.check_output(['systemd-run','--unit=aura-affinity-live-c98cdd3015a36636-retry1','--property=RuntimeMaxSec=300','--setenv=AURA_RUN_AFFINITY_LIVE=1','/usr/bin/python3','-B',str(p)],stderr=subprocess.STDOUT,timeout=8).decode()
print(json.dumps({'started':True,'single_retry_after_original_audio_recovery':True,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'old_failed_result_preserved':str(records[-1]),'unit':'aura-affinity-live-c98cdd3015a36636-retry1','original_camera_before_retry':h['pid']}))
