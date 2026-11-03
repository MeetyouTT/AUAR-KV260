import ast,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='board/runtime/board_speaker_business.py'
expected='f82bc71d00c355c164d43ca0b6a853ea6a32e67c84ffd228791d7070209b907e'
assert sha(ROOT/'candidate_runtime'/name)==expected
assert sha(ROOT/'baseline_runtime'/name)=='6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816'
cases=list(ET.parse(HERE/'INDEPENDENT_EDGE_V3.xml').iter('testcase'))
assert len(cases)==15 and all(c.find('failure') is None and c.find('error') is None for c in cases)
unchanged={}
for filename in ('tools/provisional_voice.py','tools/progressive_speaker.py','tools/binding_hub_runtime.py',
  'tools/speaker_device.py','common/speaker_identity.py','common/identity_links.py','board/identity/store.py',
  'board/runtime/board_business.py','tools/yuki_jobs_candidate.py','common/feature_intents.py'):
 before=sha(ROOT/'baseline_runtime'/filename);after=sha(ROOT/'candidate_runtime'/filename)
 assert before==after;unchanged[filename]=after
def methods(path,cls):
 tree=ast.parse(path.read_text(encoding='utf-8'));node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
 return {n.name:ast.dump(n,include_attributes=False) for n in node.body if isinstance(n,ast.FunctionDef)}
