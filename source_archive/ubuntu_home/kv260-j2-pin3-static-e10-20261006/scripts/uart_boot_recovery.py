#!/usr/bin/env python3
"""Recover the boot interrupted by a reviewed UART command; never edit boot settings."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['inspect', 'resume'])
args = parser.parse_args()
failed = json.loads((ROOT / 'CURRENT_BENCH.json').read_text())
if failed.get('error') != 'Incomplete command response: PWM_LOAD_EXTRACT':
    raise SystemExit('Requires the recorded pre-load command interruption')
prior = (Path(failed['evidence']) / 'uart.raw').read_bytes()
if not (b'Model: ZynqMP KV260 revB' in prior and b'Reset reason:\tSOFT' in prior
        and b'ZynqMP>' in prior and prior.rstrip().endswith(b'>')):
    raise SystemExit('Recorded KV260 U-Boot continuation prompt not confirmed')
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT / 'evidence' / (stamp + '-uart-boot-' + args.action)
out.mkdir(exist_ok=False)
status = {'phase': 'uart-boot-' + args.action, 'complete': False,
          'evidence': str(out), 'failed_load_evidence': failed['evidence'],
          'boot_settings_changed': False, 'diagnostic_loaded': False,
          'boot_command_sent': False}
spec = importlib.util.spec_from_file_location('reviewed_uart',
    '/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
prompt = re.compile(rb'(?m)^ZynqMP> $')
# The login shell may emit terminal-control bytes immediately before the prompt.
root_prompt = re.compile(rb'root@[^\r\n]+:[^\r\n]*# $')
try:
    with (out / 'uart.raw').open('xb') as raw:
        uart = module.UART(raw)
        try:
            uart.receive(1)
            if uart.buf:
                raise RuntimeError('Fresh UART output present; reclassify console before recovery')
            # Cancel only the incomplete command that crossed the recorded reboot.
            uart.write(b'\x03')
            if not uart.receive(5, prompt):
                raise RuntimeError('Live U-Boot prompt not confirmed; no boot command sent')
            status['live_uboot_prompt_confirmed'] = True
            uart.line('printenv bootcmd')
            if not uart.receive(5, prompt):
                raise RuntimeError('Boot environment query did not complete')
            text = uart.buf.decode(errors='replace')
            lines = re.findall(r'(?m)^bootcmd=([^\r\n]+)\r?$', text)
            if len(lines) != 1:
                raise RuntimeError('Exactly one default boot command required')
            status['bootcmd'] = lines[0]
            if args.action == 'resume':
                reviewed = json.loads((ROOT / 'CURRENT_BOOT_RECOVERY_INSPECT.json').read_text())
                if not reviewed['complete'] or reviewed['bootcmd'] != lines[0]:
                    raise RuntimeError('Default boot command changed since inspection')
                uart.line('boot')
                status['boot_command_sent'] = True
                for step in range(1, 7):
                    if uart.receive(15, root_prompt):
                        status['root_prompt_seen'] = True
                        status['complete'] = True
                        break
                    if prompt.search(uart.buf):
                        raise RuntimeError('Default boot returned to U-Boot')
                    print(json.dumps({'boot_wait_seconds': step * 15,
                                      'root_prompt_seen': False}), flush=True)
                if not status['complete']:
                    raise RuntimeError('Linux root prompt not observed within 90 seconds')
            else:
                status['complete'] = True
        finally:
            status['host_serial_settings_restored'] = uart.close() is not None
except Exception as exc:
    status['error'] = str(exc)
finally:
    raw_bytes = (out / 'uart.raw').read_bytes()
    status['serial_bytes'] = len(raw_bytes)
    status['serial_sha256'] = hashlib.sha256(raw_bytes).hexdigest()
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    (ROOT / ('CURRENT_BOOT_RECOVERY_' + args.action.upper() + '.json')).write_text(
        json.dumps(status, indent=2) + '\n')
    print(json.dumps(status, indent=2))
raise SystemExit(0 if status['complete'] else 1)
