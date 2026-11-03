"""Use real GTK pointer events to start/stop/cancel the actual MCP01 recorder."""
import base64
import ctypes
import ctypes.util
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from PIL import Image

root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
out=Path('/home/root/aura-ui-layers-20261016')/('native-'+str(time.monotonic_ns()))
out.mkdir(mode=0o700)


def api(data=None):
    base='http://127.0.0.1:8783'
    request=base+'/api/state' if data is None else urllib.request.Request(base+'/api/command',
        data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':base})
    with urllib.request.urlopen(request,timeout=5) as r:return json.load(r)


def wait(predicate,seconds=5):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        value=api()
        if predicate(value):return value
        time.sleep(.1)
    raise AssertionError('Native recording state did not settle')


def geometry():
    response=api({'type':'save_evidence'})
    deadline=time.monotonic()+5
    while not Path(response['report']).exists() and time.monotonic()<deadline:time.sleep(.1)
    return json.loads(Path(response['report']).read_text())['ui_geometry']['visible_controls']


def click(rect):
    x,y=round(rect['x']+rect['width']/2),round(rect['y']+rect['height']/2)
    lib=ctypes.CDLL(ctypes.util.find_library('X11'));xt=ctypes.CDLL(ctypes.util.find_library('Xtst'))
    lib.XOpenDisplay.argtypes=[ctypes.c_char_p];lib.XOpenDisplay.restype=ctypes.c_void_p
    lib.XFlush.argtypes=[ctypes.c_void_p];lib.XCloseDisplay.argtypes=[ctypes.c_void_p]
    xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
    xt.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    display=lib.XOpenDisplay(b':0');assert display
    try:
        assert xt.XTestFakeMotionEvent(display,-1,x,y,0)
        assert xt.XTestFakeButtonEvent(display,1,1,0)
        lib.XFlush(display);time.sleep(.08)
        assert xt.XTestFakeButtonEvent(display,1,0,0)
        lib.XFlush(display)
    finally:lib.XCloseDisplay(display)


def screenshot(name):
    path=out/(name+'.png')
    subprocess.run(['python3','-B',str(root/'aura/tools/board_screen_capture.py'),str(path)],
                   env=dict(os.environ,DISPLAY=':0'),check=True,stdout=subprocess.PIPE,timeout=4)
    with Image.open(path) as original:
        assert original.size==(1024,600),original.size
        stream=io.BytesIO();original.convert('RGB').save(stream,format='JPEG',quality=75)
    data=stream.getvalue()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'base64':base64.b64encode(data).decode()}


assert api({'type':'ui_page','page':'main'})['ok']
wait(lambda s:s['ui_page']=='main' and s['local_recording']['can_start'])
controls=geometry();assert controls['record']['sensitive']
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:before=json.load(r)
click(controls['record'])
active=wait(lambda s:s['local_recording']['state']=='RECORDING' and s['local_recording']['sample_count']>=3200)
receipts=active['avatar_renderer']['command_results']
receipt=next(row for row in reversed(receipts) if row.get('ok') and isinstance(row.get('result'),dict) and row['result'].get('state')=='RECORDING')
artifacts={'recording.jpg':screenshot('recording')}
blocked_request=api({'type':'demo','index':0})
blocked=wait(lambda s:any(row['command_id']==blocked_request['command_id'] for row in s['avatar_renderer']['command_results']))
outcome=next(row for row in blocked['avatar_renderer']['command_results'] if row['command_id']==blocked_request['command_id'])
assert not outcome['ok'] and '停止录音' in outcome['error'],outcome
assert blocked['local_recording']['state']=='RECORDING' and not blocked['playing']
click(controls['record'])
completed=wait(lambda s:s['local_recording']['state']=='READY')
metadata=completed['local_recording']['result']
assert metadata['capture_id']==receipt['result']['capture_id']
assert metadata['pcm_bytes']==metadata['sample_count']*2 and metadata['sample_count']>=3200
artifacts['recorded.jpg']=screenshot('recorded')
time.sleep(.3);click(controls['record'])
wait(lambda s:s['local_recording']['state']=='RECORDING' and s['local_recording']['sample_count']>=3200)
click(controls['interaction_cancel'])
cancelled=wait(lambda s:s['local_recording']['state']=='CANCELLED' and s['audio_output_state']=='NULL')
assert cancelled['local_recording']['result'] is None and cancelled['local_recording']['can_start']
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:after=json.load(r)
assert before['pid']==after['pid'] and before['service_epoch']==after['service_epoch']
assert after['capture_frames']>before['capture_frames'] and after['detected_frames']>before['detected_frames']
assert not any(after[k] for k in ('camera_error','detector_error','preview_error'))
print(json.dumps({'status':'PASS_NATIVE_POINTER_RECORD_STOP_CANCEL','controls':controls,
    'start_receipt':receipt,'completed_recording':metadata,'blocked_playback':outcome,
    'cancelled':cancelled['local_recording'],'camera_before':before,'camera_after':after,
    'artifacts':artifacts,'physical_finger_touch_tested':False},ensure_ascii=False))
