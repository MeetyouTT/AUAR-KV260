#!/usr/bin/env python3
"""Explicit PWM control with optional UART observation; preserve every response."""
import argparse
import ast
import base64
import datetime
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shlex
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['inspect', 'scratch', 'start', 'stop', 'restore'])
parser.add_argument('--watch-seconds', type=int, choices=[0, 120], default=0)
args = parser.parse_args()
if args.watch_seconds and args.action not in ('start', 'inspect'):
    parser.error('Observation is supported only for start or inspect')
ROOT = Path(__file__).resolve().parents[1]
bench = json.loads((ROOT / 'CURRENT_BENCH.json').read_text())
assert bench['candidate_active'], 'PWM candidate is not active'
assert bench['complete'] or args.action in ('inspect','stop','restore'), 'Control verification required before START'
stage = json.loads((ROOT / 'CURRENT_BOARD_STAGE.json').read_text())
assert stage['complete'] and stage['destination'] == bench['archive']
if args.action == 'start':
    for prerequisite in ('SCRATCH', 'STOP'):
        checked = json.loads((ROOT / ('CURRENT_' + prerequisite + '.json')).read_text())
        assert checked['complete'] and checked.get('archive') == bench['archive']
        assert checked.get('bench_evidence') == bench['evidence'], prerequisite + ' must pass for this loading session'
# Reuse reviewed remote guards without importing the loader's executable main.
tree = ast.parse((ROOT / 'scripts/uart_load.py').read_text())
constants = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
             if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
             and n.targets[0].id in ('COMMON', 'RESTORE')}
source = constants['COMMON']
if args.action == 'restore':
    source += r'''
if active()==[APP] and fw()==FW:
 run(['python3','-B',str(package/'board/probe.py'),'--stop'],10)
'''
    source += constants['RESTORE']
else:
    source += r'''
assert active()==[APP] and fw()==FW and state()=='operating'
original=check_official_hashes()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==original['boot_id'],'boot changed'
manifest=json.loads((package/'manifest.json').read_text())
for relative,meta in manifest.items():
 p=package/relative
 assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['sha256']
 if relative.startswith('lib/firmware/'):
  assert hashlib.sha256((Path('/')/relative).read_bytes()).hexdigest()==meta['sha256']
summary=Path('/sys/kernel/debug/clk/clk_summary').read_text()
lines=[x.split() for x in summary.splitlines() if x.split() and x.split()[0]=='pl0_ref']
assert len(lines)==1 and int(lines[0][1])>0
rate=int(lines[0][4]);assert abs(rate-99999001)<=99999001*.001
action=sys.argv[3]
command=['python3','-B',str(package/'board/probe.py')]
if action in ('start','stop','scratch'):command.append('--'+action)
registers=json.loads(run(command,10))
assert registers['frames_left']==0
running=bool(registers['status']&1)
if action=='start':assert running and registers['status'] in (5,7)
elif action in ('stop','scratch'):assert registers['status']==4
else:assert registers['status'] in (4,5,7)
assert registers['ip_id']=='0x50574d54' and registers['build_id']=='BUILD_ID_PLACEHOLDER'
assert registers['run_frames']==0 and registers['pulse_us']==1500
assert registers['period_ticks']==1999980 and registers['pulse_ticks']==149999
print(json.dumps({'action':action,'registers':registers,'pl0_actual_hz':rate,
 'boot_id':original['boot_id'],
 'continuous_running':running,'output_register_low':not bool(registers['status'] & 2),
 'external_waveform_verified':False}))
'''
build_id = json.loads((ROOT / 'evidence/source_identity.json').read_text())['build_id']
source = source.replace('BUILD_ID_PLACEHOLDER', hex(int(build_id, 16)))
tag = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT / 'evidence' / (tag + '-uart-' + args.action)
out.mkdir(parents=True, exist_ok=False)
(out / 'remote.py').write_text(source)
status = {'phase': 'uart-' + args.action, 'complete': False, 'evidence': str(out),
          'archive': bench['archive'], 'bench_evidence': bench['evidence'],
          'start_requested': args.action == 'start', 'external_waveform_verified': False}
