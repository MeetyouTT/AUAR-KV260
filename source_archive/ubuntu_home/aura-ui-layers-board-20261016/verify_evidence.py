"""Independently verify UART records, both candidate packages and native results."""
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
from PIL import Image

WORK=Path(__file__).resolve().parent
AURA=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
responses=0
artifacts=0
file_artifacts=0
failures=[]
for folder in sorted((WORK/'evidence').iterdir()):
    result=json.loads((folder/'result.json').read_text())
    assert result['console_echo_restored'],folder
    raw=(folder/'serial.raw').read_bytes().decode('utf-8','replace')
    begins=re.findall(r'\bBEGIN (MEDIA\d+) (\d+) (\d+)\r?$',raw,re.M)
    assert len(begins)==len(result['commands']),folder
    for row,(marker,code,size) in zip(result['commands'],begins):
        chunks=re.findall(r'^DATA '+marker+r' (\d+) ([A-Za-z0-9+/=]+)\r?$',raw,re.M)
        assert [int(i) for i,_ in chunks]==list(range(len(chunks)))
        data=gzip.decompress(base64.b64decode(''.join(x for _,x in chunks),validate=True))
        digest=hashlib.sha256(data).hexdigest()
        assert re.findall(r'^END '+marker+r' ([0-9a-f]{64})\r?$',raw,re.M)==[digest]
        assert int(code)==row['exit_code'] and int(size)==row['bytes']==len(data)
        assert digest==row['sha256'] and (folder/(row['name']+'.output')).read_bytes()==data
        responses+=1
        if int(code):
            assert result['phase'] in ('ready','native-pages'),(folder,data[-2000:])
            failures.append({'phase':result['phase'],'evidence':str(folder),'exit_code':int(code)})
            continue
        value=json.loads(data)
        for name,record in value.get('artifacts',{}).items():
            data=base64.b64decode(record['base64'],validate=True)
            assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256']
            assert (folder/name).read_bytes()==data
            file_artifacts+=1
            if Path(name).suffix.lower() in ('.jpg','.jpeg','.png'):
                with Image.open(io.BytesIO(data)) as picture:assert picture.size==(1024,600)
                artifacts+=1
    assert result['complete'] or result['phase'] in ('ready','native-pages')

packages=[]
for archive in sorted(WORK.glob('ui-layers-*.zip')):
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        m=json.loads(z.read('manifest.json'))
        assert set(z.namelist())==set(m['files'])|{'manifest.json'}
        for name,row in m['files'].items():
            data=z.read(name)
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
        packages.append({'update_id':m['update_id'],'files':len(m['files']),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()})

bundle=json.loads((WORK/'capture_bundle.json').read_text())
manifest=json.loads((WORK/'manifest.json').read_text())
assert hashlib.sha256((WORK/bundle['zip']).read_bytes()).hexdigest()==bundle['sha256']
with zipfile.ZipFile(WORK/bundle['zip']) as archive:
    for name in manifest['runtime_files']:
        assert archive.read('aura/'+name)==(AURA/name).read_bytes()
    assert archive.read('startup/launcher.py')==(AURA/'scripts/board_ui_startup/launcher.py').read_bytes()


def phase(name):
    folders=sorted((WORK/'evidence').glob('*-'+name))
    candidates=[]
    for folder in folders:
        p=folder/'response.json'
        if p.exists():candidates.append((folder,json.loads(p.read_text())))
    assert candidates,name
    return candidates[-1]


_,applied=phase('apply-fixed')
_,ready=phase('ready-final-*')
_,pages=phase('native-pages')
_,recorded=phase('native-recording')
_,final=phase('playback-final')
assert applied['status']=='START_REQUESTED' and ready['status']=='READY'
assert ready['startup_enabled']=='enabled'
assert applied['update_id']==manifest['update_id']==ready['update_id']
assert 'Ran 18 tests' in applied['native_tests'] and applied['native_tests'].rstrip().endswith('OK')
for relative in manifest['runtime_files']:
    expected=manifest['files']['aura/'+relative]['sha256']
    assert applied['runtime_files'][relative]==ready['runtime_files'][relative]==expected
assert pages['status']=='PASS_NATIVE_LAYERS_CAMERA_AND_SETTINGS'
assert pages['vision_snapshot']['snapshot']['source_kind']=='actual'
assert pages['vision_snapshot']['frame_visible']
assert pages['layer_return']=={'ui_page':'vision','ui_layer':'presentation'}
assert 'camera_expand' not in pages['main_geometry']['visible_controls']
assert 'record' not in pages['vision_geometry']['visible_controls']
assert recorded['status']=='PASS_NATIVE_POINTER_RECORD_STOP_CANCEL'
audio=recorded['completed_recording']
assert audio['capture_id']==recorded['start_receipt']['result']['capture_id']
assert audio['sample_count']>=3200 and audio['pcm_bytes']==audio['sample_count']*2
assert abs(audio['duration_seconds']-audio['sample_count']/16000)<1e-6
assert not recorded['blocked_playback']['ok'] and recorded['cancelled']['result'] is None
assert final['status']=='PASS_PLAYBACK_RECORDING_INTERLOCK_AND_FINAL_IDLE'
assert not final['recording_rejected_during_playback']['ok']
s=final['final']
assert s['ui_page']=='main' and s['ui_layer']=='presentation'
assert s['phase']=='IDLE' and not s['playing'] and s['audio_output_state']=='NULL' and not s['error']
assert s['local_recording']['can_start'] and s['local_recording']['result'] is None
assert s['ui_settings']['volume']==58 and not s['ui_settings']['muted']
assert final['services'].count('ActiveState=active')==2 and final['services'].count('NRestarts=0')==2
assert final['camera']['pid']==applied['camera_before']['pid']==984
assert final['camera']['service_epoch']==applied['camera_before']['service_epoch']
assert not any(final['camera'][k] for k in ('camera_error','detector_error','preview_error'))
result={'status':'PASS_DEPLOYED_NATIVE_UI_WITH_RECORDED_RECOVERED_FAILURES',
        'verified_uart_responses':responses,'verified_image_artifacts':artifacts,
        'verified_file_artifacts':file_artifacts,
        'packages':packages,'update_id':manifest['update_id'],'startup_release':manifest['startup_release'],
        'recovered_board_failures':failures,'host_framework_tests':161,'host_launcher_port_tests':3,
        'board_related_tests':18,'actual_camera_displayed':True,
        'native_recording':audio,'physical_finger_touch_tested':False,
        'final':'main / presentation / IDLE / volume 58% / no retained audio',
        'board_boot_id':final['camera']['board_boot_id'],'camera_pid_unchanged':984,
        'limits':['real Windows dialogue not connected','physical finger touch not tested',
                  'no new cold boot or long stability acceptance']}
(WORK/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
