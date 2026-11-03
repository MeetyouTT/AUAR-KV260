"""Xvfb/XTest input to real GTK buttons; the pan transport is fake hardware."""
import ctypes
import ctypes.util
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import gi
gi.require_version('Gtk', '3.0'); gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from board.motion.manual import ManualPan
from tools.pan_controls import stage_type
from test_manual_pan import Hardware


class Base:
    def __init__(self):
        self.Gtk, self.Gdk, self.GLib = Gtk, Gdk, GLib
        self.geometry = dict(x=593, y=32, w=423, h=516)
        self.window = Gtk.Window(); self.window.set_decorated(False)
        self.window.set_default_size(1024, 600); self.window.move(0, 0)
        self.bridge = SimpleNamespace(allowed_commands=set())
        self.controls = {}; self.page = 'vision'; self.results = []
        self.build_window(False)

    def build_window(self, windowed):
        self.fixed = Gtk.Fixed(); self.window.add(self.fixed)
        button = Gtk.Button(label='设置'); self.fixed.put(button, 420, 490)
        button.connect('clicked', self.activated, {'type':'unused'}, 'vision_settings')
        self.controls['vision_settings'] = button
        self.vision_insights = Gtk.Label(label='synthetic test, no camera')
        self.fixed.put(self.vision_insights, 593, 32)
        self.avatar_title = Gtk.Label(label='视觉解读'); self.fixed.put(self.avatar_title, 593, 4)
        self.window.show_all()

    def show_page(self, page): self.page = page
    def activated(self, widget, data, key): self.results.append(self.native(data))
    def native(self, data):
        try: return self.command(data)
        except Exception as exc: return dict(ok=False, error=str(exc))
    def command(self, data): return dict(ok=True)
    def refresh_runtime(self, *args): pass
    def observe_touch(self, *args): return False
    def cleanup(self): self.window.destroy()


def spin(seconds):
    end = time.monotonic()+seconds
    while time.monotonic()<end:
        while Gtk.events_pending(): Gtk.main_iteration_do(False)
        time.sleep(.002)


hardware = Hardware(1420)
pan = ManualPan(lambda:hardware, duration_s=.08)
stage = stage_type(Base, lambda:pan)()
x11 = ctypes.CDLL(ctypes.util.find_library('X11'))
xtst = ctypes.CDLL(ctypes.util.find_library('Xtst'))
x11.XOpenDisplay.argtypes = [ctypes.c_char_p]; x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
display = x11.XOpenDisplay(None); assert display
checks = []


def send_click(key):
    widget = stage.pan_buttons[key]
    x, y = widget.translate_coordinates(stage.fixed, widget.get_allocated_width()//2,
                                        widget.get_allocated_height()//2)
    xtst.XTestFakeMotionEvent(display, -1, x, y, 0)
    xtst.XTestFakeButtonEvent(display, 1, 1, 0)
    xtst.XTestFakeButtonEvent(display, 1, 0, 0)
    x11.XSync(display, False)


try:
    stage.open_pan_dialog(); spin(.4)
    assert pan.read()['state']=='READY'
    # Programmatic activation and public/JSON dispatch have no native event.
    stage.pan_buttons['right'].clicked(); spin(.1)
    assert pan.read()['history']==[]
    for data in [dict(type='pan_jog', direction='right'),
                 dict(type='pan_jog', direction='right', _pan_source=time.monotonic(), _pan_input='forged')]:
        assert not stage.native(data)['ok']
    assert pan.read()['history']==[]
    checks.append('programmatic_and_remote_jog_rejected')

    send_click('right'); spin(.3)
    assert pan.read()['state']=='READY' and pan.read()['pulse_us']==1440, (pan.read(), stage.results)
    assert pan.read()['history'][-1]['completion']=='FULL_PULSE_FINISH'
    checks.append('fresh_xserver_pointer_event_moves_fake_transport_once')

    # Queue input on the X server without dispatching GTK for 350 ms.
    before = len(pan.read()['history'])
    send_click('left'); time.sleep(.35); spin(.15)
    assert len(pan.read()['history'])==before, (pan.read(), stage.results)
    checks.append('queued_click_across_gui_stall_rejected')
    spin(.35)
    assert len(pan.read()['history'])==before
    checks.append('no_automatic_replay_after_recovery')

    send_click('left'); spin(.3)
    assert pan.read()['pulse_us']==1420 and len(pan.read()['history'])==before+1
    checks.append('new_click_after_recovery_accepted')

    stage.refresh_pan_dialog()
    assert stage.pan_buttons['stop'].get_sensitive()
    stage.pan_buttons['stop'].clicked(); spin(.1)
    assert pan.read()['state']=='READY' and hardware.flags==0
    checks.append('stop_remains_available_without_input_freshness_gate')

    result = dict(status='REAL_GTK_XSERVER_INPUT_FAKE_HARDWARE_PASS',
                  board_accessed=False, physical_motion=False, actual_camera_used=False,
                  checks=checks, final_pulse_us=pan.read()['pulse_us'])
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
finally:
    stage.cleanup(); x11.XCloseDisplay(display)
