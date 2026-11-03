"""Build and deploy a small, hashed camera release over the existing UART."""
import base64
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shlex
import zipfile

ROOT = Path(__file__).resolve().parent
AURA = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
BOARD = '/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura/'
spec = importlib.util.spec_from_file_location('hotplug_wire', '/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py')
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
inventory = json.loads(Path('/home/ghmd/kv260-display-check-20261017/evidence/20261017T110932.416900Z/camera_hotplug_inventory.json').read_text())
names = ['board/vision/camera_device.py', 'board/vision/ui_camera_service.py',
         'config/board_camera_ui.json', 'scripts/board_camera_ui/aura-camera-ui.service',
         'tests/framework/test_camera_device.py']
payload = {name: (AURA/name).read_bytes() for name in names}
payload['installed-camera.service'] = payload['scripts/board_camera_ui/aura-camera-ui.service']
files = {}
for name, data in payload.items():
    target = '/etc/systemd/system/aura-camera-ui.service' if name == 'installed-camera.service' else BOARD + name
    files[name] = {'target': target, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                   'before_sha256': inventory['files'].get(target, {}).get('sha256')}
release_id = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:16]
manifest = {'release_id': release_id, 'files': files}
(ROOT/'manifest.json').write_text(json.dumps(manifest, indent=2))
blob = io.BytesIO()
with zipfile.ZipFile(blob, 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('manifest.json', json.dumps(manifest))
    archive.writestr('board_apply.py', (ROOT/'board_apply.py').read_bytes())
    for name, data in payload.items():
        archive.writestr('payload/' + name, data)
data = blob.getvalue()
(ROOT/('release-' + release_id + '.zip')).write_bytes(data)
stage = '/home/root/aura-camera-hotplug-20261017/release-' + release_id
common = 'from pathlib import Path\nimport base64,hashlib,json\np=Path(%r)\np.mkdir(parents=True,exist_ok=True)\n' % stage
commands = []
parts = []
for index, start in enumerate(range(0, len(data), 850)):
    name = 'part-%03d' % index
    parts.append(name)
    source = common + 'b=base64.b64decode(%r,validate=True)\nf=p/%r\n' % (base64.b64encode(data[start:start+850]).decode(), name)
    source += 'if f.exists():assert f.read_bytes()==b\nelse:\n with f.open("xb") as s:s.write(b)\nprint(json.dumps({"part":%d,"bytes":len(b)}))\n' % index
    commands.append((name, wire.wire(source), 20))
source = common + 'import io,zipfile\nb=b"".join((p/n).read_bytes() for n in %r)\n' % parts
source += 'assert hashlib.sha256(b).hexdigest()==%r\n' % hashlib.sha256(data).hexdigest()
source += '''with zipfile.ZipFile(io.BytesIO(b)) as z:
 for name in z.namelist():
  rel=Path(name);assert not rel.is_absolute() and '..' not in rel.parts
  f=p/rel;f.parent.mkdir(parents=True,exist_ok=True);body=z.read(name)
  if f.exists():assert f.read_bytes()==body
  else:
   with f.open('xb') as s:s.write(body)
print(json.dumps({'staged':str(p),'bytes':len(b)}))
'''
commands.append(('stage-verify', wire.wire(source), 25))
commands.append(('apply', 'python3 -B ' + shlex.quote(stage + '/board_apply.py'), 90))
folder = ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
folder.mkdir(parents=True, exist_ok=False)
status = {'complete': False, 'release_id': release_id, 'stage': stage, 'responses': []}
uart = None
try:
    with (folder/'serial.raw').open('xb') as raw:
        try:
            uart = wire.transport_module().UART(raw)
            uart.connect()
            for index, (name, command, timeout) in enumerate(commands):
                (folder/(name+'.command')).write_text(command)
                rc, response, digest = uart.command(command, 'HOTPLUG%03d' % index, timeout)
                (folder/(name+'.output')).write_bytes(response)
                status['responses'].append({'name': name, 'exit_code': rc, 'sha256': digest})
                if rc:
                    raise RuntimeError(response.decode(errors='replace')[-4000:])
                value = json.loads(response)
                (folder/(name+'.json')).write_text(json.dumps(value, indent=2))
                print(json.dumps({'step': name, 'result': value}), flush=True)
            status['complete'] = True
        finally:
            if uart:
                status['console_echo_restored'] = uart.close()
except Exception as exc:
    status['error'] = str(exc)
(folder/'result.json').write_text(json.dumps(status, indent=2))
print(json.dumps({'evidence': str(folder), **status}), flush=True)
raise SystemExit(0 if status['complete'] else 1)
