"""Rebuild every UART response, including the retained staging-helper failure."""
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
failures=[]
for folder in sorted((WORK/'evidence').iterdir()):
    status=json.loads((folder/'result.json').read_text())
    assert status['console_echo_restored'],str(folder)
    raw=(folder/'serial.raw').read_bytes().decode('utf-8','replace')
    begins=re.findall(r'\bBEGIN (MEDIA\d+) (\d+) (\d+)\r?$',raw,re.M)
    assert len(begins)==len(status['commands'])
    for row,(marker,rc,size) in zip(status['commands'],begins):
        chunks=re.findall(r'^DATA '+marker+r' (\d+) ([A-Za-z0-9+/=]+)\r?$',raw,re.M)
        assert [int(i) for i,_ in chunks]==list(range(len(chunks)))
        data=gzip.decompress(base64.b64decode(''.join(chunk for _,chunk in chunks),validate=True))
        digest=hashlib.sha256(data).hexdigest()
        assert re.findall(r'^END '+marker+r' ([0-9a-f]{64})\r?$',raw,re.M)==[digest]
        assert int(rc)==row['exit_code'] and int(size)==row['bytes']==len(data)
        assert row['sha256']==digest and (folder/(row['name']+'.output')).read_bytes()==data
        responses+=1
        if int(rc):
            assert status['phase']=='ui-stage' and row['name']=='stage-verify'
            assert b"KeyError: 'release_id'" in data
            failures.append({'phase':status['phase'],'step':row['name'],'exit_code':int(rc),
                             'reason':'staging manifest field mismatch, repaired before deployment'})
    assert status['complete'] or status['phase']=='ui-stage'


def phase(name):
    folder=sorted((WORK/'evidence').glob('*-'+name))[-1]
    return folder,json.loads((folder/'response.json').read_text())


bundle=json.loads((WORK/'capture_bundle.json').read_text())
blob=(WORK/bundle['zip']).read_bytes()
assert len(blob)==bundle['bytes'] and hashlib.sha256(blob).hexdigest()==bundle['sha256']
with zipfile.ZipFile(io.BytesIO(blob)) as archive:
    assert archive.testzip() is None
    manifest=json.loads(archive.read('manifest.json'))
    for name,row in manifest['files'].items():
        data=archive.read(name)
        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
        if name.startswith('aura/'):
            assert (AURA/name[5:]).read_bytes()==data,name
_,applied=phase('apply-ui')
_,ready=phase('ui-ready')
assert applied['status']=='START_REQUESTED' and ready['status']=='READY'
assert 'Ran 18 tests' in applied['native_tests'] and applied['native_tests'].rstrip().endswith('OK')
for relative,row in manifest['runtime_files'].items():
    expected=manifest['files']['aura/'+relative]['sha256']
    assert applied['runtime_files'][relative]==ready['runtime_files'][relative]==expected
native_folder,native=phase('native-recording')
assert native['status']=='PASS_NATIVE_POINTER_RECORD_STOP_CANCEL'
assert native['start_receipt']['ok']
recorded=native['completed_recording']
assert native['start_receipt']['result']['capture_id']==recorded['capture_id']
assert recorded['sample_count']==62000 and recorded['pcm_bytes']==124000 and recorded['duration_seconds']==3.875
assert not native['blocked_playback']['ok'] and native['cancelled']['result'] is None
original=json.loads((native_folder/'response.output').read_bytes())
for name,row in original['artifacts'].items():
    data=base64.b64decode(row['base64'],validate=True)
    assert (native_folder/name).read_bytes()==data
    assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    with Image.open(io.BytesIO(data)) as image:
        assert image.size==(1024,600)
_,automatic=phase('auto-limit')
assert automatic['status']=='PASS_REAL_20_SECOND_AUTO_STOP'
assert automatic['recording']['result']['sample_count']==320000
assert automatic['recording']['result']['pcm_bytes']==640000
assert len(automatic['samples'])>=50 and automatic['no_audio_owner_after']
_,final=phase('playback-final')
assert final['status']=='PASS_PLAYBACK_RECORDING_INTERLOCK_AND_FINAL_IDLE'
assert final['playing_observed']['playing'] and not final['recording_rejected_during_playback']['ok']
s=final['final']
assert s['phase']=='IDLE' and s['audio_output_state']=='NULL' and not s['error']
assert s['local_recording']['can_start'] and s['local_recording']['result'] is None
assert s['ui_page']=='main' and s['ui_settings']['volume']==58 and not s['ui_settings']['muted']
assert s['ui_runtime']['frame_visible'] and s['ui_runtime']['link']=='READY'
assert final['services'].count('ActiveState=active')==2 and final['services'].count('NRestarts=0')==2
assert final['camera']['pid']==applied['camera_before']['pid']==986
assert final['camera']['service_epoch']==applied['camera_before']['service_epoch']
assert not any(final['camera'][k] for k in ('camera_error','detector_error','preview_error'))
addresses=json.loads(final['addresses'])
eth=next(i for i in addresses if i['ifname']=='eth0')
assert 'NO-CARRIER' in eth['flags'] and not eth['addr_info'] and final['route']==''
host=json.loads((WORK/'host_regression.json').read_text())
assert host['exit_code']==0 and host['tests']==161
collector=json.loads((WORK/'collector_check.json').read_text())
assert collector['status']=='PASS'
result={'status':'PASS_NATIVE_UI_RECORDING_WITH_RECORDED_LIMITS','update_id':manifest['update_id'],
    'startup_release':manifest['startup_release'],'uart_responses_verified':responses,
    'recorded_helper_failures':failures,'payload_files_verified':len(manifest['files']),
    'runtime_files_verified':len(manifest['runtime_files']),'screenshots_verified':2,
    'host_tests_passed':161,'board_tests_passed':18,'runtime_collection_files':collector['collected_files'],
    'native_recording_samples':recorded['sample_count'],'automatic_limit_samples':320000,
    'recording_blocks_playback':True,'playback_blocks_recording':True,
    'final_state':'IDLE; recording cancelled, no retained audio, main page; volume 58%',
    'camera_unchanged_during_update':True,
    'limits':['physical finger touch not tested','Windows/LAN/media reply not connected',
              'no new cold boot or long stability acceptance','motion/identity/PL integration pending']}
(WORK/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
