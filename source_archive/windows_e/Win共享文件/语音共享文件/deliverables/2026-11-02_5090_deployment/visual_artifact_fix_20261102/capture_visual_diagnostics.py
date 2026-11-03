import json,time,http.client,os
from pathlib import Path
EXPECTED=json.loads('{"all_other_device_access_frozen": true, "boot_id": "a6d4a069-e9b0-4065-8df7-dc23556b168e", "startup_path": "/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json", "startup_sha256": "c1154308fcd25a9c8d957f33c5e2a4db0a0ef73e7656eb5aa437e29af9cd123b", "owners": {"aura-avatar-ui.service": {"pid": 363452, "birth_ticks": "2933733", "command_sha256": "48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d"}, "aura-camera-ui.service": {"pid": 362659, "birth_ticks": "2850120", "command_sha256": "acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd"}}}')
def request(method='GET',port=8783,path='/api/state',body=None):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=4)
 try:
  h={'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783'}
  if body is not None:h['Content-Type']='application/json';body=json.dumps(body).encode()
  c.request(method,path,body=body,headers=h);r=c.getresponse();v=r.read(2097153);assert r.status==200 and len(v)<=2097152;return json.loads(v)
 finally:c.close()
v=request();was_enabled=v['handsfree_dialogue']['enabled'];pause_sent=False
if was_enabled:
 p=Path('/home/root/aura-5090-recovery-20261102-a6d4a069/root-gui-original-20261102T190749Z-properties')/'visual-pause-intent.json';fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(b'{"single_pause_toggle":true}\n');f.flush();os.fsync(f.fileno())
 request('POST',body={'type':'conversation_toggle'});pause_sent=True
for _ in range(10):
 v=request();h=v['handsfree_dialogue']
 if h['enabled'] is False and h['microphone_open'] is False and h['state']=='PAUSED' and not v['playing'] and not v.get('pending_job'):break
 time.sleep(.3)
assert h['enabled'] is False and h['microphone_open'] is False and h['state']=='PAUSED'
"""Metadata-only discovery and one exact-window move, for an idle layout slot.

This module does not connect to X11 until explicitly constructed by the later
granted layout step. It never creates a window or restarts an original process.
"""
import ctypes as C


