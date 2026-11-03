"""Install/start only this camera adapter, then connect and verify the live UI."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

from board_apply import ROOT, STAGE, MANIFEST, api, atomic, protected, run, sha, verify_payload
from board_probe import click, report, screenshot, wait

CAMERA_UNIT=Path('/etc/systemd/system/aura-camera-ui.service')
SOURCE=ROOT/'aura/board/vision/ui_camera_service.py'
UNIT_SOURCE=ROOT/'aura/scripts/board_camera_ui/aura-camera-ui.service'


def health():
    with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=2) as stream:return json.load(stream)


def owned():
    assert CAMERA_UNIT.is_file() and sha(CAMERA_UNIT)==sha(UNIT_SOURCE)
    pid=int(run(['systemctl','show',CAMERA_UNIT.name,'-p','MainPID','--value']).strip())
    if pid:
        assert str(SOURCE).encode() in (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
    return pid


def start():
    verify_payload()
    for name in MANIFEST['runtime_files']:assert sha(ROOT/name)==MANIFEST['files'][name]['sha256'],name
    preflight=json.loads(run(['python3','-B',str(SOURCE),'--check'],timeout=30))
    assert preflight['status']=='PASS' and preflight['camera_opened'] is False
    before={'ui':api(),'protected':protected(),'preflight':preflight}
    backup=STAGE/'camera-before.json'
    if backup.exists():
        assert CAMERA_UNIT.exists();owned()
    else:
        assert not CAMERA_UNIT.exists(),'Existing camera service requires ownership review'
        assert not before['ui']['ui_runtime']['connection']['enabled'],'Keep current live connection unchanged'
        with socket.socket() as port:
            port.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);port.bind(('127.0.0.1',8790))
        backup.write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n')
        atomic(CAMERA_UNIT,UNIT_SOURCE.read_bytes())
        run(['systemctl','daemon-reload'])
    run(['systemctl','enable',CAMERA_UNIT.name])
    run(['systemctl','reset-failed',CAMERA_UNIT.name])
    run(['systemctl','--no-block','start',CAMERA_UNIT.name])
    print(json.dumps({'camera_start_requested':True,'preflight':preflight,'protected':protected()}))


def connect():
    owned();end=time.monotonic()+15;value=None
    while time.monotonic()<end:
        try:
            value=health()
            if value['capture_frames']>=3 and value['detected_frames']>=3:break
        except (OSError,ValueError):pass
        time.sleep(.2)
    assert value and value['capture_frames']>=3 and value['detected_frames']>=3,value
    assert not value['camera_error'] and not value['detector_error'],value
    assert api({'type':'ui_service_config','values':{'enabled':True,'host':'127.0.0.1','port':8790}})['ok']
    ui=wait(lambda v:v['ui_runtime']['link']=='READY' and v['ui_runtime']['frame_visible'])
    assert ui['ui_runtime']['snapshot']['source_kind']=='actual'
    assert api({'type':'ui_page','page':'main'})['ok']
    print(json.dumps({'connected':True,'health':value,'ui':ui,'camera_pid':owned()},ensure_ascii=False))


def status():
    try:value=health()
    except Exception as exc:value={'error':str(exc)}
    sys.path.insert(0,str(ROOT/'aura'))
    from board.vision.ui_camera_service import video_owners
    print(json.dumps({'camera_service':run(['systemctl','show',CAMERA_UNIT.name,'-p','MainPID','-p','ActiveState',
        '-p','SubState','-p','NRestarts','-p','UnitFileState']), 'health':value,'ui':api(),
        'camera_owners':video_owners('/dev/video0'),'protected':protected(),
        'journal':run(['journalctl','-u',CAMERA_UNIT.name,'-n','8','--no-pager'])},ensure_ascii=False))


def test():
    pid=owned();launch=json.loads((ROOT/'launch.json').read_text());before=health()
    initial=api();preferences=initial['ui_settings']
    time.sleep(3);after=health()
    assert after['capture_frames']>before['capture_frames'] and after['detected_frames']>before['detected_frames']
    assert after['capture_age_ms']<1000 and after['observation_age_ms']<750,after
    assert api({'type':'ui_page','page':'main'})['ok'];time.sleep(.3)
    click(517,268);time.sleep(.5)
    _,large=report();dialog=large['ui_geometry']['dialogs'][0]
    assert dialog['title']=='摄像头实时画面' and dialog['width']<=1024 and dialog['height']<=600,dialog
    expanded=screenshot(large)
    click(dialog['x']+dialog['width']-80,dialog['y']+dialog['height']-34);time.sleep(.3)
    _,closed=report();assert not closed['ui_geometry']['dialogs'],closed['ui_geometry']
    # Repeat the formerly crashing diagnostics while the real camera is active.
    for _ in range(3):report()
    final=api();assert final['ui_runtime']['frame_visible']
    assert json.loads((ROOT/'launch.json').read_text())['pid']==launch['pid'],'GUI restarted during diagnostics'
    assert owned()==pid and not health()['detector_error']
    for key in ('volume','muted','fullscreen','economy'):assert final['ui_settings'][key]==preferences[key],key
    print(json.dumps({'checks_passed':['real_capture_progress','real_detection_progress','fresh_preview',
        'native_expand_button','bounded_large_view','native_close_button','five_diagnostics_without_restart',
        'settings_preserved'],'before':before,'after':health(),'ui':final,'dialog':dialog,
        'gui_pid':launch['pid'],'camera_pid':pid,'screenshot':expanded,
        'main_screenshot':screenshot(closed)},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('camera-start','camera-connect','camera-status','camera-test'),required=True)
    args=parser.parse_args()
    {'camera-start':start,'camera-connect':connect,'camera-status':status,'camera-test':test}[args.phase]()
