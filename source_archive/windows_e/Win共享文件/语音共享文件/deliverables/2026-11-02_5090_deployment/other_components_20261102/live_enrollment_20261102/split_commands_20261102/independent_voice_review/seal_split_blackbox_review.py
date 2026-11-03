import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE.parent/'candidate_runtime'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
loaded=json.loads((HERE/'BLACKBOX_LOADED_SOURCES.json').read_text(encoding='utf-8'))
names=('common/binding_intent.py','board/runtime/board_business.py','board/runtime/audio/board_dialogue_jobs.py')
reviewed={name:sha(CANDIDATE/name) for name in names}
assert reviewed=={
 'common/binding_intent.py':'8048cd5bd4f3f80cd872f373e1eed149820f37d2ec40042390c17cfb4cd94df1',
 'board/runtime/board_business.py':'c01bb04c7bfbce8d78b51aefa5faf0426527be13edf6e26d8d28828c488222b3',
 'board/runtime/audio/board_dialogue_jobs.py':'7c0fc844a6848b43c2fc659522d9be962d0c6130c2f0bcc121ff81142fde5134'}
for name,digest in reviewed.items():assert loaded[str(CANDIDATE/name)]==digest
def xml(name):
 p=HERE/name;cases=list(ET.parse(p).iter('testcase'));failed=[c.attrib['name'] for c in cases if c.find('failure') is not None or c.find('error') is not None]
 return dict(tests=len(cases),passed=len(cases)-len(failed),failed=len(failed),failure_names=failed,sha256=sha(p))
