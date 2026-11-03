import hashlib,json,sqlite3,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/home/root/aura-sface-formal-20261023/30072c67abc3f06b')
d=json.loads((root/'report.json').read_text());assert d['complete'] and d['passed'] and d['accepted']
sys.path.insert(0,str(root))
from handoff import BoardOps
from live_checks import validate_state
ops=BoardOps(Path(d['handoff_root']));ops.verify();assert ops.ready('candidate')
h=ops.m.camera();validate_state(h);ops.m.single_owner(h['pid'])
assert h['pid']==d['camera_pid'] and h['identity_backend']=='DPU_SFACE_INT8' and h['identity_ready']
config=json.loads(Path(d['identity_config']).read_text());old=json.loads(Path(config['feature_backend']['fallback_config']).read_text())
assert hashlib.sha256(Path(old['database']).expanduser().read_bytes()).hexdigest()==d['old_database_sha256']
con=sqlite3.connect(Path(d['new_database']).as_uri()+'?mode=ro',uri=True)
try:
 binding=con.execute('SELECT model_id,dimension FROM identity_model_binding').fetchall()
 assert binding==[('sface-int8-12b2ff5c7de15713',128)]
 counts={name:con.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ('identities','templates')}
finally:con.close()
assert counts=={'identities':1,'templates':1}
states={name:ops.service('show',name,'-p','ActiveState','--value').strip()
 for name in (d['timer']+'.timer','aura-sface-formal-30072c67abc3f06b.service')}
assert all(value=='inactive' for value in states.values())
rollback=subprocess.run(['/usr/bin/python3','-B',d['rollback'],'--check'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
assert rollback.returncode==0,rollback.stderr.decode(errors='replace')[-200:]
keys=('scope','complete','passed','accepted','phase','error','restore_error','previous_release','previous_unit_sha256',
 'release','source_manifest_sha256','candidate_pins','unit_sha256','unit_hashes','config_sha256','identity_config',
 'identity_config_sha256','new_database','old_database_sha256','handoff_root','timer','rollback','rollback_sha256',
 'camera_pid','audio_pid','xserver_pid','guard_left_armed','migration','stages')
out={key:d.get(key) for key in keys};out['source_files_in_package']=len(d['source_manifest'])
out['report_sha256']=hashlib.sha256((root/'report.json').read_bytes()).hexdigest()
out['current_audit']={'passed':True,'read_only':True,'camera_pid':h['pid'],'audio_pid':ops.pid('aura-avatar-ui.service'),
 'xserver_pid':ops.pid('xserver-nodm.service'),'formal_identity_backend':h['identity_backend'],
 'face_backend':h['face_targets']['backend'],'feature_inference':h['feature_inference'],
 'optional':h['dpu_schedule']['optional'],'sface_slot_wait':h['dpu_schedule']['sface_slot_wait'],
 'yunet_slot_wait':h['dpu_schedule']['yunet_slot_wait'],
 'gap_intervals':h['face_targets']['freshness_metrics']['counters']['observed_gap_intervals'],
 'independent_admission':h['face_targets']['slot_retry'].get('independent_admission'),
 'old_database_unchanged':True,'new_database_binding':binding,'new_database_counts':counts,
 'source_model_config_gui_and_owner_verified':True,'inactive_auxiliary_units':states,
 'audio_state':ops.ui().get('audio_output_state'),'field_unknown_person_accuracy_validated':False,'match_diagnostics':h.get('match_diagnostics')}
out['rollback_read_only_check']=json.loads(rollback.stdout)
print(json.dumps(out))
