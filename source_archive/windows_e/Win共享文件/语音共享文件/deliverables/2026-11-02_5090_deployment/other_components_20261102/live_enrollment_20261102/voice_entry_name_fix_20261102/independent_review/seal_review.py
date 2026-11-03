import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={'common/feature_intents.py':'2ad13c7a5a175a85dfb412182fca44a79229962ff742b18691a7b72ea75f15f2',
 'board/runtime/board_business.py':'bf185a86dfd1f94924759c194b0246b51e64cb0a09654c935e8e1310f7bbea51',
 'tools/yuki_jobs_candidate.py':'d7bade70cf15cd5c7dd9bb17be702f86c5f2d1a32ad5c5809dddffde7a71d200'}
loaded=json.loads((HERE/'CANDIDATE_LOADED.json').read_text(encoding='utf-8'))
for name,digest in expected.items():assert sha(ROOT/'candidate_runtime'/name)==digest==loaded[str(ROOT/'candidate_runtime'/name)]
cases=list(ET.parse(HERE/'CANDIDATE_INDEPENDENT.xml').iter('testcase'))
assert len(cases)==43 and all(c.find('failure') is None and c.find('error') is None for c in cases)
result=dict(status='INDEPENDENT_LOCAL_REVIEW_PASS_NO_PRODUCT_OR_PRIVACY_BLOCKER',reviewed_sources=expected,
    tests=dict(total=43,passed=43,failed=0,errors=0),xml_sha256=sha(HERE/'CANDIDATE_INDEPENDENT.xml'),
    test_source_sha256=sha(HERE/'test_name_grammar_and_bound_yuki.py'),compiled_source_record_sha256=sha(HERE/'CANDIDATE_LOADED.json'),
    actual_composition_verified=['Actual formal CandidatePair and actual BoardPersonaCandidate readiness guard',
        'Actual bind_runtime_pair attaches instance _route and _admit_text; __func__ identity asserted',
        'Actual LocalRecordController keeps raw recognized text, scope, owner and cancellation event',
        'Original SpeakerDevice uses RAM synthetic store/encoder/VAD; no device or model constructor'],
    grammar_checks=['Whole self-directed voice start; no substring extraction or speculative prefix deletion',
        'Quoted, negative and query commands cannot create a new enrollment or supply pending name',
        'Name helper only runs inside prior same-actor 120s pending voice entry',
        'Chinese ASCII/fullwidth inter-character spaces normalize by removal only, preserving every non-space character',
        'Latin internal spaces, nonbreaking spaces, mixed punctuation, command tails, query/negation names and over20 chars reject',
        'Original valid_name and original20-char voice slot retained; original name validator file bytes unchanged',
        'Original waiting-name called-me alias compatible; unarmed name does not start voice',
        'Recognized original voice queries also consume no sample during active sampling',
        'Three distinct original samples then original final confirmation; wrong joint/face confirmations do not save'],
    static_checks=['Yuki entire module AST equals original18d4 after reverting only two kind-tuple additions',
        'Business original methods except LocalIdentityReplies.__call__ match baseline AST exactly',
        'Clock, reset/epoch/current, grants/scope/ACK and metadata logic otherwise unchanged',
        'Original binding_intent8048 and common.voice_enrollment validator bytes unchanged'],
    limitations=['Tests are generated synthetic inputs and RAM fixtures, not captured user names/audio or live-state evidence',
        'Negation/quote tests concern arming or supplying name; the original already-consented sampler still accepts ordinary arbitrary utterances as samples',
        'No assertion of blanket semantic rejection of every possible voice-sample question; recognized original status questions are covered',
        'First test harness used an invalid SimpleNamespace persona and was correctly rejected by readiness; fixed to real BoardPersonaCandidate without relaxing the guard',
        'No board/network/private-store/model/axis/service access occurred; publication remains root-only with fresh CAS'],
    board_actions=False,ssh_or_get=False,private_media_or_store_reads=False,candidate_modified_by_reviewer=False)
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report='''独立审阅通过：最终2ad13 / bf185 / d7bade三文件无产品或隐私阻断点，43个独立本地场景全部通过。

测试使用真实formal CandidatePair和真实BoardPersonaCandidate，实际调用bind_runtime_pair，断言Jobs实例的_route/_admit_text.__func__正是现役Yuki函数；随后通过原LocalRecordController和原SpeakerDevice，未把默认BoardDialogueJobs.route当成真实装配。只有Store/encoder/VAD和PCM为RAM合成对象，没有模型、设备或真实私库。早期fixture错误使用SimpleNamespace persona被原guard拒绝，后已改成真实合法persona，未放松任何产品检查。

自然语音入口仅整句自我请求fullmatch。待姓名只在原same-actor、120秒voice pending里处理；严格姓名cue及保留的“叫我…”兼容走共享helper。中文半角/全角空白只删除原字符之间的空白，不猜字、不替换姓名；原valid_name文件及原20字符slot不变。Latin字内空白、不换行空白、混合连字符/冒号尾巴、问题/否定姓名、指令尾巴、引用和超长形状均不能补名。未发起登记的名字句不能开启voice。

原始ASR记录经LocalRecordController逐字保留，包括称呼前缀、姓名cue冒号和中文空格；只把原FSM的规范入口临时转成具名start，不把规范化名字反写成原用户记录。查询在等待姓名时不建采样，原可识别voice状态问句在正式samples阶段也不消费样本。三段独立录音及最终“确认保存声纹”仍由原Device执行；人脸/联合保存确认不替代它，无face/provider/unified route动作。

静态确认：Yuki模块只变两处kind tuple，逆转即与18d4整模块AST相同；Business除LIR.__call__两处改动外全部原方法AST不变，含AAC clock、trace、reset/epoch、owner/grant/scope/ACK。binding_intent8048与common.voice_enrollment原validator字节保持。

边界：引用/否定测试证明不会误启登记或给等待中的姓名授权；不能据此宣传原已同意的自由语音sampler会语义过滤所有可能的句子。识别得到的原状态问句已单独测不采样，原自由样本策略没有重写。本次没有读真实现场原话/姓名或模型输出，未SSH/GET、读私库、操作服务或设备。root仍需按最终源SHA和最新startup做CAS发布，审查不替代真实语音验收。
'''
(HERE/'REVIEW.txt').write_text(report,encoding='utf-8')
print(json.dumps({'verdict_sha256':sha(HERE/'REVIEW_VERDICT.json'),'review_sha256':sha(HERE/'REVIEW.txt'),'tests':43,'all_pass':True}))
