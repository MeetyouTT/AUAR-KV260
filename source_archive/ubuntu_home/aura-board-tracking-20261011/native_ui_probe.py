#!/usr/bin/env python3
"""Native UI acceptance: XTest pointer events, screenshots and a labelled fixture."""
import argparse
import base64
import ctypes
import ctypes.util
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.request
from PIL import Image

ROOT = Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
STAGE = Path(__file__).resolve().parent.parent


def api(value=None):
    base = 'http://127.0.0.1:8783'
    request = base+'/api/state' if value is None else urllib.request.Request(base+'/api/command',
        data=json.dumps(value).encode(),headers={'Content-Type':'application/json','Origin':base})
    with urllib.request.urlopen(request,timeout=10) as stream:return json.load(stream)


def wait(predicate,seconds=8):
    end = time.monotonic()+seconds
    while time.monotonic()<end:
        value = api()
        if predicate(value):return value
        time.sleep(.15)
    raise AssertionError('UI state did not settle')


def click(x,y):
    xlib = ctypes.CDLL(ctypes.util.find_library('X11'))
    xtst = ctypes.CDLL(ctypes.util.find_library('Xtst'))
    xlib.XOpenDisplay.argtypes=[ctypes.c_char_p];xlib.XOpenDisplay.restype=ctypes.c_void_p
    xlib.XFlush.argtypes=[ctypes.c_void_p];xlib.XCloseDisplay.argtypes=[ctypes.c_void_p]
    xtst.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
    xtst.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    display = xlib.XOpenDisplay(b':0');assert display
    try:
        assert xtst.XTestFakeMotionEvent(display,-1,int(x),int(y),0)
        assert xtst.XTestFakeButtonEvent(display,1,1,0)
        xlib.XFlush(display);time.sleep(.08)
        assert xtst.XTestFakeButtonEvent(display,1,0,0)
        xlib.XFlush(display)
    finally:xlib.XCloseDisplay(display)


def report():
    value = api({'type':'save_evidence'});assert value['ok']
    end=time.monotonic()+8
    while not Path(value['report']).exists() and time.monotonic()<end:
        job=api().get('diagnostic_job') or {}
        if job.get('diagnostic_id')==value.get('diagnostic_id') and job.get('state')=='FAILED':
            raise AssertionError(job)
        time.sleep(.1)
    data = json.loads(Path(value['report']).read_text())
    return value,data


def screenshot(data, root_window=False):
    if root_window:
        path = STAGE/('root-'+str(time.monotonic_ns())+'.png')
        subprocess.run(['python3','-B',str(ROOT/'aura/tools/board_screen_capture.py'),str(path)],
            env=dict(os.environ,DISPLAY=':0'),check=True,timeout=4)
    else:
        if data.get('screenshot_path'):path=Path(data['screenshot_path'])
        else:
            info = json.loads((ROOT/'launch.json').read_text())
            path = max(Path(info['evidence']).glob('window_*.png'),key=lambda p:p.stat().st_mtime_ns)
    with Image.open(path) as source:
        image = source.convert('RGB');out = io.BytesIO();image.save(out,format='JPEG',quality=76)
    raw = out.getvalue()
    return {'source':str(path),'width':image.width,'height':image.height,'bytes':len(raw),
            'sha256':hashlib.sha256(raw).hexdigest(),'jpeg_base64':base64.b64encode(raw).decode()}


def page(name):
    names = ('main','demo','devices','connection','settings')
    click(62+names.index(name)*115,82)
    state = wait(lambda v:v['ui_page'] == name)
    time.sleep(.35)
    record,data = report();geometry = data['ui_geometry']
    assert (geometry['width'],geometry['height']) == (1024,600),geometry
    for key,rect in geometry['visible_controls'].items():
        assert rect['height'] >= 48 and rect['x']+rect['width'] <= 585 and rect['y']+rect['height'] <= 556,(key,rect)
    if name == 'main' and state['ui_runtime']['link'] == 'DISABLED':
        assert not geometry['visible_controls']['record']['sensitive']
        assert not geometry['visible_controls']['ask_frame']['sensitive']
    print(json.dumps({'page':name,'record':record,'geometry':geometry,'state':state,
                      'input_events':data['input_events'],'screenshot':screenshot(data)},ensure_ascii=False))


