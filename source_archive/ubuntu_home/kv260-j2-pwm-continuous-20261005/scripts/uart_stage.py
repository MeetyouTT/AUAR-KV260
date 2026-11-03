#!/usr/bin/env python3
"""Copy only the checked PWM archive into independent board staging over UART."""
import base64
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
EXPECTED_CID = '0353445345333247805558c00401a100'
stage = json.loads((ROOT / 'CURRENT_STAGE.json').read_text())
assert stage['complete'] and not stage['board_accessed']
source = Path(stage['archive'])
data = source.read_bytes()
assert hashlib.sha256(data).hexdigest() == stage['sha256'] and len(data) == stage['bytes']
tag = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT / 'evidence' / (tag + '-uart-stage')
out.mkdir(parents=True, exist_ok=False)
dest = '/home/root/aura-pwm-live-stage/' + tag + '/' + source.name
temp = dest + '.partial'
spec = importlib.util.spec_from_file_location('reviewed_uart', TRANSPORT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
status = {'phase': 'uart-stage', 'complete': False, 'evidence': str(out),
          'source': str(source), 'destination': dest, 'bytes': len(data),
          'sha256': stage['sha256'], 'frames': 0, 'pl_loaded': False,
          'start_sent': False}


def pycommand(code, *args):
    return 'python3 -B -c ' + shlex.quote(code) + ''.join(' ' + shlex.quote(str(a)) for a in args)


try:
    with (out / 'uart.raw').open('wb') as raw:
        uart = module.UART(raw)
        try:
            uart.connect()
            init = """import sys
from pathlib import Path
p=Path(sys.argv[1]);cid=Path('/sys/block/mmcblk1/device/cid').read_text().strip()
assert cid=='0353445345333247805558c00401a100'
assert not p.exists() and not Path(str(p)+'.partial').exists()
p.parent.mkdir(parents=True,exist_ok=True)
Path(str(p)+'.partial').open('xb').close()
print('STAGE_READY')"""
            rc, output, _ = uart.command(pycommand(init, dest), 'PWM_STAGE_READY', 30)
            assert rc == 0 and output.strip() == b'STAGE_READY', output
            write = """import base64,sys
from pathlib import Path
p=Path(sys.argv[1]);offset=int(sys.argv[2]);d=base64.b64decode(sys.argv[3],validate=True)
assert p.stat().st_size==offset
with p.open('ab') as f:f.write(d)
print('ACK',offset+len(d))"""
            for sequence, offset in enumerate(range(0, len(data), 1200)):
                chunk = data[offset:offset+1200]
                command = pycommand(write, temp, offset, base64.b64encode(chunk).decode())
                assert len(base64.b64encode(command.encode())) + 800 < 3800
                rc, output, _ = uart.command(command, 'PWM_STAGE_' + str(sequence), 30)
                assert rc == 0 and output.strip() == ('ACK ' + str(offset+len(chunk))).encode(), output
                status['frames'] = sequence + 1
                if status['frames'] % 10 == 0:
                    print(json.dumps({'frames': status['frames'], 'bytes_acked': offset+len(chunk)}), flush=True)
            finish = """import hashlib,os,sys
from pathlib import Path
p=Path(sys.argv[1]);dest=Path(sys.argv[2]);want=sys.argv[3];size=int(sys.argv[4])
with p.open('rb') as f:
 h=hashlib.sha256();n=0
 for chunk in iter(lambda:f.read(65536),b''):h.update(chunk);n+=len(chunk)
assert n==size and h.hexdigest()==want and not dest.exists()
os.link(p,dest);p.unlink()
print('STAGE_HASH_OK',n,h.hexdigest())"""
            rc, output, _ = uart.command(pycommand(finish, temp, dest, stage['sha256'], len(data)),
                                          'PWM_STAGE_FINISH', 30)
            assert rc == 0 and output.strip() == (
                'STAGE_HASH_OK ' + str(len(data)) + ' ' + stage['sha256']).encode(), output
            status['complete'] = True
        finally:
            status['console_echo_restored'] = uart.close()
except Exception as exc:
    status['error'] = str(exc)
    raise
finally:
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    (ROOT / 'CURRENT_BOARD_STAGE.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status, indent=2))
