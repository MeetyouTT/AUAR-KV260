"""Read UART bytes independently; distinguish actual model and board checks."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
import wave
import zipfile

WORK=Path(__file__).resolve().parent
AURA=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
responses=attachments=0
failures=[]
for folder in sorted((WORK/'evidence').iterdir()):
    result=json.loads((folder/'result.json').read_text())
    incomplete=result['phase']=='native-asr' and not result['complete']
    if not incomplete:assert result['console_echo_restored'],folder
    else:failures.append({'phase':'native-asr','reason':'PNG response exceeded UART timeout; incomplete output retained'})
    raw=(folder/'serial.raw').read_bytes().decode('utf-8','replace')
    begins=re.findall(r'\bBEGIN (MEDIA\d+) (\d+) (\d+)\r?$',raw,re.M)
    assert len(begins)==len(result['commands'])+(1 if incomplete else 0),folder
    for row,(marker,code,size) in zip(result['commands'],begins):
        chunks=re.findall(r'^DATA '+marker+r' (\d+) ([A-Za-z0-9+/=]+)\r?$',raw,re.M)
        assert [int(i) for i,_ in chunks]==list(range(len(chunks)))
        body=gzip.decompress(base64.b64decode(''.join(c for _,c in chunks),validate=True))
        digest=hashlib.sha256(body).hexdigest()
        assert re.findall(r'^END '+marker+r' ([0-9a-f]{64})\r?$',raw,re.M)==[digest]
        assert len(body)==int(size)==row['bytes'] and int(code)==row['exit_code']
        assert digest==row['sha256'] and (folder/(row['name']+'.output')).read_bytes()==body
        responses+=1
        if int(code):
            failures.append({'phase':result['phase'],'exit_code':int(code)});continue
        value=json.loads(body)
        for name,record in value.get('artifacts',{}).items():
            data=base64.b64decode(record['base64'],validate=True)
            assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256']
            assert (folder/name).read_bytes()==data
            attachments+=1
    assert result['complete'] or result['phase']=='apply-update' or incomplete,(folder,result)

bundle=json.loads((WORK/'capture_bundle.json').read_text())
manifest=json.loads((WORK/'manifest.json').read_text())
packages=[]
for path in sorted(WORK.glob('asr-ui-*.zip')):
    with zipfile.ZipFile(path) as archive:
        m=json.loads(archive.read('manifest.json'))
        assert archive.testzip() is None
        assert set(archive.namelist())==set(m['files'])|{'manifest.json'}
        for name,row in m['files'].items():
            data=archive.read(name)
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    packages.append({'update_id':m['update_id'],'files':len(m['files']),
                     'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
blob=(WORK/bundle['zip']).read_bytes()
assert hashlib.sha256(blob).hexdigest()==bundle['sha256']
with zipfile.ZipFile(WORK/bundle['zip']) as archive:
    assert archive.testzip() is None
    assert set(archive.namelist())==set(manifest['files'])|{'manifest.json'}
    assert json.loads(archive.read('manifest.json'))==manifest
    for name,row in manifest['files'].items():
        data=archive.read(name)
        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    for relative in manifest['runtime_files']:
        assert archive.read('aura/'+relative)==(AURA/relative).read_bytes()

actual=json.loads((WORK/'actual_asr.json').read_text())
assert actual['status']=='PASS' and not actual['live_board_gui_or_lan_test']
model=AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14/model.int8.onnx'
model_id='paraformer-'+hashlib.sha256(model.read_bytes()).hexdigest()[:24]
for row in actual['records']:
    audio=Path(row['input'])
    assert hashlib.sha256(audio.read_bytes()).hexdigest()==row['wav_sha256']
    with wave.open(str(audio),'rb') as w:pcm=w.readframes(w.getnframes())
    assert len(pcm)//2==row['sample_count'] and hashlib.sha256(pcm).hexdigest()==row['pcm_sha256']
    assert row['result']['state']=='READY' and row['result']['text']
    assert row['result']['model_id']==model_id
ui=json.loads((WORK/'gtk-preview/validation.json').read_text())
assert not ui['board_asr_verified'] and len(ui['screens'])==6
assert ui['screens']['recognized']['transcript']==actual['records'][1]['result']['text']
assert all((s['width'],s['height'],s['scroll_height'])==(1024,600,52) for s in ui['screens'].values())

def phase(name):
    folders=sorted((WORK/'evidence').glob('*-'+name))
    return json.loads((folders[-1]/'response.json').read_text())

applied,ready,accepted=phase('apply-fixed'),phase('ready-final'),phase('native-asr-fixed')
assert applied['status']=='START_REQUESTED' and ready['status']=='READY'
assert applied['update_id']==ready['update_id']==manifest['update_id']
assert 'Ran 32 tests' in applied['native_tests'] and applied['native_tests'].rstrip().endswith('OK')
for relative in manifest['runtime_files']:
    assert ready['runtime_files'][relative]==applied['runtime_files'][relative]==manifest['files']['aura/'+relative]['sha256']
assert accepted['status']=='PASS_NATIVE_RECORDING_AND_DISCONNECTED_ASR'
assert not accepted['actual_board_asr_transcription_verified']
assert accepted['recorded']['sample_count']>=24000
assert accepted['disconnected_result']['state']=='ERROR' and not accepted['disconnected_result']['text']
final=accepted['final']
assert final['ui_page']=='main' and final['ui_layer']=='presentation' and final['phase']=='IDLE'
assert not final['error'] and final['local_recording']['result'] is None
assert not final['local_transcription']['service']['enabled'] and not final['local_transcription']['text']
assert final['ui_settings']['volume']==58 and not final['ui_settings']['muted']
prepared=phase('prepared-target')
assert prepared['status']=='ASR_TARGET_CONFIGURED' and not prepared['service_ready_verified']
final=prepared['final']
assert final['local_transcription']['service']['enabled']
assert final['local_transcription']['service']['host']=='192.168.50.1'
assert final['local_transcription']['service']['port']==8791
assert final['local_recording']['result'] is None and not final['local_transcription']['text']
assert final['ui_page']=='main' and final['ui_layer']=='presentation' and final['phase']=='IDLE' and not final['error']
result={'status':'PASS_SOFTWARE_AND_DEPLOYMENT_LAN_ASR_NOT_VERIFIED','verified_uart_responses':responses,
        'packages':packages,
        'verified_attachments':attachments,'board_failures':failures,'package_sha256':bundle['sha256'],
        'package_files':len(manifest['files']),'update_id':manifest['update_id'],
        'startup_release':manifest['startup_release'],'host_framework_tests':182,'board_related_tests':32,
        'actual_model_verified_on_host':True,'actual_board_mcp01_wav_transcribed_on_host':True,
        'live_board_asr_and_lan_verified':False,'host_gtk_asr_states':6,
        'asr_target_configured':'192.168.50.1:8791','asr_target_ready_verified':False,
        'board_native_recording':accepted['recorded'],'final':final}
(WORK/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
