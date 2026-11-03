"""Seal subtitle publication/live metadata and current continuation entries locally."""
from pathlib import Path
import argparse,hashlib,json,time
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parents[1];TASK=HERE.parents[1];PROJECT=TASK.parents[1]
OWNER=PROJECT/'deliverables/2026-10-30_board_owner';CANON=OWNER/'integration/production_business_acceptance'
def read(p):return json.loads(p.read_bytes())
def encoded(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def put(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(data)
def replace(p,data):
 tmp=p.with_name(p.name+'.subtitle-record-tmp');put(tmp,data);tmp.replace(p)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--feedback',choices=('pending','both_visible','failed'),default='pending')
 parser.add_argument('--trial-directory',type=Path,required=True);a=parser.parse_args()
 pkg=HERE/'package/subtitle_receipt';spec=read(pkg/'candidate_spec.json')
 ready_path=HERE/'evidence/subtitle_receipt_forward_ready_1793536079425576200.json';ready=read(ready_path)['result']
 trial=a.trial_directory.resolve();assert trial.parent==(HERE/'evidence').resolve()
 result=read(trial/'RESULT.json')
 assert result['exit_code']==0
 terminal=next(r for r in result['terminal_events'] if r.get('status')=='ONE_NEW_TURN_COMPLETE')
 final=read(trial/'FINAL_PAUSED.json');proof=final['proof'];state=proof['state']
 assert state['listening_state']=='PAUSED' and state['microphone_open'] is False and state['playing'] is False
 assert state['following'] is False and state['readback']['flags']==0 and state['readback']['lease_left_ms']==0
 assert proof['startup_sha256']==ready['startup_sha256']==spec['startup_sha256']
 assert proof['manifest_sha256']==ready['source_manifest_sha256']==spec['source_manifest_sha256']
 rows=[json.loads(s) for s in (trial/'metadata.jsonl').read_text('utf-8').splitlines() if s.strip()]
 samples=[r for r in rows if r.get('kind')=='sample'];target=terminal['request_token']
 target_samples=[r for r in samples if r.get('request_token')==target or r.get('ack_request_token')==target]
 observed=[r.get('caption_metadata',{}) for r in target_samples]
 api_flags=[r.get('caption_metadata',{}) for r in samples]
 completed=next(r for r in reversed(target_samples) if r.get('ack_committed') and r.get('ack_request_token')==target and r.get('latency',{}).get('complete'))
 report=dict(schema='aura-subtitle-actual-release-and-live-1',status='SUBTITLE_RELEASED_LIVE_COMPLETED_FINAL_PAUSED',
             recorded_utc=datetime.now(timezone.utc).isoformat(),ready=ref(ready_path),current_spec=ref(pkg/'candidate_spec.json'),
             current=proof,public_arm=ref(HERE/'evidence/subtitle_public_arm_r2_1793535861024814000.json'),
             first_failed_arm_preserved=ref(HERE/'evidence/subtitle_public_arm_1793535538927862300.json'),
             first_failed_live_window=dict(result=ref(HERE/'evidence/live_trial_1793536079510966000/RESULT.json'),
               status='WINDOW_TIMEOUT_WITH_INFLIGHT_GENERATION_CANCELLED_BY_OLD_CLEANUP',
               first_token_entry_rejected=True,late_second_request_was_generating_at_deadline=True,
               user_saw_recognition_subtitle=True,user_received_response_audio=False,
               audio_failure_not_attributed_solely_to_late_request_cancellation=True),
             publisher_bundle=ref(pkg/'BUNDLE_MANIFEST.json'),rollback_plan=ref(pkg/'rollback_plan.json'),
             only_one_source_changed=True,unchanged_components=379,original_controller_files=25,
             camera_and_current_pan_configurations_and_wide_preserved=True,
             caption_trial=dict(directory=str(trial),result=ref(trial/'RESULT.json'),metadata=ref(trial/'metadata.jsonl'),final_paused=ref(trial/'FINAL_PAUSED.json'),
                                request_token=target,matching_complete_ack=True,latency=completed.get('latency'),prepare_latency=completed.get('prepare_latency'),
                                audio_output=completed.get('audio_output'),runtime_faults=completed.get('runtime_faults'),
                                showing_true_observed=any(v.get('showing') is True for v in observed),
                                showing_false_observed=any(v.get('showing') is False for v in observed),
                                api_reply_empty_all_observed=bool(api_flags) and all(v.get('api_reply_empty') is True for v in api_flags),
                                api_transcript_empty_all_observed=bool(api_flags) and all(v.get('api_transcript_empty') is True for v in api_flags),
                                unknown_fields_present=any(v.get('showing') is None or v.get('api_reply_empty') is None or v.get('api_transcript_empty') is None for v in api_flags),
                                user_feedback_receipt=ref(trial/'USER_FEEDBACK.json') if (trial/'USER_FEEDBACK.json').exists() else None,
                                user_feedback=a.feedback),
             caption_text_or_screenshots_exported=False,performance_resampled_after_subtitle_change=False,
             user_report_multi_turn_memory_ok=True,over_five_minute_summary_retrieval_verified=False,
             caveats=['Caption lifecycle showing is a software slot flag; actual two-column display is confirmed only by user feedback during recognition/playback.',
                      'Normal pause may clear captions; no requirement that paused captions remain visible.',
                      'Previous performance comparison belongs to startup71c28; this subtitle release keeps projection hot paths but was not performance-resampled.',
                      'Saved PIDs, state and pulse are observation-specific; fresh proof is required before later operations.'])
 report_path=HERE/'CURRENT_SUBTITLE_RELEASE.json'
 if report_path.exists():put(HERE/'subtitle_release_history'/('before_'+str(time.time_ns())+'.json'),report_path.read_bytes())
 replace(report_path,encoded(report))
 targets=[CANON/'spec.json',CANON/'actual_ready.json',OWNER/'coordination/runtime_windows.json',HERE/'LATEST.json',TASK/'LATEST_REVIEW.json',PROJECT/'AGENTS.md',PROJECT/'README.md',TASK/'README.md']
 archive_root=HERE/'docs_state_subtitle'/('t'+str(time.time_ns()))
 archives=[]
 for p in targets:
  dest=archive_root/'before'/p.relative_to(PROJECT);put(dest,p.read_bytes());archives.append(dict(original=ref(p),archive=ref(dest)))
 old=(CANON/'spec.json').read_bytes();assert old in ((pkg/'base_spec.json').read_bytes(),(pkg/'candidate_spec.json').read_bytes())
 replace(CANON/'spec.json',(pkg/'candidate_spec.json').read_bytes());replace(CANON/'actual_ready.json',encoded(ready))
 current_ref=ref(report_path);coord=read(OWNER/'coordination/runtime_windows.json')
 coord['continuation_history'].append(dict(original_bytes_archive=archives[2]['archive'],previous_current_observation=coord.get('current_observation'),reason='Actual subtitle one-source release and final paused live receipt'))
 coord.update(startup_sha256=spec['startup_sha256'],source_manifest_sha256=spec['source_manifest_sha256'],configuration_sha256=spec['configuration_sha256'],
              supervisor_pid=proof['owners']['supervisor']['pid'],gtk_pid=proof['owners']['gtk']['pid'],camera_pid=proof['owners']['camera']['pid'],
              camera_birth_ticks=proof['owners']['camera']['birth_ticks'],status=report['status'],current_observation=current_ref,
              latest_subtitle_release=current_ref,last_device_state=state,last_device_observed_mono=proof['observed_mono'],
              updated_utc=report['recorded_utc'],current_live_state_claimed=False)
 coord['operator_instruction']=dict(spec=ref(CANON/'spec.json'),publisher=str(HERE/'tools/publish_subtitle_receipt.py'),
  sole_publisher_thread='01a195e4-58a7-72d3-b141-d5d373579f7f',publication_complete=True,publication_expected_listening_enabled=False,
  usage='Latest committed source is de04; exact rollback restores984d/71c28. Any later operation must use fresh current owner/source/state proof.')
 coord['verified_listening']=dict(enabled=False,state='PAUSED',microphone_open=False,startup_sha256=spec['startup_sha256'],source=ref(trial/'FINAL_PAUSED.json'))
 coord['device_operation_owner']['state']='IDLE_FINAL_PAUSED_SUBTITLE_RELEASE_COMPLETE'
 coord['retained_mechanical_boundary'].update(pan_state='READY',pulse_us=state['readback']['width_us'],tracking_enabled=False,last_actual_state_reference=ref(trial/'FINAL_PAUSED.json'))
 coord['current_revision_acceptance']['subtitle_two_columns_user_confirmed']=a.feedback=='both_visible'
 coord['current_revision_acceptance']['subtitle_user_feedback_status']=a.feedback
 coord['current_revision_acceptance']['user_report_multi_turn_memory_ok']=True
 for key in ('production_UI_switch','production_business_cutover'):
  coord[key].update(startup_sha256=spec['startup_sha256'],source_manifest_sha256=spec['source_manifest_sha256'],configuration_sha256=spec['configuration_sha256'],
                    current_observation=current_ref,state=report['status'],updated_utc=report['recorded_utc'])
 replace(OWNER/'coordination/runtime_windows.json',encoded(coord))
 latest=read(HERE/'LATEST.json');latest.update(status=report['status'],subtitle_release=current_ref,latest_actual_state=ref(trial/'FINAL_PAUSED.json'),subtitle_user_feedback=a.feedback);replace(HERE/'LATEST.json',encoded(latest))
 visual=read(TASK/'LATEST_REVIEW.json');visual['latest_subtitle_release']=current_ref;visual['following']=False;visual['output_closed']=True;replace(TASK/'LATEST_REVIEW.json',encoded(visual))
 note=f'''<!-- subtitle-current-20261101 -->
字幕一源修复已发布并完成一轮真人完整播放回执，最终PAUSED/mic=false/无播放、main页面，原跟随关闭、转轴输出关闭。字幕两栏用户反馈状态：{a.feedback}。

当前startup `{spec['startup_sha256']}`，manifest `{spec['source_manifest_sha256']}`，spec `{ref(pkg/'candidate_spec.json')['sha256']}`，源de04；380项闭包实读匹配，唯一改动production_memory_presentation，另379项/原相机430894/原25控制器/当前四配置/wide固件保持。supervisor{proof['owners']['supervisor']['pid']}、GTK{proof['owners']['gtk']['pid']}；完整birth/命令指纹见[最新实板状态]({str(report_path).replace(chr(92),'/')})。

原71c28的UI性能对照与全部失败/重做证据保留；字幕新版未重复性能采样。用户已报告多轮记忆正常，非超过五分钟摘要检索验收。后续操作先新鲜核对，不沿用下方旧startup/PID。
<!-- /subtitle-current-20261101 -->

'''
 for p in (PROJECT/'AGENTS.md',PROJECT/'README.md',TASK/'README.md'):
  body=p.read_text('utf-8-sig');start='<!-- subtitle-current-20261101 -->';end='<!-- /subtitle-current-20261101 -->'
  if start in body:
   first=body.index(start);last=body.index(end,first)+len(end);body=body[:first]+body[last:].lstrip('\r\n')
  replace(p,note.encode()+body.encode())
 put(archive_root/'SEAL.json',encoded(dict(schema='aura-local-subtitle-current-state-seal-1',before=archives,after=[ref(p) for p in targets],current_release=current_ref,device_access=False)))
 print(json.dumps(dict(status=report['status'],current_release=current_ref,caption=report['caption_trial'],device_access=False),ensure_ascii=False))

if __name__=='__main__':main()
