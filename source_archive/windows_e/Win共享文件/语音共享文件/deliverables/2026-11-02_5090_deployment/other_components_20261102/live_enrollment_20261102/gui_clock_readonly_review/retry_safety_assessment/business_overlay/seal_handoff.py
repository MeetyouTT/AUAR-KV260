"""Seal local candidate, source-order analysis and synthetic validation receipts."""
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[4]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
validation=json.loads((HERE/'VALIDATION.json').read_text(encoding='utf-8'))
assert validation['case_count']==43 and validation['all_cases_pass']
candidate=HERE/'candidate/board/runtime/board_business.py'
assert sha(candidate)=='aac26f39b8cbec1496df93a3de24b0bc2a14289552d2728c585f3625ef779eae'
base=OUT/'identity_dialogue_collaboration/baseline'
order_sources={}
for relative in ('tools/production_board_business_gui.py','tools/board_business_gui.py','tools/board_avatar_gtk.py',
                 'tools/production_frontend_selection.py','board/runtime/audio/board_frontend_process.py',
                 'board/runtime/audio/board_capture.py','board/runtime/board_speaker_business.py'):
    path=base/relative
    order_sources[relative]={'local_public_source_path':str(path),'sha256':sha(path)}
handoff={
 'schema':'aura-initialize-clock-recovery-candidate-handoff-1',
 'sealed_host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'LOCAL_CANDIDATE_VALIDATED_PENDING_INDEPENDENT_REVIEW_AND_LIVE_ACCEPTANCE',
 'candidate_sha256':sha(candidate),'baseline_sha256':manifest['files']['board/runtime/board_business.py']['before_sha256'],
 'scope':'Only BoardBusinessRuntime.initialize_clock; no common clock/client/producer changes',
 'source_clock_sha256':'93b65ec3d9ca393b32499845297c78a2f1f71bc19e069b2ce3dc6f69e795af02',
 'source_client_sha256':'600e044dedfc90c70e319e0e91999b8b4b7f648e0a5ca98e2a1bc0ab09a076b2',
 'startup_order_public_sources':order_sources,
 'startup_order_facts':[
  'Production GUI constructs pinned Paraformer and frontend pool before initialize_clock(timeout=3.)',
  'Runtime creates jobs with start_worker=False; start() occurs later via GUI activation',
  'Production GUI calls _attach_speaker and ECAPA initialization only after Date initialization succeeds',
  'Reviewed Stage constructs recording/render worker/UiServiceClient/CameraPreviewWorker after prepare_board_business returns',
  'Frontend process constructor waits for HELLO; no capture frame is requested by this constructor'],
 'source_inferences_not_runtime_proof':[
  'Native ASR/frontend sessions or a preloaded frontend child exist before Date sampling and might contend for CPU scheduling',
  'Python sources do not establish native idle-thread spinning or GIL ownership',
  'Current-process ECAPA or GUI preview work cannot explain the earlier constructor Date sample under this reviewed call order',
  'External camera/OS/host scheduling remains outside this source-only analysis'],
 'root_cause_of_actual_GUI_RTT_over_1s_proved':False,
 'retry_rule':{
  'same_absolute_original_deadline':True,'production_caller_timeout_seconds':3.,'attempts_max':2,
  'unchanged_per_sample_max_rtt_seconds':1.,
  'original_ClockUnavailable_exact_type_and_args_only':['sample_rtt_exceeded'],
  'real_original_clock_and_client_classes_only_for_retry':True,
  'first_request_for_fake_nonstandard_timeline_retained':True,
  'runtime_not_started_not_closed':True,
  'source_boot_endpoint_verifier_clock_policy_and_full_anchor_unchanged':True,
  'fatal_busy_unknown_prior_error_or_cancellation_rejects_retry':True,
  'existing_persistent_anchor_requires_exact_rejection_save_revision_increment':1,
  'fresh_anchor_none_requires_before_and_after_revision_zero':True,
  'clock_lock_used_only_for_short_readonly_detached_tokens':True,
  'clock_or_file_lock_held_over_HTTP':False,
  'second_failure_has_no_retry_catch':True,
  'old_HTTP_Date_or_proof_replay_allowed':False},
 'hidden_anchor_conflict_boundary':{
  'original_Clock_suppresses_rejection_save_ClockUnavailable_then_rethrows_RTT_error':True,
  'code_only_retry_is_insufficient':True,
  'actual_original_persistence_and_conflict_exercised_with_local_synthetic_files':True,
  'revision_conflict_no_second_GET':True},
 'verified_TTL_expiry':validation['natural_verified_TTL_expiry'],
 'expiry_required_candidate_change':False,
 'synthetic_cases':43,'synthetic_cases_pass':43,
 'whole_module_AST_other_than_initialize_clock_unchanged':True,
 'SQL_single_writer_clock_algorithm_anchor_origin_uncertainty_or_policy_changed':False,
 'initial_Windows_synthetic_fixture_boundary':'Initial long fixture name failed before setup with anchor_write_failed; shorter isolated names exercised the unmodified persistence path successfully',
 'review_artifact_hashes':{n:sha(HERE/n) for n in ('CANDIDATE.diff','SOURCE_MANIFEST.json','VALIDATION.json','test_overlay.py')},
 'real_board_network_models_private_Store_business_anchors_or_axis_accessed':False,
 'local_synthetic_anchor_fixture_files_created_and_retained':True,
 'producer_three_file_candidate_or_production_sources_modified':False,
 'live_recovery_or_deployment_claimed':False}
