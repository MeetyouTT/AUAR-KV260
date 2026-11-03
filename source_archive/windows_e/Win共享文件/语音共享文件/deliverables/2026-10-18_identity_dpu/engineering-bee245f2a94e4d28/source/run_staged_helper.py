"""Integrity-stage a long owned helper and run it with recorded UART responses."""
import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source')
parser.add_argument('--phase', required=True)
args = parser.parse_args()
source = (ROOT/args.source).resolve()
assert source.parent == ROOT and args.phase.replace('-', '').isalnum()
raw_source = source.read_bytes()
compile(raw_source, str(source), 'exec')
digest = hashlib.sha256(raw_source).hexdigest()
remote = '/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/'+digest[:16]
common = "import os,json,hashlib,base64\nfrom pathlib import Path\nassert os.uname().machine=='aarch64'\nassert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'\np=Path(%r)\np.mkdir(parents=True,exist_ok=True)\nassert not p.is_symlink()\n" % remote
payload = gzip.compress(raw_source, mtime=0)
commands = []
names = []
for i, start in enumerate(range(0, len(payload), 600)):
    name = 'fragment-%03d' % i
    names.append(name)
    code = common+'data=base64.b64decode(%r)\nf=p/%r\n' % (base64.b64encode(payload[start:start+600]).decode(), name)
    code += "if f.exists():assert not f.is_symlink() and f.read_bytes()==data\nelse:\n with f.open('xb') as s:s.write(data)\nprint(json.dumps({'staged_fragment':%d}))\n" % i
    commands.append(('fragment-%03d' % i, code))
code = common+'import gzip\ndata=gzip.decompress(b"".join((p/n).read_bytes() for n in %r))\nassert hashlib.sha256(data).hexdigest()==%r\nf=p/"source.py"\n' % (names, digest)
code += "if f.exists():assert not f.is_symlink() and f.read_bytes()==data\nelse:\n with f.open('xb') as s:s.write(data)\nexec(compile(data,str(f),'exec'))\n"
commands.append(('response', code))
spec = importlib.util.spec_from_file_location('checked_wire', '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
commands = [(name, wire.wire(code)) for name, code in commands]
out = ROOT/'evidence'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+args.phase)
out.mkdir(parents=True)
(out/'source.py').write_bytes(raw_source)
status = {'complete': False, 'source_sha256': digest, 'evidence': str(out), 'responses': []}
uart = None
try:
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart = wire.transport_module().UART(raw)
            uart.connect()
            for i, (name, command) in enumerate(commands):
                rc, body, sha = uart.command(command, 'SFACE%03d' % i, 85 if name == 'response' else 15)
                (out/(name+'.output')).write_bytes(body)
                status['responses'].append({'name': name, 'exit_code': rc, 'sha256': sha, 'bytes': len(body)})
                if rc:
                    raise RuntimeError(body.decode(errors='replace')[-2000:])
                value = json.loads(body)
                (out/(name+'.json')).write_text(json.dumps(value, indent=2)+'\n')
                if name == 'response':
                    print(json.dumps(value), flush=True)
            status['complete'] = True
        finally:
            if uart:
                status['console_echo_restored'] = uart.close()
except Exception as exc:
    status['error'] = str(exc)
(out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
(ROOT/('latest-'+args.phase+'.json')).write_text(json.dumps(status, indent=2)+'\n')
print(json.dumps(status), flush=True)
raise SystemExit(0 if status['complete'] else 1)
