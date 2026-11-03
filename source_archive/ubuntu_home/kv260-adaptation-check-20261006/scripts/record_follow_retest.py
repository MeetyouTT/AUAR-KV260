"""Publish local evidence-backed status, preserving the previous host snapshots."""
import datetime,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VS=Path('/home/ghmd/kv260-visual-servo-20261007')
VISION=Path('/home/ghmd/kv260-realtime-vision-20261007')
def read_evidence(name):
 p=ROOT/'evidence'/name
 meta=json.loads((p/'status.json').read_text())
 data=(p/'result.txt').read_bytes()
 assert meta['rc']==0 and meta['console_echo_restored']
 assert hashlib.sha256(data).hexdigest()==meta['output_sha256']
 return meta,json.loads(data)
def atomic(path,data):
 tmp=path.with_name(path.name+'.follow-retest.tmp')
 assert not tmp.exists()
 tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 tmp.replace(path)

tests=[]
for name in ('20261009T031438.404568Z-newboot_visual_direction_start',
             '20261009T031627.087994Z-newboot_visual_direction_start',
             '20261009T031804.999593Z-newboot_visual_direction_start'):
 meta,result=read_evidence(name)
 assert result['stop_verified'] and result['commands']==result['attempts']
 tests.append({'execution':meta,'result':result})
final_meta,final=read_evidence('20261009T031903.092907Z-newboot_vsrv_final')
monitor_meta,monitor=read_evidence('20261009T031722.608555Z-newboot_stop_monitor')
assert final['passed'] and final['stop_status']['flags']==0 and final['stop_status']['lease_left_ms']==0
assert monitor['passed'] and monitor['all_disabled'] and monitor['ack_seq_unchanged'] and monitor['visible_samples']==47
backup=Path(final_meta['evidence'])
for path in (VISION/'CURRENT_RUNTIME.json',VS/'LATEST_DIRECTION_RETEST.json'):
 target=backup/('previous-host-'+path.parent.name+'-'+path.name)
 with target.open('xb') as f:f.write(path.read_bytes())
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
record={'scope':'NEWBOOT_FINITE_VISUAL_FOLLOW_RETEST','recorded_utc':now,
 'boot_id':final['boot_id'],'camera_epoch':final['after']['epoch'],
 'bidirectional_command_coverage_passed':True,'continuous_following_passed':False,
 'lost_target_stop_passed':True,'visible_target_does_not_rearm_passed':True,
 'physical_axis_following_confirmed':False,'mechanical_feedback':'AWAITING_USER',
 'physical_reference_valid':False,'speed_tuning_performed':False,
 'tests':tests,'post_loss_monitor':{'execution':monitor_meta,'result':monitor},
 'final_verification':{'execution':final_meta,'result':final},
 'host_trace_verification':str(ROOT/'evidence/20261009T031744.253555Z-newboot_direction_evidence/HOST_TRACE_VERIFICATION.json'),
 'report':str(VS/'FOLLOW_RETEST_REPORT.md'),'previous_host_state_directory':str(backup)}
atomic(VS/'CURRENT_FOLLOW_RETEST.json',record)
atomic(VS/'LATEST_DIRECTION_RETEST.json',record)
runtime={'active_mode':'VIDEO_PREVIEW_WITH_IDLE_VSRV','active_pid':final['preview_pid'],
 'boot_id':final['boot_id'],'release':final['release'],'run_root':final['run_root'],
 'physical_actuation_enabled':False,'physical_reference_valid':False,
 'physical_axis_following_confirmed':False,'motion_simulation_enabled':False,
 'reference_x_px':320,'updated_utc':now,'actual_active_application':final['app'][0],
 'source_platform_not_loaded':False,'visual_following_started':False,
 'finite_visual_bench_performed':True,'continuous_following_passed':False,
 'after':final['after'],'mirror_horizontal':True,
 'coordinate_convention':'MIRRORED_SELF_VIEW','camera_epoch':final['after']['epoch'],
 'control_observation_path':final['after']['control_observation_path'],
 'detector_input_size':[192,192],'detector_cpu_threads':2,
 'latest_stop_verification':final_meta,'latest_board_verification':final_meta,
 'stop_status':final['stop_status'],'follow_retest':str(VS/'CURRENT_FOLLOW_RETEST.json'),
 'previous_host_state_directory':str(backup),
 'screen_verification':{'evidence':str(ROOT/'evidence/20261009T031538.075014Z-realtime_verify'),
 'kind':'ACTUAL_X11_FRAMEBUFFER_INSPECTED','physical_screen_user_confirmed_this_boot':False},
 'mechanical_feedback':'AWAITING_USER'}
atomic(VISION/'CURRENT_RUNTIME.json',runtime)
for path in (VS/'CURRENT_FOLLOW_RETEST.json',VS/'LATEST_DIRECTION_RETEST.json',VISION/'CURRENT_RUNTIME.json'):
 loaded=json.loads(path.read_text());assert loaded['boot_id']==final['boot_id']
assert json.loads((VISION/'CURRENT_RUNTIME.json').read_text())['stop_status']['flags']==0
print(json.dumps({'status_updated':True,'boot_id':final['boot_id'],
 'accepted_commands_by_test':[t['result']['commands'] for t in tests],
 'all_tests_stopped':True,'continuous_following_passed':False,
 'previous_host_state_directory':str(backup)},ensure_ascii=False))
