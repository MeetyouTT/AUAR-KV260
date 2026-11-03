from pathlib import Path
from datetime import datetime,timezone
import json,csv,shutil,sys,hashlib,re,subprocess,zipfile,base64
sys.stdout.reconfigure(encoding='utf-8')
R=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
work=Path(__file__).parent
shared=Path(r'E:\Win共享文件')
voice=shared/'语音共享文件/deliverables'
scope=json.loads((voice/'2026-11-02_5090_deployment/DEPLOYMENT_CURRENT.json').read_text(encoding='utf-8'))
keys=['updated_utc','latest_user_scope_update','voice_CPU_retention','face_voice_association_required','face_voice_association_status','axis_functional_behavior_user_accepted','axis_keep_current_parameters','memory_user_feedback','memory_current_project_blocker']
ss={k:scope[k] for k in keys if k in scope}
ss['scope']='Saved user acceptance and scope; no fresh physical or runtime proof'
(R/'sources/project_scope_summary.json').write_text(json.dumps(ss,ensure_ascii=False,indent=2),encoding='utf-8')
for rel,name in [('2026-11-02_5090_deployment/dialogue_latency_20261101/TWO_TURN_LATENCY.json','dialogue_two_turn_latency.json'),('2026-11-02_5090_deployment/dialogue_latency_20261101/metrics_semantics.txt','dialogue_latency_semantics.txt'),('2026-11-02_5090_deployment/tts_calibration.json','tts_calibration.json')]:
 p=voice/rel
 if p.exists():shutil.copy2(p,R/'evidence'/name)
