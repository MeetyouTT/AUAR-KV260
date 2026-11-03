"""Helpers for the separately granted original-camera restoration only.

The caller supplies the new grant and previously sealed actual receipts.
No project import, Native call, model or private database access occurs here.
"""
import ast
import copy
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time

original = {'__name__': 'original_camera_metadata_functions'}
exec(compile(STOP_SOURCE, '<unchanged-original-normal-stop-helpers>', 'exec'), original)
regular, digest, require = original['regular'], original['digest'], original['require']
pinned, create = original['pinned'], original['create']
CP = Path(SEAL['genuine_checkpoint_pin']['path'])
CP_SHA = SEAL['genuine_checkpoint_pin']['sha256']
BOOT = GRANT['boot_id']
TX = Path(SESSION) / 'original-camera-restore'
OP = original['OPERATOR']
OPS = OP.parent.parent


def show(name, props='MainPID,ControlPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'):
    p = subprocess.run(['systemctl', 'show', name, '--property=' + props], capture_output=True, text=True, timeout=5)
    require(p.returncode == 0, 'Service metadata unavailable')
    return dict(row.split('=', 1) for row in p.stdout.splitlines() if '=' in row)


def process(pid):
    path = Path('/proc') / str(pid)
    return dict(pid=int(pid), birth_ticks=(path/'stat').read_text().rsplit(')', 1)[1].split()[19],
                command_sha256=digest((path/'cmdline').read_bytes()))


def get_health():
    c = http.client.HTTPConnection('127.0.0.1', 8790, timeout=3)
    try:
        c.request('GET', '/health'); r = c.getresponse(); raw = r.read(2097153)
        require(r.status == 200 and len(raw) <= 2097152, 'Camera public health unavailable')
        return json.loads(raw)
    finally:
        c.close()


def platform():
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT, 'Boot changed')
    context = json.loads(pinned(dict(path=AXIS['context_board_path'], sha256=AXIS['context_sha256'])))
    require(context == AXIS['context'] and context['boot_id'] == BOOT, 'Original wide context changed')
    require(digest(Path('/sys/firmware/fdt').read_bytes()) == context['fdt_sha256'], 'FDT changed')
    require(Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
            == context['firmware_name'] == 'aura-visual-servo-b4096-wide-v1.bit.bin', 'Original wide inactive')
    require(Path('/sys/class/fpga_manager/fpga0/state').read_text().strip() == 'operating', 'FPGA not operating')
    require(regular('/etc/vart.conf').decode() == AXIS['platform']['vart'], 'VART platform changed')
    report = json.loads(pinned(dict(path=AXIS['identity_stop_report_board_path'], sha256=AXIS['identity_stop_report_sha256'])))
    require(report == AXIS['original_identity_stop_report'] and report['identity_stop_passed'] is True
            and report['after_stop']['flags'] == 0 and report['after_stop']['lease_left_ms'] == 0, 'Original ID/STOP proof differs')
    require(all(report[k] is False for k in ('ARM_sent', 'COMMIT_sent', 'BIND_sent', 'REFERENCE_sent')), 'Motion appeared in original STOP proof')
    return context


def source_snapshot(expected_startup_sha=None):
    startup_path = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
    startup_raw = regular(startup_path)
    require(digest(startup_raw) == (expected_startup_sha or GRANT['startup_sha256']), 'Startup changed')
    startup = json.loads(startup_raw); aura = Path(startup['runtime']) / 'aura'
    pins = startup['component_sha256']
    if expected_startup_sha is None:
        require(pins == GRANT['component_sha256'], 'Granted component map changed')
    require(len(pins) == 380, 'Component count changed')
    for path, sha in pins.items():
        require(digest(regular(aura/path)) == sha, 'Installed component changed: ' + path)
    ui_path = aura/'config/board_avatar_gtk.json'; ui_raw = regular(ui_path); ui = json.loads(ui_raw)
    selected_pin = ui['board_business']['face_readback']; selected_raw = pinned(selected_pin); selected = json.loads(selected_raw)
    if expected_startup_sha is None:
        require(selected_pin == {k: GRANT['selected_face_binding'][k] for k in ('path', 'sha256')}, 'Selected spec changed')
    for path, sha in selected['source_sha256'].items():
        require(digest(regular(path)) == sha, 'Selected source changed: ' + path)
    c = FRESH['normal_stop_expected']['source_closure']
    py_manifest = json.loads(pinned(c['native_python_manifest']))
    native_aura = CP.parent.parent/'aura'
    require(len(py_manifest['files']) == 222 and
            {str(p.relative_to(native_aura)):digest(regular(p)) for p in native_aura.rglob('*.py') if not p.is_symlink()}
            == py_manifest['files'], 'Original Native Python closure changed')
    op_manifest = json.loads(pinned(c['native_operator_manifest']))
    require(len(op_manifest['files']) == 7, 'Original operator file set changed')
    for path, sha in op_manifest['files'].items(): pinned(dict(path=path, sha256=sha))
    c_manifest = json.loads(pinned(c['native_c_unit_manifest']))
    require(len(c_manifest['files']) == 6, 'Original C unit file set changed')
    for name, sha in c_manifest['files'].items():
        p = Path(name); require(not p.is_absolute() and '..' not in p.parts, 'C source path escapes')
        pinned(dict(path=str(OP/p), sha256=sha))
    pinned(c['native_library'])
    props = show('aura-camera-ui.service', 'FragmentPath,DropInPaths')
    require({props['FragmentPath']} | set(props['DropInPaths'].split())
            == set(c['camera_systemd']['source_sha256']), 'Camera unit source set changed')
    for path, sha in c['camera_systemd']['source_sha256'].items(): pinned(dict(path=path, sha256=sha))
    return dict(startup_path=startup_path, startup_raw=startup_raw, startup=startup, aura=aura,
                ui_path=ui_path, ui_raw=ui_raw, ui=ui, selected=selected, selected_pin=selected_pin)


