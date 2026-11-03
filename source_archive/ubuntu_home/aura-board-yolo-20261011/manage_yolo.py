#!/usr/bin/env python3
"""Single-UART, recorded YOLO integration commands; no PL or motion control."""
import argparse
import base64
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import zipfile

WORK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('aura_yolo_wire', '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)


def probe_commands(stage_only=False):
    if not stage_only:
        saved = json.loads((WORK / 'probe_manifest.json').read_text())
        path = saved['stage'] + '/probe_model.py'
        program = 'import hashlib,subprocess\np=' + repr(path) + '\nassert hashlib.sha256(open(p,"rb").read()).hexdigest()==' + repr(saved['files']['probe_model.py']['sha256']) + '\nraise SystemExit(subprocess.call(["python3","-B",p]))'
        return [('probe', wire.wire(program), 90)]
    previous = json.loads((WORK / 'probe_manifest.json').read_text()) if (WORK / 'probe_manifest.json').exists() else None
    repo = Path('/home/ghmd/Win共享文件/共享文件夹/aura/board/vision')
    files = {name: (repo / 'native' / name).read_bytes() for name in ['yolox_bridge.cpp', 'build_yolox.py']}
    files.update({'yolo_dpu.py': (repo / 'yolo_dpu.py').read_bytes(),
                  'probe_model.py': (WORK / 'probe_model.py').read_bytes(),
                  'bus-reference.jpg': (WORK / 'bus-reference.jpg').read_bytes()})
    manifest = {name: {'sha256': hashlib.sha256(blob).hexdigest(), 'bytes': len(blob)} for name, blob in files.items()}
    release_id = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
    stage = '/home/root/aura-yolo-20261011/probe-' + release_id
    (WORK / 'probe_manifest.json').write_text(json.dumps({'stage': stage, 'files': manifest}, indent=2) + '\n')
    archive = WORK / ('probe-' + release_id + '.zip')
    base = previous['stage'] if previous and previous['stage'] != stage else ''
    changed = {name for name, row in manifest.items() if not base or previous['files'].get(name) != row}
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as stream:
        for name, blob in files.items():
            if name in changed:stream.writestr(name, blob)
        stream.writestr('manifest.json', json.dumps(manifest))
    data = archive.read_bytes()
    payload = base64.b64encode(data).decode()
    commands = [('prepare', wire.wire('from pathlib import Path;Path(' + repr(stage) + ').mkdir(parents=True,exist_ok=True)'), 15)]
    for index, start in enumerate(range(0, len(payload), 1500)):
        chunk = payload[start:start + 1500]
        program = 'from pathlib import Path;import hashlib\np=Path(' + repr(stage + '/probe.zip.b64.part') + ')\ns=' + repr(chunk) + '\nn=p.stat().st_size if p.exists() else 0\nassert n>=' + str(start) + '\n'
        program += 'if n==' + str(start) + ':\n with p.open("ab") as f:f.write(s.encode())\n'
        program += 'assert hashlib.sha256(p.read_bytes()[:' + str(start + len(chunk)) + ']).hexdigest()==' + repr(hashlib.sha256(payload[:start + len(chunk)].encode()).hexdigest())
        commands.append(('chunk-%03d' % index, wire.wire(program), 15))
    program = '''import base64,hashlib,io,json,zipfile
from pathlib import Path
root=Path(STAGE);data=base64.b64decode((root/'probe.zip.b64.part').read_bytes(),validate=True)
assert hashlib.sha256(data).hexdigest()==SHA
with zipfile.ZipFile(io.BytesIO(data)) as archive:
 manifest=json.loads(archive.read('manifest.json'));assert archive.testzip() is None
 assert set(archive.namelist())<=set(manifest)|{'manifest.json'}
 for name in list(manifest)+['manifest.json']:
  assert '/' not in name and '..' not in name
  blob=archive.read(name) if name in archive.namelist() else (Path(BASE)/name).read_bytes()
  if name!='manifest.json':assert len(blob)==manifest[name]['bytes'] and hashlib.sha256(blob).hexdigest()==manifest[name]['sha256']
  if name.endswith('.py'):compile(blob,name,'exec')
  p=root/name
  if p.exists():assert p.read_bytes()==blob
  else:
   with p.open('xb') as stream:stream.write(blob)
print(json.dumps({'stage':STAGE,'verified':True,'files':manifest}))
'''
    commands.append(('verify', wire.wire('STAGE=' + repr(stage) + '\nBASE=' + repr(base) + '\nSHA=' + repr(hashlib.sha256(data).hexdigest()) + '\n' + program), 20))
    return commands


def update_commands(phase):
    meta = json.loads((WORK / 'package_validation.json').read_text())
    manifest = json.loads((WORK / 'manifest.json').read_text())
    stage = '/home/root/aura-yolo-20261011/update-' + meta['update_id']
    commands = []
    if phase in ('stage', 'deploy'):
        data = Path(meta['delta_archive']).read_bytes()
        assert len(data) == meta['delta_bytes'] and hashlib.sha256(data).hexdigest() == meta['delta_sha256']
        payload = base64.b64encode(data).decode()
        commands.append(('prepare', wire.wire('from pathlib import Path;Path(' + repr(stage) + ').mkdir(parents=True,exist_ok=True)'), 15))
        for index, start in enumerate(range(0, len(payload), 1500)):
            chunk = payload[start:start + 1500]
            program = 'from pathlib import Path;import hashlib\np=Path(' + repr(stage + '/update.zip.b64.part') + ')\ns=' + repr(chunk) + '\nn=p.stat().st_size if p.exists() else 0\nassert n>=' + str(start) + '\n'
            program += 'if n==' + str(start) + ':\n with p.open("ab") as f:f.write(s.encode())\n'
            program += 'assert hashlib.sha256(p.read_bytes()[:' + str(start + len(chunk)) + ']).hexdigest()==' + repr(hashlib.sha256(payload[:start + len(chunk)].encode()).hexdigest())
            commands.append(('chunk-%03d' % index, wire.wire(program), 15))
        program = '''import base64,hashlib,io,json,zipfile
from pathlib import Path,PurePosixPath
root=Path(STAGE);data=base64.b64decode((root/'update.zip.b64.part').read_bytes(),validate=True)
assert hashlib.sha256(data).hexdigest()==SHA
with zipfile.ZipFile(io.BytesIO(data)) as archive:
 manifest=json.loads(archive.read('manifest.json'));assert archive.testzip() is None
 assert set(archive.namelist())<=set(manifest['files'])|{'manifest.json'}
 for name in list(manifest['files'])+['manifest.json']:
  rel=PurePosixPath(name);assert not rel.is_absolute() and '..' not in rel.parts
  blob=archive.read(name) if name in archive.namelist() else Path(manifest['verified_board_seeds'][name]).read_bytes()
  if name!='manifest.json':
   row=manifest['files'][name];assert len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],name
  if name.endswith('.py'):compile(blob,name,'exec')
  p=root/'payload'/name;p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists():assert p.read_bytes()==blob
  else:
   with p.open('xb') as stream:stream.write(blob)
print(json.dumps({'stage':STAGE,'verified':True,'payload_files':len(manifest['files'])}))
'''
        commands.append(('verify', wire.wire('STAGE=' + repr(stage) + '\nSHA=' + repr(meta['delta_sha256']) + '\n' + program), 25))
    if phase in ('apply', 'deploy', 'rollback'):
        path = stage + '/payload/board_apply.py'
        action = 'rollback' if phase == 'rollback' else 'apply'
        program = 'import hashlib,subprocess\np=' + repr(path) + '\nassert hashlib.sha256(open(p,"rb").read()).hexdigest()==' + repr(manifest['files']['board_apply.py']['sha256']) + '\nraise SystemExit(subprocess.call(["python3","-B",p,"--phase",' + repr(action) + ']))'
        commands.append((action, wire.wire(program), 140))
    if phase in ('status', 'deploy', 'final'):
        commands.append(('status', wire.wire('STAGE=' + repr(stage) + '\n' + (WORK / 'board_status.py').read_text()), 120))
    if phase == 'final':
        commands.append(('watch', wire.wire((WORK / 'board_watch.py').read_text()), 45))
    if phase in ('acceptance', 'deploy'):
        path = stage + '/payload/board_camera_control.py'
        program = 'import hashlib,subprocess\np=' + repr(path) + '\nassert hashlib.sha256(open(p,"rb").read()).hexdigest()==' + repr(manifest['files']['board_camera_control.py']['sha256']) + '\nraise SystemExit(subprocess.call(["python3","-B",p,"--phase","camera-test"]))'
        commands.append(('camera-test', wire.wire(program), 90))
    if phase in ('profile', 'deploy'):
        commands.append(('profile', wire.wire((WORK.parent / 'aura-board-ui-design-20261009/board_preview_profile.py').read_text()), 60))
    return commands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('inspect', 'model_inspect', 'model_probe', 'probe_stage', 'probe',
        'stage', 'apply', 'status', 'acceptance', 'profile', 'deploy', 'rollback', 'final'), required=True)
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    update_phase = args.phase in ('stage', 'apply', 'status', 'acceptance', 'profile', 'deploy', 'rollback', 'final')
    source = '' if update_phase or args.phase in ('probe_stage', 'probe') else (WORK / ('board_' + args.phase + '.py')).read_text()
    commands = update_commands(args.phase) if update_phase else probe_commands(args.phase == 'probe_stage') if args.phase in ('probe_stage', 'probe') else [(args.phase, wire.wire(source), 90)]
    if args.validate:
        print(json.dumps({'phase': args.phase, 'board_accessed': False, 'commands': len(commands), 'source_sha256': hashlib.sha256(source.encode()).hexdigest()}))
        return 0
    folder = WORK / 'evidence' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-' + args.phase)
    folder.mkdir(parents=True)
    result = {'phase': args.phase, 'source_sha256': hashlib.sha256(source.encode()).hexdigest(), 'complete': False, 'commands': []}
    result['command_set_sha256'] = hashlib.sha256('\n'.join(c for _,c,_ in commands).encode()).hexdigest()
    uart = None
    with (folder / 'serial.raw').open('xb') as raw:
        try:
            uart = wire.transport_module().UART(raw)
            uart.connect()
            print(json.dumps({'evidence': str(folder), 'root_shell_confirmed': True}), flush=True)
            for index, (label, command, timeout) in enumerate(commands):
                (folder / (label + '.command')).write_text(command + '\n')
                rc, body, digest = uart.command(command, 'YL%03d' % index, timeout)
                (folder / (label + '.output')).write_bytes(body)
                result['commands'].append({'label': label, 'exit_code': rc, 'bytes': len(body), 'sha256': digest})
                (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
                if rc:
                    raise RuntimeError(label + ': ' + body.decode(errors='replace')[-7000:])
                if body.strip():
                    value = json.loads(body)
                    for name, artifact in value.pop('artifacts', {}).items():
                        assert Path(name).name == name
                        blob = base64.b64decode(artifact.pop('base64'), validate=True)
                        assert len(blob) == artifact['bytes'] and hashlib.sha256(blob).hexdigest() == artifact['sha256']
                        (folder / name).write_bytes(blob)
                    for name in ('screenshot', 'main_screenshot'):
                        shot = value.get(name)
                        if shot:
                            blob = base64.b64decode(shot.pop('jpeg_base64'), validate=True)
                            assert len(blob) == shot['bytes'] and hashlib.sha256(blob).hexdigest() == shot['sha256']
                            (folder / (name + '.jpg')).write_bytes(blob)
                    (folder / (label + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
                    print(json.dumps({'step': label, 'result': value}, ensure_ascii=False)[:5500], flush=True)
                elif index % 10 == 0:
                    print(json.dumps({'step': label, 'completed': index + 1, 'total': len(commands)}), flush=True)
            result['complete'] = True
        except Exception as exc:
            result['error'] = type(exc).__name__ + ': ' + str(exc)
            print(json.dumps({'error': result['error']}), flush=True)
        finally:
            if uart:
                result['console_echo_restored'] = uart.close()
            (folder / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in dict(result, evidence=str(folder)).items() if k != 'commands'}), flush=True)
    return 0 if result['complete'] and result.get('console_echo_restored') else 1


if __name__ == '__main__':
    raise SystemExit(main())
