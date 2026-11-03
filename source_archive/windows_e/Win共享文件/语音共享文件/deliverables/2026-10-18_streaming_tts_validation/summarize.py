"""Publish measured evidence only after the original service is verified restored."""
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ANALYSIS=ROOT.parent/'语言模型分析'

def read(path):return json.loads((HERE/path).read_text(encoding='utf-8-sig'))
def main():
    restored=read('selected-pipeline/restored.json')
    assert restored['status']=='PASS_ORIGINAL_RESTORED_ACTUAL_CHANNEL'
    assert all(restored['protected_source_checks'].values())
    baseline=read('baseline_channel.json')
    vulkan=read('streaming.json');cuda=read('cuda/streaming.json');content=read('cuda/audio_content.json')
    variants={name:read('cuda-cli-validated/'+name+'/quick_content.json') for name in ('f16_no_flash','f16_flash')}
    phase_cases={name:len(value['cases']) for name,value in variants.items()}
    passed=[name for name,value in variants.items() if value['passed_content']]
    selected_content=read('selected-pipeline/audio_content.json')
    pipeline=read('selected-pipeline/pipeline.json') if (HERE/'selected-pipeline/pipeline.json').exists() else None
    complex_result=read('selected-pipeline/complex_llm.json')
    pipeline_content=read('selected-pipeline/pipeline_content.json')
    listening=read('listening.json')
    summary={'status':'CANDIDATE_REQUIRES_REVIEW' if passed else 'VALIDATED_NO_VOICE_CANDIDATE_ADOPTED','production_changed':False,'actual_physical_playback_tested':False,'original_model_sha256':restored['model_sha256'],'source_files_unchanged':len(restored['protected_source_checks']),'baseline_first_pcm_ms':[t['first_pcm_ms'] for t in baseline['turns']],'baseline_actual_asr_llm_tts':True,'vulkan_valid_cases':len(vulkan['cases']),'vulkan_early_stop':True,'cuda_valid_cases':len(cuda['cases']),'cuda_content_cases':len(content['cases']),'cuda_content_error_rate_range':[min(r['character_error_rate'] for r in content['cases']),max(r['character_error_rate'] for r in content['cases'])],'cuda_precision_variant_cases':phase_cases,'cuda_precision_variants_passed_content':passed,'restored_first_pcm_ms':restored['channel']['turns'][0]['first_pcm_ms'],'camera_pid':restored['board']['camera']['pid'],'target_5090_tested':False,'stable_3s_end_to_end_verified':False}
    (HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 27B保持不变：原生流式语音验证（2026-10-18）','','本轮完成Windows本机独立验证，正式服务仍使用原27B/IQ4_XS与OmniVoice16，未切换语音引擎。当前硬件为RTX 5060 Ti 16GB；没有RTX 5090 Laptop 24GB的实测结果。','','## 结论','','CUDA低首包与有效可懂的回答必须同时成立。当前候选还没有通过全部验收，不能据此宣称稳定3秒或将其接入正式玩偶。','','## 当前正式链路','','历史真实录音通过正式ASR→27B→OmniVoice16，3次主机首PCM为'+ '、'.join(f"{t['first_pcm_ms']/1000:.3f}秒" for t in baseline['turns'])+'，三次均非TTS缓存。首轮准备开销更大，回复措辞不同；不是固定文本的因果性能对照，也没有测扬声器声学开口。当前结果说明波动仍在，不能只取最快一次。','','## 独立语音候选','','原27B与原参考音频保持。CosyVoice3语音候选使用Q8 GGUF与INT8参考前端；变更的是独立TTS候选，未改27B权重、量化、上下文、思考预算或人设。全部候选权重与下载分段在 `D:/AIModels/cosyvoice3-streaming-validation`。','','| 配置 | 已完成样本 | 实测 | 处理 |','|---|---:|---|---|']
    for name,key in (('整段返回','0'),('25-token分块','25'),('50-token分块','50')):
        row=vulkan['summary'][key]
        lines.append(f"| Vulkan，{name} | {row['n']} | 首PCM中位数{row['first_pcm_median_ms']/1000:.3f}秒；连续播放最早开始估算{row['continuous_start_median_ms']/1000:.3f}秒 | 延迟不合格 |")
    lines+=['','Vulkan共6条完整样本，内容ASR筛查均无字词差异。25与50两种分块都明显超标，因此在原定12次ABBA完成前主动停止，未继续做该配置的27B完整联动；不声称完整12次已执行。','',f"CUDA默认配置完成12次交错合成。25-token分块的4次首PCM中位数为{cuda['summary']['25']['first_pcm_median_ms']/1000:.3f}秒，按到达轨迹估算不需额外等待以防断流。但其中6条内容筛查的字错误率为{summary['cuda_content_error_rate_range'][0]*100:.1f}%–{summary['cuda_content_error_rate_range'][1]*100:.1f}%，与输入明显不符，直接排除，未执行后续27B联动。速度不能作为可用语音成绩。",'','### 高精度缓存与注意力诊断','']
    for name,value in variants.items():
        status=read('cuda-cli-validated/'+name+'/candidate_status.json')
        lines.append(f"- {name}：实际K={status['k_cache_type']}、V={status['v_cache_type']}，LLM/Flow FlashAttention={status['llm_use_flash_attn']}/{status['flow_use_flash_attn']}；{len(value['cases'])}条音频的字错误率为"+'、'.join(f"{r['character_error_rate']*100:.1f}%" for r in value['cases'])+'；'+('内容初筛通过，详见该目录扩展测试，尚不能替代听音。' if value['passed_content'] else '内容未通过，不采用。'))
    selected=read('cuda-cli-validated/f16_no_flash/streaming.json')
    lines+=['','### 保留的25-token流式配置','','关闭两处FlashAttention、实际K=F16/V=F32时，已完成12次合成交错对照。其中25-token模式4次首PCM为'+ '、'.join(f"{r['first_pcm_ms']/1000:.3f}秒" for r in selected['cases'] if r['chunk_tokens']==25)+'。四次到达轨迹均未显示需额外预缓冲以防断流，这只是主机到达估算，不是板端播放验证。','','扩展内容筛查发现整段返回及其他分块仍有词差异，不能把某个配置的初筛通过推广到所有输出模式。因此只保留25-token模式，另外重测该模式全部4条音频，字错误率为'+ '、'.join(f"{r['character_error_rate']*100:.1f}%" for r in selected_content['cases'])+'。相同文本两次PCM哈希一致，内容重测仍不代替听音。']
    summary['selected_stream_content_cases']=len(selected_content['cases'])
    summary['selected_stream_content_errors']=[r['character_error_rate'] for r in selected_content['cases']]
    if pipeline:
        summary['selected_pipeline_status']=pipeline['status']
        summary['selected_pipeline_first_pcm_ms']=[r['first_pcm_from_input_ms'] for r in pipeline['cases']]
        lines+=['','### 原27B联动','','以下为独立通道的“输入文本→主机首音频”，不含ASR、录音结束判定、网络到板端或扬声器开口。保留原27B、原上下文与复杂问题768 token预算；不以等待提示计时。','','| 输入 | 模式 | 首PCM | 连续播放最早开始估算 | 回复 |','|---|---|---:|---:|---|']
        for row in pipeline['cases']:
            lines.append('| '+row['input']+' | '+row['route']['mode']+f" | {row['first_pcm_from_input_ms']/1000:.3f}秒 | {row['continuous_start_from_input_ms']/1000:.3f}秒 | "+row['reply']['reply_text'].replace('|','/')+' |')
        lines+=['','这不是正式界面全链路验收，无法据此承诺稳定3秒，尤其不能保证所有复杂问题。']
    summary.update(status='PROMISING_STREAMING_VOICE_NOT_PRODUCTION_READY',sample_listening=listening['user_answer'],production_voice_switched=False,native_reasoning_first_answer_text_ms=complex_result['first_answer_text_ms'],native_reasoning_spoken_ready_ms=complex_result['spoken_field_ready_ms'],reasoning_test_expected=174,reasoning_test_observed=156,reasoning_test_correct=False,pipeline_content_screen=pipeline_content,model_hash_method=restored['model_hash_method'])
    lines+=['','### 明确思考路由与实际联动内容','','前面的商品问句被现有规则路由为chat，不能算作复杂推理测试。另测“'+complex_result['input']+'”，确认为reasoning并保留原768 token预算：首个答案文字'+f"{complex_result['first_answer_text_ms']/1000:.3f}秒，完整台词字段{complex_result['spoken_field_ready_ms']/1000:.3f}秒。"+'此项仅测27B，不含候选TTS。','','该次27B最终回答为：“'+complex_result['reply']['reply_text']+'” 正确结果应为174，而它给出156。这是保留原模型下暴露的实际错误，不能将开启思考等同于结果正确，不能掩盖为通过；需要后续增加算术工具校验。','','三条实际联动音频再次送入ASR，原始字错误率为'+ '、'.join(f"{r['character_error_rate_raw']*100:.1f}%" for r in pipeline_content['cases'])+'。其中有“什么/傻瓜”的转写差异及“三件58元/三千五十八元”的数字边界问题；ASR差异本身不证明TTS一定改词，需针对这些实际音频听音并校验语义。不能只凭两条固定台词的零错误率就判断所有自由回复可靠。','','### 用户听音','','用户已明确反馈候选 `quick-1.wav` “接近原声线，听感自然”。这是该样本声线与自然度通过，不覆盖另外三条自由回复、玩偶实际播放、复杂问题或完整链路延迟。正式声线没有切换。']
    (HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines+=['','候选将请求的F16值缓存自动提升到F32，本轮直接记录实际K/V精度。更早的动态接口诊断及首轮CLI诊断在配置校验阶段退出，没有生成有效诊断音频，未被计作性能或质量失败样本。对应日志保留在 `cuda-variants` 和 `cuda-cli-matrix`。','','最初文档字段不一致导致的一轮WAV返回已中止并归档 `invalid_wav_contract_attempt`，全部排除。有效测试明确请求 `format=pcm`、校验 `audio/pcm` 并拒绝容器头，不把HTTP/WAV头计为开口。','','## 恢复、限制与后续','','已等待正式8792真实就绪，核对62个原文件和27B权重SHA256，执行真实ASR→27B→OmniVoice16通道。最后恢复验证主机首PCM为'+f"{summary['restored_first_pcm_ms']/1000:.3f}秒。"+'板端相机健康、YOLO/DPU错误字段为空；相机PID='+str(summary['camera_pid'])+'。未改板端程序、视觉模型或FPGA。没有新增玩偶实际播放；新增的是电脑端候选样本试听，用户已接受该样本，不沿用历史听音作为本轮完整链路验收。','','声音内容正确并不等于汐蓝声线相似或语气自然；这些必须试听。复杂问题保留原推理预算，不把等待提示算作答案。未通过内容筛查的输出模式不用于27B联动；只对25-token模式单独验收。','','默认CUDA量化缓存/注意力组合的异常与该移植项目记录的问题表现相似，但尚未定位到具体内核；更高精度缓存并关闭FlashAttention后，选定流式模式已改善。源码构建的CUDA后端或官方CosyVoice实现保留为后续备选，不能认定所有CosyVoice实现都失败。当前未进行这些构建或WSL系统改造。','','5090笔记本需要目标机器实测功耗、显存峰值、冷热启动、50轮p50/p95、物理扬声器开口、长句断流、插话与声线。`5090_validation_profile.json`只提供待执行配置，不能将5060 Ti或项目宣传数字视为5090成绩。','','## 证据与来源','','完整证据：`E:/Win共享文件/语音共享文件/deliverables/2026-10-18_streaming_tts_validation`。结果JSON、PCM/WAV、命令、服务日志、模型/源码哈希及未计入的失败尝试均保留；没有复制LLM权重、私钥或虚拟环境到共享目录。','','[CosyVoice.cpp](https://github.com/Lourdle/cosyvoice.cpp)、[接口实际实现](https://github.com/Lourdle/cosyvoice.cpp/blob/v0.2.0/tools/server/cosyvoice-server-webui.cpp)、[预编译CUDA类似问题](https://github.com/Lourdle/cosyvoice.cpp/issues/15)、[固定语音资源](https://huggingface.co/Lourdle/Fun-CosyVoice3-0.5B-2512-GGUF/tree/ab01740bbbfcc059fd748163787554f7c8977e64)。']
    lines+=['','恢复时原权重已在紧邻的上一阶段完整计算SHA256。最终阶段只对该权重进行推理读取，因此复用那次已验证哈希，同时复核文件大小、修改/创建时间、文件标识均未变；方法及原证据路径记录在 `selected-pipeline/model_hash_reuse.json`，没有冒充又一次完整读取。最终62个原文件的哈希逐一重新校验。','','后续优先事项：先处理数字/单位边界及自由回复内容校验，再减小27B台词就绪时间和与TTS联动的GPU等待；候选保留为独立试验，完整玩偶集成与实际听音另行验收，不将本轮样本试听升级为正式上线。']
    (HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    path=ANALYSIS/'27B原生流式语音实测_20261018.md'
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (HERE/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))

if __name__=='__main__':main()