def paused_gui():
    g = show('aura-avatar-ui.service')
    require(all(g[k] == v for k,v in dict(MainPID='0', ControlPID='0', ActiveState='inactive', SubState='dead', Job='').items()),
            'GUI must remain normally stopped')
    original['no_service_processes']('aura-avatar-ui.service')
    require(json.loads(regular('/home/root/.local/share/aura-board-business/listening_preference.json'))
            == {'version': 1, 'enabled': False}, 'Listening must remain paused')


def original_verify(aura, candidate):
    path = aura/'board/runtime/audio/face_gallery_readback.py'; raw = regular(path)
    require(digest(raw) == 'b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e', 'Original metadata verifier changed')
    klass = next(n for n in ast.parse(raw).body if isinstance(n, ast.ClassDef) and n.name == 'FaceGalleryReadback')
    method = copy.deepcopy(next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == '_verify'))
    method.decorator_list = []
    scope = dict(Path=Path, hashlib=hashlib, json=json)
    exec(compile(ast.Module(body=[method], type_ignores=[]), '<original-metadata-only-verifier>', 'exec'), scope)
    scope['_verify'](candidate)


def alive_camera():
    unit = show('aura-camera-ui.service'); pid = int(unit['MainPID'])
    require(pid > 0 and all(unit[k] == v for k,v in dict(ControlPID='0', ActiveState='active', SubState='running',
            Job='', Result='success', Restart='no', KillMode='process', SendSIGKILL='no', TimeoutStopUSec='infinity').items()),
            'Original camera lifecycle is not stable')
    owner = process(pid); health = get_health(); native = health['dpu_schedule']
    require(owner['command_sha256'] == FRESH['camera_owner']['command_sha256'], 'Original camera command changed')
    require(health['pid'] == pid and health['board_boot_id'] == BOOT and health['identity']['ready'] is True
            and not health['identity'].get('error') and health['motion_command_emitted'] is False
            and not any(health.get(k) for k in ('camera_error', 'detector_error', 'preview_error'))
            and native['native_critical'] is True and native['native_abi'] == 2
            and native['owner_fenced'] is False and native['quiesced'] is False, 'Original camera/Native not healthy')
    require(process(pid) == owner and show('aura-camera-ui.service')['MainPID'] == str(pid), 'Camera owner changed')
    return owner, health, unit


def hardware_owners():
    dpu, motion = [], []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            maps = (p/'maps').read_text(); fds = []
            for fd in (p/'fd').iterdir():
                try: fds.append(os.readlink(fd))
                except (FileNotFoundError, ProcessLookupError): pass
            if any(s in maps for s in ('libvart', 'libaura_native_operator')) or any(s.startswith(('/dev/dri/renderD', '/dev/dpu')) for s in fds): dpu.append(process(int(p.name)))
            if 'libvsrv.so' in maps or '/dev/mem' in fds: motion.append(process(int(p.name)))
        except (FileNotFoundError, ProcessLookupError): continue
        except OSError: require(not p.exists(), 'Unreadable live hardware ownership')
    return dict(dpu=sorted(dpu,key=lambda x:x['pid']), motion=sorted(motion,key=lambda x:x['pid']))


def encoded(value): return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def replace_known(path, before, after):
    path = Path(path); require(regular(path) == before, 'CAS before-image differs')
    info = path.stat(); temp = path.with_name(path.name + '.camera-restore-' + str(os.getpid()))
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, info.st_mode & 0o777)
    with os.fdopen(fd, 'wb') as f: f.write(after); f.flush(); os.fsync(f.fileno())
    os.chown(temp, info.st_uid, info.st_gid)
    require(regular(path) == before, 'CAS source changed before replace')
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
