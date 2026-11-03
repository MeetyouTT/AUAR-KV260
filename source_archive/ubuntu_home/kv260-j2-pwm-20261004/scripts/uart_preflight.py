#!/usr/bin/env python3
"""Read current board state through the reviewed UART transport; no PL writes."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
EXPECTED_CID = '0353445345333247805558c00401a100'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-boot', action='store_true',
                        help='listen passively for up to 120 seconds before confirming the root prompt')
    args = parser.parse_args()
    tag = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'evidence' / (tag + '-pwm-uart-readonly')
    out.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location('reviewed_uart', TRANSPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    identity = """import hashlib,json,os,platform
from pathlib import Path
p=Path('/sys/block/mmcblk1/device/cid');cid=p.read_text().strip()
assert cid=='0353445345333247805558c00401a100','Unexpected SD identity'
assert platform.machine()=='aarch64','Unexpected machine'
files=Path('/lib/firmware/xilinx/kv260-benchmark-b4096')
print(json.dumps(dict(sd_cid=cid,kernel=platform.release(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),uptime=Path('/proc/uptime').read_text().strip(),fpga_state=Path('/sys/class/fpga_manager/fpga0/state').read_text().strip(),dev_mem=Path('/dev/mem').exists(),libc=os.confstr('CS_GNU_LIBC_VERSION'),elf_loader=Path('/lib/ld-linux-aarch64.so.1').exists(),firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\\0').decode(),official_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files.iterdir() if p.is_file()})))
"""
    commands = [
        ('identity', 'python3 -B -c ' + shlex.quote(identity)),
        ('active-state', "xmutil listapps; systemctl is-active dfx-mgr; systemctl show dfx-mgr -p MainPID; ls /sys/kernel/config/device-tree/overlays; cat /etc/vart.conf; ps -eo pid,comm,args | rg 'dfx-mgr|vitis|benchmark|python|aura'".replace("rg 'dfx-mgr|vitis|benchmark|python|aura'", "grep -E 'dfx-mgr|vitis|benchmark|python|aura'")),
        ('clock-and-drivers', "cat /sys/kernel/debug/clk/clk_summary; ls /sys/bus/platform/drivers | grep -E 'afi|fclk|zocl'; ls -l /lib/firmware/xilinx/kv260-benchmark-b4096; df -h /home/root /lib/firmware; ip -4 addr show"),
    ]
    state = {'phase': 'uart-readonly', 'evidence': str(out), 'complete': False,
             'transport_sha256': hashlib.sha256(TRANSPORT.read_bytes()).hexdigest(),
             'commands': [], 'pl_loaded': False, 'start_sent': False}
    try:
        with (out / 'uart.raw').open('wb') as raw:
            uart = module.UART(raw)
            try:
                if args.capture_boot:
                    state['boot_capture_requested'] = True
                    print(json.dumps({'boot_capture_ready': True, 'evidence': str(out)}), flush=True)
                    for i in range(6):
                        found = uart.receive(20, module.PROMPT)
                        print(json.dumps({'listen_seconds_limit': (i + 1) * 20,
                                          'bytes_received': len(uart.buf),
                                          'root_prompt_seen': found}), flush=True)
                        if found:
                            break
                    state['boot_capture_bytes'] = len(uart.buf)
                uart.connect()
                for i, (label, command) in enumerate(commands):
                    (out / (label + '.command')).write_text(command + '\n')
                    rc, data, digest = uart.command(command, 'PWM_PREFLIGHT_' + str(i), 30)
                    (out / (label + '.output')).write_bytes(data)
                    state['commands'].append({'label': label, 'rc': rc, 'sha256': digest})
                    if rc:
                        raise RuntimeError(label + ' failed: ' + data.decode(errors='replace'))
            finally:
                uart.close()
        state['complete'] = True
    except Exception as exc:
        state['error'] = str(exc)
        raise
    finally:
        (out / 'status.json').write_text(json.dumps(state, indent=2) + '\n')
        (ROOT / 'CURRENT_PREFLIGHT.json').write_text(json.dumps(state, indent=2) + '\n')
        print(json.dumps(state, indent=2))


if __name__ == '__main__':
    main()
