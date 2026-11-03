"""Collect numeric evidence without accessing devices, databases, or models."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent
SHARE = Path('E:/Win共享文件')
OLD = SHARE/'协作任务/2026-11-02_作品概述_AMD实跑_01a19c53'
EVIDENCE = SHARE/'协作任务/2026-11-02_dual_reports/evidence'
DEPLOY = SHARE/'语音共享文件/deliverables/2026-11-02_5090_deployment'
SOURCES = []
METRICS = []
IDS = {}


def source(name, path, scope):
    data = path.read_bytes()
    sid = f'S{len(SOURCES)+1:02d}'
    SOURCES.append(dict(id=sid, name=name, path=str(path), bytes=len(data),
                        sha256=hashlib.sha256(data).hexdigest(), scope=scope))
    return sid, json.loads(data.decode('utf-8-sig'))


def metric(key, label, value, unit, device, scope, sid):
    assert type(value) in (int, float), (key, value)
    assert key not in IDS, key
    row = 5+len(METRICS)
    IDS[key] = row
    METRICS.append(dict(key=key, label=label, value=value, unit=unit,
                        device=device, scope=scope, source=sid, row=row))
    return key


def main():
    sections = {}
    sid, fpga = source('Vivado与XSim本次实跑', OLD/'RESULT_SUMMARY.json', '2026-11-02重新分析既有最终布线DCP，非本轮完整重建或上板')
    _, resource = source('本次FPGA资源原值', OLD/'resource_metrics.json', '布局布线后静态资源')
    for name, rec in resource.items():
        for attr in ['used','available']:
            metric('fpga_'+name+'_'+attr, name+' '+attr, rec[attr], '个/块', 'Vivado 2022.2', '2026-11-02对2026-10-28最终DCP重新分析', sid)
    for key in ['routable_nets','fully_routed_nets','routing_error_nets','setup_failing_endpoints','hold_failing_endpoints','drc_warning_total','cdc_critical_total','unconstrained_input_ports','unconstrained_output_ports']:
        metric(key,key,fpga[key],'项','Vivado 2022.2','本次重新生成报告',sid)
    for key in ['setup_worst_slack_ns','hold_worst_slack_ns']:
        metric(key,key,float(fpga['tool_metrics'][key]),'ns','Vivado 2022.2','仅已有约束范围',sid)
    for i, width in enumerate(fpga['actual_vcd_measurements']['pulse_width_us'],1):
        metric('pulse_width_'+str(i),'第'+str(i)+'个完整PWM脉宽',width,'µs','XSim 2022.2','本轮RTL仿真，非实板示波器测量',sid)
    metric('pwm_period','PWM仿真周期',fpga['actual_vcd_measurements']['period_ms'][0],'ms','XSim 2022.2','本轮nominal仿真',sid)
    metric('xsim_passed','通过的测试台',fpga['xsim_tests_passed'],'套','XSim 2022.2','本轮4套现有RTL测试',sid)
    sections['fpga'] = fpga

    latency_rows = []
    for name, file, cpu_key, dpu_key in [('YuNet','v04_yunet_board.json','cpu_fp32','dpu_int8_with_cpu_postprocess'),('SFace','v05_sface_three_model_board.json','arm_cpu_fp32','dpu_int8_with_input_output_conversion')]:
        sid, d = source(name+'历史实板固定输入对照',EVIDENCE/file,'KV260，硬件和FP32/INT8同时变化，非本轮模型测速')
        t=d['core']['latencies']
        for precision, key in [('cpu',cpu_key),('dpu',dpu_key)]:
            for stat in ['median_ms','p95_ms','samples']:
                metric(name+'_'+precision+'_'+stat,name+' '+precision+' '+stat,t[key][stat],'次' if stat=='samples' else 'ms','KV260历史实板','固定输入，范围随模型保留',sid)
        latency_rows.append(dict(name=name,cpu=cpu_key,dpu=dpu_key,sample_scope='含预后处理' if name=='YuNet' else '已对齐输入，含输入输出转换'))
        if name=='SFace':
            sections['mixed']=d['core']['mixed']
            for rec in d['core']['mixed']:
                for model in ['yolo','yunet','sface']:
                    if rec.get(model):
                        metric('mixed_'+rec['mode']+'_'+model,'混跑 '+rec['mode']+' '+model,rec[model]['median_ms'],'ms','KV260历史实板','预编码固定输入核心网络调用，非整帧业务耗时',sid)
    sections['latency_rows']=latency_rows

    sid, xir = source('Vitis AI本次XIR解析',ROOT/'vitis_ai_inspection_stdout.json','Ubuntu Vitis AI 3.0本轮只读解析，无DPU推理')
    models=[]
    for label, data in zip(['YuNet','SFace','YOLO官方参考'],xir['models']):
        part=next(p for p in data['partitions'] if p['device']=='DPU')
        models.append(dict(model=label,shape=' × '.join(map(str,part['inputs'][0]['shape'])),dtype=part['inputs'][0]['dtype'],partitions=data['dpu_partition_count'],bytes=data['bytes'],sha256=data['sha256'],fingerprint=part['fingerprint'],deployed_match=label!='YOLO官方参考',source=sid))
        metric(label+'_bytes',label+' 编译文件大小',data['bytes'],'B','Ubuntu XIR','本轮读取文件；YOLO为非现役参考字节',sid)
    sid_yolo, audit = source('现役YOLO模型历史同SHA解析', SHARE/'协作任务/2026-10-26_DPU模型量化核查/evidence/audit.json', '现役YOLO字节与本轮官方参考不同；保留历史板端同SHA信息')
    yolo = audit['models']['yolo']
    yolo_part = next(p for p in yolo['historical_board_xir'] if p['attrs'].get('device')=='DPU')
    deployed_yolo = dict(model='YOLOX-Nano', shape=' × '.join(map(str,yolo_part['inputs'][0]['dims'])),
        dtype=yolo_part['inputs'][0]['type'], partitions=1, bytes=yolo['bytes'], sha256=yolo['deployed_sha256'],
        fingerprint=yolo['deployed_fingerprint'], deployed_match=True, source=sid_yolo, historical_only=True)
    metric('YOLOX-Nano_bytes','现役YOLO编译文件大小',yolo['bytes'],'B','KV260历史同SHA记录','本轮未取回现役字节，不以官方参考替代',sid_yolo)
    sections['models']=[deployed_yolo]+models

    sid, sf=source('SFace公开独立评测',EVIDENCE/'v06_sface_quality.json','1000对主机FP32/INT8模拟，非1000对实板测试')
    for label,key in [('FP32','fp32'),('INT8','int8_simulation')]:
        r=sf['models'][key]['held_out_at_train_selected_threshold']
        for attr in ['false_accepts','negative_pairs','false_rejects','positive_pairs','threshold']:
            metric('sface_'+label+'_'+attr,'SFace '+label+' '+attr,r[attr],'分数' if attr=='threshold' else '对','公开LFW主机评测','训练集选阈值，独立1000对测试',sid)
    sid, yu=source('YuNet量化输出一致性',EVIDENCE/'v07_yunet_quality.json','浮点模型参考，不是人工标注真值检出率')
    r=yu['thresholds']['0.9']
    for k in ['reference_faces','matched_iou_ge_05','images']:
        metric('yunet_agreement_'+k,'YuNet '+k,r['counts'][k],'张/脸','公开输入主机评测','阈值0.9，FP32参考对照',sid)
    for k in ['matched_box_iou_median','landmark_error_pixels_median']:
        metric('yunet_'+k,'YuNet '+k,r[k],'px' if 'pixels' in k else 'IoU','公开输入主机评测','非人工真值AP',sid)

    ui_path=SHARE/'语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101/CURRENT_PUBLICATION.json'
    sid,ui=source('玩偶界面历史前后观察',ui_path,'2026-11-01主页面，暂停聆听及跟随，非严格因果A/B')
    comparisons=[]
    names={'board_cpu_percent_median':'整板CPU中位数','gtk_one_core_cpu_percent_median':'GTK单核CPU中位数','callback_cpu_ms_median':'回调CPU耗时中位数','publish_ms_median':'状态发布耗时中位数','callback_wall_ms_p95':'回调墙钟耗时P95','native_presentations_per_second':'原生呈现帧率'}
    for r in ui['comparison']:
        if r['label'] not in names:continue
        unit='fps' if r['label']=='native_presentations_per_second' else '%' if 'percent' in r['label'] else 'ms'
        comparisons.append(dict(key=r['label'],label=names[r['label']],unit=unit))
        for stage in ['before','after']:
            metric('ui_'+r['label']+'_'+stage,names[r['label']]+' '+stage,r[stage],unit,'KV260历史界面观察','GUI重启及场景变化未受控，不能单独归因',sid)
    for key,field,label in [('callback_max','native_callback_max_ms_before_after','原生绘制最大耗时'),('egl_max','native_egl_bind_max_ms_before_after','EGL绑定最大耗时'),('age_p95','visual_source_age_p95_ms_before_after','视觉源龄P95')]:
        comparisons.append(dict(key=key,label=label,unit='ms'))
        for i,stage in enumerate(['before','after']):metric('ui_'+key+'_'+stage,label+' '+stage,ui[field][i],'ms','KV260历史界面观察','保留变差的尾部指标',sid)
    sections['ui_comparisons']=comparisons

    sid,turns=source('两轮真人对话分段计时',DEPLOY/'dialogue_latency_20261101/TWO_TURN_LATENCY.json','2026-11-02保存的此前boot两轮实测，非新版复验或声学首声')
    stages=['asr_ms','context_ms','llm_rpc_ms','tts_rpc_ms','first_audio_queued_from_worker_ms','capture_complete_to_observed_speaking_ms']
    for r in turns['turns']:
        for stage in stages:metric('turn'+str(r['ordinal'])+'_'+stage,'第'+str(r['ordinal'])+'轮 '+stage,r[stage],'ms','KV260+Windows原模型','完整播放ACK；采集结束至软件SPEAKING，非声学起音',sid)
    sections['dialogue_stages']=stages
    sections['dialogue_turns']=turns['completed_turns']

    sid,asr=source('板端ASR线程描述性对照',SHARE/'语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/performance_review_newboot/asr_threads_v20_r2/ACTUAL_COMPARISON_01.json','每设置4次公开音频解码，背景变化，非严格因果提速')
    for thread,r in asr['aggregates'].items():
        for attr in ['samples','mean_decode_wall_ms','median_decode_wall_ms','aggregate_real_time_factor']:
            metric('asr_thread'+thread+'_'+attr,thread+'线程 '+attr,r[attr],'次' if attr=='samples' else 'RTF' if 'factor' in attr else 'ms','KV260历史独立ASR','不含构造/预热，不含真人录音端点，不是WER',sid)

    sid,run=source('正常业务30秒板端资源',EVIDENCE/'v09_resource_samples.json','2026-10-31原业务播报恢复聆听、跟随关闭；非当前负载')
    for key,label,value,unit in [('cpu_mean','整板CPU平均',run['cpu_average_percent']['cpu'],'%'),('cpu_peak','整板CPU一秒峰值',run['cpu_one_second_peaks_percent']['cpu'],'%'),('dpu_busy_mean','DPU任务忙时平均',run['dpu']['average_busy_percent'],'%'),('dpu_busy_peak','DPU任务忙时峰值',run['dpu']['peak_busy_percent'],'%'),('memory_mean_kib','系统内存平均已用',run['memory']['mean_used_kib'],'KiB'),('memory_min_available_kib','系统内存最低可用',run['memory']['minimum_available_kib'],'KiB'),('resource_duration','采样时长',run['duration_s'],'s')]:
        metric(key,label,value,unit,'KV260历史30秒观察','CPU四核总量100%；DPU为驱动CU忙时',sid)
    sections['resource_series']=[dict(seconds=r['seconds'],cpu_percent=r['cpu']['cpu'],dpu_busy_percent=100-r['dpu'][-1],memory_used_gib=(r['memory_kib']['MemTotal']-r['memory_kib']['MemAvailable'])/1048576) for r in run['samples']]

    sid,llm=source('27B单独准入探针',DEPLOY/'llm_calibration.json','仅1次4-token公开探针，不能代表稳定吞吐或整机对话速度')
    for attr in ['eval_count','prompt_eval_count','eval_duration','total_duration']:
        metric('llm_'+attr,attr,llm['metrics'][attr],'token' if 'count' in attr else 'ns','Windows RTX 5090 Laptop','4-token准入探针；稳定tokens/s待补',sid)
    metric('llm_context_tokens','27B探针上下文长度',llm['context_length'],'token','Windows RTX 5090 Laptop','已记录配置',sid)
    metric('llm_peak_gpu','探针物理显存峰值',llm['physical_peak_used_mib'],'MiB','Windows RTX 5090 Laptop','单模型探针，非联合长稳峰值',sid)
    sections['llm_model']=dict(name=llm['model'],context_length=llm['context_length'],quantization='IQ4_XS',probe_output_tokens=llm['metrics']['eval_count'])
    sid,tts=source('OmniVoice16公开短句校准',DEPLOY/'tts_calibration.json','2次暖态未缓存合成；无板端播放或质量评分')
    samples=[r for r in tts['measurements'] if r['kind']=='uncached_public_tts']
    for i,r in enumerate(samples,1):
        for k in ['seconds','samples','rate']:metric('tts'+str(i)+'_'+k,'TTS样本'+str(i)+' '+k,r[k],{'seconds':'s','samples':'sample','rate':'Hz'}[k],'Windows RTX 5090 Laptop','OmniVoice16，暖态、缓存未命中、未播放',sid)
    sections['tts_count']=len(samples)
    sid,env=source('当前Windows模型主机只读环境',ROOT/'WINDOWS_MODEL_ENVIRONMENT_READONLY.json','本轮GPU与Ollama版本/驻留检查，无新推理')
    metric('gpu_total_mib','当前GPU总显存',int(env['gpu_inventory'].split(',')[-2].strip().split()[0]),'MiB','Windows当前GPU','nvidia-smi本轮只读读取',sid)
    sections['windows_environment']=env

    sid,mem=source('记忆自然保留评估',EVIDENCE/'v10_retention_result.json','存储半段通过，真实摘要召回待验证')
    for key,value,unit in [('memory_before_age',mem['baseline_closed_age_seconds'],'s'),('memory_after_age',mem['after_closed_age_seconds'],'s'),('memory_before_user_rows',mem['baseline_body_rows'][0],'行'),('memory_before_assistant_rows',mem['baseline_body_rows'][1],'行'),('memory_after_user_rows',mem['after_body_rows'][0],'行'),('memory_after_assistant_rows',mem['after_body_rows'][1],'行')]:
        metric(key,key,value,unit,'KV260历史记忆元数据','自然超过五分钟，摘要保留；召回未验收',sid)

    sources_only=[dict(id='TEMPLATE',name='官方技术文档模板',path='C:/Users/REVO1/Downloads/技术文档模板.docx',scope='章节与文字/图片要求')]
    checklist=[
      ['封面','作品名称','必需','使用AUAR·雪妃，避免学校标识','已有名称','文字整理'],
      ['摘要','800字内摘要','必需','概括功能、架构、真实指标和完成范围','已有草稿，需更新最终指标','文字整理'],
      ['1.1','功能与特性400字内','必需，图片可选','功能文字；可配当前角色/字幕及视觉界面','文字已有，当前实屏待采','KV260截图'],
      ['1.2','应用领域400字内','必需，图片可选','桌面交互、展演、教学场景','文字可写；实景照可选','现场拍摄或文字'],
      ['1.3','技术特点400字内','必需','PS/PL/Windows分工、单DPU多模型、监督IP','有架构图及本次原生BD','Ubuntu Vivado'],
      ['1.4','性能指标200字内','必需，建议表格','选5项代表结果，注明测试范围','本工作簿可选取','汇总已有记录及补测'],
      ['1.5','创新点200字内逐点','必需','以对照结果或仿真支持实际实现特点','有历史模型对照及本次RTL仿真','Ubuntu分析与XSim'],
      ['1.6','设计流程200字内','必需，图片可选','研发步骤流程图','已有设计流程图','根据研发记录绘制'],
      ['2.1','系统整体框图及模块关系','必需','相机、板端PS/PL、Windows、音频、屏幕、单轴连接关系','已有工程示意，需与最终版本核对','源码/配置核对绘图'],
      ['2.2.1','硬件整体介绍','必需','硬件清单、型号、接口、供电和各自职责','部分SKU和实物版本待确认','文件核对与实物查看'],
      ['2.2.2','机械设计图','有机械设计时需要','总装、支架、轴线、零点、尺寸和允许行程','最终CAD/手绘尺寸图待补','机械CAD或现场测绘'],
      ['2.2.3','电路模块设计图','必需','信号、电源、地、关键输入输出；可用原理图或接线图','E10约束已核对，实物端子仍待确认','电路资料与实物连线核对'],
      ['2.3.1','软件整体介绍与关键图','必需','板端、Windows、模型服务、界面、数据流','已有主流程图，最终界面待采','代码核对及运行截图'],
      ['2.3.2','软件模块及关键函数流程','必需','视觉、身份、语音、记忆、运动各模块流程和输入输出','已有三条主流程；最终关键函数图需补细化','源码分析与绘图'],
      ['3.1','整机正面和斜45度全局照','必需','整机、开发板、外设、结构和真实运行屏幕','缺当前整机照片','现场相机拍摄'],
      ['3.2.1','机械成果实物照片','按实际机械成果提供','支架、轴承/舵机、底座、固定方式','缺最终装配特写','现场拍摄'],
      ['3.2.2','电路成果实物照片','必需','KV260型号、供电、J2与隔离/供电模块连线','缺可辨端子的实拍','现场拍摄'],
      ['3.2.3','软件成果界面照片','必需','当前角色、字幕、视觉及实际启用功能','历史界面已有，当前版本待采','KV260原生截图及实屏照片'],
      ['3.3','功能与量化性能证据','必需，指标按实现选择','DPU/视觉、交互、资源、控制等实测表和图','已有阶段数据；统一最终版本实测待补','板卡、Windows与Ubuntu分别采集'],
      ['4.1','可扩展之处300字内','必需','以现有架构说明后续可扩展功能','已有草稿，可按最终范围更新','文字整理'],
      ['4.2','心得体会1000字内','必需','真实研发、制作、测试、失败与取舍','已有工程记录，个人经历由队伍确认','研发记录与本人补充'],
      ['5','参考文献不超过20篇','必需','实际用到的官方手册、模型原文和工具资料','已有8项，可按最终引用调整','来源核对'],
    ]
    tests=[
      ['DPU单模型吞吐','KV260，Ubuntu可远程发起','沿用现役联合固件，核对模型SHA和DPU指纹；空闲时测单线程batch1','建议预热20次，测100次，重复3轮','kernel耗时、FPS、P50/P95、线程与batch','当前维护中；不得与相机竞争DPU'],
      ['DPU业务完整耗时','KV260','相同公开输入，分别统计预处理、DPU、后处理','建议100帧及3轮','各阶段耗时和整帧耗时；不以1000/kernel_ms冒充业务FPS','需板卡维护交接'],
      ['三模型调度','KV260','相同输入/人数/负载，对比单模型及三模型同一版本','建议每组60秒、3轮','有效结果频率、P95等待、图龄、超限与丢弃','需板卡交接；保留失败和降级记录'],
      ['现场视觉质量','Ubuntu评估+KV260推理','代表场景人工标注，已登记/未知/多人分开统计','按场景建立独立测试集','YOLO AP/召回、误检；人脸FAR/FRR与样本数','需真实标注；现有FP32一致性不是人工真值AP'],
      ['玩偶界面帧率','KV260','当前主页面，分别记录空闲及语音播放时原生呈现计数','建议各60秒、3轮','真实呈现fps、绘制P50/P95、CPU、字幕和播放完整性','需板卡交接；配置16fps不等于实测16fps'],
      ['LLM稳定吞吐及首token','Windows GPU主机','现役27B及同一参数，公开固定提示，记录首个有效token与末包计数','建议1次预热，10题各3次；冷暖态分组','TTFT、总耗时、输出token、token/s和显存','维护期间暂不加推理负载；4-token旧探针不能代表稳态'],
      ['TTS合成与RTF','Windows GPU主机','同模型/音色/16步，公开短中长句，区分初始化和暖态','建议每长度3次，全部缓存未命中','首PCM/完整合成耗时、音频时长、RTF、显存','不把主机PCM就绪当扬声器首声'],
      ['语音识别与端到端交互','KV260+Windows','公开录音带人工转写；真人录音完整链单列','建议至少10轮，保留错误和取消','CER/WER、ASR耗时、软件起播、完整播放成功率','真实声学首声需要外部声学记录'],
      ['系统资源与稳定性','KV260+Windows','同版完整负载，包含视觉、界面、对话与实际启用任务','建议短窗60秒加持续运行场景','CPU、DPU忙时、内存、GPU、错误和持续时间','短窗数据不能作为多小时稳定性证明'],
      ['记忆召回','KV260业务链','使用公开事实自然超过摘要窗口后追问，记录正确/错误','按实际声明设计问题集','摘要保存与真实召回分别计数','不导出身份模板或私库；跨模态关联已取消'],
      ['转轴量化参数','现场仪器与实物','已有跟随功能获用户验收；若报告要角度/速度数值再测','按实际需要标定','真实行程、角速度、停点偏差和示波器PWM','不重复调参或重开已关闭的跟随功能验收'],
      ['冷启动恢复','KV260','在交接窗口测试正式发布的启动顺序和外设恢复','建议3次完整冷启动','每次READY、相机/音频/界面恢复时间和失败记录','离线65项测试不等于冷启动实测'],
    ]
    output=dict(created_utc=datetime.now(timezone.utc).isoformat(),metrics=METRICS,metric_rows=IDS,
                sections=sections,sources=SOURCES,template_sources=sources_only,
                checklist=checklist,tests=tests,source_scope='本轮新XIR解析与已完成的Vivado/XSim实跑；其余为有条件的历史记录，未访问板卡或发起新LLM/TTS推理')
    (ROOT/'report_data.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'numeric_observations':len(METRICS),'sources':len(SOURCES),'template_items':len(checklist),'test_protocols':len(tests)},ensure_ascii=False))


if __name__=='__main__':main()
