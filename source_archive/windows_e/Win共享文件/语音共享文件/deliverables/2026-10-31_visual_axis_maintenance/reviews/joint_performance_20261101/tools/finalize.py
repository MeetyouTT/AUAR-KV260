"""Summarize already-saved baseline receipts and publish local pointers, with no device access."""
from pathlib import Path
import hashlib
import json
import statistics
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parents[1]
TASK=HERE.parents[1]
PROJECT=TASK.parents[1]
OWNER=PROJECT/'deliverables/2026-10-30_board_owner'

def load(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode())
def replace(p,v):
    tmp=p.with_name(p.name+'.joint-tmp');save(tmp,v);tmp.replace(p)
def triplet(v):return f"{v['median']:.2f} / {v['p95']:.2f} / {v['maximum']:.2f}"

def main():
    assert not (HERE/'HANDOFF.json').exists()
    baseline=HERE/'evidence/baseline_1793532356967963000.json'
    roles_path=HERE/'evidence/process_roles_1793532468100081700.json'
    assert ref(baseline)['sha256']=='e3310917239f647cd17427471c02d6ff4645f4f41383314303bb09ec82349272'
    assert ref(roles_path)['sha256']=='abf625ab294c34c921b3928e7ce6c91df35f03efc7730b9a6353c5939dd5960d'
    envelope=load(baseline);data=envelope['result'];summary=data['summary'];rows=data['samples']
    assert data['status']=='COMPLETE' and len(rows)==31
    assert data['before']['owners']==data['after']['owners']
    assert data['before']['state']['page']==data['after']['state']['page']=='main'
    assert all(r['state']['following'] is False and r['state']['readback']['flags']==0 and r['state']['readback']['lease_left_ms']==0
               and r['state']['listening_state']=='PAUSED' and r['state']['microphone_open'] is False and r['state']['playing'] is False for r in rows)
    names={'430894':'相机','496785':'监督进程','496789':'GTK（含业务/暂停音频逻辑）',
           '496791':'multiprocessing资源追踪','496818':'GStreamer音频工作进程',
           '496871':'板端音频前端进程','574018':'multiprocessing.spawn子进程（具体工作职责未知）'}
    for row in load(roles_path)['result']['processes']:
        fp=row['fingerprint'];pid=str(fp['pid'])
        assert all(r['processes'][pid]['birth_ticks']==fp['birth_ticks'] for r in rows)
    observer_core=sum(r['observer']['cpu_ms'] for r in rows[1:])/1000/summary['elapsed_seconds']*100
    model_rows=[r['model_health'] for r in rows]
    assert all(m['available'] for m in model_rows)
    model_counts=[m['metrics']['counts'] for m in model_rows]
    model_admissions=[m['metrics']['backend']['gpu_coordination']['counts'] for m in model_rows]
    derived=dict(
        process_role_mapping=names,
        audio_process_pids_verified=[496818,496871],
        audio_classifier_correction='The baseline automatic audio name filter missed gstreamer_audio_worker.py and board_frontend_process.py. Both were already included in all 31 process resource samples as owned_child; the post-window fingerprint receipt classifies them. An empty automatic audio list does not mean no audio process.',
        dedicated_business_cpu=None,gtk_shared_business_and_audio_cpu=True,
        dedicated_memory_rejection_count=None,memory_discarded_is_not_rejection_count=True,
        observer_cpu_one_core_percent=observer_core,observer_cpu_all_four_cores_share_percent=observer_core/4,
        observer_included_in_board_cpu=True,observer_cost_is_not_negligible=True,
        accepted_llm_first=model_counts[0]['accepted_llm'],accepted_llm_last=model_counts[-1]['accepted_llm'],
        accepted_llm_constant_all_samples=all(c['accepted_llm']==model_counts[0]['accepted_llm'] for c in model_counts),
        llm_admitted_first=model_admissions[0]['llm_admitted'],llm_admitted_last=model_admissions[-1]['llm_admitted'],
        inference_active_any=any(m['metrics']['active'] for m in model_rows),inference_pending_max=max(m['metrics']['pending'] for m in model_rows),
        health_endpoint_only_no_inference_sent=True,
        model_host_process_identity_verified=False,
        gpu_free_memory_claimed_fresh=False,
        gpu_memory_age_ms_first=model_rows[0]['metrics']['backend']['gpu_coordination']['memory']['age_ms'],
        gpu_memory_age_ms_last=model_rows[-1]['metrics']['backend']['gpu_coordination']['memory']['age_ms'],
        source_state_unchanged_before_after=True,low_interference_does_not_mean_zero_overhead=True,
        physical_panel_observed=False,real_dialogue_latency_measured=False,
        independent_draw_counter_available=False,independent_swap_counter_available=False)
    handoff=dict(schema='aura-joint-performance-handoff-1',status='BASELINE_COMPLETE_NO_CANDIDATE_DEPLOYED',
                 sealed_utc=datetime.now(timezone.utc).isoformat(),baseline_completed_utc=envelope['utc'],
                 baseline=ref(baseline),process_classification=ref(roles_path),before=data['before'],after=data['after'],
                 summary=summary,derived=derived,scope=data['scope'],privacy=data['privacy'],caveats=data['caveats'],
                 next_action='Main chat prepares a frozen equivalence candidate locally. This receipt authorizes no further device test or deployment.',
                 device_operator_thread='01a195e4-58a7-72d3-b141-d5d373579f7f',device_commands_inflight=False)
    save(HERE/'HANDOFF.json',handoff)
    ui=summary['ui']
    proc_lines=[]
    for pid,p in summary['processes'].items():
        proc_lines.append(f"| {names.get(pid,'未知')} / {pid} | {triplet(p['cpu_one_core_percent'])} | {p['rss_kb']['median']/1024:.1f} | {p['pss_kb']['median']/1024:.1f} |")
    timing_lines=[]
    for group,key,label in [('ui_callback_previous','wall_ms','上一完整GTK回调 wall'),('ui_callback_previous','thread_cpu_ms','上一完整GTK回调 CPU'),
                            ('ui_callback_previous','publish_ms','状态发布'),('ui_stage_timings_ms','presentation','presentation投影'),
                            ('ui_stage_timings_ms','business_public','business public'),('ui_stage_timings_ms','runtime_widgets','运行控件总段'),
                            ('ui_runtime_timings_ms','display_activity','显示保活'),('ui_settings_timings_ms','device_scan','设备扫描')]:
        timing_lines.append(f"| {label} | {triplet(ui[group][key])} |")
    text=f'''# 联合性能基线（2026-11-01）

完成约{summary['elapsed_seconds']:.3f}秒、31点主页面暂停基线，间隔目标2秒。开始时已在main页面，无需切页；结束保留main。前后完整owner、380项组件、23项相机绑定源、原控制器25文件、wide固件/VART/FDT均通过核对；未部署候选或改变运行配置。窗口完成时间：{envelope['utc']}。

全窗语音PAUSED/enabled=false/mic=false、无播放，follow=false、READY、flags=0/lease=0/active=false/armed=false。脉宽读回全窗1400µs，输出关闭；这是本轮新鲜读回，不沿用此前跟随收尾1632µs，也不推定机械位置。

## 资源占用

整板4核CPU忙碌率中位/P95/最大 **{triplet(summary['board_cpu_busy_percent'])}%**。下表进程CPU按100%=一个逻辑核，内存为31点中位MiB；CPU为30个相邻区间。

| 进程 | CPU 中位/P95/最大 %单核 | RSS MiB | PSS MiB |
|---|---:|---:|---:|
{chr(10).join(proc_lines)}

GTK主线程CPU中位{summary['threads_one_core_percent']['gtk_main']['median']:.2f}%单核，渲染工作线程{summary['threads_one_core_percent']['renderer_worker']['median']:.2f}%。业务与部分音频逻辑共用GTK，独占业务CPU仍unknown。音频工作进程/前端的资源数据已采到，后续只读完整指纹补充确认其脚本职责；原自动音频名过滤器的空列表是覆盖缺口，不能解释成没有音频进程。

观察器每点CPU中位{summary['observer_cpu_ms']['median']:.1f}ms，wall中位{summary['observer_wall_ms']['median']:.1f}ms；窗口估算消耗{observer_core:.2f}%单核，约{observer_core/4:.2f}%整板，包含在整板读数中。遍历/proc及PSS读取有可见成本，本轮不是零开销对照；后续候选比较应保持相同观察方法，或先冻结更轻观察器再建立配套基线。未对资源数值直接减去观察器CPU。

## UI、角色与视觉

| 耗时项 | 中位/P95/最大 ms |
|---|---:|
{chr(10).join(timing_lines)}

31个UI回调序号、角色帧计数、渲染序号、视觉帧号各自均不同。UI上一回调与当前publication内stage属于相邻回调，不能逐项相加断言同一回调总耗时。P95采用31点最近秩统计，属于稀疏采样分布，不是全量每次回调的P95；保存的rolling profile/pipeline分位数也没有当作新单次耗时重新统计。

角色全窗visible=true、frame_scheduling_active=true、target_fps=16。原生呈现计数4260→5205，约 **{summary['counters']['avatar']['frames']['per_second']:.2f}/s**；author_ticks约60.10/s属于控制更新，不是屏幕帧率。原生age中位/P95/最大{triplet(summary['avatar']['age_ms'])}ms；独立draw/swap次数未提供，不能虚构。原生EGL swap耗时{triplet(summary['avatar']['egl_swap_ms'])}ms、GTK绘制回调{triplet(summary['avatar']['gtk_callback_ms'])}ms。此处为软件状态和原生计数，未观察物理面板。

相机实际窗口计数：采集/预览均约12.50/s，检测约9.93/s。视觉源龄（observation_age）中位/P95/最大{triplet(summary['camera']['observation_age_ms'])}ms。GUI及渲染worker故障计数全窗0；相机/检测/识别错误字段清空，owner_fenced=false，native累计period_overruns 6→6。visual timeline错误历史计数1→1，未新增，不能写累计0。

UI状态发布、presentation投影，以及显示保活/扫描长尾可作为本地候选定位线索；本轮没有证明哪一项改动能改善真实对话等待，也没有发布任何候选。

## 记忆与模型计数

记忆worker completed55→59、discarded0→0、failure_streak=0、error=false；完成次数增加不等于调用模型。独立摘要拒绝计数未提供，保持unknown。模型健康GET中accepted_llm全窗1010、llm_admitted1011→1011，active=false、pending=0，无推理请求由观察器发出。只读取健康端点，没有核验Windows进程generation；健康响应的GPU空闲缓存age约{derived['gpu_memory_age_ms_last']/1000:.0f}秒，不能当最新可用显存。

未触发真实麦克风、播放或对话，不包含真人首声延迟结论。未保存正文、音频、图像、模板或身份；原相机、识别阈值、动画和16fps目标均保持。

[结构化交接](HANDOFF.json) · [完整脱敏样本](evidence/{baseline.name}) · [子进程职责核对](evidence/{roles_path.name}) · [最新指针](LATEST.json)。本轮设备命令已结束，后续候选ARM验证另按主窗口冻结包串行安排；本回执不启动新设备测试。
'''
    with (HERE/'HANDOFF.md').open('x',encoding='utf-8') as f:f.write(text)
    latest=dict(schema='aura-joint-performance-latest-1',handoff=ref(HERE/'HANDOFF.json'),summary=ref(HERE/'HANDOFF.md'),
                baseline=ref(baseline),status=handoff['status'],device_commands_inflight=False)
    save(HERE/'LATEST.json',latest)
    targets=[TASK/'LATEST_REVIEW.json',OWNER/'coordination/runtime_windows.json']
    archived=[]
    for p in targets:
        dest=HERE/'docs_state_final/before'/p.relative_to(PROJECT)
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(p.read_bytes())
        archived.append(dict(original=ref(p),archive=ref(dest)))
    review=load(targets[0]);review['latest_joint_performance']=ref(HERE/'LATEST.json');replace(targets[0],review)
    coord=load(targets[1]);coord['latest_joint_performance_baseline']=ref(HERE/'LATEST.json')
    coord['last_device_observed_utc']=envelope['utc'];coord['last_device_state']=data['after']['state']
    coord['retained_mechanical_boundary']['pulse_us']=data['after']['state']['readback']['width_us']
    coord['retained_mechanical_boundary']['last_actual_state_reference']=ref(baseline)
    coord['device_operation_owner']['state']='IDLE_BASELINE_COMPLETE_NO_INFLIGHT_COMMANDS'
    coord['updated_utc']=datetime.now(timezone.utc).isoformat();replace(targets[1],coord)
    save(HERE/'docs_state_final/SEAL.json',dict(schema='aura-local-joint-baseline-seal-1',before=archived,after=[ref(p) for p in targets],
                                              latest=ref(HERE/'LATEST.json'),device_access_in_finalizer=False,
                                              files=[ref(p) for folder in ('tools','remote','evidence') for p in sorted((HERE/folder).glob('*')) if p.is_file()]))
    print(json.dumps(dict(status=handoff['status'],latest=ref(HERE/'LATEST.json'),summary=ref(HERE/'HANDOFF.md'),
                          observer_cpu_one_core_percent=observer_core,device_access=False),ensure_ascii=False))


if __name__=='__main__':main()
