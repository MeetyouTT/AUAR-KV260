import hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
p=Path('/home/root/aura-post-power-20261022/helpers/10261c1b5b2b7458/source.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='10261c1b5b2b745877121c90d940be80e67f91ae57a524ed2040a1f52af4f65c'
spec=importlib.util.spec_from_file_location('_read_only_trial_definitions',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
h=m.camera();m.healthy(h);m.single_owner(h['pid']);ui=m.ui_idle()
assert m.digest(m.UNIT)==m.UNIT_SHA
assert m.runtime_for(h['pid'])==(m.BASE/'aura',m.BASE/'board_camera_ui.json')
for name,digest in m.BASELINE.items():assert m.digest(m.BASE/'aura'/name)==digest
identity=json.loads((m.BASE/'board_identity.json').read_text())
assert identity['face_backend']['kind']=='dpu_yunet'
assert identity['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
for key in ('model','manifest'):assert m.digest(identity['face_backend'][key])==identity['face_backend'][key+'_sha256']
assert h.get('shadow') is None and h.get('pipeline_metrics') is None
assert h['face_targets'].get('slot_retry') is None and h['face_targets'].get('freshness_metrics') is None
timers={}
for p in (Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')).glob('recovery50-*/deployment-result.json'):
    d=json.loads(p.read_text());assert d['complete'] and d['rollback_verified'] and not d['rollback_timer_left_armed']
    name=d['timer']+'.timer';state=m.service('show',name,'-p','ActiveState','--value').strip()
    assert state=='inactive';timers[name]=state
print(json.dumps({'read_only':True,'passed':True,'camera_pid':h['pid'],'backend':h['face_targets']['backend'],
 'original_unit_sha256':m.UNIT_SHA,'original_source_hashes_verified':len(m.BASELINE),
 'original_model_and_manifest_verified':True,'windows_identity_preserved':True,
 'experiment_metrics_retry_shadow_disabled':True,'timers':timers,'ui':ui}))
