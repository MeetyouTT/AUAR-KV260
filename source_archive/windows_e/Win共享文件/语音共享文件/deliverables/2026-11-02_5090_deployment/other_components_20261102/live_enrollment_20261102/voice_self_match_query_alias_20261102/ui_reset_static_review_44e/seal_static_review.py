"""Static public-source call graph only. No runtime, device or private reads."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
RUNTIME=ROOT/'candidate_runtime';INTEGRATION=ROOT/'integration_source_44e'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
exact={'tools/board_recording.py':'e70a9f4ca4768b3a1fabfc33145e39edbcb8cf20e0c76f269cc0b032fb54ce26',
 'tools/production_memory_presentation.py':'de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2',
 'board/runtime/history_delete.py':'647b5cf85ad5595305067bcced2b118f83e89ca79ba45b7ad91090fd9515023f'}
for name,digest in exact.items():assert sha(INTEGRATION/name)==digest
core=('tools/streaming_controller.py','tools/realtime_controller.py','tools/voice_first_recording.py',
 'tools/handsfree_recording.py','tools/barge_in_recording.py','tools/production_listening.py',
 'tools/formal_yuki.py','tools/formal_native_yuki.py','tools/native_yuki.py',
 'board/runtime/board_business.py','board/runtime/audio/board_dialogue_jobs.py','board/runtime/audio/capture.py')
sources={str(INTEGRATION/name):digest for name,digest in exact.items()}
sources.update({str(RUNTIME/name):sha(RUNTIME/name) for name in core})
normal=[
 dict(case='CAPTURE_ARM',chain='VoiceFirst._listen -> HandsFree._listen -> RecordingController._listen -> Jobs.cancel/capture_started',
      resets_enrollment=False,note='Jobs.cancel invalidates generation and playback; it does not call reset_enrollment'),
 dict(case='ACTUAL_SPEECH_START',chain='AutomaticCapture VAD transition -> HandsFree._speech_started -> Jobs.capture_started',
      resets_enrollment=False,note='Refreshes capture owner from RAM; invalid source stays unavailable'),
 dict(case='STREAM_START',chain='Presentation.channel_event -> NativeStreaming.channel_event -> Streaming.channel_event(start) -> Realtime.begin_dialogue -> visual.cancel',
      resets_enrollment=False,note='NativeStreaming/Streaming/Realtime cancel chain belongs to visual controller, not recording controller'),
 dict(case='NORMAL_NATIVE_INVALIDATE',chain='visual.cancel -> portrait_offload.invalidate -> StrictLocalPortrait/LocalPortrait.invalidate',
      resets_enrollment=False,note='Invalidates old numeric visual generation; does not fail pair or clear ready'),
 dict(case='FULL_PLAYBACK_COMPLETE',chain='Streaming.tick -> completed_streams -> IDLE/stream=None -> Recording.tick -> Jobs.acknowledge',
      resets_enrollment=False,note='Full receipt goes to original ACK action worker'),
 dict(case='ACK_SUCCESS_REARM',chain='Jobs._perform_action(ack) committedTrue -> Recording._auto_tick -> _listen after0.5s settle',
      resets_enrollment=False,note='No select_conversation on ordinary same-session rearm'),
 dict(case='PRESENTATION_RETIRE',chain='recording.tick wrapper -> Presentation.retire_consumed',
      resets_enrollment=False,note='Only retires consumed display/log/utterance references after original idle gates; no cancel or ACK')]
reset=[
 dict(case='EXPLICIT_CANCEL_PAUSE_STOP_OR_CLOSE',chain='Recording.cancel -> Jobs.cancel -> Jobs.reset_enrollment -> LIR.reset -> business.reset',
      gate='Explicit recording cancel, event reset/cancel, stop/close or queued external worker cancel'),
 dict(case='HANDLED_RECORDING_ASR_STREAM_AUDIO_ERROR',chain='Recording._auto_tick(error or last_error) -> _auto_fail -> Jobs.reset_enrollment',
      gate='Original recording/transcription ERROR, auto_error or controller.last_error; does not require RuntimeFault'),
 dict(case='ACK_FAILURE_OR_TIMEOUT',chain='Recording._auto_tick -> _auto_fail -> Jobs.reset_enrollment',
      gate='Matching complete ACK committedFalse, or no matching ACK by original7s deadline'),
 dict(case='VOICEFIRST_SERVICE_ERROR',chain='VoiceFirst._monitor_tick -> _finish_session(SERVICE_ERROR) -> HandsFree._finish_session -> Recording.cancel',
      gate='Observed recording/transcription ERROR or auto_error; original5s cooldown'),
 dict(case='VOICEFIRST_30S_SILENCE',chain='VoiceFirst._monitor_tick -> _finish_session(CONVERSATION_SILENCE) -> Recording.cancel',
      gate='monitor_owned/monitor_entered, capture still RECORDING, elapsed listen_started>=30s and speech_activeFalse'),
 dict(case='AUTOMATIC_NEW_AUDIO_SESSION',chain='VoiceFirst._monitor_tick(!monitor_owned) -> _select_listening_conversation -> Jobs.select_conversation -> reset_enrollment',
      gate='After session cooldown with feedback ready and idle; second reset may follow the silence/service cleanup'),
 dict(case='SERVICE_OR_NATIVE_NOT_READY',chain='production_listening.monitor_tick -> _finish_session(SERVICE_NOT_READY) -> Recording.cancel',
      gate='Owned listener and runtime not started/closed or pair.ready_nowFalse'),
 dict(case='EXPLICIT_CONVERSATION_OR_PROFILE_CHANGE',chain='Jobs.select_conversation/select_profile -> reset_enrollment',
      gate='Original idle selection checks; changes actor/session scope'),
 dict(case='STAGE_RENDER_FAULT_OR_PAIR_FAILURE',chain='External worker.cancel -> recording.cancel; pair invalidators may queue worker.cancel',
      gate='Needs actual fault/readiness metadata. Local GTK/worker source may be one of CPU-maintained mismatches; no current fault claimed')]
reply_classes={
 'ORIGINAL_UNCALIBRATED':'本机有声纹记录，但现场阈值尚未校准，不能确认当前说话者是否已登记。',
 'PROBE_NO_CANDIDATE':'这段声音还未形成稳定的登记声纹候选。完整现场校准尚未完成，我先不确定称呼。',
 'PROBE_COLLECTING_PREFIX':'已完成第',
 'PROBE_CANDIDATE_PREFIX':'声音候选称呼是',
 'PROBE_CANDIDATE_SUFFIX':'。完整现场校准尚未完成。'}
result=dict(status='STATIC_PUBLIC_SOURCE_CALLGRAPH_COMPLETE_NO_PRODUCT_CHANGE',source_sha256=sources,
 normal_paths=normal,reset_paths=reset,fixed_reply_source_classes=reply_classes,
 important_semantics=['LIR.reset_since_trace is set by external LIR.reset only; internal flow.reset and ordinary entry-mode retirement do not set it',
  'Probe deliberately leaves enrollment FSM inactive and entry_modeNone; do not fabricate active enrollment to preserve probe state',
  'business.reset resets probe phase/count toCANCELLED0 even when no enrollment FSM was active',
  'CONVERSATION_SILENCE/SERVICE_ERROR reason persists through next automatic arm because arm changes state without clearing monitor_reason',
  'Next _wake_detected overwrites reason with SPEECH_ACCEPTED; fixed reasons in existing watch can locate prior cleanup without a blind retry',
  'A40point snapshot showingCANCELLED0 does not identify which reset caller happened or prove probe never ran',
  'The two public calibration-related reply families differ; user paraphrase alone does not distinguish original uncalibrated bypass from probe0/3 or3/3'],
 limitations=['No live board/API/private store or retained user body was read in this review',
  'Exact e70a/de04/647b supplied local pin snapshots checked. Core337 live-match provenance is root-reported; no independent SSH refresh',
  'Root reports2 CPU-maintained GTK files differ. Their exact identities were requested; local GTK/worker fallback paths are conditional until source confirmation',
  'Identity agent reports true outer-component synthetic normal start/ACK/rearm3/3 pass; this static review does not claim hardware output timing reproduction',
  'No single historical reset root cause is asserted from static sources alone'],
 board_actions=False,source_or_candidate_changes=False,device_or_model_actions=False)
(HERE/'STATIC_RESET_REVIEW.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report='''44e页面reset静态审阅完成，未修改产品或候选。

主结论：正常capture→stream start→全播放/ACK→同session重听，没有直接调用reset_enrollment。真实Streaming.start经Realtime.begin_dialogue调用的self.cancel属于NativeStreaming/Streaming/Realtime视觉对象；并非Recording.cancel。StrictLocalPortrait.invalidate仅清旧视觉generation，不pair.fail、不把ready置false。de04 presentation既不重绑visual.cancel，也不调用登记reset；retire_consumed只退休已消费显示和PCM引用。history_delete647b的notify钩子也是presentation失效，不触identity reset。

正常路径：VoiceFirst/HandsFree._listen→Recording._listen只Jobs.cancel失效代际、开启capture并绑定RAM owner；VAD起点再次capture_started。Streaming.tick完成只append完整completion并IDLE/stream=None；Recording.tick将完整receipt送Jobs ACK并ANSWERED，成功ACK在0.5秒tail后再次_listen，不重选conversation。

真实重置来源全集见JSON表。Recording.cancel和_auto_fail会调用Jobs.reset_enrollment；后者可由录音/ASR/stream/audio错误、controller.last_error、ACK失败或7秒ACK超时触发，不要求RuntimeFault。VoiceFirst._finish_session把SERVICE_ERROR、CONVERSATION_SILENCE等交给HandsFree，后者直接调用RecordingController.cancel。production readiness失败也会finish。选择conversation/profile、明确取消/暂停/停止/close及真实外部stage/renderer/pair失败会进入原取消链。

原30秒边界尤其容易和复验观察混淆：已进入audio会话、capture仍RECORDING、从listen_started满30秒且当前无speech，会CONVERSATION_SILENCE→Recording.cancel清一次；cooldown后自动新会话会_select_listening_conversation→Jobs.select_conversation再清一次。此时probe不必是active enrollment也会被business.reset置CANCELLED0。monitor_reason在新arm时不清，直到下一次_wake_detected写SPEECH_ACCEPTED，因此既有40点watch的固定reason可能直接提供来源；无需再让用户盲试。

reset_since_trace=True只可能来自外部LIR.reset；flow.handle/guide内部reset或_entry_for模式正常回收均不会置该flag。probe本来就不打开SpeakerDevice的registration session，entry_modeNone/activeFalse正确，不能假装active来躲cleanup。CANCELLED0只证明最后一次全会话清理，不证明这条query从未跑probe，也不能单凭40点后置快照认定是哪一caller。

关于听感：“本机有声纹记录，但现场阈值尚未校准…”是原Device未标定fallback；“这段声音还未形成稳定…完整现场校准尚未完成…”是probe未形成候选；“声音候选称呼是…完整现场校准尚未完成”是probe3/3。用户转述“校准还没做完”不能独立区分这些。已把公开固定literal类别交root，与其既有严格只读COUNT分类配合；本代理没有读取真实正文。

源码证据为本地现役pin快照e70a board_recording、de04 presentation、647b history_delete，加root报告337匹配的core文件。两份CPU维护GTK mismatch的确切名称尚待root给既有比较记录；本地GTK/AvatarWorker异常兜底路径只作条件说明，不冒称当前真实触发。Identity代理真扩层已报告正常start/ACK/rearm3/3合成通过，与静态一致；其后会补30秒与handled failure case，此审阅不重复搭假active FSM。

全程无SSH/GET、板端状态读取、真实音视频/私库访问或设备动作。
'''
(HERE/'STATIC_RESET_REVIEW.txt').write_text(report,encoding='utf-8')
print(json.dumps({'review_sha256':sha(HERE/'STATIC_RESET_REVIEW.json'),'text_sha256':sha(HERE/'STATIC_RESET_REVIEW.txt'),'normal_paths':len(normal),'reset_paths':len(reset)}))