# Keep the actual simulator logs whose hashes appear in result.json.
code=r'''from pathlib import Path
import json,base64
base=Path('/home/ghmd/auar-techdoc-01a1a1a5/verification')
out={str(p.relative_to(base)):base64.b64encode(p.read_bytes()).decode() for p in base.rglob('*') if p.is_file() and p.suffix in ['.log','.json'] and p.stat().st_size<200000}
print(json.dumps(out,ensure_ascii=False))
'''
p=subprocess.run(['ssh','aura-ubuntu','python3 -'],input=code.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
for name,txt in json.loads(p.stdout).items():
 dest=R/'evidence/ubuntu_rtl'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(base64.b64decode(txt))
# Portable copies of the exact authoring and collection scripts.
for name in ['build_word.py','build_diagrams.py','collect_live.py','prepare_evidence.py','ubuntu_charts.py','qa_report.py','export_word.ps1']:
 t=(work/name).read_text(encoding='utf-8')
 if name.endswith('.py'):
  t=t.replace("R=Path(r'E:\\Win共享文件\\协作任务\\2026-11-03_technical_report_01a1a1a5')","R=Path(__file__).resolve().parents[1]")
  t=t.replace("ROOT=Path(r'E:\\Win共享文件\\协作任务\\2026-11-03_technical_report_01a1a1a5')","ROOT=Path(__file__).resolve().parents[1]")
  if name=='ubuntu_charts.py':t=t.replace("ROOT=Path(__file__).resolve().parent","ROOT=Path(__file__).resolve().parent\nif ROOT.name=='tools': ROOT=ROOT.parent")
  if name=='prepare_evidence.py':t=t.replace("shutil.move(str(R/name),str(Path(r'E:\\报告制作_20261103')/name))","shutil.move(str(R/name),str(R/'qa'/name))")
 else:t=t.replace("$reportRoot = 'E:\\Win共享文件\\协作任务\\2026-11-03_technical_report_01a1a1a5'","$reportRoot = Split-Path -Parent $PSScriptRoot")
 (R/'tools'/name).write_text(t,encoding='utf-8')
s=json.loads((R/'evidence/live_summary.json').read_text(encoding='utf-8'))
records=[('cpu_mean','79.433435','percent','60 interval weighted mean all four cores=100'),('cpu_p95','84.786317','percent','60 interval linear quantile'),('cpu_max','86.294416','percent','maximum one-second interval'),('memory_mean_used','1.152562','GiB','61 samples MemTotal-MemAvailable'),('memory_min_available','2.679489','GiB','61 samples'),('capture_rate','22.571063','Hz','counter delta over59.988313s'),('primary_complete_rate','9.885259','Hz','counter delta over59.988313s'),('yunet_complete_rate','9.851919','Hz','591 native completes over59.988313s'),('sface_complete_rate','0.133359','Hz','8 native completes over59.988313s'),('primary_overruns_delta','0','count','unchanged cumulative counter'),('observation_age_p95','164','ms','61 health snapshots at approximately1Hz'),('observation_age_max','219','ms','61 health snapshots'),('icmp_rtt_p50','1.010','ms','30 emitted samples linear interpolation'),('icmp_rtt_p95','1.7365','ms','30 emitted samples linear interpolation'),('icmp_rtt_p99','1.821','ms','30 emitted samples linear interpolation'),('icmp_rtt_max','1.850','ms','emitted sample precision; ping summary1.848ms'),('icmp_loss','0','percent','30 sent30received'),('xsim_tests_passed','4','count','12 tool stages source unchanged not board verified')]
with (R/'data/metrics_current.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['metric','value','unit','condition','evidence','scope'])
 for metric,value,unit,cond in records:w.writerow([metric,value,unit,cond,'evidence/ubuntu_rtl/rtl/result.json' if metric.startswith('xsim') else 'evidence/live_board_samples.json','2026-11-03_current_board_read_only_or_offline_simulation'])
toolsread='''# 工具使用说明

这些脚本对应本次实际工作。请在完整报告包的新副本中运行，避免改写已经归档的测量和回执。

- build_word.py 用 python-docx 从 report/technical_report.md 生成 Word。脚本中的 Windows 字体路径对应本机。
- export_word.ps1 使用 Microsoft Word 的隐藏 COM 实例更新目录并导出同版 PDF；只打开本报告，不接管其他文档。
- build_diagrams.py 用 ReportLab 和 Poppler 生成五张机制图的 PDF 与 PNG。
- ubuntu_charts.py 从 data/live_resources.csv 与 live_rtt.csv 绘制三组新曲线。可在 Ubuntu 已有 Vitis AI CPU 容器执行，Matplotlib 版本 3.4.3。
- collect_live.py 用已配置的 aura-kv260 SSH 连接只读采集状态、当前 X11 页面、资源与 ICMP。默认约 60 秒；不发录音、推理或运动命令。采样期间仍可能受现场原有业务影响。
- prepare_evidence.py 从采样计算指标，并通过 aura-ubuntu 取四套 XSim 回执。读取临时完整健康状态后只将所需汇总纳入公开证据。
- qa_report.py 用本机打包 Poppler 渲染 PDF 供逐页检查。QA 图片没有包含在交付 ZIP 中。

本机文档工具包没有 LibreOffice 可执行文件，canonical render_docx.py 因找不到 soffice.exe 失败。本报告使用已安装 Microsoft Word 原生导出，再由打包 Poppler 渲染检查，因此 PDF 与交付 Word 的目录、分页来自同一份实际文档。

XSim 的实际命令和日志位于 evidence/ubuntu_rtl。完整工程、模型、固件构建和部署继续使用方案 A 工程包，报告中的命令不是新的工程安装器。
'''
(R/'tools/readme.md').write_text(toolsread,encoding='utf-8')
readme='''# AUAR 雪妃技术报告交付

按用户指定 writing_sample.md 的九章主线完成。封面使用用户提供的 10 周年 PSD 合成图，版式参考设计与验证报告。内含 19 幅正文配图、13 张表、参考文献及 A 至 F 六个附录。

先看 auar_xuefei_technical_report.pdf；需要修改时打开同名 DOCX。report/technical_report.md 是正文源，figures 是可单独插入报告的图，data 是逐点及汇总数据，evidence 是原始回执，sources 是材料与来源索引，tools 是制作与采集脚本。

本次新增工作：读取当前 KV260 界面和运行状态；59.988313 秒只读自然负载采样；30 次板端到 Windows 的 ICMP；Ubuntu 独立目录重跑四套 RTL 测试；Ubuntu Matplotlib 根据真实 CSV 生成三组新曲线。历史质量、资源和模型短测保留原版本与条件。没有重新烧写位流、改生产服务、启用聆听或跟随，也没有重新测量物理运动或声学首声。

报告可供继续编辑和技术审阅。以下现场材料仍应在最终提交前补齐：

1. 实际装配的整机正面与45度照片、板卡特写、最终供电接线图及机械尺寸/限位图。当前图1-1是实际屏幕截图，不能充当整机实物照片。
2. 示波器或逻辑分析仪的 PWM 电气测量、机械零点与允许行程，以及传感器到实际执行响应的分位数。
3. 扬声器声学首声与统一版本的完整交互成功率、异常恢复、冷启动和持续运行记录。本次窗口中聆听和人脸跟随均关闭。
4. FPGA、DPU、语音及记忆案例更完整的真实原问答、模型ID和个人贡献。现有复盘与真实摘录已区分。
5. 正式团队/作者信息、最终报名组别和页面字段；模型、角色、第三方IP的公开分发授权，以及新环境完整构建和部署回执。

当前板卡操作时钟偏离实际时间，日志同时保留主机UTC、单调时长和bootID。当前运行配置指纹与方案A业务基准分别记录，不宣称全现场同版。完整工程使用已有 auar_xuefei 方案A包，本ZIP仅归档报告和证据。
'''
(R/'readme.md').write_text(readme,encoding='utf-8')
# Add explicit provenance for all sources used in this report.
man=json.loads((R/'sources/source_manifest.json').read_text(encoding='utf-8'))
for p in [Path(r'D:\Download\writing_sample.md'),Path(r'C:\Users\REVO1\Downloads\10周年.psd'),Path(r'C:\Users\REVO1\Downloads\Write\Write\验证报告\验证报告.pdf'),next((shared/'参赛资料').glob('*2026FPGA*AMD.pdf'))]:
 man.append({'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'role':'user_reference'})
(R/'sources/source_manifest.json').write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf-8')
print('supporting evidence and tools ready; metrics',len(records))
