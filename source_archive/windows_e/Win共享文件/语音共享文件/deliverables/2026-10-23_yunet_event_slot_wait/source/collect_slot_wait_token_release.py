import hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/home/root/aura-slot-wait-release-20261023/4970321c51bdea6c')
d=json.loads((root/'report.json').read_text());assert d['complete'] and d['passed'] and d['accepted']
sys.path.insert(0,str(root))
from handoff import BoardOps
from live_checks import validate_state
ops=BoardOps(Path(d['handoff_root']));ops.verify();assert ops.ready('candidate')
h=ops.m.camera();validate_state(h);ops.m.single_owner(h['pid']);ops.m.ui_idle()
release=Path(d['release']);assert ops.m.runtime_for(h['pid'])==(release/'aura',release/'board_camera_ui.json')
for name,expected in d['candidate_pins'].items():assert hashlib.sha256((release/'aura'/name).read_bytes()).hexdigest()==expected
assert hashlib.sha256(ops.m.UNIT.read_bytes()).hexdigest()==d['unit_hashes']['candidate']
assert ops.service('show',d['timer']+'.timer','-p','ActiveState','--value').strip()=='inactive'
base=json.loads((Path(d['previous_release'])/'board_camera_ui.json').read_text())
cfg=json.loads((release/'board_camera_ui.json').read_text());assert cfg.pop('yunet_slot_wait_ms')==100 and cfg==base and cfg.get('yunet_dpu_recovery') is True
rollback=subprocess.run(['/usr/bin/python3','-B',d['rollback'],'--check'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
assert rollback.returncode==0,rollback.stderr.decode(errors='replace')[-200:]
rollback_check=json.loads(rollback.stdout)
stages=[]
for stage in d['stages']:
 row={key:value for key,value in stage.items() if key!='final'}
 f=stage['final'];face=f['face_targets'];diag=f['dpu_schedule']['optional_diagnostics']
 row['final']={'pid':f['pid'],'face_backend':face['backend'],'formal_identity_backend':f['identity_backend'],
  'source_age_ms':face['source_age_ms'],'freshness':face['freshness_metrics'],
  'retry':face['slot_retry'],'yunet':f['dpu_schedule']['optional']['yunet'],
  'slot_wait':f['dpu_schedule']['yunet_slot_wait'],'recovery':f['dpu_schedule']['yunet_recovery'],'primary_period_overruns':f['dpu_schedule']['primary_period_overruns'],
  'native_counters':diag['counters']['yunet'],'fault_events':diag['fault_events']}
 stages.append(row)
keys=('scope','complete','passed','accepted','phase','error','error_location','restore_error','previous_release',
 'previous_unit_sha256','release','source_manifest_sha256','candidate_pins','unit_hashes','config_sha256',
 'handoff_root','timer','rollback','rollback_sha256','camera_pid','audio_pid','xserver_pid','guard_left_armed','unit_sha256')
out={key:d.get(key) for key in keys};out['stages']=stages
out['source_files_in_package']=len(d['source_manifest'])
out['report_sha256']=hashlib.sha256((root/'report.json').read_bytes()).hexdigest()
out['current_audit']={'read_only':True,'passed':True,'camera_pid':h['pid'],'audio_pid':ops.pid('aura-avatar-ui.service'),
 'xserver_pid':ops.pid('xserver-nodm.service'),'source_hashes_verified':len(d['candidate_pins']),
 'only_camera_config_change_is_slot_wait_100ms':True,'guard_inactive':True,'single_owner_verified':True,
 'formal_identity_backend':h['identity_backend'],'face_backend':h['face_targets']['backend'],
 'yunet':h['dpu_schedule']['optional']['yunet'],'slot_wait':h['dpu_schedule']['yunet_slot_wait'],'recovery':h['dpu_schedule']['yunet_recovery'],
 'freshness_counters':h['face_targets']['freshness_metrics']['counters'],'audio_state':ops.ui().get('audio_output_state')}
out['rollback_read_only_check']=rollback_check
print(json.dumps(out))