class PopupDisplay:
    def __init__(self):
        self.x = C.CDLL('libX11.so.6')
        x = self.x
        x.XOpenDisplay.argtypes = [C.c_char_p]; x.XOpenDisplay.restype = C.c_void_p
        x.XDefaultRootWindow.argtypes = [C.c_void_p]; x.XDefaultRootWindow.restype = C.c_ulong
        x.XDefaultScreen.argtypes = [C.c_void_p]; x.XDefaultScreen.restype = C.c_int
        for name in ('XDisplayWidth', 'XDisplayHeight'):
            fn = getattr(x,name); fn.argtypes = [C.c_void_p,C.c_int]; fn.restype = C.c_int
        x.XInternAtom.argtypes = [C.c_void_p,C.c_char_p,C.c_int]; x.XInternAtom.restype = C.c_ulong
        x.XQueryTree.argtypes = [C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),
                                C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
        x.XQueryTree.restype = C.c_int
        x.XGetWindowProperty.argtypes = [C.c_void_p,C.c_ulong,C.c_ulong,C.c_long,C.c_long,C.c_int,C.c_ulong,
            C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ubyte))]
        x.XGetWindowProperty.restype = C.c_int
        x.XGetGeometry.argtypes = [C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_int),
                                  C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint)]
        x.XGetGeometry.restype = C.c_int
        x.XTranslateCoordinates.argtypes = [C.c_void_p,C.c_ulong,C.c_ulong,C.c_int,C.c_int,
                                            C.POINTER(C.c_int),C.POINTER(C.c_int),C.POINTER(C.c_ulong)]
        x.XTranslateCoordinates.restype = C.c_int
        x.XMoveWindow.argtypes = [C.c_void_p,C.c_ulong,C.c_int,C.c_int]; x.XMoveWindow.restype = C.c_int
        x.XSync.argtypes = [C.c_void_p,C.c_int]; x.XSync.restype = C.c_int
        x.XFree.argtypes = [C.c_void_p]; x.XFree.restype = C.c_int
        x.XCloseDisplay.argtypes = [C.c_void_p]; x.XCloseDisplay.restype = C.c_int
        self.errors = []
        handler = C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p)
        self.error_handler = handler(lambda display,event: self.errors.append(True) or 0)
        x.XSetErrorHandler.argtypes = [handler]; x.XSetErrorHandler.restype = C.c_void_p
        x.XSetErrorHandler(self.error_handler)
        self.display = x.XOpenDisplay(b':0'); assert self.display, 'Original display unavailable'
        self.root = int(x.XDefaultRootWindow(self.display))
        self.pid_atom = x.XInternAtom(self.display,b'_NET_WM_PID',True)
        assert self.pid_atom, 'Original X11 PID metadata unavailable'
        screen = x.XDefaultScreen(self.display)
        self.screen = [x.XDisplayWidth(self.display,screen),x.XDisplayHeight(self.display,screen)]

    def close(self):
        if self.display: self.x.XCloseDisplay(self.display); self.display = None

    def children(self, window):
        root,parent,count = C.c_ulong(),C.c_ulong(),C.c_uint()
        values = C.POINTER(C.c_ulong)()
        ok = self.x.XQueryTree(self.display,window,C.byref(root),C.byref(parent),C.byref(values),C.byref(count))
        assert ok, 'Original X11 tree unavailable'
        try: return int(parent.value),[int(values[i]) for i in range(count.value)]
        finally:
            if values: self.x.XFree(values)

    def pid(self, window):
        kind,fmt,count,extra = C.c_ulong(),C.c_int(),C.c_ulong(),C.c_ulong()
        data = C.POINTER(C.c_ubyte)()
        code = self.x.XGetWindowProperty(self.display,window,self.pid_atom,0,1,False,0,
            C.byref(kind),C.byref(fmt),C.byref(count),C.byref(extra),C.byref(data))
        try:
            if code == 0 and fmt.value == 32 and count.value == 1 and data:
                return int(C.cast(data,C.POINTER(C.c_ulong))[0])
            return None
        finally:
            if data: self.x.XFree(data)

    def geometry(self, window):
        root,child = C.c_ulong(),C.c_ulong()
        x,y,root_x,root_y = C.c_int(),C.c_int(),C.c_int(),C.c_int()
        width,height,border,depth = C.c_uint(),C.c_uint(),C.c_uint(),C.c_uint()
        assert self.x.XGetGeometry(self.display,window,C.byref(root),C.byref(x),C.byref(y),C.byref(width),
                                   C.byref(height),C.byref(border),C.byref(depth)), 'Popup geometry unavailable'
        assert self.x.XTranslateCoordinates(self.display,window,self.root,0,0,C.byref(root_x),C.byref(root_y),C.byref(child))
        return dict(window=window,x=root_x.value,y=root_y.value,width=width.value,height=height.value,border=border.value)

    def windows_for_pid(self, pid):
        # GTK popup windows are root children; do not inspect window names,
        # text, screenshots, private properties, or unrelated descendants.
        _,windows = self.children(self.root)
        result = []
        for window in windows:
            if self.pid(window) == pid:
                row = self.geometry(window); row['parent'] = self.children(window)[0]; result.append(row)
        self.x.XSync(self.display,False)
        assert not self.errors, 'X11 tree changed during metadata query; inspect again under a new read step'
        return result

    def move_exact(self, pid, expected, new_y):
        assert expected['parent'] == self.root, 'Move only the exact root-level original popup'
        assert 0 <= new_y and new_y + expected['height'] <= self.screen[1]
        matches = [row for row in self.windows_for_pid(pid) if row['window'] == expected['window']]
        assert matches == [expected], 'Exact PID/window/before geometry changed'
        self.x.XMoveWindow(self.display,expected['window'],expected['x'],new_y)
        self.x.XSync(self.display,False)
        assert not self.errors, 'X11 move has an uncertain result; observe without resending'
        after = self.geometry(expected['window'])
        self.x.XSync(self.display,False)
        assert not self.errors
        assert after == {k:v for k,v in dict(expected,y=new_y).items() if k!='parent'}, 'Popup did not reach the exact requested position'
        return dict(after,parent=self.root)

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
result = dict(status='CURRENT_FACE_HINT_IDLE_METADATA_READ_ONLY',boot_id=EXPECTED['boot_id'],
    startup_sha256=digest(startup_raw),component_count=380,owners=owners,editor_unit=units['aura-face-zone-editor.service'],
    editor_source_path=str(script),editor_source_sha256=digest(source_raw),editor_source_base64=base64.b64encode(source_raw).decode(),
    editor_source_references_in_380_components=references,related_public_unit_or_manifest_metadata=related,
    editor_PID_windows=windows,screen=screen,ui_page=view.get('ui_page'),
    paused_idle_and_follow_disabled=True,device_or_axis_command_sent=False,
    file_or_window_or_service_modified=False,media_or_private_database_read=False)


