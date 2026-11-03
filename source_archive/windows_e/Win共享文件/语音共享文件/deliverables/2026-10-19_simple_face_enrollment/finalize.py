"""Finalize only after active-source, deployment and real-voice evidence passes."""
import json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
read=lambda name:json.loads((HERE/name).read_text(encoding='utf-8-sig'))
write=lambda path,value:path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
c=read('candidate.json');d=read('deployment.json');v=read('source_verification.json');p=read('preflight.json')
voice=read('voice_host_probe.json')
assert d['status']=='SIMPLE_ENROLLMENT_DEPLOYED_AWAITING_REAL_USER_VALIDATION'
assert c['tests_passed'] and c['preflight_passed'] and all(p[k] for k in ('real_models_passed','bootstrap_passed','widget_passed'))
assert len(v['active_sources'])==18 and all(v['preserved'].values())
assert v['pc_health']['identity_voice_enrollment']['sampling_guidance_version']==3
assert v['pc_health']['identity_voice_enrollment']['confirmation_before_sampling'] is True
assert voice['status']=='PASS_REAL_ASR_TTS_UPFRONT_PROMPT_AUTOMATIC_RELAY_AND_ORIGINAL_CHAT'
pc_count=int(re.search(r'(\d+) passed',(HERE/'tests_pc.log').read_text(encoding='utf-8-sig')).group(1))
linux_count=int(re.search(r'Ran (\d+) tests',(HERE/'tests_board.log').read_text(encoding='utf-8')).group(1))
c.update(activated=True,deployment_status=d['status']);write(HERE/'candidate.json',c)
summary={'client_date':'2026-10-19','status':d['status'],'active_runtime':c['runtime'],
    'pc_tests_passed':pc_count,'linux_tests_passed':linux_count,'active_sources_verified':18,
    'combined_registration_and_name_supported':True,'upfront_explicit_consent_required':True,
    'replacement_requires_explicit_update_consent':True,'automatic_sampling_validation_and_save':True,
    'no_final_spoken_confirmation_required':True,'automatic_save_bound_to_sample_token':True,
    'only_committed_result_reports_success':True,'uncertain_write_is_not_retried':True,
    'public_image_real_models_passed':True,'fixture_logical_capture_clock':True,'pose_quality_injected':False,
    'actual_asr_tts_host_probe_passed':True,'actual_board_listening_passed':None,
    'actual_user_simple_registration_passed':None,'departure_return_recognition_passed':None,
    'threshold':.85,'ambiguity_margin':.1,'threshold_changed':False,
    'selection_minimum_ms':15000,'ram_maximum_face_candidates':24,'heldout_validation_frames':5,
    'database_revision_before':d['database_revision_before'],'database_revision_after':d['database_revision_after'],
    'registered_count':d['enrolled_count'],'database_hash_unchanged':not d['identity_database_modified'],
    'preserved_source_config':v['preserved'],'photos_exported':False,'templates_exported':False,'video_saved':False,
    'limits':['Simpler enrollment does not prove real-user angle robustness at 0.85.',
              'No liveness or speaker-to-face verification; existing half-duplex voice remains.']}
write(HERE/'verification_summary.json',summary)
write(HERE/'listening.json',{'client_date':'2026-10-19','workflow':'upfront-confirmation-automatic-completion',
    'actual_board_listening_passed':None,'actual_user_simple_registration_passed':None,'departure_return_recognition_passed':None})
previous=HERE.parent/'2026-10-19_natural_face_enrollment'/'verification_summary.json'
old=json.loads(previous.read_text(encoding='utf-8-sig'))
old.update(status='SUPERSEDED_BY_UPFRONT_CONFIRMATION_AUTOMATIC_COMPLETION',
    subsequent_user_feedback='主要是这样的话操作太难了',
    user_selected_start='一句话说帮我登记身份，我叫……',superseded_by=str(HERE/'verification_summary.json'))
write(previous,old)
block=(f'> **2026-10-19 登记操作已简化：** 一句话说“帮我登记身份，我叫……”，玩偶复述后只在开头确认一次，'
    '之后自动选样、验证、保存并播报结果，末尾不再要求确认。保留0.85、明确更新确认及原视觉/语音模型。'
    f'PC{pc_count}项、Linux{linux_count}项、真实模型和语音HTTP预检通过；部署身份库未变，真人简化流程待验证。'
    '[本轮流程、证据与回退](deliverables/2026-10-19_simple_face_enrollment/README.md)。\n\n')
