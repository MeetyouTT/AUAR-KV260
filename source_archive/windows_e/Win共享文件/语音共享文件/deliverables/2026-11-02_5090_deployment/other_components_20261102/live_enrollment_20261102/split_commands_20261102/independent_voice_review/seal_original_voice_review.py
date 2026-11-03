import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent
RUNTIME=HERE.parents[1]/'start_sync_fix/candidate_runtime'
files=('tools/speaker_device.py','common/feature_intents.py','common/speaker_identity.py','board/identity/store.py',
       'board/runtime/board_speaker_business.py','board/runtime/board_business.py','tools/binding_hub_runtime.py')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cases=list(ET.parse(HERE/'ORIGINAL_VOICE_CONTRACT.xml').iter('testcase'))
assert len(cases)==24 and all(c.find('failure') is None and c.find('error') is None for c in cases)
result=dict(status='ORIGINAL_PUBLIC_CONTRACT_REVIEW_COMPLETE_SPLIT_CANDIDATE_NOT_YET_REVIEWED',
    public_local_sources={name:sha(RUNTIME/name) for name in files},tests=dict(total=24,passed=24,failed=0),
    tests_sha256=sha(HERE/'test_original_voice_contract.py'),xml_sha256=sha(HERE/'ORIGINAL_VOICE_CONTRACT.xml'),
    original_start_commands=['登记声纹','帮我登记声纹','注册我的声纹'],
    named_start_example='帮我登记声纹，我叫某某',save_command='确认保存声纹',
    original_sample_contract=dict(start_utterance_is_sample=False,count=3,distinct_raw_pcm_sha256=True,
        sample_rate=16000,channels=1,bits=16,min_recording_seconds=3,max_recording_seconds=20,
        minimum_vad_seconds=2.5,vad='webrtcvad mode2 30ms',window_seconds=180,
        final_confirmation_required=True,voice_gallery_revision_cas=True,automatic_profile_access=False),
    same_name_policy='No automatic update: new UUID at save; close-existing score refuses new template; far voice can create another identity with identical display name.',
    split_requirements=['Intercept explicit modality before unified route or SpeakerDevice.turn',
        'Face-only must not call voice turn, open speaker samples, or create unified link attempt',
        'Voice-only should call original business.turn with audio owner and unmodified PCM, without visual/gallery gate',
        'During active voice sampling, explicit face command must not become a voice sample',
        'During active face sampling, explicit voice command must not silently cancel or supersede face',
        'Arbitrary intended voice sample followups must continue original speaker session; combined public.active alone does not distinguish voice from unified',
        'Same name across face/voice does not authorize automatic cross-modal link or grant',
        'Keep c514/01b NoSpeech handling; preserve true service failure, explicit cancel, conversation switch and original expiry cleanup'],
    known_boundaries=['Recognized original speaker status questions never consume sample; unrecognized wording may count as ordinary voice sample during samples stage',
        'Independent original voice save can work uncalibrated but must not claim verified current speaker',
        'Business.turn after_original_voice_turn reconciles existing links and control evidence; it does not create new cross-modal links',
        'Original reset clears standalone speaker sessions and save receipts; 30s audio-session silence and true error cleanup remain relevant'],
    board_actions=False,ssh_calls=False,real_private_store_reads=False,model_or_device_initialization=False,
    production_changes=False,split_candidate_changes=False,
    limitations=['Tests use the real original FSM with RAM synthetic store/encoder/VAD; no model accuracy or field quality claim',
        'Local source SHA records are provenance; root must CAS against latest production pins before any deployment',
        'This report does not approve the not-yet-present split entry candidate'])
(HERE/'ORIGINAL_VOICE_REVIEW.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report='''原独立声纹流程审查及合成测试已完成，24项全过；尚未审入口拆分候选。

原口令：裸“登记声纹”“帮我登记声纹”“注册我的声纹”会提示带姓名重新说，并不建立待姓名状态或开始采样。可直接说“帮我登记声纹，我叫某某”。开场命令本身的PCM不计样本，接着原SpeakerDevice收到三段不同原PCM SHA的语音。默认原质量边界是16kHz单声道PCM16、每段3–20秒，其中WebRTC mode2/30ms判断的有效语音至少2.5秒；提示建议每段3–10秒。三段还需原向量一致性通过，随后明确说“确认保存声纹”才提交；“确认登记”“好的”“确认”都不能替代。原session窗口180秒，写入保留声纹库revision CAS和max32。

同名不等于更新。原SpeakerDevice保存每次生成新UUID，并不按display_name寻找替换ID；与已有voice过于接近则拒绝新增，距离较远可以出现同名另一条目。不能承诺“同名自动更新”，更不能因此替换原voice或把face名自动绑到voice。原删除同名选择还要求唯一对应，因此多个同名也会拒绝含糊删除。

无视觉边界：SpeakerDevice.turn只有meta/text/pcm，原BoardSpeakerBusiness.turn也没有visual参数。可在原有效audio owner、对话scope、deadline、generation检查下独立采样保存，不需要face1或face KNOWN。独立voice保存不发profile grant，未校准时不能把样本保存宣称为已确认说话者；即使匹配提示名字，也不会自动开放私人记忆。business.turn后的after_original_voice_turn只校对已有derived voice引用、记录原控制证据，不创建新的跨模态关联。不可为独立voice入口调用unified route/FaceExchange或同名自动关联。

最小入口建议：先识别显式模态，再调用任何business.route/turn。faceonly走原face flow，voiceonly及其后续三段走原business.turn。另一模态已active时应明确忙/要求先完成或取消，不能把另一模态口令吞成voice样本，也不能隐式取消正在进行的face。原business.public.active合并了speaker.sessions和unified router active/name_waiting，不能当成精确的standalone voice active。

已复现串扰反例：原SpeakerDevice的samples态将未识别为query/start/cancel/delete的普通句作为采样；直接把“登记视觉，我叫合成视觉”交给它，会增加一个voice样本。这说明分流必须发生在原turn之前。原认可的状态问句如“查询声纹保存状态”不会消费样本；“声纹登记好了么”不属于现窄规则，active时可能成为普通采样，不宜在现场建议使用。此审查不扩展任何口令解析规则。

意外reset：原Recording.cancel/_auto_fail及select_conversation/profile调用reset_enrollment，继而LocalIdentityReplies.reset同时清face flow和business；business.reset会清独立speaker.sessions和save_receipts。刚部署的c514/01b NoSpeech修复避免真空识别走此清理，但真服务故障、明确暂停/取消、30秒audio会话静音关闭仍保持原清理语义，不应顺手移除。

测试覆盖：原口令及带姓名start、开场不计样本、三独立SHA、重复PCM拒绝、2.5秒总录音不足、3秒录音中2.49秒有效拒绝/2.52秒接受、query不采样、不一致向量失败、严格最终确认、同名近声拒新增/远声新ID、取消/180秒过期、原request幂等。测试只在RAM使用合成store/encoder/VAD和生成PCM，无SSH、设备、相机、真实库、原录音或模型访问；没有修改生产或其它代理候选。
'''
(HERE/'ORIGINAL_VOICE_HANDOFF.txt').write_text(report,encoding='utf-8')
print(json.dumps({'review_sha256':sha(HERE/'ORIGINAL_VOICE_REVIEW.json'),'handoff_sha256':sha(HERE/'ORIGINAL_VOICE_HANDOFF.txt'),'tests':24,'all_pass':True}))
