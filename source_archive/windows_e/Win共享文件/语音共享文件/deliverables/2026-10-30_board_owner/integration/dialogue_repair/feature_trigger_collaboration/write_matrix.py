"""Evidence inventory, with real / synthetic / human status kept separate."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def row(id,request,executor,result,boundary,model,coverage='passed',human=True,gap=None):
    return dict(id=id,public_example=request,actual_executor=executor,expected_real_result=result,
        model_visibility=model,code_or_fake=dict(status=coverage,evidence='candidate_v2/REGRESSION_TESTS.xml'),
        real_execution=dict(status='pending_root_coordinated_test',evidence=None),
        human_acceptance=dict(status='pending' if human else 'not_required_for_this_boundary'),
        boundary=boundary,gap=gap)


def main():
    local='板端直接形成有来源的回执并请求TTS；27B不参与该结果判断，也没有工具调用。'
    private='仅在板端受控流程读取结果；不向27B发送模板、私人库、图库身份ID或授权令牌。'
    rows=[
        row('V01','你现在看到了什么 / 现在镜头前有几个人',
            'paired._route -> LocalVisualQueries -> VisualTimelineWorker.record_current_observation',
            '只能回答新鲜稳定的人体目标总数；无有效观察时明确不能判断。',
            '同boot/相机源与新鲜度、稳定计数、原设备scope和来源依赖保持。',local),
        row('V02','镜头左边有几个人 / 我左边有几个人','paired._route -> LocalVisualQueries',
            '明确没有方位计数能力，不能把整幅总数当左边人数。',
            '目前相机投影不提供方位字段；候选不会从总数推断位置。',local,human=False,
            gap='候选已修正错误总数解释；方位功能本身未实现。'),
        row('V03','你能看见我吗','paired._route -> LocalVisualQueries',
            '不能由人体目标数证明看见提问者本人；说明能力范围。',
            '目标检测不是说话者关联或身份认证。',local,human=False),
        row('V04','我手里是什么颜色的杯子','paired._route -> LocalVisualQueries',
            '明确不能判断任意物品/颜色；不编造所见。',
            '没有Qwen视觉模型；本查询只接人员计数，不泛化YOLO类别能力。',local,human=False),
        row('V05','刚才看到几个人 / 最近五分钟镜头有没有人','LocalVisualQueries -> device history_with_status',
            '按明确时间范围检索真实计数或摘要，并说明限量/跨界/细节不可还原。',
            '历史不成为当前画面；空结果不等于当时没人；不可递归把旧答复当观察。',local),
        row('V06','查询昨天的视觉记录','LocalVisualQueries -> legacy_history + structured history',
            '旧视觉记录单独标明历史；新计数和旧语义记录不混作当前事实。',
            '同device scope；不读取私人对话当摄像头事件。',local),
        row('V07','摄像头断线后现在有人吗','VisualTimelineWorker.current_observation',
            '失效/过期/数量变化尚未稳定时不能判断，不沿用上个计数。',
            '旧缓存、新相机代次、过期帧都不制造无人事件。',local),
        row('I01','我是谁呀 / 我登记过身份吗','LocalIdentityReplies -> original face query/binding proofs',
            '仅同一新鲜可用人脸结果可给镜头内匹配称呼；UNKNOWN不取图库最近姓名。',
            '人脸匹配不等于画外说话者身份；“没认出”不等于“未登记”。',private),
        row('I02','帮我登记身份，我叫测试甲','LocalIdentityReplies -> VoiceEnrollment -> original identity command',
            '先复述姓名并取得明确确认，之后原采样/独立验证与token提交。',
            '仅真实COMMITTED保存回执可播成功；不接受LLM文本当数据库回执。',private),
        row('I03','确认更新登记','Original face enrollment FSM',
            '原ID明确更新确认、图库修订和目标一致性均通过后才允许保存。',
            '不自动重登记、不降原阈值/间隔/独立帧要求。',private),
        row('I04','取消登记 / 无新鲜人脸 / 多人 / 超时','Original face enrollment FSM',
            '取消/失败/目标换代不得保存，失败可解释；原已提交人脸不能虚称回滚。',
            '保留采样时段/来源/同意/活体原有边界；本轮不声称新增防伪认证。',private),
        row('S01','声纹现在可用吗 / 我登记过声纹吗','paired._route -> LocalIdentityReplies -> BoardSpeakerBusiness.turn',
            '读真实本机库/校准状态；有记录但未标定时不宣称当前说话者已登记或已识别。',
            'ready、存在记录、现场标定、确认身份是不同状态。',private),
        row('S02','听声音知道我是谁吗 / 你能通过声音认出我吗','Original speaker/query/proof path',
            '未标定直接说明不能可靠确认；候选/临时代号不能变成认证或个人权限。',
            '原阈值、分差、连续distinct capture和有效期不变；face与voice不自动视为同一人。',private),
        row('S03','记住我的声音，我叫测试甲','paired._route -> original three-utterance SpeakerDevice',
            '真实FSM开始登记，三段不同PCM经原质量/一致性检查；此时仍未保存。',
            '不能被普通记忆指令截走；无真实模板测试仅fake encoder/合成PCM。',private),
        row('S04','确认保存声纹','SpeakerDevice -> original consent/CAS enroll',
            '仅已有有效三段待确认会话才能保存；无待确认会话必须说明没有保存。',
            '同意、库修订、重复/过近模板、超时/取消边界保持。',private),
        row('S05','删除声纹，名字是测试甲 / 确认删除声纹','SpeakerDevice -> original preview/confirm delete',
            '先唯一名字预告并等待明确确认；取消保留模板，过期/无待确认不能虚报删除。',
            '只操作原scope和CAS修订；本窗口从不操作真实库。',private),
        row('S06','帮我登记声纹 / 取消声纹登记','Original SpeakerDevice controlled handler',
            '缺姓名给原流程的明确用法，不虚称开始/保存；取消不保存新声纹。',
            '没有名字/三段/确认不能制造成功。',private),
        row('S07','解释一下登记声纹是什么意思 / 不要识别我的声纹','Narrow full-sentence intent policy',
            '不进入登记/识别执行分支；普通模型也不得声称已有执行结果。',
            '引用、否定、假设和别人说的话不提供执行同意。',
            '没有工具结果，仅原978B设备诚实规则；实际27B公开诊断另列。',human=False),
        row('M01','记住：项目是海风 / 更正 / 忘记','PairedMemoryCommands -> BoardMemoryCommands -> BoardMemoryStore',
            '当前匿名会话明确事实按真实操作结果回答；保留原始输入和来源。',
            '姓名陈述不是身份登记同意；个人范围仍要真实授权。',
            '当前有效明确事实/授权检索文本进入27B；无模板或授权令牌。',human=False),
        row('M02','我们昨天聊了什么','paired._route -> trusted timeline query -> BoardContextBuilder',
            '只有明确历史请求才检索，检索结果标来源/时间/不完整状态。',
            '不能用最近聊天补造过去、把空结果当事情未发生。',
            '本次明确查询的文本摘要与状态进入27B；当前视觉不自动混入。',human=False),
        row('M03','删除昨天的记录 / 确认删除','paired._route -> history_delete_preview (not registered)',
            '当前会失败关闭；没有真正日期预览/删除回执，不得说已删除。',
            '必须保留原范围/预览期限/明确确认，不能直接按日期DELETE。',
            '此路径未执行27B或删除；现役缺口。',coverage='confirmed_missing_handler',human=False,
            gap='候选未实现日期删除预览handler，待根单独集成并验收。'),
        row('D01','帮我计算58乘3','paired._route -> reasoning_dialogue (not registered)',
            '当前命中特殊推理路由会失败关闭，不能作为已接通功能。',
            '不能静默改模型/思考配置冒充完整推理通道。',
            '此路径在27B请求前失败；普通聊天仍走既有模型。',coverage='confirmed_missing_handler',human=False,
            gap='候选未接native reasoning handler，根需按原模型预算另行核对。'),
        row('A01','播放完成 / 取消 / 迟到ACK','BoardDialogueJobs + original player receipt controller',
            '只有完整归属/样本数/哈希/播放token匹配才记助手已播；取消/过期不回写。',
            '半双工与原8帧队列不变；合成ACK不等于扬声器听感。',
            '仅板端已确认历史可参与后续模型上下文。'),
        row('P01','访问个人记忆','LocalProfileSelections + live ProfileAccess grant checks',
            '真实授权才能进入个人scope；撤销后阻止继续生成/播放/写入。',
            '声纹候选、人脸匹配、姓名或LLM文本都不能签发个人grant。',private,human=False),
        row('L01','保持用户手动暂停','Root v16 saved startup/observation + existing preference owner',
            '用户PAUSED/mic=false保持；只有用户要求恢复后才开麦。',
            '本窗口未重启、发布、开麦、播放或改生产参数。',
            '这不是语言模型授权开关。',coverage='root_saved_metadata_only',human=False),
        row('H01','跟随/机械运动','Existing board hardware protection',
            '跟随false、FAULT/null保持；本轮未测运动。',
            '不改boot/FDT/固件/VART/绑定，不绕过保护。',
            '模型没有运动执行权。',coverage='not_executed',human=True),
        row('R01','16fps与长稳/真人听音','Root-only physical acceptance',
            '本轮功能候选没有提供新物理帧率/听音/长稳通过证据。',
            '原未通过门槛保留，不拿短计数/合成PCM冒充。',
            '不涉及模型功能执行。',coverage='not_executed',human=True),
    ]
    save_status=row('S08','你已经帮我把声纹登记保存成功了吗？',
        'paired read-only priority -> LocalIdentityReplies status bypass -> original SpeakerDevice state/actual-commit metadata',
        '登记前无回执仅说不能判断；登记中只读进度不增加样本；实际事务后同actor/版本/60s内回执才可确认本会话已提交。',
        '过期/重启/库改动/取消新尝试/失败事务不留有效成功回执；不能推断未保存，不授予身份或个人权限。',
        '真实状态直接TTS，不让27B猜FSM、不编设置确认流程。',human=True)
    save_status['code_or_fake']['evidence']='candidate_v2/FOCUSED_TESTS.xml'
    rows.append(save_status)
    # A saved root metadata receipt is an actual deployment observation, not
    # actual feature acceptance or permission to resume the microphone.
    next(r for r in rows if r['id']=='L01')['real_execution']=dict(
        status='root_v16_saved_metadata_verified',
        evidence='../paraformer_small_validation/v16_evidence/observation.json',
        limitation='Saved snapshot only; feature chat did not query the live device.')
    for r in rows:
        if r['code_or_fake']['status'] in ('confirmed_missing_handler','not_executed'):
            r['real_execution']['status']='not_accepted'
    matrix=dict(schema='aura.feature-trigger-test-matrix.v2',status='FROZEN_V2_NOT_DEPLOYED',
        latest_candidate='candidate_v2',do_not_integrate_v1=True,
        baseline_startup_sha256='bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c',
        actual_architecture='自然语言请求由板端确定路由和执行，真实结果直接回执或按授权进入模型；没有LLM function calling协议。',
        source_executor_binding='ProductionGuiBoardBusiness -> bind_runtime_pair -> tools.yuki_jobs_candidate._route',
        local_receipt=dict(regression_passed=265,new_focused_passed=16,failed=0,errors=0,historical_tests_deselected=3,
                           persona_fixture_changes='Only public retired character-name literals, no assertion relaxation.'),
        evidence_levels=['real_verified','code_or_fake_verified','human_pending'],
        model_grounding=dict(status='root_actual_partial_failure',script='public_board_probe_v2/worker.py',
            pin='public_board_probe_v2/STAGE_BUNDLE.json',no_feature_chat_inference=True,function_calling_verified=False,
            prior_attempt=dict(evidence='PUBLIC_MODEL_GROUNDING.json',status='transport_peer_denied_from_windows',
                               not_model_or_feature_generation_failure=True),
            focused_fake_transport_tests=dict(passed=2,evidence='public_board_probe_v2/TESTS.xml'),
            actual_public_evidence='PUBLIC_BOARD_GROUNDING_ACTUAL_1793455702380023100.json',
            root_manual_review='ROOT_REVIEW.json',completed_model_requests=4,strict_pass=2,qualified=1,failed=1,
            route_comparison=['PAIRED_ROUTE_BASELINE.json','PAIRED_ROUTE_V1.json','PAIRED_ROUTE_V2.json'],
            note='四题故意绕过板端功能路由；不是4个真实能力PASS。v16的Q2已有声纹路由，冻结v1反而漏Q2；v2本地恢复只读路径，尚未部署或实机复验。'),
        public_human_script='真人联合验收脚本.txt',rows=rows)
    (HERE/'TEST_MATRIX.json').write_text(json.dumps(matrix,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(matrix_rows=len(rows),production_deployed=False,local_passed=265),ensure_ascii=False))


if __name__=='__main__':
    main()
