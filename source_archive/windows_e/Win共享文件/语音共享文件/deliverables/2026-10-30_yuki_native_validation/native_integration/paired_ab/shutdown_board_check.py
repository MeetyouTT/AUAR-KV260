"""Bounded cleanup and preservation audit of character-owned test processes only."""
from pathlib import Path
import datetime, json, os, runpy, signal, time, zipfile

base = Path('/home/root/aura-yuki-validation-20261030')
phase = base / 'native_integration'
ab = phase / 'paired_ab'
tags = {'run_suite.py','paired_renderer_harness.py','old_renderer_harness.py',
        'precision_validation_worker.py','clock_revision_worker.py','validate_gtk_clock.py',
        'validate_gtk_lifecycle.py','validate_native.py','yuki_frame_export','yuki_runtime_audit'}

def owned():
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            argv = [x.decode() for x in (proc/'cmdline').read_bytes().split(b'\0') if x]
            matches = [x for x in argv if x.startswith(str(base)+'/') and Path(x).name in tags]
            if not matches:
                continue
            stat = (proc/'stat').read_text().rsplit(')', 1)[1].split()
            found.append(dict(pid=int(proc.name), start_ticks=int(stat[19]),
                              pgid=os.getpgid(int(proc.name)), script=matches[0]))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return found

before = owned()
for item in before:
    if any(x['pid']==item['pid'] and x['start_ticks']==item['start_ticks'] for x in owned()):
        os.kill(item['pid'], signal.SIGTERM)
if before:
    time.sleep(1)
for item in owned():
    if any(x['pid']==item['pid'] and x['start_ticks']==item['start_ticks'] for x in before):
        os.kill(item['pid'], signal.SIGKILL)
remaining = owned()
runpy.run_path(str(phase/'final_board_preservation.py'), run_name='__main__')
preservation = json.loads((phase/'results/final-preservation.json').read_text())
camera_alive = Path('/proc/1333').exists()
archive = ab/'pilot-v1-shutdown-evidence.zip'
pilot = ab/'runs/pilot-v1'
entries = []
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
    for path in sorted(pilot.rglob('*')):
        if path.is_file() and path.suffix in {'.json','.jsonl','.log'}:
            relative = path.relative_to(ab).as_posix()
            output.write(path, relative)
            entries.append(relative)
report = dict(status='PASS' if not remaining and preservation['status']=='PASS' and camera_alive else 'FAIL',
              at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              owned_processes_before=before, owned_processes_remaining=remaining,
              production_preservation=preservation, camera_pid=1333, camera_pid_alive=camera_alive,
              pilot_archive=str(archive), pilot_archive_files=entries,
              formal_12_case_suite_started=False, nojpeg_board_control_started=False,
              production_deployed=False, uart_opened=False,
              shutdown_executed_by_character=False)
(ab/'shutdown-board-check.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))
assert report['status']=='PASS'