(HERE/'HANDOFF.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf-8')
report='''本地恢复候选已准备：仅BoardBusinessRuntime.initialize_clock，待独审和现场验收。

基线 b08209eca7979825e26845080bca5e1d64e065d3cabd1178df763a93540573f2
候选 aac26f39b8cbec1496df93a3de24b0bc2a14289552d2728c585f3625ef779eae

保留原单个绝对截止时间（生产调用timeout=3s），每份样本继续通过原clock的1s RTT门槛。仅首份抛原ClockUnavailable精确固定sample_rtt_exceeded时，允许最多第二份全新原client GET/连接/Date/一次性proof。第二份任何失败立即结束；不重放旧样本，不扩大期限或修改系统时间、clock算法、anchor或业务库。

仅真实StableTimelineClock+InferenceHttpClient、runtime尚未started且未closed可重取。原timeline.lock短区间只读取detached元数据token；原对象、boot/source/policy/monotonic/endpoint/verifier/path/完整anchor必须不变，且无fatal、busy、取消、超期或其它前置错误。已有persistent anchor必须由原拒绝保存把file_revision精确加1；fresh无anchor仅接受前后revision0。不能证明时保留首份原失败。任何clock/file锁都不跨HTTP持有。fake/nonstandard timeline的原首请求仍允许，但没有重取权限。

原93b6的RTT异常处理会吞掉拒绝状态保存的ClockUnavailable，再抛最初RTT错误。仅凭固定码会漏掉隐藏anchor_revision_conflict。本候选以原成功保存后的revision凭据收口。合成验证既用了纯RAM注入，也用了本地隔离synthetic-boot文件，通过原_save_locked和原文件锁实际验证保存成功/冲突。另一个原Clock.save推进fixture文件版本后，隐藏冲突确实仍被RTT码遮住，但候选只发1次GET就拒绝。

自然TTL过期已实测：原quality.reason变verification_expired、safe_for_compaction=false；原status仍verified、last_error空、fatal=false。现白名单已覆盖，不需要加状态或改候选。先慢样本拒绝并正常保存，再以同一3s预算取全新快样本，原observe合法恢复verified；原anchor origin和uncertainty不变。

43个合成场景全过，整模块AST仅initialize_clock改变。覆盖慢→快、两份慢、同绝对deadline、取消/boot/source/policy/endpoint/path/fatal/owner变化、hidden revision冲突、第二份anchor冲突、fake timeline、token只读/锁及HTTP期间无锁。首次Windows fixture路径过长造成setup的anchor_write_failed已保留边界；只缩短合成路径后原持久逻辑通过，没有改clock或候选。

启动顺序：ASR和frontend模型/子进程在Date前已构造，业务ASR worker尚未启动；ECAPA在Date成功后才初始化；recording/render/UI服务和preview worker在prepare_board_business返回后才构造。因此不能把本进程ECAPA/GUI preview说成当前Date采样期间后台负载。已加载native ASR/frontend线程池可能影响CPU调度，但源码不能证明其空闲spinning/GIL情况。现网GUI>1s的精确成因仍未定位，独立RAM16ms/5ms不构成反证或复现。

本轮没有SSH、GET、板卡/模型/真实Store/业务anchor/轴操作，没有修改producer三文件；仅本地独立候选、合成夹具与报告。没有宣称已部署或已恢复GUI。
'''
(HERE/'HANDOFF.txt').write_text(report,encoding='utf-8')
print(json.dumps({n:sha(HERE/n) for n in ('HANDOFF.json','HANDOFF.txt','VALIDATION.json','CANDIDATE.diff','SOURCE_MANIFEST.json')}))