v2=xml('SPLIT_V2_BLACKBOX.xml');v1=xml('SPLIT_V1_BLACKBOX.xml')
assert v2['tests']==30 and v2['failed']==0 and v1['tests']==15 and v1['failed']==2
manifest=json.loads((HERE.parent/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
manifest_matches=all(reviewed[row['file']]==row['after_sha256'] for row in manifest['changed_files'])
result=dict(status='LOCAL_REVIEWED_SOURCE_SNAPSHOT_NO_CODE_BLOCKER',reviewed_sources=reviewed,
    original_voice_contract=xml('ORIGINAL_VOICE_CONTRACT.xml'),blackbox_v2=v2,first_draft_counterexamples=v1,
    producer_manifest_matches_reviewed_source=manifest_matches,
    loaded_sources_sha256=sha(HERE/'BLACKBOX_LOADED_SOURCES.json'),test_sha256=sha(HERE/'test_split_entry_blackbox.py'),
    contract_checks=['Voice-only: no face source/readback, unified route, face command, or cross-modal link attempt',
       'Face-only: no voice turn, voice sample or voice save dispatch',
       'Bare voice -> pending name -> 200 public polls while Device inactive -> same actor name followup opens original Device',
       'Unarmed/cancelled/reset/expired/different-session name hints cannot start enrollment',
       'Three actual original SpeakerDevice synthetic samples and final original confirmation save',
       'Wrong face/joint confirmation cannot save standalone voice',
       'Active opposite-modality request is busy without consuming or discarding original sample/target',
       'Exact original controller begin_turn cancellation window cannot resurrect pending voice authority',
       'Exact original face start+guide registered/reset outside producer.finally -> first voice request opens directly',
       'Exact original voice save outside producer.finally -> first face request opens directly',
       'Actual BoardDialogueJobs._route dispatches both explicit entry kinds',
       'Entire Jobs AST equals 01b27 after removing only the two new kind-tuple members',
       'Quoted/negative/hypothetical strings do not arm standalone entry; original remember-self joint kind remains'],
    model_accuracy_claim=False,real_enrollment_claim=False,production_or_service_or_axis_actions=False,
    private_store_or_media_reads=False,ssh_calls=False,
    limitations=['Runtime dependencies are exact original public methods with RAM fixtures; no physical devices, production stores or model loads',
        'Review is for the exact three hashes above; later producer source changes require refreshed review',
        'Producer manifest/diff sealing is separate; this review records actual compiled bytes independently',
        'Root must rebase against CPU-returned latest production source/startup pins; f507 is only the historical candidate base',
        'Future association of two separately enrolled modalities is outside this change; old explicit joint compatibility is retained'],
    deployment_authority='Root only after CPU maintenance handback; no authorization or hardware action was exercised by this review')
(HERE/'SPLIT_ENTRY_REVIEW_V2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report='''独立入口候选审查：本地实读三文件快照无代码阻断点，30个独立黑盒全部通过。

实读/编译SHA：
common/binding_intent.py 8048cd5bd4f3f80cd872f373e1eed149820f37d2ec40042390c17cfb4cd94df1
board/runtime/board_business.py c01bb04c7bfbce8d78b51aefa5faf0426527be13edf6e26d8d28828c488222b3
board/runtime/audio/board_dialogue_jobs.py 7c0fc844a6848b43c2fc659522d9be962d0c6130c2f0bcc121ff81142fde5134

两种独立入口隔离已验证。声纹only在face provider设置为一访问即失败时，仍能进行原开场、三段不同PCM和“确认保存声纹”，没有snapshot/readback/unified route/face命令。人脸only没有voice turn/采样/保存，原已知脸结果也不会接着启动voice。两者都没有新关联尝试或profile grant路径。同名自动替换及之后的单独关联不在本轮实现范围，旧“记住我…”联合kind保持。

bare“登记声纹/帮我登记声纹”返回原提示后，Device本身仍inactive；候选仅保留同actor、120秒待姓名入口。200次public轮询不会清掉它，后续“我叫…”才转回原具名start。未armed、取消/reset、过期或换session的姓名句不能独立授予登记。跨模态命令在旧采样前被busy拦截，不消费或丢弃原声纹/人脸状态。

首版取消窗口已作为真实反例保留：15测试中13过、2失败。精确原BoardDialogueController在store.begin_turn的原_check之后、producer之前发生reset+cancel时，旧barevoice仍会复活待名入口。修订版c01bb用原锁/epoch/current及CAS清理修复，两个反例均过，没有放松取消断言。V1 XML保持原证据，不将首版称作通过。

root补充的完成边界也通过：调用真实原VoiceEnrollment._start_simple和guide，在LIR producer.finally之外完成registered/reset，再发首次voice命令，直接进入原voice；调用真实原SpeakerDevice在finally外保存后，再发首次face命令，直接进入原face。测试使用真实原FSM和合成camera/ACK，不以一个立即返回的fakeface掩盖完成后的stale mode。

Jobs装配已直接调用真实_route，验证两种新kind均进原本地handler。整个Jobs AST在只移除两处kind tuple新增成员后，与已部署NoSpeech底座01b27完全相同；c514/01b其它逻辑、a911 face和85联合router没有被此候选重写。

原SpeakerDevice独立契约另有24项全部通过，见ORIGINAL_VOICE_HANDOFF.txt。所有测试只读公开本地源，使用RAM store/encoder/VAD、生成PCM、原有ordered channel/controller方法；没有SSH、板端状态读取、真实相机/语音/模型/私库或服务动作。CPU交权后没有任何板端调用。此次通过仅限上述实读SHA；producer若再改源码，须按新字节复验；生产CAS及最新startup重基由CPU归还后的root负责，f507只是候选历史底座。
'''
(HERE/'SPLIT_ENTRY_HANDOFF_V2.txt').write_text(report,encoding='utf-8')
print(json.dumps({'review_sha256':sha(HERE/'SPLIT_ENTRY_REVIEW_V2.json'),'handoff_sha256':sha(HERE/'SPLIT_ENTRY_HANDOFF_V2.txt'),
 'tests':v2['tests'],'passed':v2['passed'],'producer_manifest_matches':manifest_matches}))
