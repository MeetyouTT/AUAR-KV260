"""Recorded single-UART commands for this bounded camera/UI update."""
import argparse
import base64
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('tracking_wire', '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)


def target_commands(phase='target'):
    """Stage only the acceptance helper in bounded, hash-checked UART chunks."""
    helper_name = 'board_' + phase + '.py'
    data = (ROOT / helper_name).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    stage = '/home/root/aura-bytetrack-20261011/live-acceptance-' + digest[:16]
    common = 'from pathlib import Path\nimport base64,hashlib,json\np=Path(%r)\n' % stage
    commands = [{'label': phase + '-prepare', 'source': common + 'p.mkdir(parents=True,exist_ok=True)\n', 'timeout': 20}]
    fragments = []
    for index, start in enumerate(range(0, len(data), 900)):
        name = 'fragment-%03d' % index
        fragments.append(name)
        encoded = base64.b64encode(data[start:start + 900]).decode()
        source = common + "blob=base64.b64decode(%r,validate=True)\nf=p/%r\n" % (encoded, name)
        source += "if f.exists():assert f.read_bytes()==blob\nelse:\n with f.open('xb') as stream:stream.write(blob)\n"
        source += "print(json.dumps({'fragment':f.name,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}))\n"
        commands.append({'label': name, 'source': source, 'timeout': 20})
    source = common + "blob=b''.join((p/name).read_bytes() for name in %r)\n" % fragments
    source += "assert len(blob)==%d and hashlib.sha256(blob).hexdigest()==%r\n" % (len(data), digest)
    source += "f=p/%r\nif f.exists():assert f.read_bytes()==blob\nelse:\n with f.open('xb') as stream:stream.write(blob)\n" % helper_name
    source += "compile(blob,str(f),'exec')\nprint(json.dumps({'helper':str(f),'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}))\n"
    commands.append({'label': phase + '-verify', 'source': source, 'timeout': 20})
    source = common + "f=p/%r\nassert hashlib.sha256(f.read_bytes()).hexdigest()==%r\n" % (helper_name, digest)
    source += "import subprocess\nraise SystemExit(subprocess.call(['python3','-B',str(f)]))\n"
    commands.append({'label': phase, 'source': source, 'timeout': 150})
    return commands


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True, choices=['inspect', 'stage', 'probe', 'deploy', 'final', 'target', 'choice', 'select', 'screen', 'live', 'watch', 'rollback'])
    args = parser.parse_args()
    if args.phase in ('target', 'select', 'live'):
        commands = target_commands(args.phase)
    elif args.phase == 'stage':
        commands = json.loads((ROOT / (args.phase + '_commands.json')).read_text())
    else:
        commands = [{'label': args.phase, 'source': (ROOT / ('board_' + args.phase + '.py')).read_text(), 'timeout': 150}]
    # Compile and check line limits before opening or changing the console.
    for row in commands:
        row['wire_command'] = wire.wire(row['source'])
    folder = ROOT / 'evidence' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-' + args.phase)
    folder.mkdir(parents=True)
    result = {'complete': False, 'phase': args.phase, 'commands': []}
    uart = None
    with (folder / 'serial.raw').open('xb') as raw:
        try:
            uart = wire.transport_module().UART(raw)
            uart.connect()
            print(json.dumps({'evidence': str(folder)}), flush=True)
            for index, row in enumerate(commands):
                label = row['label']
                command = row['wire_command']
                (folder / (label + '.command')).write_text(command + '\n')
                rc, body, digest = uart.command(command, 'BT%03d' % index, row.get('timeout', 25))
                (folder / (label + '.output')).write_bytes(body)
                result['commands'].append({'label': label, 'exit_code': rc, 'bytes': len(body), 'sha256': digest})
                if rc:
                    raise RuntimeError(body.decode(errors='replace')[-4000:])
                if body.strip():
                    value = json.loads(body)
                    for name, artifact in value.pop('artifacts', {}).items():
                        assert Path(name).name == name
                        blob = base64.b64decode(artifact.pop('base64'), validate=True)
                        assert len(blob) == artifact['bytes'] and hashlib.sha256(blob).hexdigest() == artifact['sha256']
                        (folder / name).write_bytes(blob)
                    (folder / (label + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
                    print(json.dumps({'step': label, 'result': value}, ensure_ascii=False)[:3200], flush=True)
                elif index % 10 == 0:
                    print(json.dumps({'completed': index + 1, 'total': len(commands)}), flush=True)
                (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            result['complete'] = True
        except Exception as exc:
            result['error'] = type(exc).__name__ + ': ' + str(exc)
        finally:
            if uart:
                result['console_echo_restored'] = uart.close()
            (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
