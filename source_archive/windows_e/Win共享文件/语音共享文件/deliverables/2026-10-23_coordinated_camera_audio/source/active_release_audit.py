import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/home/root/aura-release-acceptance-20261023/63d4244d6add3ad0')
d=json.loads((root/'report.json').read_text());assert d['complete'] and d['passed'] and d['accepted']
p=root/'release_control.py';assert hashlib.sha256(p.read_bytes()).hexdigest()=='0b6f1e2d559af957929719b1c45673f9e1dc1da98cc072e09a62b8b7aba389f6'
spec=importlib.util.spec_from_file_location('_release_audit_definitions',p);r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
release=Path(d['release']);assert r.tree_manifest(release/'aura')==d['source_manifest']
assert r.sha(release/'runtime_entry.py')==d['runtime_entry_sha256']
co=Path(d['handoff_root']);p=co/'handoff.py'
assert r.sha(p)=='12a6a4ea98f33926465d3e0cb6ae046cf3a82f29fbaa8021d4beaad249f9c734'
spec=importlib.util.spec_from_file_location('_active_release_handoff',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ops=m.BoardOps(co);ops.verify();assert ops.ready('candidate')
assert r.sha(ops.m.UNIT)==d['unit_sha256']
assert r.sha(release/'camera.original.service')==ops.meta['unit_hashes']['original']
assert r.sha(release/'gil_camera_launcher.py')=='0cec741d143a012b5d5aa5808f404e7b818510d2773f3b122dd1fb639222ae02'
assert r.sha(release/'restore_original.py')=='e512d80518dda62a0df06af1f79429f814cc52aa40e0c9c2686de89bb4036906'
assert ops.service('show',d['timer']+'.timer','-p','ActiveState','--value').strip()=='inactive'
h=ops.m.camera();ops.m.healthy(h);ops.m.single_owner(h['pid']);ops.m.ui_idle()
assert ops.m.runtime_for(h['pid'])==(release/'aura',Path(ops.meta['config']))
assert h['face_targets']['slot_retry']['recovery_interval_ms']==50
assert h['face_targets']['freshness_metrics']['counters']['observed_gap_intervals']==0
assert h['face_targets']['freshness_metrics']['observer_failures']==0
cu=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto')
assert (cu/'base_paddr').read_text().strip()=='0xa0010000'
first=(cu/'stat').read_text().split()[0];time.sleep(.35);last=(cu/'stat').read_text().split()[0]
after=ops.m.camera();assert after['pid']==h['pid'] and after['detected_frames']>h['detected_frames']
assert first==last,'CU statistics collector still running'
out={'read_only':True,'passed':True,'release':str(release),'unit_sha256':d['unit_sha256'],
 'source_files_verified':len(d['source_manifest']),'runtime_entry_verified':True,'rollback_entry_verified':True,
 'original_backup_verified':True,'original_models_identity_config_and_gui_files_verified':True,
 'guard_inactive':True,'cu_statistics_disabled':True,'camera_pid':h['pid'],'audio_pid':ops.pid('aura-avatar-ui.service'),
 'xserver_pid':ops.pid('xserver-nodm.service'),'allowed_cpus':sorted(os.sched_getaffinity(h['pid'])),
 'face_backend':h['face_targets']['backend'],'formal_identity_backend':h['identity_backend'],
 'face_source_age_ms':h['face_targets']['source_age_ms'],'retry':h['face_targets']['slot_retry'],
 'yunet':h['dpu_schedule']['optional']['yunet'],'gaps':h['face_targets']['freshness_metrics']['counters']['observed_gap_intervals'],
 'audio_state':ops.ui().get('audio_output_state')}
start_ticks=int((Path('/proc')/str(h['pid'])/'stat').read_text().split(') ')[1].split()[19])
out['camera_process_age_s']=float(Path('/proc/uptime').read_text().split()[0])-start_ticks/os.sysconf('SC_CLK_TCK')
out['native_counters']=h['dpu_schedule'].get('optional_diagnostics',{}).get('counters',{}).get('yunet')
out['freshness_counters']=h['face_targets']['freshness_metrics']['counters']
assert out['native_counters']['native_failed']==out['retry']['withdrawn_after_slot']
out['real_native_failures']=out['native_counters']['native_failed']-out['retry']['withdrawn_after_slot']
out['primary_period_overruns']=h['dpu_schedule']['primary_period_overruns']
print(json.dumps(out))
