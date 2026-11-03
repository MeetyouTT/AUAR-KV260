"""Read-only script for the later exclusive idle layout phase.

Requires EXPECTED and the local X11 helper source injected by its granted
caller. No UI command, file write, service action, media or private DB read.
"""
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import subprocess


def raw(path, limit=16777216):
    path = Path(path)
    assert path.is_absolute() and path.resolve() == path and not path.is_symlink()
    fd = os.open(path,os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as f:
        a = os.fstat(f.fileno()); assert stat.S_ISREG(a.st_mode) and a.st_size <= limit
        data = f.read(limit+1); b = os.fstat(f.fileno())
    assert len(data) <= limit
    identity = lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_uid,s.st_gid)
    assert identity(a) == identity(b) == identity(path.stat())
    return data


def digest(data): return hashlib.sha256(data).hexdigest()
def owner(pid):
    p = Path('/proc')/str(pid)
    return dict(pid=int(pid),birth_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19],
                command_sha256=digest((p/'cmdline').read_bytes()))
def unit(name):
    p = subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,FragmentPath,DropInPaths'],capture_output=True,text=True,timeout=5)
    assert p.returncode == 0
    return dict(row.split('=',1) for row in p.stdout.splitlines() if '=' in row)


assert EXPECTED['all_other_device_access_frozen'] is True
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == EXPECTED['boot_id']
startup_path = Path(EXPECTED['startup_path']); startup_raw = raw(startup_path)
assert digest(startup_raw) == EXPECTED['startup_sha256']
startup = json.loads(startup_raw); aura = Path(startup['runtime'])/'aura'; pins = startup['component_sha256']
assert len(pins) == 380
script = Path('/home/root/aura-boundary-nav-20261029/editor-page-sync-v2/face_zone_editor.py')
source_raw = raw(script)
assert digest(source_raw) == '6a8bce7270534bb3b0f71dff657eac5da92b46855fdb7c9748a63b678be8ede4'
references = []
for path,sha in pins.items():
    data = raw(aura/path); assert digest(data) == sha
    if str(script).encode() in data or digest(source_raw).encode() in data: references.append(path)
units = {name:unit(name) for name in ('aura-avatar-ui.service','aura-camera-ui.service','aura-face-zone-editor.service')}
for value in units.values(): assert value['ActiveState'] == 'active' and value['SubState'] == 'running' and not value['Job'] and int(value['MainPID']) > 0
owners = {name:owner(int(value['MainPID'])) for name,value in units.items()}
for name,prior in EXPECTED['owners'].items(): assert owners[name] == prior
c = http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:
    c.request('GET','/api/state');response = c.getresponse();body = response.read(2097153)
    assert response.status == 200 and len(body) <= 2097152; view = json.loads(body)
finally: c.close()
hf = view['handsfree_dialogue']; business = view['board_business']
assert hf['enabled'] is False and hf['microphone_open'] is False and hf['state'] == 'PAUSED'
assert view['phase'] == 'IDLE' and view['playing'] is False and not view['pending_job']
assert view['manual_pan']['automatic_following'] is False
assert business['speaker']['active'] is False and business['speaker']['queued_or_active'] == 0
assert business['dialogue']['voice_enrollment']['active'] is False
assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json')) == {'version':1,'enabled':False}
editor_owner = owners['aura-face-zone-editor.service']
argv = (Path('/proc')/str(editor_owner['pid'])/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
assert str(script).encode() in argv
related = {}
paths = {units['aura-face-zone-editor.service']['FragmentPath']} | set(units['aura-face-zone-editor.service']['DropInPaths'].split())
paths |= {str(script.parent/name) for name in ('manifest.json','source-manifest.json','runtime-manifest.json','deployment.json') if (script.parent/name).is_file()}
for path in sorted(paths):
    data = raw(path,1048576)
    related[path] = dict(sha256=digest(data),references_old_editor_sha256=digest(source_raw).encode() in data)
display = PopupDisplay()
try: windows = display.windows_for_pid(editor_owner['pid']); screen = display.screen
finally: display.close()
assert raw(startup_path) == startup_raw and raw(script) == source_raw
assert all(owner(int(units[name]['MainPID'])) == value for name,value in owners.items())
print(json.dumps(dict(status='CURRENT_FACE_HINT_IDLE_METADATA_READ_ONLY',boot_id=EXPECTED['boot_id'],
    startup_sha256=digest(startup_raw),component_count=380,owners=owners,editor_unit=units['aura-face-zone-editor.service'],
    editor_source_path=str(script),editor_source_sha256=digest(source_raw),editor_source_base64=base64.b64encode(source_raw).decode(),
    editor_source_references_in_380_components=references,related_public_unit_or_manifest_metadata=related,
    editor_PID_windows=windows,screen=screen,ui_page=view.get('ui_page'),
    paused_idle_and_follow_disabled=True,device_or_axis_command_sent=False,
    file_or_window_or_service_modified=False,media_or_private_database_read=False)))
