"""Record the user's narrow confirmation and a read-only overall project snapshot."""
import datetime,json
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];root=P.parent
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
feedback={'recorded_utc':stamp,'user_statement':'没问题额，现在整体确认下目前情况',
 'confirmed_scope':'User reports the recognition-to-listening issue is now OK after r6.',
 'verbatim_test_phrase_supplied':False,'whole_project_acceptance':False,
 'notes':'Does not imply acceptance of latency, all wake words, memory cross-day behavior, voiceprint calibration or whole-device stability.'}
path=H/'human_feedback.json';assert not path.exists()
path.write_text(json.dumps(feedback,ensure_ascii=False,indent=2),encoding='utf-8')
progress=json.loads((H/'PROGRESS.json').read_text(encoding='utf-8'))
progress.update(human_retest_pending=False,human_retest_result='USER_CONFIRMED_OK_FOR_REPORTED_ISSUE',
 human_feedback='human_feedback.json',updated_utc=stamp,listening_remains_off=False,
 scope='Confirmed HTTP503 cancellation handoff path and warm TTS retention; user now confirms reported issue is OK.')
progress['current_user_operated_state']={'listening_enabled':True,'microphone_open':True,'state':'WAITING_WAKE','agent_enabled_microphone':False}
(H/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
report={'checked_utc':stamp,'audit_kind':'Read-only service and UI health plus prior scoped acceptance receipts',
 'human_feedback':feedback,'whole_project_complete':False,
 'windows':{'voice_revision':'voice-turn-handoff-20261029-r6',
  'source_fingerprint':'b991e72050af52d86e947594303fc30e5a5675aa2a95140ff7910ba8a0d582a8',
  'service_ports_ready':[8791,8792,8795,8796,8810,8812,11435],
  'tts_ready':True,'tts_quarantined':False,'dialogue_model_resident':True,
  'dialogue_model':'aura-qwen3.8-27b-abliterated:iq4_xs','memory_conversations':144,'memory_turns':276,
  'memory_background_running':True,'memory_background_error':'','memory_background_mode':'source_excerpts',
  'visual_background_running':True,'speaker_ready':True,'speaker_calibrated':False,'automatic_profile_unlock':False},
 'board':{'listening_enabled':True,'microphone_open':True,'handsfree_state':'WAITING_WAKE',
  'last_playback_ack_committed':True,'phase':'IDLE','audio_output_state':'IDLE_READY',
  'portrait_target_fps':16,'portrait_sample_fps_min':15.481276705451549,'portrait_sample_fps_max':15.608453920456522,
  'portrait_samples':8,'portrait_sample_period_s':.5,'portrait_modes_in_sample':['remote'],
  'portrait_transport_failures':0,'portrait_remote_frames_accepted_increased':True,
  'observer_enabled':True,'observer_interval_seconds':15,'observer_error':'',
  'camera_capture_age_ms':37,'camera_capture_hz':14.89,'detection_hz':9.94,
  'camera_error':'','detector_error':'','preview_error':'','face_ready':True,'face_backend':'DPU_SFACE_INT8',
  'face_detector_backend':'DPU_YUNET_INT8','face_processed':7412,
  'mechanical_state':'READY','pulse_us':1604,'automatic_following':False,'mechanical_reference_calibrated':False},
 'implemented':['vision_independent_voice_dialogue','ASR_27B_OmniVoice','streaming_playback_and_cancellation',
  'explicit_authorized_fact_memory','natural_current_fact_queries','correction_history_1_to_32',
  'confirmed_transcript_deletion_and_source_invalidation','conversation_visual_timeline','background_excerpt_summaries',
  'visual_question_answering','periodic_visual_observation','DPU_face_enrollment_and_recognition',
  'speaker_enrollment_and_matching_flow','windows_portrait_composition_and_local_fallback','board_mechanical_control'],
 'verification':{'latest_windows_regressions':285,'includes_prior_267':True,'tests_do_not_add_across_stages':True,
  'actual_board_handoff_pairs':3,'actual_wake_protocol_checks':2,'user_confirms_reported_issue':True},
 'open':['general_dialogue_latency_tail','stable_speaking_frame_intervals','short_interjection_and_noise_wake_accuracy',
  'fact_effective_time_and_richer_history','cross_day_human_memory_acceptance','audiovisual_speaker_attribution',
  'field_voiceprint_calibration','full_mechanical_calibration_and_separate_motion_acceptance','long_duration_whole_device_acceptance'],
 'ownership':{'Windows':['audio_frontend','ASR','27B_dialogue','TTS','semantic_VLM','memory_and_permissions','ECAPA','portrait_composition'],
  'board':['capture','playback_and_audio_clock','touch_UI_and_display','DPU_detection_and_face','mechanical_control']},
 'migration_deferred':True,'llm_storage':'D:/AIModels','mutations_during_audit':{'application_code':False,'restart':False,'model_load_or_unload':False,
 'microphone_or_motion_command':False,'raw_identity_or_image_read':False}}
out=H/'overall_status_after_user_confirm.json';assert not out.exists()
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
p=P/'AGENTS.md';data=p.read_bytes();marker=b'<!-- /voice-handoff-fixed-20261029 -->'
line=('- 用户随后明确“没问题额”，确认本次退聆听故障复测正常，仅限该问题；记录见deliverables/2026-10-29_listening_bounce/human_feedback.json及overall_status_after_user_confirm.json。当前监听已由用户开启，短采样WAITING_WAKE/麦克风true，最近现场回答完整播放ACK成功。其余整体待验项保持，不能扩大为整机通过。\r\n').encode('utf-8')
assert data.count(marker)==1;p.write_bytes(data.replace(marker,line+marker,1))
for p,old,new in [
 (P/'README.md','监听部署时暂停，现场需手动重开，用“汐蓝，你好”整句复测。','用户已确认本次故障复测正常，监听已由用户重新开启。'),
 (root/'后续任务_先读这里.md','监听交付时关闭，待现场手动开启并用原话复测。','本次故障用户已确认正常，监听已由用户重新开启。'),
 (root/'语言模型分析/README.md','普通聊天长尾和真人原话复测待验，迁移暂缓。','本次故障用户已确认正常，普通聊天长尾等整体待验项保持，迁移暂缓。')]:
 data=p.read_bytes();a=old.encode('utf-8');assert data.count(a)==1,(str(p),old)
 p.write_bytes(data.replace(a,new.encode('utf-8'),1))
print(json.dumps({'status':'CONFIRMED_CURRENT_PROJECT_SNAPSHOT','voice':'r6','user_confirms_reported_issue':True,
 'listening_enabled_by_user':True,'whole_project_complete':False,'snapshot':str(out)},ensure_ascii=True))