def keypad():
    assert api({'type':'ui_page','page':'connection'})['ok']
    time.sleep(.4);click(528,256);time.sleep(.5)
    record,data = report();dialog = data['ui_geometry']['dialogs'][0]
    assert dialog['width'] <= 1024 and dialog['height'] <= 600,dialog
    shot = screenshot(data,True)
    click(dialog['x']+70,dialog['y']+125);time.sleep(.3)
    _,typed = report()
    assert typed['ui_geometry']['dialogs'][0]['entry_lengths'] == [1],typed['ui_geometry']
    click(dialog['x']+dialog['width']*.25,dialog['y']+dialog['height']-38);time.sleep(.4)
    _,closed = report();assert not closed['ui_geometry']['dialogs']
    print(json.dumps({'keypad':dialog,'cancel_preserves_connection':api()['ui_runtime']['connection'],
                      'typed_one_character_verified':True,'screenshot':shot},ensure_ascii=False))


def fixture():
    before = api();connection = before['ui_runtime']['connection']
    assert not connection['enabled'],'Do not disturb an existing live service connection'
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);probe.bind(('127.0.0.1',8790))
    script = Path(__file__).resolve().parent/'fixture_provider.py'
    log = STAGE/('fixture-provider-'+str(time.monotonic_ns())+'.log')
    with log.open('xb') as stream:
        child = subprocess.Popen(['python3','-B',str(script)],stdin=subprocess.DEVNULL,
                                  stdout=stream,stderr=subprocess.STDOUT)
    result = {'scope':'BOARD_UI_WITH_EXPLICIT_FIXTURE_NOT_REAL_AUDIO_MODEL_CAMERA_OR_PL'}
    try:
        assert api({'type':'ui_service_config','values':{'enabled':True,'host':'127.0.0.1','port':8790}})['ok']
        ready = wait(lambda v:v['ui_runtime']['snapshot'] is not None and v['ui_runtime']['frame_visible'])
        assert ready['ui_runtime']['snapshot']['source_kind'] == 'fixture'
        result['ready'] = ready
        assert api({'type':'ui_page','page':'main'})['ok']
        time.sleep(.4);click(98,516)
        listening = wait(lambda v:v['ui_runtime']['snapshot']['modules']['audio']['state'] == 'RECORDING')
        result['record_request'] = listening
        time.sleep(.3);click(98,516)
        stopped = wait(lambda v:v['ui_runtime']['snapshot']['modules']['audio']['state'] == 'READY')
        result['stop_request'] = stopped
        assert stopped['ui_runtime']['snapshot']['modules']['motion']['state'] == 'FAULT'
        wait(lambda v:not v['ui_runtime']['pending_count'])
        time.sleep(.3);click(485,516)
        cancelled = wait(lambda v:v['ui_runtime']['snapshot'].get('interaction_suppressed') is True)
        assert cancelled['ui_runtime']['snapshot']['modules']['interaction']['reply'] == ''
        result['cancel'] = cancelled
        _,data = report();result['screenshot'] = screenshot(data)
        with urllib.request.urlopen('http://127.0.0.1:8790/fixture/commands',timeout=3) as stream:
            result['fixture_commands'] = json.load(stream)
        assert [v['action'] for v in result['fixture_commands']] == ['record_start','record_stop','cancel']
        result['checks_passed'] = ['fixture_label','bounded_preview','record_button_request',
                                   'stop_button_request','cancel_late_reply','independent_motion_fault']
    finally:
        restored = api({'type':'ui_service_config','values':connection});assert restored['ok']
        wait(lambda v:v['ui_runtime']['link'] == 'DISABLED')
        assert str(script).encode() in (Path('/proc')/str(child.pid)/'cmdline').read_bytes().split(b'\0')
        child.terminate();child.wait(timeout=4)
    result['restored_connection'] = api()['ui_runtime']['connection']
    result['fixture_pid_exited'] = child.returncode is not None
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('page','keypad','fixture'),required=True)
    parser.add_argument('--page',default='main')
    args = parser.parse_args()
    if args.phase == 'page':page(args.page)
    elif args.phase == 'keypad':keypad()
    else:fixture()
