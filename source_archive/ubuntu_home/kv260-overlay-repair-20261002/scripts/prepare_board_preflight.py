#!/usr/bin/env python3
"""Prepare UART read-only inventory, preserving the existing collector and evidence."""
import hashlib
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CID = "0353445345333247805558c00401a100"


def main():
    source = Path("/home/ghmd/AMD_Smart/logs/fpga/2026-09-30-kv260-readonly/collect_serial.py")
    output = ROOT / "evidence" / "board_preflight"
    output.mkdir(parents=True, exist_ok=False)
    code = source.read_text()
    replacements = {
        "select.select([fd], [], [], 0.2)": "select.select([fd], [], [], 0.01)",
        "range(0, len(payload), 24)": "range(0, len(payload), 4)",
        "payload[pos:pos+24]": "payload[pos:pos+4]",
        "time.monotonic() + 0.015": "time.monotonic() + 0.04",
        "if not record['complete']:": "if not record['complete'] or record['exit_code'] != 0:",
        "Collection stopped: completion marker/prompt missing": "Collection stopped: incomplete or unsuccessful command",
    }
    for before, after in replacements.items():
        if code.count(before) != 1:
            raise RuntimeError("Preserved UART collector differs: " + before)
        code = code.replace(before, after)
    anchor = "    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)"
    guard = '''    resolved_port = os.path.realpath(PORT)
    if not Path(PORT).exists():
        raise RuntimeError('Board UART not connected: ' + PORT)
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            fds = list((proc / 'fd').iterdir())
        except (OSError, PermissionError):
            continue
        for candidate_fd in fds:
            try:
                if os.path.realpath(candidate_fd) == resolved_port:
                    raise RuntimeError('UART already open by PID ' + proc.name)
            except OSError:
                continue
'''
    if code.count(anchor) != 1:
        raise RuntimeError("UART open statement differs")
    code = code.replace(anchor, guard + anchor)
    (output / "collect_serial.py").write_text(code)
    identity = '''import os,platform,hashlib,json,subprocess
from pathlib import Path
assert os.geteuid()==0, "Not the board root shell"
cid=Path('/sys/class/block/mmcblk1/device/cid').read_text().strip()
assert cid=='%s', "Unexpected test card: "+cid
assert platform.release()=='5.15.36-xilinx-v2022.2', "Unexpected kernel"
model=Path('/proc/device-tree/model').read_bytes().replace(b'\\0',b'').decode()
assert 'K26' in model, "Unexpected device model"
print(json.dumps({'cid':cid,'model':model,'uname':platform.uname()._asdict()},indent=2))
print(Path('/proc/version').read_text())
print(Path('/etc/os-release').read_text())
module=Path(subprocess.check_output(['modinfo','-n','zocl'],text=True).strip())
for p in (module,Path('/usr/lib/libxrt_core.so.2.14.0'),Path('/usr/bin/dfx-mgrd'),Path('/usr/lib/libdfx.so.1.0')):
 print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
subprocess.run(['modinfo','zocl'],check=True)
subprocess.run(['xmutil','listapps'],check=True)
subprocess.run(['systemctl','is-active','dfx-mgr'],check=True)
''' % EXPECTED_CID
    clients = '''import os,json
from pathlib import Path
clients=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit(): continue
 try:
  for fd in (proc/'fd').iterdir():
   try: target=os.readlink(fd)
   except OSError: continue
   if target.startswith('/dev/dri/'):
    clients.append({'pid':int(proc.name),'comm':(proc/'comm').read_text().strip(),'fd':fd.name,'target':target})
 except OSError: continue
module=Path('/sys/module/zocl')
print(json.dumps({'drm_clients':clients,'zocl_holders':[p.name for p in (module/'holders').iterdir()] if (module/'holders').exists() else None,'zocl_refcnt':(module/'refcnt').read_text().strip() if (module/'refcnt').exists() else None},indent=2))
'''
    def python_command(text):
        return "python3 -B -c " + shlex.quote(text)
    manifest = [{"id": "identity_runtime", "command": python_command(identity), "timeout": 180},
                {"id": "kernel_config", "command": "gzip -dc /proc/config.gz", "timeout": 180},
                {"id": "open_drm_clients", "command": python_command(clients), "timeout": 180},
                {"id": "kernel_before", "command": "dmesg", "timeout": 180}]
    (output / "01-readonly.commands.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    metadata = {"source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "scope": "Prepared only; UART read-only inventory. No driver replacement, overlay switch or MMIO.",
        "collector_sha256": hashlib.sha256(code.encode()).hexdigest(), "expected_test_card_cid": EXPECTED_CID,
        "expected_kernel_release": "5.15.36-xilinx-v2022.2", "input_pacing": "4 bytes per >= 40 ms"}
    (output / "preparation.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"prepared": str(output), "commands": len(manifest), "executed_on_board": False}))


if __name__ == "__main__":
    main()
