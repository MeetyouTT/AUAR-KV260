"""Record the root's actual apply receipt; this script performs no board calls."""
import datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
receipt=HERE.parent/'maintenance_original_axis_20261101/identity_query_applied.json'
original=receipt.read_bytes();wrapper=json.loads(original);value=wrapper['board_result']
assert wrapper['script_sha256']=='0ab6383fd78192a230aaa85a24a6c841d9417586bce28014989d0b795e5af1ae'
assert value['status']=='IDENTITY_QUERY_V2_UPDATED_GUI_STILL_STOPPED'
assert value['source_after_sha256']=='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
assert value['startup_after_sha256']=='0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f'
assert value['component_count_verified']==380 and value['selected_binding_verified'] and value['original_verifier_passed']
assert value['camera_owner_unchanged'] and not value['identity_config_or_database_changed']
status={'schema':'aura-identity-dialogue-collaboration-final-2',
    'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'APPLIED_BY_ROOT_GUI_ACTIVATION_PENDING_SEPARATE_PLATFORM_MAINTENANCE',
    'root_apply_receipt':str(receipt),'root_apply_receipt_sha256':hashlib.sha256(original).hexdigest(),
    'root_apply_completed_utc':value['completed_utc'],
    'source_after_sha256':value['source_after_sha256'],'startup_at_identity_apply':value['startup_after_sha256'],
    'board_actor':'root','board_mutations_by_this_subagent':False,
    'identity_parameters_or_database_changed':False,'runtime_activation_confirmed':False,
    'startup_gui_camera_binding_after_other_maintenance_must_be_refreshed':True,
    'local_validation':{'focused_methods':15,'baseline_failures_including_subtests':19,
        'baseline_errors':0,'candidate_failures':0,'candidate_errors':0,'original_synthetic_regressions_passed':22},
    'independent_review':'../identity_dialogue_review/INDEPENDENT_AUDIT_V2.json',
    'pre_apply_local_bundle':'DELIVERY_MANIFEST_V2.json',
    'remaining':['root normal GUI startup after its separate platform maintenance',
        'fresh complete software-state observation using actual final startup/camera/binding',
        'real known-person recognition and speech collaboration acceptance']}
(HERE/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
text='''身份识别与语言协同 v2 最终接续

root已实际应用v2，真实回执：../maintenance_original_axis_20261101/identity_query_applied.json。
实际status=IDENTITY_QUERY_V2_UPDATED_GUI_STILL_STOPPED，380组件、原selected24pin及原_verify通过，camera1333 owner保持。
源85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809；本次应用时startup0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f。
本子代理没有板端操作；source/backup/receipt由root唯一应用。root已安排GUI继续停着接它负责的转轴平台维护，故当前不声称新GUI运行或真人身份识别验收通过。

修复：声纹登记SAMPLING_VOICE阶段的身份整句问题不会再成为下一段声纹样本；复用现行query_reply完整谓词，包含原两句voice查询，继续原联合resolver。未知/冲突不冒名，候选不等于认证，个人私库grant保持。当前0.50/0.10/3000及所有人脸数据保持。
本地15专项方法+子例全通过，原生产19断言失败/0 errors；原22项合成speaker回归通过。独立v2复核通过。详见HANDOFF_V2.txt和DELIVERY_MANIFEST_V2.json；v1/a94已冻结，不部署。

collect_after_identity_query_v2.py是原过滤reader只改startup常量的草稿，SHA dc5acb3bcf805e9634fd41db5445d31abf3707538bdbbf8c7c05fc56abf3303f；尚未实板运行。
它只适用于本次应用时的0f2a/camera1333/selected4d8上下文。root后续若恢复转轴平台并产生新相机owner/新readback，应按真实最终来源重新派生reader并严格核验，不能只绕过固定断言或把本次中间startup当最终状态。

本次文件修改已解决一个可复现的语言/身份流程串扰；它不会让当时的UNKNOWN自动变KNOWN。已登记人实际在镜头前的识别、真实语音协作及部署后完整GUI状态仍由root接续验收。
'''
(HERE/'FINAL_HANDOFF.txt').write_text(text,encoding='utf-8')
print(json.dumps({'status':status['status'],'handoff':str(HERE/'FINAL_HANDOFF.txt'),
    'root_apply_receipt_sha256':status['root_apply_receipt_sha256']}))
