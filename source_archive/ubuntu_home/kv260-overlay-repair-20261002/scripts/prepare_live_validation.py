#!/usr/bin/env python3
"""Prepare fresh, separately logged UART phases without changing sealed evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = "/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin"
TEST = "/home/root/kv260-test-20261001"
SAMPLE = "/home/root/Vitis-AI/examples/vai_library/samples/classification"


def python_command(code):
    return "python3 -B -c " + shlex.quote(code)


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = ROOT / "evidence" / ("board_validation_" + stamp)
    run.mkdir(exist_ok=False)
    preserved = ROOT / "evidence/board_preflight/collect_serial.py"
    code = preserved.read_text()
    code = code.replace("All evidence files are written on the Ubuntu host. No board files are created.",
        "Evidence files are written on the Ubuntu host. Reviewed manifests may create independent backups or temporarily load the repair candidate.")
    code = code.replace("# No temporary files, hardware writes, or board-side installations.",
        "# This wrapper transports the output of the separately reviewed phase.")
    (run / "collect_serial.py").write_text(code)
    (run / "run.json").write_text(json.dumps({"created_utc": stamp, "initial_state": "Original driver and official app",
        "preserved_collector_sha256": hashlib.sha256(preserved.read_bytes()).hexdigest(),
        "sealed_index_sha256": hashlib.sha256((ROOT / "EVIDENCE.sha256").read_bytes()).hexdigest(),
        "board_work_directory": "/home/root/kv260-zocl-repair-" + stamp}, indent=2) + "\n")
    state = '''import os,json
from pathlib import Path
root_dev=os.stat('/').st_dev
drm=[]
for p in sorted(Path('/sys/class/drm').iterdir()):
 if not (p.name.startswith('card') or p.name.startswith('render')) or not (p/'device').exists(): continue
 dev=p/'device'; driver=dev/'driver'
 drm.append({'name':p.name,'device':str(dev.resolve()),'driver':str(driver.resolve()) if driver.exists() else None,'module':str((driver/'module').resolve()) if (driver/'module').exists() else None})
module=Path('/sys/module/zocl')
params={p.name:p.read_text().strip() for p in (module/'parameters').iterdir()}
firmware=Path('/proc/device-tree/fpga-full/firmware-name')
print(json.dumps({'uptime':Path('/proc/uptime').read_text().strip(),'root_device':Path('/sys/dev/block/%d:%d'%(os.major(root_dev),os.minor(root_dev))).resolve().name,'drm':drm,'zocl_parameters':params,'loaded_srcversion':(module/'srcversion').read_text().strip(),'fpga_state':Path('/sys/class/fpga_manager/fpga0/state').read_text().strip(),'firmware_name':firmware.read_bytes().rstrip(b'\\0').decode(),'vart_conf':Path('/etc/vart.conf').read_text()},indent=2))
'''
    hashes = '''import json,hashlib
from pathlib import Path
files=list(Path('/lib/firmware/xilinx/kv260-benchmark-b4096').glob('*'))+list(Path('/usr/share/vitis_ai_library/models/resnet18').glob('resnet18.*'))
files += [Path('/home/root/kv260-test-20261001/'+x) for x in ('pytorch-resnet-dog.jpg','samoyed.list','baseline-backup/baseline-files.tar.gz')]
files += [Path('/home/root/Vitis-AI/examples/vai_library/samples/classification/'+x) for x in ('test_jpeg_classification','test_performance_classification')]
for p in files:
 if not p.is_file(): continue
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}))
'''
    phases = {"02-state": [
        {"id": "drivers_and_parameters", "command": python_command(state), "timeout": 100},
        {"id": "baseline_hashes", "command": python_command(hashes), "timeout": 180},
        {"id": "manager_state", "command": "dfx-mgr-client -listPackage", "timeout": 45}],
        "03-baseline-functional": [
        {"id": "dpu_query", "command": "env XLNX_VART_FIRMWARE=" + FIRMWARE + " xdputil query", "timeout": 60},
        {"id": "classification", "command": "cd " + TEST + " && env XLNX_VART_FIRMWARE=" + FIRMWARE + " " + SAMPLE + "/test_jpeg_classification resnet18 " + TEST + "/pytorch-resnet-dog.jpg", "timeout": 60}]}
    benchmark = []
    for threads in (1, 2):
        for repeat in range(4):
            seconds = 10 if repeat == 0 else 60
            command = '''cd %s || exit 1
snapshot() {
for f in /sys/class/hwmon/hwmon*/temp*_input; do
if test -f "$f"; then printf '%%s=' "$f"; cat "$f"; fi
done
}
echo TEMPERATURE_BEFORE_MILLIC
snapshot
env XLNX_VART_FIRMWARE=%s %s/test_performance_classification resnet18 -s %d -t %d %s/samoyed.list
bench_rc=$?
echo TEMPERATURE_AFTER_MILLIC
snapshot
exit "$bench_rc"
''' % (TEST, FIRMWARE, SAMPLE, seconds, threads, TEST)
            benchmark.append({"id": "t%d_%s" % (threads, "warmup" if repeat == 0 else "r%d" % repeat),
                              "command": command, "timeout": seconds + 80})
    phases["04-baseline-performance"] = benchmark
    for phase, manifest in phases.items():
        (run / (phase + ".commands.json")).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"run": str(run), "phases": list(phases), "executed_on_board": False}))


if __name__ == "__main__":
    main()
