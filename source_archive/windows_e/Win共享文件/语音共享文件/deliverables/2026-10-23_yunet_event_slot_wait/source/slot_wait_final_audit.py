import hashlib,json,os,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/home/root/aura-slot-wait-release-20261023/9d649227aade936c')
d=json.loads((root/'report.json').read_text());assert d['complete'] and d['passed'] and d['accepted']
sys.path.insert(0,str(root))
from handoff import BoardOps
from live_checks import validate_state
ops=BoardOps(Path(d['handoff_root']));ops.verify();h=ops.m.camera();validate_state(h)
assert h['pid']==d['camera_pid'];ops.m.single_owner(h['pid']);ops.m.ui_idle()
release=Path(d['release']);assert ops.m.runtime_for(h['pid'])==(release/'aura',release/'board_camera_ui.json')
unit=ops.m.UNIT.read_bytes();assert hashlib.sha256(unit).hexdigest()==d['unit_hashes']['candidate']
assert b'injection_entry' not in unit and str(release/'runtime_entry.py').encode() in unit
states={name:ops.service('show',name,'-p','ActiveState','--value').strip() for name in (
 d['timer']+'.timer','aura-slot-wait-release-9d649227aade936c.service')}
assert set(states.values())=={'inactive'}
face=h['face_targets'];fresh=face['freshness_metrics'];schedule=h['dpu_schedule']
assert schedule['yunet_recovery']['enabled'] and schedule['yunet_recovery']['phase']=='RUNNING'
assert fresh['counters']['observed_gap_intervals']==0 and fresh['observer_failures']==0
counts=schedule['optional_diagnostics']['counters']['yunet']
assert counts['native_failed']==face['slot_retry']['withdrawn_after_slot']
cu=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto')
a=(cu/'stat').read_text().split()[0];time.sleep(.35);b=(cu/'stat').read_text().split()[0]
after=ops.m.camera();assert a==b and after['pid']==h['pid'] and after['detected_frames']>h['detected_frames']
print(json.dumps({'passed':True,'read_only':True,'boot':ops.meta['boot'],'release':str(release),
 'unit_sha256':d['unit_hashes']['candidate'],'camera_pid':h['pid'],'audio_pid':ops.pid('aura-avatar-ui.service'),
 'xserver_pid':ops.pid('xserver-nodm.service'),'audio_state':ops.ui().get('audio_output_state'),
 'allowed_cpus':sorted(os.sched_getaffinity(h['pid'])),'current_face_backend':face['backend'],
 'formal_identity_backend':h['identity_backend'],'yunet':schedule['optional']['yunet'],
 'slot_wait':schedule['yunet_slot_wait'],'recovery':schedule['yunet_recovery'],'source_age_ms':face['source_age_ms'],
 'gap_intervals':fresh['counters']['observed_gap_intervals'],'real_native_failures':0,
 'injection_disabled_in_active_unit':True,'cu_statistics_disabled':True,'inactive_auxiliary_units':states,
 'protected_sources_config_models_and_gui_verified':True,'primary_period_overruns':schedule['primary_period_overruns']}))