before=methods(ROOT/'baseline_runtime'/name,'BoardSpeakerBusiness');after=methods(ROOT/'candidate_runtime'/name,'BoardSpeakerBusiness')
changed=sorted(k for k in before if before[k]!=after[k])
assert set(changed)=={'__init__','_refresh_public','public','_call','turn','_cancel_actor','reset','health'}
observation=json.loads((HERE/'LATE_ADOPTION_OBSERVATION.json').read_text(encoding='utf-8'))
assert observation['source_sha256']==expected and observation['next_phase']!='CANDIDATE' and observation['next_distinct']<=1
result=dict(status='INDEPENDENT_LOCAL_REVIEW_PASS_NO_REMAINING_CODE_BLOCKER',source=name,
 before_sha256='6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816',candidate_sha256=expected,
 tests=dict(total=15,passed=15,failed=0,errors=0),xml_sha256=sha(HERE/'INDEPENDENT_EDGE_V3.xml'),
 test_source_sha256=sha(HERE/'test_probe_adoption_edges.py'),unchanged_original_components=unchanged,
 modified_existing_worker_methods=changed,
 checks=['Actual fullYuki/LIR/single-worker Hub chain, original matcher, synthetic192D vectors and fresh synthetic stores',
  'Late adoption cancellation followed by another true public service.turn caller cannot reuse unadopted/cancelled third capture',
  'Worker-finished candidate rechecked at caller adoption for monotonic2s, absolute wall bounds and ClockUnavailable',
  'Expired text contains no registered synthetic name; clock faults in worker adoption are real failures',
  'public and health take clock reads outside service.lock and project clock failure as EXPIRED without throwing',
  'Exact-request cache retry has zero extra encode; three fullYuki queries have exactly3 encode calls',
  '600s original control descriptor cache retains NOT_CALIBRATED/candidate_idNone and no candidate name',
  'Original nonprobe dict/None/different-string return objects remain identical despite expired same-meta probe cache',
  'Encoder/store namespace mismatch never encodes or produces a new candidate against old store',
  'Adoption ledger holds only metadata,cancelEvent,adopted boolean; no job,PCM or callback closure',
  'Historical candidate count is bounded and does not extend2s candidate validity',
  'Uncalibrated/identity_verified/personal_memory_allowed remain false; no active crossmodal people or profile grant'],
 prior_counterexample=dict(source='779213f6f4cde9f1f9738f4a9d694336d2bcbea05dd23ad7f28fa4e8ff045917',
    evidence_file='LATE_ADOPTION_779_COUNTEREXAMPLE.json',sha256=sha(HERE/'LATE_ADOPTION_779_COUNTEREXAMPLE.json'),
    issue='Cancelled completed-third contribution could be reused by queued next owner before cleanup; fixed by adopted Event ledger'),
 boundaries=['Candidate is computational/self-match evidence, never field calibration or identity authentication',
   'candidate_completed/completed_is_historical reports prior adopted computation; it is not a live identity proof or playback ACK',
   'Original progressive analyzer may maintain its existing anonymous descriptive store; this review does not claim zeroSQL across original pipeline',
   'Tests use only generated PCM and fresh synthetic stores; no real enrolled name/audio/model accuracy is evaluated',
   'Review applies to f82 bytes only; subsequent changes require refreshed review'],
 board_actions=False,ssh_or_get=False,real_private_data_reads=False,model_or_device_initialization=False,
 reviewer_changed_candidate=False)
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report='''独立审阅通过：单文件最终f82bc71d00c355c164d43ca0b6a853ea6a32e67c84ffd228791d7070209b907e无剩余代码阻断点，15个独立边界全部通过。

已通过实际fullYuki→LIR→原sole-worker/Hub链验证三次query恰3次编码、原3distinct和0.8/0.1门槛不变。exact-request重复或过期重试不重复编码；600秒原control descriptor缓存只保留NOT_CALIBRATED、candidate_id=None，不存候选称呼。model/store namespace不一致时不再以旧模板形成新候选。

最重要的原779取消反例已保留：第3次worker完成但caller未采纳时取消，下一合法owner可抢在清理前复用已取消贡献形成候选。最终版本的账本仅保存meta/Event/adopted，不保留job、回调闭包或PCM；下一代会拒绝任何未采纳或已取消的旧贡献。独立回归改用另一真实service.turn调用者排队，下一代只COLLECTING1，不含取消的第3段。

实际返回文本也受原proof绝对2秒约束：worker完成后caller延迟超过2秒或wall越过bounds会返回不含姓名的固定EXPIRED；adoption时ClockUnavailable按真实异常失败，不吞成候选。原_Call非probe的dict/None/不同str即使同meta存在过期probe缓存也保持原对象原值，不被派生提示替换。

public/health只在service.lock内复制元数据，释放后再取timeline time，避免service→clock和原clock→idle health的反向锁序。两入口clock故障均仅将公开投影变EXPIRED，不使API/GUI轮询抛出，也不改变worker实际clock故障语义。candidate_completed是饱和65535的历史计算计数，不延长有效期，不等于身份已验证或播放已ACK。

公开字段仍为固定枚举/有界计数/bool，不含姓名、ID、分数、向量或原文；field_calibrated、identity_verified、personal_memory_allowed继续false。未创建跨模态active person或profile grant。计算候选只用于本人匹配复验，不能宣称已完成现场校准或身份认证。

静态确认原Device/Progressive/Provisional/IdentityStore/BindingHub/IdentityLinks及LIR/Yuki等10个关键组件字节未变；原worker已有方法仅__init__、public/health投影、_call采纳、turn显式query入口、_cancel_actor/reset清理增加派生逻辑，_submit、_run、质量、原analysis等方法AST保持。新gallery token为soleworker内私有SELECT/hash，不导出内容；原observer可能维护既有匿名描述库，不宣称整个原流水零SQL。

全部验证仅本地生成PCM、192D合成encoder、原方法和新建合成库；没有SSH/GET、真实设备/模型/登记音频/身份库访问，未修改候选或生产。root仍是唯一发布者，须以最新源/startup进行CAS并按原维护守卫启动。
'''
(HERE/'REVIEW.txt').write_text(report,encoding='utf-8')
print(json.dumps({'verdict_sha256':sha(HERE/'REVIEW_VERDICT.json'),'review_sha256':sha(HERE/'REVIEW.txt'),
 'tests':15,'changed_existing_methods':changed}))
