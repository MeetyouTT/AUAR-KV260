"""Collect hashes and bounded numerical evidence for the system audit."""
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
SHARE = Path('/home/ghmd/Win共享文件')
PAN = SHARE / '协作任务/2026-10-26_转轴完整复核与首帧修复'
USB = SHARE / '协作任务/2026-10-26_音频USB告警与队列保护'
FIRM = SHARE / '语音共享文件/deliverables/2026-10-23_pan_joint_firmware'
VOICE = SHARE / '语音共享文件/aura'
PRODUCTION = SHARE / '语音共享文件/deliverables/2026-10-24_native_critical_live/source/aura'


def info(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                mtime_utc=dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat())


def main():
    paths = [
        PAN / 'README.md', PAN / 'FINAL_RUNTIME_STATUS.json', PAN / 'VALIDATION_CURRENT.json',
        PAN / 'r12-v16-supervised-detail.json', PAN / 'r12-v16-supervised-30s.json',
        PAN / 'unattended-v17-live-stage-profile.json',
        USB / 'README.md', USB / 'CONTINUED_OBSERVATION.json',
        USB / 'audio_queue_bound_candidate/gstreamer_persistent_engine.py',
        FIRM / 'candidate/rtl/visual_servo.sv',
        FIRM / 'candidate/native/vsrv_mmio.c',
        FIRM / 'evidence/implementation/utilization.rpt',
        FIRM / 'evidence/independent-audit/check_timing.rpt',
        FIRM / 'evidence/independent-audit/drc.rpt',
        FIRM / 'evidence/independent-audit/pwm_timing.rpt',
        Path('/home/ghmd/aura-pan-joint-20261023/platform/pin.xdc'),
        SHARE / 'output/hardware/AURA_单舵机完整接线_5V.md',
        SHARE / '协作任务/2026-10-26_转轴输入延迟与USB恢复/single-terminal-usb-capture.json',
        SHARE / '语音共享文件/deliverables/2026-10-26_profile_memory/PROGRESS.json',
        SHARE / '语音共享文件/deliverables/2026-10-26_profile_memory/README.md',
        SHARE / '语音共享文件/deliverables/2026-10-26_system_completion/README.md',
        VOICE / 'board/runtime/audio/remote_frontend.py',
        VOICE / 'board/runtime/audio/automatic_capture.py',
        VOICE / 'common/profile_access.py', VOICE / 'tools/board_model_host.py',
        VOICE / 'config/experiments.json',
        SHARE / '语音共享文件/deliverables/2026-10-18_board_dialogue/launch_models.py',
        SHARE / '.verysync/ignoreList',
        PRODUCTION / 'board/vision/ui_camera_service.py',
    ]
    paths += [PAN / 'continuous_v10r14_candidate' / name for name in
              ('continuous_session.py', 'continuous_face_control.py', 'deadline_driver.py',
               'batch_driver.py', 'run_face_motion.py', 'session_shutdown.py')]
    inventory = [info(p) for p in paths]
    (ROOT / 'source_inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    z = ZipFile('/home/ghmd/下载/项目.zip')
    names = [
        '项目/README.md',
        '项目/方案/AURA_KV260_完整实施方案_无声源定位版_2026-09-30.md',
        '项目/方案/AURA_当前现状三人分工_2026-10-02.md',
        '项目/aura_fpga/readme.md',
        '项目/方案/AURA_KV260_外设控制与采购规格_2026-09-26.md',
        '项目/方案/reference_round4_20260926/扩展板设计分析_舵机_麦克风与音响_v1_0.extracted.md',
        '项目/方案/reference_round4_20260926/servo_drive_scheme_confirmation_technical_record_v1_0.extracted.md',
    ]
    zip_sources = []
    for name in names:
        raw = z.read(name)
        zip_sources.append(dict(member=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    (ROOT / 'zip_sources.json').write_text(json.dumps(zip_sources, ensure_ascii=False, indent=2) + '\n')
    drc = (FIRM / 'evidence/independent-audit/drc.rpt').read_text()
    drc_counts = Counter(re.findall(r'^([A-Z][A-Z0-9]*-\d+)#\d+ (?:Warning|Critical Warning|Error)', drc, re.M))
    cdc = (ROOT / 'fpga/cdc.rpt').read_text()
    cdc_summary = [dict(id=m[0], severity=m[1], count=int(m[2]), description=m[3]) for m in
                   re.findall(r'^(CDC-\d+)\s+(Info|Warning|Critical)\s+(\d+)\s+(.+)$', cdc, re.M)]
    criticals = [line.strip() for line in cdc.splitlines()
                 if re.match(r'\s*\d+\s+CDC-\d+\s+Critical', line)]
    runtime = json.loads((PAN / 'FINAL_RUNTIME_STATUS.json').read_text())
    observation = json.loads((USB / 'CONTINUED_OBSERVATION.json').read_text())
    timing = (ROOT / 'fpga/timing.rpt').read_text()
    summary = re.search(r'^\s+0\.001\s+0\.000\s+0\s+392547\s+0\.000\s+0\.000\s+0\s+392498', timing, re.M)
    methodology = (ROOT / 'fpga/methodology.rpt').read_text()
    methodology_rows = [dict(id=m[0], severity=m[1], description=m[2].strip(), count=int(m[3]))
                        for m in re.findall(r'^\|\s*([A-Z]+[A-Z0-9]*-\d+)\s*\|\s*(Warning|Advisory|Critical Warning)\s*\|\s*([^|]+)\|\s*(\d+)\s*\|', methodology, re.M)]
    congestion = (ROOT / 'fpga/congestion.rpt').read_text()
    run_status = (ROOT / 'fpga/audit_status.tsv').read_text().splitlines()
    (ROOT / 'review_facts.json').write_text(json.dumps(dict(
        collected_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        board_scope='historical sealed reports; this audit did not access board or Windows',
        runtime=runtime,
        observed_seconds=observation['observed_seconds'], kernel_windows=observation['kernel_windows'],
        usb_warning_count_in_bounded_samples=observation['warning_count_in_bounded_samples'],
        routed_setup_hold_summary_matches_frozen_report=bool(summary),
        original_drc_counts=dict(drc_counts), cdc_summary=cdc_summary,
        cdc_critical_paths=criticals,
        custom_servo_in_cdc_report='aura_m3_regs' in cdc,
        methodology=methodology_rows,
        no_congestion_windows_above_level_5='No congestion windows are found above level 5' in congestion,
        fpga_report_generation_status=run_status,
        fpga_report_generation_complete=len(run_status)==11 and all('\tPASS' in line for line in run_status),
        user_hardware_confirmation=dict(pin='J2.3', isolator='ADuM1201',
            evidence='User confirmed in current conversation; follows project files',
            exact_rail_and_ground_as_built='not independently measured'),
        calculations=dict(command_center_us=1420, hard_min_us=1400, hard_max_us=1600,
            negative_travel_us=20, positive_travel_us=180,
            slow_command_1us_ms=1000/6, slow_command_3us_ms=3000/6,
            fast_command_1us_ms=1000/20, fast_command_3us_ms=3000/20,
            anchor_p95_remaining_ms=500-439, initial_pwm_required_remaining_ms=20+23+3,
            caveat='ideal command accumulation and old r12/v16 field sample; not physical servo latency or a current r14 tail guarantee'),
        software_validation=dict(selected_regressions_passed=18, counterexamples_reproduced=3,
            hardware_waveform_measured=False, actual_motion_commands=0)), ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(source_files=len(inventory), zip_members=len(zip_sources),
                          cdc_critical_paths=len(criticals), custom_servo_cdc_mentions='aura_m3_regs' in cdc)))


if __name__ == '__main__':
    main()
