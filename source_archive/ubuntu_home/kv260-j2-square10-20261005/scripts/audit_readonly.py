#!/usr/bin/env python3
"""Sample the existing guarded accessor in inspect mode; never change PL/output."""
import ast
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
stage = json.loads((ROOT / 'CURRENT_BOARD_STAGE.json').read_text())
bench = json.loads((ROOT / 'CURRENT_BENCH.json').read_text())
assert stage['complete'] and bench['candidate_active']
assert stage['destination'] == bench['archive']
tree = ast.parse((ROOT / 'scripts/uart_load.py').read_text())
common = next(ast.literal_eval(n.value) for n in tree.body
              if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
              and n.targets[0].id == 'COMMON')
source = common + r'''
assert active()==[APP] and fw()==FW and state()=='operating'
original=check_official_hashes()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==original['boot_id']
manifest=json.loads((package/'manifest.json').read_text())
for relative,meta in manifest.items():
 assert hashlib.sha256((package/relative).read_bytes()).hexdigest()==meta['sha256']
 if relative.startswith('lib/firmware/'):
  assert hashlib.sha256((Path('/')/relative).read_bytes()).hexdigest()==meta['sha256']
samples=[];started=time.monotonic()
for index in range(48):
 before=time.monotonic()-started
 values=json.loads(run([str(package/'board/mmio32'),'inspect'],5))
 after=time.monotonic()-started
 assert values['build_id']=='0x79b89dfe' and values['status'] in (5,7)
 assert values['period_ticks']==9999900 and values['pulse_ticks']==4999950
 samples.append({'before_seconds':before,'after_seconds':after,'status':values['status']})
 time.sleep(.01)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==original['boot_id']
print(json.dumps({'boot_id':original['boot_id'],'firmware':FW,'samples':samples,
 'output_logic_levels_seen':sorted(set((s['status']>>1)&1 for s in samples)),
 'writes_performed':False,'external_voltage_measured':False}))
'''
compile(source, '<readonly-audit>', 'exec')
tag = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT / 'evidence' / (tag + '-readonly-audit')
out.mkdir(exist_ok=False)
(out / 'remote.py').write_text(source)
transport = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
spec = importlib.util.spec_from_file_location('reviewed_uart', transport)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
payload = base64.b64encode(gzip.compress(source.encode(), mtime=0)).decode()
code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(payload) + ')))'
command = 'python3 -B -c ' + shlex.quote(code) + ' ' + shlex.quote(stage['destination']) + ' ' + stage['sha256']
transport_tree = ast.parse(transport.read_text())
method = next(n for n in ast.walk(transport_tree) if isinstance(n, ast.FunctionDef) and n.name == 'command')
wrapper = ast.literal_eval(method.body[0].value)
wire = 'python3 -B -c ' + shlex.quote(wrapper) + ' ' + shlex.quote(base64.b64encode(command.encode()).decode()) + ' PWM_AUDIT'
assert len(wire.encode()) <= 3800, len(wire.encode())
status = {'complete': False, 'evidence': str(out), 'wire_bytes': len(wire.encode()),
          'writes_performed': False, 'transport_sha256': hashlib.sha256(transport.read_bytes()).hexdigest()}
try:
    with (out / 'uart.raw').open('wb') as raw:
        uart = module.UART(raw)
        try:
            uart.connect()
            rc, data, digest = uart.command(command, 'PWM_AUDIT', 45)
            (out / 'result.output').write_bytes(data)
            status.update(rc=rc, result_sha256=digest)
            if rc:
                raise RuntimeError(data.decode(errors='replace'))
            status.update(complete=True, result=json.loads(data))
        finally:
            status['console_echo_restored'] = uart.close()
finally:
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    (ROOT / 'CURRENT_READONLY_AUDIT.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps({k:v for k,v in status.items() if k!='result'}))
    if status.get('result'):
        print(json.dumps({k:v for k,v in status['result'].items() if k!='samples'}))
