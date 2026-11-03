import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def xml(p):
    tree=ET.parse(p);cases=list(tree.iter('testcase'));fail=[]
    for c in cases:
        if c.find('failure') is not None or c.find('error') is not None:fail.append(c.attrib.get('classname','')+'::'+c.attrib['name'])
    return dict(tests=len(cases),passed=len(cases)-len(fail),failed=len(fail),failures=fail,sha256=sha(p))

manifest=json.loads((HERE/'MANIFEST.json').read_text(encoding='utf-8'))
for name,row in manifest['files'].items():
    assert sha(HERE/'baseline'/name)==row['before_sha256']
    assert sha(HERE/'candidate'/name)==row['candidate_sha256']
results={name:xml(HERE/(name+'.xml')) for name in ('CANDIDATE_PIPELINE','BASELINE_PIPELINE','CANDIDATE_ORIGINAL_REGRESSION','BASELINE_ORIGINAL_REGRESSION')}
assert results['CANDIDATE_PIPELINE']['tests']==31 and results['CANDIDATE_PIPELINE']['failed']==0
assert results['BASELINE_PIPELINE']['failed']==8
assert results['CANDIDATE_ORIGINAL_REGRESSION']['failures']==results['BASELINE_ORIGINAL_REGRESSION']['failures']
assert results['CANDIDATE_ORIGINAL_REGRESSION']['tests']==70 and results['CANDIDATE_ORIGINAL_REGRESSION']['failed']==7
readback=json.loads((HERE.parent/'PUBLIC_SOURCE_READBACK.json').read_text(encoding='utf-8'))
assert readback['stable_startup'] and all(v['sha256']==v['pin'] for v in readback['sources'].values())
result=dict(status='LOCAL_CANDIDATE_FROZEN_PENDING_ROOT_REVIEW',public_source_boot_id=readback['boot_id'],
    public_source_startup_sha256=readback['startup_sha256'],public_pinned_sources_verified=len(readback['sources']),
    files=manifest['files'],diff_sha256=sha(HERE/'CANDIDATE.diff'),
    validation=results,original_regression_new_failures=[],
    code_scope=['BoardNoSpeech marker class','BoardParaformer.transcribe empty-text exception type only',
                'BoardDialogueJobs._admit_text true empty/whitespace handling after original control-char check',
                'BoardDialogueJobs._execute narrow ASR marker catch plus original current/deadline check'],
    unchanged=['models, thresholds, PCM, recognizer arguments, sample quality, voice and face consent',
               '120s consent/90s sampling limits, target/revision binding, gallery and original registry',
               'generic service failures, ACK failure, explicit pause/cancel, context/generation checks',
               'original player receipts, memory grant/scope policy, source authority and all other modules'],
    observed_lifecycle=['Normal committed-ACK rearm does not reset enrollment',
      'VAD speech-start callback refreshes the initial microphone-open capture snapshot',
      'Original generic empty-ASR error can reset an authorize stage and route a later bare confirmation to ordinary dialogue',
      'Original 30-second conversation-silence closure remains in force'],
    limitations=['Synthetic recognizer/model/player/memory fixtures; no real audio, GPU/ARM model load, device or private store',
      'Speaker preservation proves zero speaker/identity dispatch and unchanged synthetic collected count; it is not a real voice-model enrollment test',
      'This mechanism is reproducible and fits observed SERVICE_ERROR cycles, but the historical incident has no retained capture metadata and is not uniquely attributed',
      '70 original tests are not all passing: four pre-existing alias/intent fixture failures and three pre-existing GUI fixture missing character_pair'],
    board_mutations=False,service_or_gui_actions=False,model_requests=False,private_data_reads=False,axis_actions=False,
    merge_note='Root only: CAS the two sources against exact before hashes, preserve all latest UI and four diagnostic candidates, update only those two current startup pins. No overall startup/UI replacement. Keep paired files consistent before any root-managed normal GUI start.')
