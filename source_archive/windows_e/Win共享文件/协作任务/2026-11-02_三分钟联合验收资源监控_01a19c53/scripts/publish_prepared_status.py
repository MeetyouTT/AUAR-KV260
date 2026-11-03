from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,py_compile
root=Path(__file__).resolve().parent.parent
shared=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment/joint_acceptance_180s_20261102')
shared.mkdir(parents=True,exist_ok=True)
collector=root/'scripts'/'board_monitor.py'
py_compile.compile(str(collector),doraise=True)
status={'schema':'auar-resource-observer-1','updated_utc':datetime.now(timezone.utc).isoformat(),
 'phase':'PREPARED_WAITING_NEW_HANDOFF_AND_START_GATE','prepared':True,'collector_active':False,
 'resource_observer_thread':'01a19c53-3a84-7c30-8e70-9368a35318d8',
 'output_directory':str(root),'collector_script':str(collector),'collector_sha256':hashlib.sha256(collector.read_bytes()).hexdigest(),
 'interval_seconds':2,'max_duration_seconds':200,
 'exclusive_reads':['/proc/stat','/proc/meminfo','/proc/<pid>/stat','/proc/net/dev','/proc/loadavg','available thermal and CPU-frequency sysfs','8790 /health numeric metadata'],
 'not_queried_by_resource_collector':['8783 UI','8791 ASR','8797 Windows model host'],
 'new_dpu_statistics_enable':False,'board_files_or_services_modified':False,'extra_model_inference':False,
 'needs_from_main':['New identity-owner handoff file with a current valid window','START_GATE.json with start_utc and board_monotonic_s if available','Main GUI/Windows numeric samples and actual end marker for aligned plots'],
 'pre_gate_preflight':{'fresh_boot_id':'a6d4a069-e9b0-4065-8df7-dc23556b168e','resource_only_boot_proc_read_performed':True,'api_queries':0,'sample_count':0,'observer_process_ended':True,'startup_error':'UnboundLocalError in observer STOP flag; corrected locally before formal run','diagnostic_files_retained':True},
 'clock_note':'Board wall clock in preflight reports 2021-11-20; do not align by board UTC. Use board monotonic and host UTC receipt anchors. No clock change performed.',
 'planned_figures':['整板及分核CPU曲线','主要进程CPU与RSS','内存与可用余量','DPU三模型完成频率与可得耗时','主视觉观测年龄/计数与错误','联合GUI/Windows模型阶段时间线（引用主窗口采样）'],
 'scope':'Do not start demo or collect acceptance samples until explicit new handoff and START_GATE. Prior 90s/40s handoffs not reused.'}
(shared/'RESOURCE_OBSERVER_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'RESOURCE_OBSERVER_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'phase':status['phase'],'shared_status':str(shared/'RESOURCE_OBSERVER_STATUS.json'),'sample_count':0,'clock_note':status['clock_note']},ensure_ascii=False))
