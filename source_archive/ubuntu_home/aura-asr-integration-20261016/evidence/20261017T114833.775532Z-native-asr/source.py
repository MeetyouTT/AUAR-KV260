"""Real GTK recording + disconnected ASR behavior; no fake recognition server."""
import base64
import ctypes
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
BASE='http://127.0.0.1:8783'

def api(data=None):
    request=BASE+'/api/state' if data is None else urllib.request.Request(BASE+'/api/command',
        data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':BASE})
    with urllib.request.urlopen(request,timeout=4) as r:return json.load(r)

def wait(predicate,seconds=5):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        state=api()
        if predicate(state):return state
        time.sleep(.1)
    raise AssertionError('Expected UI state was not observed')

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

before=api()
assert before['local_recording']['can_start'] and before['local_recording']['result'] is None
assert not before['local_transcription']['service']['enabled']
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:camera_before=json.load(r)
assert api({'type':'ui_page','page':'main'})['ok']
wait(lambda s:s['ui_page']=='main')
diagnostic=api({'type':'save_evidence'})
deadline=time.monotonic()+5
while not Path(diagnostic['report']).exists() and time.monotonic()<deadline:time.sleep(.1)
controls=json.loads(Path(diagnostic['report']).read_text())['ui_geometry']['visible_controls']
out=Path('/home/root/aura-asr-integration-20261016')/('acceptance-'+str(time.monotonic_ns()))
out.mkdir(parents=True,mode=0o700)
disabled=None;failed=None
try:
    click(controls['record'])
    active=wait(lambda s:s['local_recording']['state']=='RECORDING' and s['local_recording']['sample_count']>=24000)
    click(controls['record'])
    stopped=wait(lambda s:s['local_recording']['state']=='READY')
    disabled=stopped['local_transcription']
    assert disabled['state']=='DISABLED' and not disabled['text']
    assert stopped['local_recording']['result']['sample_count']>=24000
    # Configure a real unavailable local endpoint. This must fail visibly and
    # must never turn into an invented transcript.
    configured=subprocess.run(['python3','-B','tools/configure_board_asr.py','--host','127.0.0.1',
                              '--timeout-ms','1000'],cwd=str(ROOT/'aura'),
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=7)
    assert configured.returncode==0,configured.stdout
    failed=wait(lambda s:s['local_transcription']['state']=='ERROR')
    assert not failed['local_transcription']['text']
    assert 'refused' in failed['local_transcription']['error'].lower(),failed['local_transcription']
    assert not failed['avatar_command_pending'] and failed['local_recording']['can_start']
    time.sleep(.2)
    screenshot=out/'disconnected-asr.png'
    subprocess.run(['python3','-B',str(ROOT/'aura/tools/board_screen_capture.py'),str(screenshot)],
                   env=dict(os.environ,DISPLAY=':0'),check=True,timeout=3)
finally:
    restored=api({'type':'asr_config','values':{'enabled':False,'host':'127.0.0.1','port':8791,'timeout_ms':30000}})
    assert restored['ok']
    wait(lambda s:not s['local_transcription']['service']['enabled'])
    click(controls['interaction_cancel'])
    final=wait(lambda s:s['local_recording']['state']=='CANCELLED' and s['local_recording']['can_start'])
assert final['local_recording']['result'] is None and not final['local_transcription']['text']
assert not final['error']
assert final['ui_settings']['volume']==before['ui_settings']['volume']==58
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:camera_after=json.load(r)
assert (camera_before['pid'],camera_before['service_epoch'])==(camera_after['pid'],camera_after['service_epoch'])
assert camera_after['capture_frames']>camera_before['capture_frames']
data=screenshot.read_bytes()
print(json.dumps({'status':'PASS_NATIVE_RECORDING_AND_DISCONNECTED_ASR',
    'actual_board_asr_transcription_verified':False,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'recorded':stopped['local_recording']['result'],'disabled':disabled,
    'configuration_ack':json.loads(configured.stdout),'disconnected_result':failed['local_transcription'],
    'final':{k:final[k] for k in ('ui_page','ui_layer','phase','local_recording','local_transcription','ui_settings','error')},
    'camera_before':camera_before,'camera_after':camera_after,
    'artifacts':{'disconnected-asr.png':{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                                        'base64':base64.b64encode(data).decode()}}},ensure_ascii=False))
