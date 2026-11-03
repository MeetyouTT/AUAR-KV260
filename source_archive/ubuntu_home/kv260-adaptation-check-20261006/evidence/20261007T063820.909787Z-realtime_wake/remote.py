"""Wake the current X session; verify the existing preview keeps advancing."""
import ctypes
import ctypes.util
import json
import subprocess
import time
from pathlib import Path

root = Path('/home/root/aura-camera-check-20261006')
pid = int((root/'preview.pid').read_text())
cmd = (Path('/proc')/str(pid)/'cmdline').read_bytes()
assert b'/home/root/aura-camera-check-20261006/fullscreen_preview.py' in cmd
before = json.loads((root/'fullscreen-status.json').read_text())
subprocess.run(['xset','-display',':0','dpms','force','on'],check=True)
x = ctypes.CDLL(ctypes.util.find_library('X11'))
x.XOpenDisplay.restype = ctypes.c_void_p
x.XOpenDisplay.argtypes = [ctypes.c_char_p]
display = x.XOpenDisplay(b':0')
assert display
for name in ['XResetScreenSaver','XSync','XCloseDisplay']:
    getattr(x,name).argtypes = [ctypes.c_void_p,ctypes.c_int] if name=='XSync' else [ctypes.c_void_p]
x.XResetScreenSaver(display)
x.XSync(display,0)
x.XCloseDisplay(display)
time.sleep(2)
after = json.loads((root/'fullscreen-status.json').read_text())
check = subprocess.run(['xset','-display',':0','q'],capture_output=True,text=True,timeout=10)
print(json.dumps({'pid':pid,'before':before,'after':after,'display':check.stdout,
                  'camera_opened':False,'fpga_modified':False,'motion_command_emitted':False},indent=2))
assert after['frames']>before['frames'] and after['error'] is None
assert check.returncode==0 and 'Monitor is On' in check.stdout