files={}
public_paths=[script,script.parent/'boundary_visibility.py']+[aura/path for path in ('tools/board_camera_preview.py','tools/board_avatar_gtk.py','board/vision/local_preview.py','board/interaction/ui_services.py')]
for path in public_paths:
 data=raw(path,1048576);files[str(path)]={'sha256':digest(data),'base64':base64.b64encode(data).decode()}
unit_path=Path(units['aura-face-zone-editor.service']['FragmentPath']);unit_data=raw(unit_path,1048576)
unit_lines=unit_data.decode().splitlines();result['editor_unit_public_source']={'path':str(unit_path),'sha256':digest(unit_data),'lines':[line for line in unit_lines if line.startswith(('[','Description=','After=','Type=','User=','WorkingDirectory=','ExecStart=','Restart=','KillMode=','TimeoutStopSec=')) and not any(word in line.upper() for word in ('PASSWORD','TOKEN','SECRET'))]}
def fields(value,keys):return {k:value[k] for k in keys if k in value}
samples=[]
for _ in range(12):
 ui=request();cam=request(port=8790,path='/v1/ui/status');runtime=ui.get('ui_runtime') or {};snap=runtime.get('snapshot') or {};modules=cam.get('modules') or {};vision=modules.get('vision') or {};metrics=runtime.get('preview_metrics') or {};m=fields(metrics,('frame_reference','frame_visible','displayed_frames','update_hz','entry_age_ms','sink_active','active_outputs','transport'));m['error_present']=bool(metrics.get('error'))
 row={'board_monotonic_ms':int(time.monotonic()*1000),'ui_sequence':ui.get('sequence'),'ui_page':ui.get('ui_page'),'preview_metrics':m,'camera_preview':fields(cam.get('preview') or {},('camera_epoch','frame_id','captured_mono_ms','width','height')),'gui_preview':fields(snap.get('preview') or {},('camera_epoch','frame_id','captured_mono_ms','width','height')),'camera_state':(modules.get('camera') or {}).get('state'),'vision_protocol_keys':sorted(vision),'camera_capture':fields(cam,('capture_frames','detected_frames','capture_age_ms','observation_age_ms')),'following':(ui.get('manual_pan') or {}).get('automatic_following')}
 samples.append(row);time.sleep(.15)
result.update(pause_sent_once=pause_sent,listening_was_enabled=was_enabled,public_source_capture=files,samples=samples,raw_faces_audio_names_templates_or_private_database_exported=False)
print(json.dumps(result))
