"""Verify the deployed layers using native pointer events and actual camera."""
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

ROOT=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
OUT=Path('/home/root/aura-ui-layers-20261016')/('pages-'+str(time.monotonic_ns()))
OUT.mkdir(mode=0o700)


def api(data=None):
    base='http://127.0.0.1:8783'
    req=base+'/api/state' if data is None else urllib.request.Request(base+'/api/command',
        data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':base})
    with urllib.request.urlopen(req,timeout=4) as r:return json.load(r)


def wait(predicate,seconds=6):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        value=api()
        if predicate(value):return value
        time.sleep(.12)
    raise AssertionError('New UI state did not settle: '+str({k:value.get(k) for k in ('ui_page','ui_layer','error')}))


def report():
    result=api({'type':'save_evidence'})
    assert result['ok'],result
    until=time.monotonic()+5
    while not Path(result['report']).exists() and time.monotonic()<until:time.sleep(.08)
    data=json.loads(Path(result['report']).read_text())
    assert not data['errors'],data['errors']
    geometry=data['ui_geometry']
    assert (geometry['width'],geometry['height'])==(1024,600),geometry
    for key,rect in geometry['visible_controls'].items():
        assert rect['height'] >= (40 if key=='layer_switch' else 48),(key,rect)
        assert 0<=rect['x'] and 0<=rect['y'] and rect['x']+rect['width']<=1024 and rect['y']+rect['height']<=600,(key,rect)
    return data


def click(rect):
    x=round(rect['x']+rect['width']/2);y=round(rect['y']+rect['height']/2)
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
    path=OUT/(name+'.png')
    subprocess.run(['python3','-B',str(ROOT/'aura/tools/board_screen_capture.py'),str(path)],
                   env=dict(os.environ,DISPLAY=':0'),check=True,stdout=subprocess.PIPE,timeout=4)
    with Image.open(path) as source:
        assert source.size==(1024,600),source.size
        out=io.BytesIO();source.convert('RGB').save(out,format='JPEG',quality=75)
    data=out.getvalue()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'base64':base64.b64encode(data).decode()}


assert api()['ui_layer']=='presentation' and api()['ui_page']=='main'
main=report();controls=main['ui_geometry']['visible_controls']
assert 'record' in controls and 'camera_expand' not in controls and 'page_devices' not in controls
artifacts={'main.jpg':screenshot('main')}
click(controls['page_vision'])
vision=wait(lambda s:s['ui_page']=='vision' and s['ui_runtime']['frame_visible'])
assert vision['ui_runtime']['snapshot']['source_kind']=='actual'
assert vision['ui_runtime']['link']=='READY'
view=report();controls=view['ui_geometry']['visible_controls']
assert 'camera_expand' in controls and 'record' not in controls and 'page_devices' not in controls
assert controls['camera_expand']['sensitive'] and controls['vision_settings']['sensitive']
artifacts['vision.jpg']=screenshot('vision')
click(controls['vision_settings'])
wait(lambda s:s['ui_page']=='settings' and s['ui_layer']=='presentation')
settings=report();controls=settings['ui_geometry']['visible_controls']
assert 'volume_less' in controls and 'page_main' in controls and 'page_devices' not in controls
assert api()['ui_settings']['volume']==58 and not api()['ui_settings']['muted']
click(controls['page_vision'])
wait(lambda s:s['ui_page']=='vision' and s['ui_runtime']['frame_visible'])
view=report();controls=view['ui_geometry']['visible_controls']
click(controls['layer_switch'])
wait(lambda s:s['ui_layer']=='debug' and s['ui_page']=='devices')
debug=report();controls=debug['ui_geometry']['visible_controls']
assert 'page_devices' in controls and 'page_main' not in controls
artifacts['debug.jpg']=screenshot('debug')
click(controls['layer_switch'])
restored=wait(lambda s:s['ui_layer']=='presentation' and s['ui_page']=='vision')
view=report();click(view['ui_geometry']['visible_controls']['page_main'])
final=wait(lambda s:s['ui_layer']=='presentation' and s['ui_page']=='main')
assert final['local_recording']['can_start'] and not final['error']
print(json.dumps({'status':'PASS_NATIVE_LAYERS_CAMERA_AND_SETTINGS',
    'main_geometry':main['ui_geometry'],'vision_geometry':view['ui_geometry'],
    'settings_geometry':settings['ui_geometry'],'debug_geometry':debug['ui_geometry'],
    'vision_snapshot':vision['ui_runtime'],'layer_return':{'ui_page':restored['ui_page'],'ui_layer':restored['ui_layer']},
    'physical_finger_touch_tested':False,'artifacts':artifacts},ensure_ascii=False))
