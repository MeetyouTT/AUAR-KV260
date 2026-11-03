from common import *
import re
report=ROOT/'report'
def copies(src, dst, pairs):
    for n,t in pairs:copy(src/n,dst/t)
perf=B/'performance_measurement_20261102'
pd=ROOT/'data/results/performance'
for n in ['RESULTS.json','board_model_gui.jsonl','windows_gpu_health.jsonl','llm_cases.csv','tts_cases.csv','windows_gpu_timeseries.csv','CONTRACT.json','DPU_LOCAL_CROSSCHECK.json','PERFORMANCE_CLOSEOUT.txt','summarize_runtime.py','measure_runtime.py','render_core_figures.ps1']:copy(perf/n,pd/n)
rs=CO/'2026-11-02_收尾性能实测_01a19c53'
for p in (rs/'figures').glob('*.png'):copy(p,report/'figures'/p.name)
copies(rs,report,[('可插入技术报告的性能小节.txt','performance_addendum.txt'),('性能指标表.csv','performance_metrics.csv')])
copies(rs/'data',pd,[('board_numeric.jsonl','board_numeric.jsonl'),('PERFORMANCE_SUMMARY.json','resource_summary.json')])
r=SH/'output/amd_report_v2_20261102'
copies(r,report,[('auar_xuefei_amd_design_report_v2.pdf','amd_design_report_v2.pdf')])
for p in (r/'attachments/wiring').glob('*'):
    if p.is_file():copy(p,report/'wiring'/p.name)
rep=CO/'2026-11-02_dual_reports'
copies(rep,report,[('auar_xuefei_competition_report.docx','competition_report_review.docx'),('auar_xuefei_competition_report.pdf','competition_report_review.pdf')])
for n in ['ai_learning_record_review.md','conversation_excerpts.md','case_index.csv','evidence_index.json']:
    copy(CO/'2026-11-02_AI辅助学习记录'/n,report/'ai_collaboration'/n)
copy(r/'attachments/ai_collaboration/wiring_case_verbatim.json',report/'ai_collaboration/wiring_case.json')
a=CO/'2026-11-02_作品概述_AMD实跑_01a19c53'
for n in ['03_vivado_block_design_native.png','05_xsim_native_wave_panel.png','05_xsim_pwm_from_actual_vcd.png']:
    copy(a/'report_figures'/n,report/'figures'/n)
copy(a/'wave_measurements.json',ROOT/'data/reference/pwm_wave_measurements.json')
for p in (a/'simulations').glob('*/*'):
    if p.name in ('xsim_console.log','actual_wave.vcd','run_wave.tcl'):
        copy(p,ROOT/'data/results/xsim'/p.parent.name/p.name)
copy(a/'SIM_STATUS.json',ROOT/'data/results/xsim/original_receipt.json')
copy(a/'vivado_reports/utilization_hierarchical.rpt',ROOT/'build/reports/utilization_hierarchical.rpt')
v=P/'deliverables/2026-10-06_voice_selected_soft_young'
sel=load(v/'selection.json')
assert sha(v/sel['reference_audio'])==sel['reference_sha256']
for n in ['selection.json','base_model_verification.json',sel['reference_audio']]:
    copy(v/n,ROOT/'src/windows/deliverables'/v.name/n)
copy(P/'deliverables/2026-10-30_board_owner/integration/resume_runtime/actual_static_cues.json',ROOT/'data/reference/public_feedback.json')
copy(P/'deliverables/2026-10-30_board_owner/integration/generate_board_static_cues.py',ROOT/'board/reference/generate_board_static_cues.py')
copy(B/'parallel_platform/inspected_public_sources/launcher.py',ROOT/'board/startup/launcher.py')
copy(P/'aura/scripts/board_camera_ui/aura-camera-ui.service',ROOT/'board/reference/camera_baseline.service')
copy(CO/'2026-10-26_DPU模型量化核查/source/inspect_xmodel.py',ROOT/'build/scripts/inspect_xmodel.py')
for p in (CO/'2026-11-02_pynq_skill/skill/pynq-contract-testgen').rglob('*'):
    if p.is_file() and '__pycache__' not in p.parts:copy(p,ROOT/'skill/pynq_contract_testgen'/p.relative_to(CO/'2026-11-02_pynq_skill/skill/pynq-contract-testgen'))
copy(CO/'2026-11-02_pynq_skill/validation/archive_reproduction.json',ROOT/'skill/pynq_contract_testgen/evidence/archive_reproduction.json')
# Motion test entry uses its historical fake clock and new placement of actual controller.
s=ROOT/'sim/motion'
module=s/'test_left_episode.py'
body=module.read_text(encoding='utf8').replace("ARCHIVE=next(p for p in HERE.parents if (p/'2026-10-31_visual_axis_maintenance').is_dir())/'2026-10-31_visual_axis_maintenance'","SOURCE=HERE.parents[1]/'src/motion'").replace("sys.path[:0]=[str(HERE/'candidate'),str(ARCHIVE/'tests/fixtures'),str(ARCHIVE/'candidate/controller')]","sys.path[:0]=[str(SOURCE/'follow'),str(HERE/'fixtures'),str(SOURCE/'controller')]").replace("HERE/'candidate/run_face_motion.py'","SOURCE/'follow/run_face_motion.py'")
module.write_text(body,encoding='utf8')
copy(B/'maintenance_original_axis_20261101/left_stop40_20261102/recovery_stability_20261102_v3/before/continuous_face_control.py',s/'before/continuous_face_control.py')
fx=P/'deliverables/2026-10-31_visual_axis_maintenance/tests/fixtures/test_recenter.py'
copy(fx,s/'fixtures/test_recenter.py')
print('Report, offline skills and evidence collected.')