path=ROOT/'README.md';raw=path.read_text(encoding='utf-8-sig')
raw=re.sub(r'^> \*\*2026-10-19 登记操作已简化：.*?\n\n','',raw,count=1,flags=re.S)
path.write_text(block+raw,encoding='utf-8')
instruction=('<!-- simple-face-enrollment-20261019 -->\n'
    '- 2026-10-19用户反馈操作太难，选择一句话“帮我登记身份，我叫……”。已部署简化流程：UI/相机`'+c['runtime']+'`，'
    'PC8792已重载，`sampling_guidance_version=3,confirmation_before_sampling=true`。正式ChannelConversationJobs启用simple模式；'
    '一句话请求和称呼后先复述，再明确确认一次（已有同名需“确认更新登记”），才启动采样。后续自动取样、验证和带采样token提交保存，'
    '不再要求末尾确认或左右/回正口令。授权绑定称呼/原ID/库修订/服务相机/采样token，取消或替换会话不能复用；'
    '只有明确拒绝未提交才等待重试，未知提交结果不重试，匹配COMMITTED才播成功。'
    '上一版自然视频选样15秒/最多24份RAM/后5份0.85及0.1身份间隔保持，固定原始特征恢复核对、DPU/ByteTrack、原27B/ASR/OmniVoice16和参数保持。'
    f'PC{pc_count}项、Linux{linux_count}项、公开单图真实模型开头确认自动写临时库（逻辑时钟、不注入质量）及真实语音HTTP通过。'
    '部署用户库数量/修订/哈希未变，不当真人成功验收；真人简化登记/听音/重返仍待验证。'
    '当前源码默认VoiceEnrollment(simple=False)仅保留旧调用兼容，正式worker明确simple=True，不要误称正式仍需末尾确认。'
    '最新证据和回退`deliverables/2026-10-19_simple_face_enrollment/README.md`及`verification_summary.json`优先于下方旧活动路径。'
    '不保存视频或默认照片、不导出模板，LLM数据仍D盘。\n<!-- /simple-face-enrollment-20261019 -->')
path=ROOT/'AGENTS.md';raw=path.read_text(encoding='utf-8-sig')
if '<!-- simple-face-enrollment-20261019 -->' in raw:
    raw=re.sub(r'<!-- simple-face-enrollment-20261019 -->.*?<!-- /simple-face-enrollment-20261019 -->',lambda _:instruction,raw,count=1,flags=re.S)
else:raw=raw.replace('# 本项目工作约定','# 本项目工作约定\n\n'+instruction,1)
path.write_text(raw,encoding='utf-8')
analysis=ROOT.parent/'语言模型分析'
report=('# 登记操作简化：开头确认后自动完成（2026-10-19）\n\n'
    '用户认为多次指令和采样配合太难，已选择一句话“帮我登记身份，我叫……”。新版先复述称呼，在开头明确确认一次，'
    '然后自动选图、验证、带采样token提交并播报结果，不再要求末尾确认。同名更新仍需明确更新授权。'
    '至少15秒视频选样、0.85门槛、0.1间隔和5份后续独立验证保持；不合格帧由系统等待，确认授权只限本次身份/修订/会话。\n\n'
    f'已加载`{c["runtime"]}`；PC{pc_count}项、Linux{linux_count}项及公开单图真实模型/真实语音HTTP预检通过。'
    f'部署身份库{d["enrolled_count"]}条/修订{d["database_revision_after"]}且哈希未变，真人简化登记、听音和重返仍待实测。'
    '操作简化不能证明任意角度超过0.85。原DPU/ByteTrack、27B/ASR/OmniVoice16和参数保持，不保存视频或默认导出照片。\n\n'
    '[完整流程、证据与回退](../语音共享文件/deliverables/2026-10-19_simple_face_enrollment/README.md)。LLM数据继续在D盘。\n')
(analysis/'登记操作简化实施_20261019.md').write_text(report,encoding='utf-8')
index=analysis/'README.md';raw=index.read_text(encoding='utf-8-sig')
raw=re.sub(r'## 最新：登记操作简化\n.*?(?=\n## |\Z)','',raw,count=1,flags=re.S)
entry=('## 最新：登记操作简化\n\n[登记操作简化实施](登记操作简化实施_20261019.md)：一句话说登记和姓名，开头明确确认一次，'
    f'后续自动取样验证保存。PC{pc_count}项、Linux{linux_count}项及真实模型/语音预检通过，0.85保持，真人流程待验证。\n\n')
index.write_text(raw.replace('# 语言模型分析统一入口\n','# 语言模型分析统一入口\n\n'+entry,1),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
