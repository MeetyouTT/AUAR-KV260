"""Freeze local review inputs; does not contact or control the board."""
import ast,datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=HERE.parent
reader=OUT/'parallel_platform/gui_startup_review/collect_gui_post_start_metadata.py'
assert hashlib.sha256(reader.read_bytes()).hexdigest()=='654fa4eaee282d7c85b60d66a89df4ed732e5fe8cc60b7c584c50e6e12575824'
old='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
new='0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f'
text=reader.read_text(encoding='utf-8');assert text.count(old)==1
text=text.replace(old,new);ast.parse(text)
target=HERE/'collect_after_identity_query_v2.py';assert not target.exists();target.write_text(text,encoding='utf-8',newline='')
path=HERE/'SOURCE_MANIFEST.json';manifest=json.loads(path.read_text(encoding='utf-8'))
manifest.update(status='LOCAL_V2_VERIFIED_INDEPENDENT_REVIEW_PASS_ROOT_APPLY_PENDING',
    verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    validation={'focused_test_methods':15,'baseline_failed_assertions_including_subtests':19,
        'baseline_errors':0,'candidate_failed_assertions':0,'candidate_errors':0,
        'original_synthetic_speaker_regressions':22,'original_regression_failures':0,
        'independent_v2_audit':'../identity_dialogue_review/INDEPENDENT_AUDIT_V2.json'},
    staged_apply_draft='APPLY_DRAFT_V2.json',board_modified=False)
path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
handoff='''身份识别与语言协同修复 v2（本地验证完成，实际应用由root唯一执行）

问题：统一身份关联处在SAMPLING_VOICE时，“我是谁”“听声音我是谁”“你认识我的声音吗”等原本支持的整句查询会先落入声纹三段采样，改变下一段采样状态；身份问题未进入既有联合解析器。

修复仅修改tools/unified_identity_binding.py一处6行分支。SAMPLING_VOICE中直接复用原tools.provisional_voice.query_reply(text,{'state':'UNKNOWN'})的纯整句判断，将查询返回ordinary，再由原BindingHubRuntime._identity_query处理。没有直接用人脸代替联合resolver；冲突不报姓名、未标定声纹仍是候选、可见人脸不证明说话者、个人档案授权规则保持。
普通声纹样本、明确保存/取消、face确认阶段、引用/否定/嵌句、同request缓存及内容变化拒绝都保留原路径。

v1/a94使用较窄共享face谓词，独审证实遗漏两句原voice查询。v1源码、测试和日志原字节保留在v1/，不得部署v1。v2复用现行hub自身谓词，避免两处语法漂移。

有效验证：15个专项测试方法及自然句子子例；原生产19个断言失败/0 errors，v2全部通过。原22项speaker/board-speaker合成回归全部通过。使用已核SHA的公开源码、合成PCM/身份、假编码器及新临时SQLite，没有模型/设备/真实库访问。早期fixture缺device.key的调试错误不计入产品失败；有效基线是BASELINE_QUERY_TESTS_V2.log。
独立复核：../identity_dialogue_review/INDEPENDENT_AUDIT_V2.json。只有本单文件router/hub和原speaker范围通过这些测试，不冒充全项目真人、ARM或识别准确率验收。

源前SHA f083fe8b618f4b09dce1587b3c32bf47f92510948e728615ce989ef31a1757cf
源后SHA 85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809
startup前 3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591
startup后 0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f
仅这一个component pin改变；GUI配置fc21、默认14pin e203、实际selected24pin4d8、camera1333/birth2359及原Native均保持。

应用草稿：apply_identity_query_v2.py，阅读模板apply_identity_query_v2.template.py，哈希见APPLY_DRAFT_V2.json。默认dry-run也要求GUI已正常停到inactive/dead/MainPID0/noJob且保存listening=false；脚本不暂停/停止/启动任何服务。root先正常结束这两轮测量并暂停聆听，确认无播放/待处理，再正常stop GUI；确认关闭完成后，根审阅草稿并经既有可信SSH送入python3 -B -，显式参数--apply-identity-query-v2才写。
脚本核同boot、前startup/full380/原源、当前相机owner、GUI配置、selected24pin及原_verify；独占备份原字节，原子CAS替换源和startup单pin；写后全380/24pin/相机推进，失败只在相同owner和精确新字节下CAS恢复，不强杀或清锁，不start。
事务目录 /home/root/aura-5090-recovery-20261102-903cfade/identity-query-sampling-v2；目录已存在或任一阶段未知时先读transaction与实际文件，不重发apply。

恢复GUI由root单独正常start。collect_after_identity_query_v2.py仅从原654fa4...过滤读回改一个startup常量，输出16项软件判定、当前owner/帧推进/PAUSED micfalse/noPlaying、原机械FAULT锁定和无寄存器映射。这个新reader尚未实板运行；它是给实际应用后的root使用的只读验证入口。

本修复不会让当前UNKNOWN自动变KNOWN；识别人脸仍需现场已登记对象、原0.50/0.10/3000参数及原目标/TTL验证。root已查明0.50更新旧0.85要求，候选未改配置、重新登记、写人脸库或读真实身份资料。未处理转轴平台或声纹现场标定。
'''
(HERE/'HANDOFF_V2.txt').write_text(handoff,encoding='utf-8')
files=['candidate/tools/unified_identity_binding.py','CANDIDATE.diff','SOURCE_MANIFEST.json',
    'PREDICTED_STARTUP_V2.json','BASELINE_QUERY_TESTS_V2.log','CANDIDATE_QUERY_TESTS_V2.log',
    'ORIGINAL_REGRESSION_V2.log','ORIGINAL_REGRESSION_V2.xml','REGRESSION_INPUTS_V2.json',
    'apply_identity_query_v2.py','apply_identity_query_v2.template.py','APPLY_DRAFT_V2.json',
    'collect_after_identity_query_v2.py','HANDOFF_V2.txt','test_identity_query_isolation.py']
delivery={p:{'sha256':hashlib.sha256((HERE/p).read_bytes()).hexdigest(),'bytes':(HERE/p).stat().st_size} for p in files}
(HERE/'DELIVERY_MANIFEST_V2.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'handoff':str(HERE/'HANDOFF_V2.txt'),'files':len(delivery),
    'post_reader_sha256':delivery['collect_after_identity_query_v2.py']['sha256'],'actual_board_execution':False}))
