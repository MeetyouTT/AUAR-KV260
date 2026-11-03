"""Independently decode UART frames and compare the captured audio artifact."""
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import wave
import zipfile

ROOT = Path(__file__).resolve().parent
AURA = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
responses = 0
for folder in sorted((ROOT/'evidence').iterdir()):
    result = json.loads((folder/'result.json').read_text())
    assert result['complete'] and result['console_echo_restored'], str(folder)
    rows = result.get('commands') or [dict(name='response', exit_code=result['exit_code'],
        bytes=result['bytes'], sha256=result['sha256'])]
    raw = (folder/'serial.raw').read_bytes().decode('utf-8','replace')
    # The shell prompt has no newline; the next BEGIN can follow "# ".
    begins = re.findall(r'\bBEGIN (MEDIA\d+) (\d+) (\d+)\r?$',raw,re.M)
    assert len(begins) == len(rows), (folder,len(begins),len(rows))
    for row, (marker, rc, size) in zip(rows, begins):
        chunks = re.findall(r'^DATA '+marker+r' (\d+) ([A-Za-z0-9+/=]+)\r?$',raw,re.M)
        assert [int(i) for i,_ in chunks] == list(range(len(chunks)))
        decoded = gzip.decompress(base64.b64decode(''.join(s for _,s in chunks),validate=True))
        end = re.findall(r'^END '+marker+r' ([a-f0-9]{64})\r?$',raw,re.M)
        digest = hashlib.sha256(decoded).hexdigest()
        assert end == [digest]
        assert int(rc)==row['exit_code']==0 and int(size)==row['bytes']==len(decoded)
        assert row['sha256']==digest and (folder/(row['name']+'.output')).read_bytes()==decoded
        responses += 1

folder = next((ROOT/'evidence').glob('*-capture-acceptance'))
response = json.loads((folder/'response.output').read_bytes())
artifact = response['artifacts']['mcp01-3s.wav']
blob = (folder/'mcp01-3s.wav').read_bytes()
assert base64.b64decode(artifact['base64'],validate=True)==blob
assert len(blob)==artifact['bytes']==96044
assert hashlib.sha256(blob).hexdigest()==artifact['sha256']==response['natural_capture']['wav_sha256']
with wave.open(io.BytesIO(blob),'rb') as wav:
    assert (wav.getframerate(),wav.getnchannels(),wav.getsampwidth(),wav.getnframes())==(16000,1,2,48000)
    pcm = wav.readframes(48000)
assert hashlib.sha256(pcm).hexdigest()==response['natural_capture']['pcm_sha256']
assert response['exclusive_owner_rejected'] and response['cancelled_audio_not_delivered']
assert response['services_unchanged']
before, after = response['camera_before'], response['camera_after']
assert (before['pid'],before['service_epoch'],before['board_boot_id']) == (after['pid'],after['service_epoch'],after['board_boot_id'])
assert after['capture_frames']>before['capture_frames'] and after['detected_frames']>before['detected_frames']
assert not any(after[k] for k in ('camera_error','detector_error','preview_error'))
assert (folder/'mcp01-3s.wav').stat().st_mode & 0o777 == 0o600

bundle = json.loads((ROOT/'capture_bundle.json').read_text())
blob = (ROOT/bundle['zip']).read_bytes()
assert hashlib.sha256(blob).hexdigest()==bundle['sha256']
with zipfile.ZipFile(io.BytesIO(blob)) as archive:
    assert archive.testzip() is None
    for relative, record in bundle['files'].items():
        data = archive.read(relative)
        assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256']
        if relative in ('board/runtime/audio/capture.py','host/model_service/protocol.py','tools/board_audio_capture.py'):
            assert (AURA/relative).read_bytes()==data

test_result = json.loads((ROOT/'framework_test_result.json').read_text())
assert test_result['exit_code']==0
test_log = (ROOT/'framework_tests.log').read_text()
assert 'Ran 149 tests' in test_log and test_log.rstrip().endswith('OK')
preflight = json.loads((ROOT/'avatar_resource_preflight.output').read_text())
assert preflight['status']=='PASS' and preflight['frames_verified']==573 and len(preflight['cached_clips'])==4
result = {'status':'PASS_CAPTURE_MILESTONE_WITH_RECORDED_LIMITS','uart_responses_verified':responses,
    'capture_release':bundle['release_id'],'bundle_files_verified':len(bundle['files']),
    'real_audio_frames':48000,'real_audio_seconds':3,'framework_tests_passed':149,
    'cached_avatar_frames_verified':573,'cached_clips_verified':4,
    'capture_frames_increment':after['capture_frames']-before['capture_frames'],
    'detection_frames_increment':after['detected_frames']-before['detected_frames'],
    'limits':response['not_tested'],'network_blocker':'eth0 NO-CARRIER; no board IP or route'}
(ROOT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