(HERE/'VALIDATION_FINAL.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report='''已冻结本地两文件候选，尚未部署。

可以确定复现的机制：BoardParaformer.transcribe 原先对识别完成但空文本抛通用 ValueError；Jobs 将它当普通错误。RecordingController._poll_transcription 把 error 置成 ERROR，随后 _auto_fail 会 reset_enrollment；LocalIdentityReplies.reset 同时清空原 face flow 与原 business。prepare_name 后跨轮的 authorize 因而丢失。真实 LocalIdentityReplies 在没有活动 flow/business 时，会让后续单独“确认登记”返回 DIALOGUE_ROUTE。此后模型会怎么说不在本次测试内，也没有调用模型。

这不是正常重听每次必经的路径。真实 committed ACK -> _auto_tick -> _listen 仅使 Jobs.cancel 做代际失效，不调用 reset_enrollment。LocalFaceExchange.cancel 只关闭本 request、释放 PCM；final face result 只移除 request gate。真实 VAD _speech_started 还会再次 capture_started(listen_id)，覆盖麦克风打开时快照，所以通常并非只固定最早的麦克风起点。若 VAD 时源失效，原 capture owner 仍为 None，不会复用更早有效证据；当前 fresh 不能代替缺失起点。原 30 秒会话静音关闭仍会 reset，未改动。

最小变更：ASR 新增 BoardNoSpeech(ValueError) 标记，只在原识别器返回空文本的一个抛出点使用。Jobs 仅在原 transcribe 调用范围捕获这个确切类型，先运行原 current/deadline 检查，然后发原 entry_rejected。直接返回的真空/空白字符串也用同支路；类型、长度与原控制字符检查仍在此之前。原 VoiceFirst._entry_rejected 只设置 wake_rearm；原 monitor 在同一 audio owner 上重听，不选择新 conversation，不延长原 consent 截止时间，不发 wake_detected，不把空文本交给任何身份/声纹/模型或记忆写逻辑。

最终专项31项全过；基线同套23通过、8失败，均对应旧空白清理与后续授权丢失。4种空白来源完整走原 ASR/Jobs/LocalIdentityReplies/VoiceEnrollment/BoardDialogueController/有序channel/完整receipt和ACK/半双工rearm，随后下一独立“确认登记”完成原 face sampler，恰1次sample_start和1次enroll；本地模型桩只允许TTS，LLM为0。空白自身没有新增identity/speaker分派、TTS、记忆turn、播放ACK，保留原name/owner/epoch/until/session。

原3个公开测试文件共70项，两版均63通过、7相同旧失败，无新增失败。4项位于旧称呼/意图fixture：missing_sensitive_board_handlers、explicit_memory_precedes_reasoning、wake_alias、real_board_store_memory_history；3项BoardAvatarStage.__new__路由fixture缺character_pair。这7项没有被本候选掩盖或修正。不存在“原70全过”的结论。

边界已覆盖：真正ValueError、OSError、TimeoutError、RuntimeError仍ERROR并清授权；非字符串/过长/控制字符仍拒绝；显式pause/cancel仍取消；换人/缺起点/过期仍原拒绝；typed NoSpeech之后deadline过期仍Timeout而非安静重听。保留所有模型、声线、参考音、阈值、质量、确认/权限和播放提交契约。

来源：本boot a6d4、startup 9a9a 的18个固定公开源全部由原严格SSH helper只读核pin；无health/真实库/音视频/轴读取。采样和声纹计数测试使用RAM合成对象；真实设备效果仍待root正常部署与用户新一轮语音验证，不能从此推定历史现场唯一根因。

只供root合并：两源以MANIFEST before SHA做CAS；保留最新startup全部其它映射和全部UI/主页面/转轴字段，只更新两pin；不要用旧startup整体覆盖。ASR和Jobs需成对一致再由root按正常流程启动GUI。此代理没有写板卡、开麦、请求模型、改变服务或操作转轴。
'''
(HERE/'HANDOFF.txt').write_text(report,encoding='utf-8')
print(json.dumps({'validation_sha256':sha(HERE/'VALIDATION_FINAL.json'),'handoff_sha256':sha(HERE/'HANDOFF.txt'),
    'candidate_pipeline':results['CANDIDATE_PIPELINE']['passed'],'baseline_fail':results['BASELINE_PIPELINE']['failed'],
    'original_same_failures':True,'diff_sha256':result['diff_sha256']}))
