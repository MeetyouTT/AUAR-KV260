"""Run a recorded helper through the existing checked UART transport."""
import argparse
import base64
import datetime
import hashlib
import importlib.util
import io
import gzip
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='board_probe.py')
    parser.add_argument('--phase', default='environment')
    parser.add_argument('--stage-capture', action='store_true')
    parser.add_argument('--stage-helper', action='store_true')
    args = parser.parse_args()
    source_path = (ROOT / args.source).resolve(strict=True)
    if source_path.parent != ROOT or not args.phase.replace('-', '').isalnum():
        raise ValueError('Helper and phase must belong to this work directory')
    source = source_path.read_text()
    spec = importlib.util.spec_from_file_location('audio_uart',
        '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
    wire = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wire)
    commands = []
    if args.stage_capture:
        manifest = json.loads((ROOT/'capture_bundle.json').read_text())
        blob = (ROOT/manifest['zip']).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == manifest['sha256']
        board_root = manifest['board_root']
        assert board_root.startswith('/home/root/aura-audio-capture-20261015/releases/')
        common = 'from pathlib import Path\nimport base64,hashlib,json\np=Path(%r)\np.mkdir(parents=True,exist_ok=True)\n' % board_root
        names = []
        for index, start in enumerate(range(0, len(blob), 600)):
            name = 'fragment-%03d' % index
            names.append(name)
            part = blob[start:start+600]
            code = common+'d=base64.b64decode(%r,validate=True)\nf=p/%r\n' % (base64.b64encode(part).decode(),name)
            code += 'if f.exists():assert f.read_bytes()==d\nelse:\n with f.open("xb") as s:s.write(d)\nprint(json.dumps({"part":%d,"bytes":len(d)}))\n' % index
            commands.append(('stage-%03d' % index, code))
        code = common+'import io,zipfile\nd=b"".join((p/n).read_bytes() for n in %r)\n' % names
        code += 'assert hashlib.sha256(d).hexdigest()==%r\n' % manifest['sha256']
        code += 'with zipfile.ZipFile(io.BytesIO(d)) as z:\n m=json.loads(z.read("manifest.json"))\n for n,r in m["files"].items():\n  assert not Path(n).is_absolute() and ".." not in Path(n).parts\n  b=z.read(n);assert len(b)==r["bytes"] and hashlib.sha256(b).hexdigest()==r["sha256"]\n  f=p/"aura"/n;f.parent.mkdir(parents=True,exist_ok=True)\n  if f.exists():assert f.read_bytes()==b\n  else:\n   with f.open("xb") as s:s.write(b)\n print(json.dumps({"release_id":m["release_id"],"files_verified":len(m["files"]),"root":str(p)}))\n'
        commands.append(('stage-verify', code))
    elif args.stage_helper:
        data = source.encode()
        compressed = gzip.compress(data, mtime=0)
        digest = hashlib.sha256(data).hexdigest()
        directory = '/home/root/aura-audio-capture-20261015/helpers/'+digest[:16]
        common = 'from pathlib import Path\nimport base64,hashlib,json\np=Path(%r)\np.mkdir(parents=True,exist_ok=True)\n' % directory
        names = []
        for index, start in enumerate(range(0, len(compressed), 600)):
            name = 'fragment-%03d' % index
            names.append(name)
            code = common+'d=base64.b64decode(%r,validate=True)\nf=p/%r\n' % (base64.b64encode(compressed[start:start+600]).decode(),name)
            code += 'if f.exists():assert f.read_bytes()==d\nelse:\n with f.open("xb") as s:s.write(d)\nprint(json.dumps({"part":%d}))\n' % index
            commands.append(('helper-%03d' % index, code))
        code = common+'import gzip\nd=gzip.decompress(b"".join((p/n).read_bytes() for n in %r))\n' % names
        code += 'assert hashlib.sha256(d).hexdigest()==%r\nf=p/"source.py"\n' % digest
        code += 'if f.exists():assert f.read_bytes()==d\nelse:\n with f.open("xb") as s:s.write(d)\nexec(compile(d,str(f),"exec"))\n'
        commands.append(('response', code))
    else:
        commands.append(('response', source))
    commands = [(name, wire.wire(code)) for name, code in commands]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    folder = ROOT / 'evidence' / (stamp + '-' + args.phase)
    folder.mkdir(parents=True, exist_ok=False, mode=0o700)
    (folder / 'source.py').write_text(source)
    for name, command in commands:
        (folder / (name+'.command')).write_text(command+'\n')
    result = {'complete': False, 'phase': args.phase,
              'source_sha256': hashlib.sha256(source.encode()).hexdigest(), 'commands': []}
    uart = None
    try:
        with (folder / 'serial.raw').open('xb') as raw:
            try:
                uart = wire.transport_module().UART(raw)
                uart.connect()
                for index, (name, command) in enumerate(commands):
                    rc, body, digest = uart.command(command, 'MEDIA%03d' % index, 45)
                    (folder / (name+'.output')).write_bytes(body)
                    result['commands'].append({'name':name,'exit_code':rc,'bytes':len(body),'sha256':digest})
                    if rc:
                        raise RuntimeError(body.decode(errors='replace')[-2000:])
                    value = json.loads(body)
                    artifacts = value.pop('artifacts', {})
                    for filename, artifact in artifacts.items():
                        assert Path(filename).name == filename
                        data = base64.b64decode(artifact.pop('base64'),validate=True)
                        assert len(data)==artifact['bytes'] and hashlib.sha256(data).hexdigest()==artifact['sha256']
                        fd = os.open(str(folder/filename),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                        with os.fdopen(fd,'wb') as out:out.write(data)
                    if artifacts:
                        value['saved_artifacts'] = artifacts
                    (folder / (name+'.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
                    print(json.dumps({'evidence': str(folder), 'step':name, 'response':value}, ensure_ascii=False), flush=True)
                result['complete'] = True
            finally:
                if uart:
                    result['console_echo_restored'] = uart.close()
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    (folder / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
