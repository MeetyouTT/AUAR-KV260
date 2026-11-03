import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={'common/feature_intents.py':'901c74d8de825bf6f22ac7cca608db3840ea7d39cc104ac4b5392dca3f7d8f6c',
 'board/runtime/board_speaker_business.py':'28d36d1f35ed173098df50e51b829a89b0f5d09c1f7281dc34381a3cedac6cfe'}
reviewed=json.loads((HERE/'REVIEWED_SOURCE_SHA.json').read_text(encoding='utf-8'))
for name,digest in expected.items():assert reviewed[name]==digest==sha(ROOT/'candidate_runtime'/name)
cases=list(ET.parse(HERE/'INDEPENDENT_ALIAS.xml').iter('testcase'))
assert len(cases)==15 and all(c.find('failure') is None and c.find('error') is None for c in cases)
result=dict(status='INDEPENDENT_REVIEW_PASS_NO_BLOCKER',reviewed_sources=expected,
 tests=dict(total=15,passed=15,failed=0,errors=0),xml_sha256=sha(HERE/'INDEPENDENT_ALIAS.xml'),
 test_sha256=sha(HERE/'test_literal_alias.py'),
 source_scope=dict(changed_functions=['common.feature_intents.speaker_text','BoardSpeakerBusiness._explicit_self_match'],
  regex_constants_per_file=4,token_added='|辨别',bytes_added_per_file=28,
  whole_module_ast_equal_to_baseline_after_literal_reversal=True),
 verified=['The two requested phrases are recognized by both original query routing and explicit probe classifier',
  'Actual formal CandidatePair+bind_runtime_pair Yuki instance method identity, LIR and original worker path exercised',
  'Each alias produces candidate only after3 distinct synthetic captures, with exactly3 original encoder calls',
  'Exact same-request retry uses cache and no extra encode',
  'Negative, quoted and hypothetical phrases do not trigger explicit probe',
  'Alias query in active original registration consumes no voice sample and does not open probe',
  'field_calibrated,identity_verified,personal_memory_allowed remain false; no active crossmodal link or profile grant'],
 preserved=['All registration helper/confirmation/quality logic',
  'All f82 cache/TTL/absolute proof bound/adoption ledger/cancel/namespace checks',
  'All model parameters, original matcher0.8/0.1 and3distinct, owner/scope/ACK behavior',
  'All public metadata shape and privacy boundaries'],
 boundaries=['Pure local generated PCM/fresh synthetic stores/encoder fixtures; no field calibration or real audio accuracy claim',
  'No production DB/text/model or network/device/service/axis action by this reviewer',
  'The review applies to exact two hashes; root remains sole production writer with latest-source CAS'])
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report='''独立快审通过：901c74d8…d8f6c feature_intents 与28d36d1f…ac6cfe worker，15个独立场景全部通过，无产品或隐私阻断。

纯literal/AST核验：只在speaker_text与_explicit_self_match各4个query regex Constant追加“|辨别”，每文件+28字节。去回这8个token后，两整模块AST分别与2ad13/f82 baseline完全相同，注册helper、cache、TTL、ledger、取消、clock、matcher门槛和所有其它逻辑不变。

“你可以根据我的声音辨别我是谁吗”和“辨别我的声音”均经过实际formal CandidatePair及bind_runtime_pair绑定的Yuki实例_route、LIR和原worker，到第3个独立合成capture才形成候选，恰好3次编码，exact-request重试不额外编码。否定、引用、假设句不触probe；登记samples中的alias查询不消费样本或开启probe。未标定、未验证身份、无私人记忆权限继续false，active links为0、未发grant。

验证只使用本地合成encoder/PCM和新建合成库，没有读取真实用户原话、音频、私库或模型；无SSH、GET或设备/服务动作。本结论限最终两SHA，root应按最新生产源与startup做原CAS发布。
'''
(HERE/'REVIEW.txt').write_text(report,encoding='utf-8')
print(json.dumps({'verdict_sha256':sha(HERE/'REVIEW_VERDICT.json'),'review_sha256':sha(HERE/'REVIEW.txt'),'tests':15,'all_pass':True}))