transport = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
spec = importlib.util.spec_from_file_location('reviewed_uart', transport)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    with (out / 'uart.raw').open('wb') as raw:
        uart = module.UART(raw)
        try:
            uart.connect()
            payload = base64.b64encode(gzip.compress(source.encode(), mtime=0)).decode()
            code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(payload) + ')))'
            command = 'python3 -B -c ' + shlex.quote(code) + ' ' + shlex.quote(stage['destination']) + ' ' + stage['sha256'] + ' ' + args.action
            rc, data, digest = uart.command(command, 'PWM_' + args.action.upper(), 75)
            (out / 'result.output').write_bytes(data)
            status.update(rc=rc, result_sha256=digest)
            if rc:
                raise RuntimeError(data.decode(errors='replace'))
            status['result'] = json.loads(data)
            if args.watch_seconds:
                if not status['result']['continuous_running']:
                    raise RuntimeError('Observation requires a running output')
                status['watch'] = {'requested_seconds': args.watch_seconds,
                                   'complete': False, 'snapshots': []}
                started = time.monotonic()
                print(json.dumps({'started': args.action == 'start',
                                  'continuous_running': True,
                                  'watch_seconds': args.watch_seconds}), flush=True)
                # START was sent once. Every subsequent command is read-only.
                inspect_command = command.rsplit(' ', 1)[0] + ' inspect'
                for index in range(1, args.watch_seconds // 30 + 1):
                    uart.buf = b''
                    uart.receive(30)
                    if re.search(rb'Kernel panic|SError|reboot:|U-Boot|Linux version', uart.buf):
                        uart.shell_ready = False
                        raise RuntimeError('Unexpected kernel/reset output captured in uart.raw')
                    watch_rc, watch_data, watch_digest = uart.command(
                        inspect_command, 'PWMW' + str(index), 45)
                    (out / ('watch-' + str(index) + '.output')).write_bytes(watch_data)
                    if watch_rc:
                        raise RuntimeError('Observation check failed: ' +
                                           watch_data.decode(errors='replace'))
                    snapshot = json.loads(watch_data)
                    if not snapshot['continuous_running'] or snapshot['boot_id'] != status['result']['boot_id']:
                        raise RuntimeError('Output stopped or board rebooted during observation')
                    status['watch']['snapshots'].append({
                        'elapsed_seconds': time.monotonic() - started,
                        'result_sha256': watch_digest, 'result': snapshot})
                    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
                    print(json.dumps({'observation_seconds': round(time.monotonic() - started, 1),
                                      'status': snapshot['registers']['status'],
                                      'boot_unchanged': True}), flush=True)
                status['watch']['complete'] = True
                status['watch']['elapsed_seconds'] = time.monotonic() - started
            status['complete'] = True
            if args.action == 'restore':
                bench['candidate_active'] = False
                bench['official_restored'] = True
                bench['restore_evidence'] = str(out)
                bench['continuous_running'] = False
            elif args.action == 'start':
                bench['start_sent'] = True
                bench['last_burst_evidence'] = str(out)
                bench['last_burst_control_verified'] = True
                bench['continuous_running'] = True
            elif args.action == 'stop':
                bench['continuous_running'] = False
                bench['last_stop_evidence'] = str(out)
            elif args.action == 'inspect':
                bench['continuous_running'] = status['result']['continuous_running']
                bench['last_inspect_evidence'] = str(out)
                bench['latest_inspect'] = str(out)
            (ROOT / 'CURRENT_BENCH.json').write_text(json.dumps(bench, indent=2) + '\n')
        finally:
            status['console_echo_restored'] = uart.close()
except Exception as exc:
    status['error'] = str(exc)
    if args.action in ('start','stop','scratch'):
        bench['complete'] = False
        bench['control_verification_required'] = True
        bench['failed_action'] = args.action
        bench['failed_action_evidence'] = str(out)
        if args.watch_seconds:
            bench['continuous_running'] = None
            bench['current_state_uncertain'] = True
        (ROOT / 'CURRENT_BENCH.json').write_text(json.dumps(bench, indent=2) + '\n')
    raise
finally:
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    (ROOT / ('CURRENT_' + args.action.upper() + '.json')).write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status, indent=2))
