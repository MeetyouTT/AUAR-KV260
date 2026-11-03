"""Build reviewable local reports and a16fps candidate; never deploy anything."""
from pathlib import Path
import datetime,hashlib,json,shutil,zipfile

ab=Path(__file__).parent;phase=ab.parent;base=phase.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fmt(v):return 'UNKNOWN' if v is None else f'{v:.4f}'
def series(v):return 'UNKNOWN' if not v else f"{v['mean']:.4f} ± {v['sample_std']:.4f}" if v['sample_std'] is not None else fmt(v['mean'])

def main():
    output=ab/'analysis-formal-resume-v3';report=read(output/'analysis.json')
    final=read(base/'evidence/native_integration/paired_ab/formal-resume-v2-final-board-check.json')
    state=read(ab/'isolated-host-state.json')
    stopped=read(ab/('fixture-cleanup-'+str(state['identity']['creation_filetime'])+'.json'))
    assert final['status']=='PASS' and not final['remaining_owned_board_processes']
    assert stopped['status'] in ('EXITED_VERIFIED_OWNED_DIAGNOSTIC_PROCESS','ALREADY_EXITED')
    quality=report['quality'];main_stats=report['main']['metrics'];control=report['same_noJPEG_feature_control']['metrics']
    signals={group:{key:data[key]['descriptive_consistent_cpu_reduction_signal'] for key in ('renderer_cpu_s_s','board_cpu_s_s','board_without_sampler_cpu_s_s')} for group,data in [('main',main_stats),('noJPEG',control)]}
    comparability=report['workload_context_comparability']
    cpu_supported=all(v for group in signals.values() for v in group.values()) and quality['status']=='PASS' and all(v['all_pairs_observed_context_match'] for v in comparability.values())
    recommendation='CPU下降信号在本轮条件下成立，但GPU成本与真实业务并发仍需用户权衡；不自动替换。' if cpu_supported else '暂不建议以节省板端性能开销为理由替换现役形象；CPU收益或工作负载证据未达到本轮预定条件。'
    lines=['雪妃板端替换：正式资源A/B结果',recommendation,
        f"主比较：渲染进程族CPU {main_stats['renderer_cpu_s_s']['new_minus_old_percent_of_baseline_mean']:.2f}%，PSS少{-main_stats['PSS_MiB']['paired_new_minus_old']['mean']:.2f}MiB；新增Mali内存{main_stats['Mali_family_MiB']['candidate']['mean']:.2f}MiB。整板CPU均值差{main_stats['board_cpu_s_s']['new_minus_old_percent_of_baseline_mean']:.2f}%，配对方向不一致，差值波动大于均值差。",
        '技术验证已通过；生产形象未替换。复合资源节省没有定义，不能把CPU、RAM、GPU取舍合成一个收益数字。',
        '\n计量条件：新boot '+final['boot_id']+'；423×438不透明同屏窗口；目标16fps；每轮新进程，预热10秒、稳态60秒；A B B A A B B A C B B C。',
        'A=现役旧remote16完整流程；B=雪妃native16；C=旧流程仅禁诊断JPEG，保留旧渲染、NativePixels/预热、队列、呈现和日志。',
        '现役UI和相机作为共同背景保持运行，额外启动一个隔离测试进程。因此这是相同背景中的增量管线比较，不是生产切换实测。8792/27B/ASR并发未运行，不外推为完整语音业务并发通过。',
        '新方案角色求值与合成均在KV260，符合板端渲染方向；旧基线按当前实际Windows输出RGB的remote16路径测量。网络和Windows减负单列，不替代板端计算收益。不切换当前入口不改变最终业务/渲染归板端的约定。',
        '\n主比较：A四次 / B四次，4个方向配对。数值为均值 ± 样本标准差；CPU单位=秒/秒，4核满载=4；内存=MiB。']
    labels={'renderer_cpu_s_s':'渲染进程族CPU','board_cpu_s_s':'整板CPU','board_without_sampler_cpu_s_s':'整板CPU扣除采样器','PSS_MiB':'进程族PSS','RSS_MiB':'进程族RSS','Mali_family_MiB':'进程族Mali内存','Mali_global_MiB':'整板Mali内存','MemAvailable_MiB':'整板MemAvailable','achieved_fps':'整60秒实测fps','tail_p95_ms':'末239间隔P95毫秒','tail_p99_ms':'末239间隔P99毫秒','xserver_cpu_s_s':'显示服务CPU','camera_cpu_s_s':'相机进程CPU','capture_frames_per_second':'相机capture计数/秒','detected_frames_per_second':'相机detected计数/秒','preview_frames_per_second':'相机preview计数/秒','identity.processed_per_second':'身份处理计数/秒','rx_MiB_s':'网口接收MiB/秒（单列）'}
    for heading,data in [('主比较',main_stats),('双方均无JPEG：C两次 / B两次（末对场景变化，以下仅留存全部数值，不作严格同负载效果估计）',control)]:
        lines += ['\n'+heading,'指标 | 旧基线 | 新方案 | 配对新减旧']
        for key,label in labels.items():
            metric=data[key];lines.append(' | '.join([label,series(metric['baseline']),series(metric['candidate']),series(metric['paired_new_minus_old'])]))
    lines += ['\nCPU方向/波动规则：所有配对差值为负，且差值均值绝对值大于2倍样本标准差；只是n=4/n=2的描述性检查，不代表统计显著性或普遍保证。',json.dumps(signals,ensure_ascii=False),
        '\n命令/PCM/暂停恢复/取消/JPEG/采样与相机连续性逐项验收：'+quality['status']+'。这是功能与采样检查，不能替代跨轮负载一致性。所有原始run保留，失败或UNKNOWN不删除、不重挑好看的运行。',
        '主8项人数均为0、身份处理计数均未增长，4对观察上下文匹配；仅代表无人脸活跃工作场景。',
        '控制第11项观察到1人、身份处理约1.292次/秒，相机CPU约1.250核；配对第12项人数0、身份处理无增量，相机CPU约0.982核。该配对场景不一致，不用于严格同负载因果结论；C/B数值全保留。',
        '第11/12项整板CPU约3.389/3.130核，均高于此前约2.4核。相机与显示CPU升高；结束后1秒快照还观察到现役UI自身约1.146核。后验快照不替代计量期间数据，不能把全部升高归给角色或单个进程。',
        '首对C9/B10均无人脸活跃，但整板CPU新减旧约+0.0941核；只有1对，不能提供重复同场景控制证据。若未来确认CPU收益，应在稳定且代表实际使用的相机场景下重测整个控制块，并增加现役UI进程族CPU观测。']
    for case in quality['cases']:
        bad=[name+':'+check['status'] for name,check in case['checks'].items() if check['status']!='PASS']
        lines.append(f"{case['index']:02d} {case['backend']}: {case['status']}"+('；'+', '.join(bad) if bad else ''))
    lines += ['\n相机帧率由计数差/单调时间差计算，身份计数不增长时仅说明本轮身份负载空闲，不算高人脸负载覆盖。人数与场景变化见analysis.json和quality证据，不能靠低相机负载证明省CPU。',
        'GPU利用率UNKNOWN：debugfs量纲未校准，全零但已知正在GLES渲染时不能写0%负载；Mali内存可读。PSS、GPU/CMA可能重叠，不直接相加。',
        'P95/P99/max是最后239个软件交付/交换间隔（约15秒），并非完整60秒的分位数。平均fps覆盖整段；净目标帧缺口有边界±1误差，不是逐帧槽位drop计数。',
        '旧方案计时在Gst identity入口，新方案在EGL swap完成；二者均非屏幕扫描输出。分别保留presenter dropped/expired、wire discarded、Gst pushed/received和native stale/rejected计数，不加总为一个drop数。',
        'A/C时间相隔且未配对，仅描述性比较；不能给JPEG精确可加贡献。C/B只匹配都不生成JPEG，仍有传输、Gst/队列与EGL、快照节律、旧回退预热等差异，不能声称纯角色算法更快。',
        '冷启动另见runs.csv：新板端进程的哈希/导入/后端初始化到首次观察到交付；Windows独立服务已经就绪，OS页缓存未清空，不是整机冷启动。',
        '\n技术基础：雪妃专用profile、10张原引擎对照/4遮罩、20时间轴待机、实际PCM时钟/暂停/取消、GTK300秒约23.96fps均已验证。鼻部异常白块已修正，保留原素材正常高光。24fps技术测试不能作为16fps之外的资源收益证明。',
        '本轮公开合成PCM经真实GStreamer同步fakesink及48k双声道转换，未输出实体声音。新版业务迁移/完整语音并发/生产单活替换后的整机效果仍需相应验收。',
        '\n结束保持检查：board源10项、286组件pin、启动器/配置、现役UI与相机通过；自有板端测试进程已退出，独立Windows fixture已按创建时间/可执行文件身份退出。测试窗口已释放；不改生产、不自动替换。',
        '\n证据：paired_ab/analysis-formal-resume-v3/{analysis.json,runs.csv}；evidence/native_integration/paired_ab/formal-resume-v2-evidence.zip；候选16fps包内附完整分析源码与原始证据。']
    text='\n'.join(lines)+'\n';(phase/'RESOURCE_AB_REPORT.txt').write_text(text,encoding='utf-8')
    summary=dict(status='RESOURCE_COMPARISON_COMPLETE_NO_PRODUCTION_SWITCH',cpu_reduction_supported_under_declared_rule=cpu_supported,
        cpu_signals=signals,quality_status=quality['status'],composite_resource_reduction_proven=False,workload_context_comparability=comparability,
        recommendation=recommendation,production_deployed=False,measured_fps=16,user_decision_required=True,
        raw_evidence_sha256=final['evidence_sha256'],report='RESOURCE_AB_REPORT.txt')
    (ab/'resource-conclusion-resume-v2.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    verification=read(phase/'verification.json');verification.update(status='TECHNICAL_AND_RESOURCE_VALIDATION_COMPLETE_USER_DECISION_PENDING',resource_reduction_proven=False,
        resource_ab=summary,replacement_decision='PENDING_USER_NO_AUTOMATIC_PRODUCTION_SWITCH')
    (phase/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
    prior=phase/'README-before-final-resource-comparison.txt'
    if not prior.exists():shutil.copyfile(phase/'README.txt',prior)
    (phase/'README.txt').write_text('雪妃板端验证已完成；现役形象未替换。\n'+recommendation+'\n\n先读 RESOURCE_AB_REPORT.txt；完整指标见 paired_ab/analysis-formal-resume-v3/。逐项功能检查PASS，但第11/12对相机场景不一致，详见报告。技术结果见verification.json，原技术说明保存在README-before-final-resource-comparison.txt。候选16fps包供审阅，部署前需针对当时业务源码重新合并两个UI补丁并核验入口。\n',encoding='utf-8')
    entry=base/'README.txt';old_entry=entry.read_text(encoding='utf-8-sig')
    marker='最新：正式12项资源对比已完成，生产形象未切换。先读 native_integration/RESOURCE_AB_REPORT.txt；此前各阶段记录保留为历史。\n\n'
    if not old_entry.startswith(marker):entry.write_text(marker+old_entry,encoding='utf-8')
    resume=phase/'SHUTDOWN_RESUME.txt';old_resume=resume.read_text(encoding='utf-8')
    marker='此断电检查点已接续完成：正式12项资源对比、JPEG控制和清理均完成。以下上电计划保留作历史；最新结果见 RESOURCE_AB_REPORT.txt。\n\n'
    if not old_resume.startswith(marker):resume.write_text(marker+old_resume,encoding='utf-8')
    progress=read(phase/'PROGRESS.json');progress.update(status='VALIDATION_COMPLETE_USER_DECISION_PENDING',updated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),formal_12_case_suite_started=True,
        formal_12_case_suite_complete=True,resource_reduction_proven=False,current_phase=recommendation,known_remaining=['user replacement decision','fresh reviewed merge and production acceptance only if user chooses replacement'])
    (phase/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
    names=['analyze_results.py','quality_checks.py','analysis-policy-resume-v2.json','finalize_resource_report.py','package_resource_candidate.py']
    (ab/'analysis-source-manifest-resume-v2.json').write_text(json.dumps({'schema':'aura.analysis.source_manifest.v1','files':{name:sha(ab/name) for name in names}},indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))

if __name__=='__main__':main()
