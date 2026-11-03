"""Test the real GUI recorder and save one independent bounded MCP01 WAV."""
import array
import base64
import ctypes
import ctypes.util
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import wave

ROOT=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.capture import Mcp01Capture


def api(data=None):
    base='http://127.0.0.1:8783'
    request=base+'/api/state' if data is None else urllib.request.Request(base+'/api/command',
        data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':base})
    with urllib.request.urlopen(request,timeout=4) as r:return json.load(r)


def wait(predicate,seconds=7):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        current=api()
        if predicate(current):return current
        time.sleep(.1)
    raise AssertionError('Recording did not reach expected state')


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


def playback_active():
    state=api()
    return (state.get('phase')!='IDLE' or state.get('playing') is not False or state.get('paused') is not False
            or state.get('local_recording',{}).get('state')=='RECORDING' or bool(state.get('avatar_command_pending')))


before=api()
assert before['ui_layer']=='presentation' and before['local_recording']['can_start']
assert not before['error'] and not playback_active()
assert api({'type':'ui_page','page':'main'})['ok']
wait(lambda s:s['ui_page']=='main')
report=api({'type':'save_evidence'})
until=time.monotonic()+5
while not Path(report['report']).exists() and time.monotonic()<until:time.sleep(.1)
controls=json.loads(Path(report['report']).read_text())['ui_geometry']['visible_controls']
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:camera_before=json.load(r)
click(controls['record'])
active=wait(lambda s:s['local_recording']['state']=='RECORDING' and s['local_recording']['sample_count']>=48000)
click(controls['record'])
stopped=wait(lambda s:s['local_recording']['state']=='READY')
gui_audio=stopped['local_recording']['result']
assert gui_audio['sample_count']>=48000 and gui_audio['pcm_bytes']==gui_audio['sample_count']*2
time.sleep(.3);click(controls['record'])
wait(lambda s:s['local_recording']['state']=='RECORDING' and s['local_recording']['sample_count']>=3200)
click(controls['interaction_cancel'])
cancelled=wait(lambda s:s['local_recording']['state']=='CANCELLED' and s['local_recording']['can_start'])
assert cancelled['local_recording']['result'] is None

# Independent capture exposes PCM for signal analysis without modifying the GUI
# or adding an endpoint that exports microphone data from the live controller.
with Mcp01Capture(playback_active,max_seconds=5) as recorder:
    recorder.start()
    deadline=time.monotonic()+7
    while recorder.snapshot()['state']=='RECORDING' and time.monotonic()<deadline:time.sleep(.05)
    recorder.stop();clip=recorder.take()
assert clip.metadata()['sample_count']==80000 and len(clip.pcm)==160000
samples=array.array('h',clip.pcm)
if sys.byteorder!='little':samples.byteswap()
peak=max(abs(x) for x in samples)
rms=math.sqrt(sum(x*x for x in samples)/len(samples))
stats={'peak':peak,'rms':round(rms,3),'rms_dbfs':round(20*math.log10(rms/32768),2) if rms else None,
       'nonzero_samples':sum(x!=0 for x in samples),'clipped_samples':sum(abs(x)>=32767 for x in samples)}
buffer=io.BytesIO()
with wave.open(buffer,'wb') as wav:
    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(clip.pcm)
data=buffer.getvalue()
out=Path('/home/root/aura-record-check-20261016')/('capture-'+str(time.monotonic_ns()))
out.mkdir(mode=0o700,parents=True)
path=out/'microphone-5s.wav'
with os.fdopen(os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(data)
final=api()
assert final['local_recording']['can_start'] and final['local_recording']['result'] is None and not final['error']
assert final['ui_settings']['volume']==before['ui_settings']['volume']
with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=3) as r:camera_after=json.load(r)
assert camera_before['pid']==camera_after['pid'] and camera_before['service_epoch']==camera_after['service_epoch']
assert camera_after['capture_frames']>camera_before['capture_frames'] and camera_after['detected_frames']>camera_before['detected_frames']
print(json.dumps({'status':'PASS_RECORDING_WITH_SIGNAL' if peak else 'CAPTURE_OK_BUT_SILENT',
    'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'gui_recording':gui_audio,
    'gui_stop_cancel_passed':True,'independent_capture':clip.metadata(),'signal':stats,'wav_path':str(path),
    'final':{'ui_page':final['ui_page'],'ui_layer':final['ui_layer'],'local_recording':final['local_recording'],
             'ui_settings':final['ui_settings'],'error':final['error']},
    'camera_before':camera_before,'camera_after':camera_after,'physical_finger_touch_tested':False,
    'artifacts':{'microphone-5s.wav':{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                                   'base64':base64.b64encode(data).decode()}}},ensure_ascii=False))
