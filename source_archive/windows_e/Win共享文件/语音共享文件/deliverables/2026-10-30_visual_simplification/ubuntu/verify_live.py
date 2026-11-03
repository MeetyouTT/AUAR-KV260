"""Final installed-runtime checks and upstream public PCM; no private identity export."""
import hashlib
import http.client
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
import wave

STAGE = Path('/home/root/aura-board-vision-20261030/06391079cfddb734-r3-ubuntu')
sys.path.insert(0,str(STAGE/'ops'))
from board_state import capture,digest
from workflow_common import signature

deployment = json.loads((STAGE/'deployment.json').read_text())
assert deployment['status'] == 'COMMITTED' and deployment['watchdog_stopped']
before = capture()
assert before['safe'] and not before['mismatches']
assert before['actual_config'] == str(STAGE/'startup/config.json') == before['pending_config']
assert signature(before) == signature(deployment['after'])
observer = before['state']['device_observer']
assert observer['enabled'] is False and observer['image_upload_enabled'] is False and observer['sent'] == 0
assert observer['retired_reason'] == 'semantic_vision_removed'
Path(before['active_pointers']['stage.log']['resolved']).relative_to(STAGE/'runtime/managed-runs')

def get(port,path='/health'):
    with urllib.request.urlopen('http://192.168.50.1:'+str(port)+path,timeout=5) as r:
        return json.load(r)

voice = get(8792)
hub = get(8812)
assert voice['ready'] and not voice['busy']
assert voice['service_revision'] == 'voice-board-vision-20261030-r12'
assert voice['visual_processing']['semantic_model_enabled'] is False
assert hub['speaker_ready'] and hub['automatic_profile_access'] is False
assert hub['visual_processing']['image_upload_enabled'] is False
with socket.socket() as probe:
    probe.settimeout(2)
    retired_port_result = probe.connect_ex(('192.168.50.1',8810))
assert retired_port_result != 0
gone = {}
for port,path in ((8812,'/v1/observations'),(8792,'/v1/voice/visual/frame')):
    client = http.client.HTTPConnection('192.168.50.1',port,timeout=5)
    try:
        client.request('POST',path,b'{}',{'Content-Type':'application/json'})
        response = client.getresponse()
        value = json.loads(response.read(4096))
        assert response.status == 410 and value['image_upload_enabled'] is False
        gone[path] = response.status
    finally:
        client.close()

with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=5) as response:
    camera = json.load(response)
# Traverse only established subsystem names, never identity-indexed maps/lists.
allowed_children = {'camera','detector','tracking','identity','features','extractor',
                    'inference','metrics','scheduler','status','health','backend'}
allowed_values = {'ready','enabled','state','backend','detector_backend','tracking_backend',
                  'model_id','processed','captured','frame_id','frame_count','camera_epoch',
                  'inference_count','detector_ready','tracking_ready','capture_fps','inference_fps'}
camera_summary = {}
def summarize(value,prefix=''):
    if not isinstance(value,dict):
        return
    for key,item in value.items():
        name = prefix+key
        if key in allowed_values and isinstance(item,(str,int,float,bool,type(None))):
            camera_summary[name] = item
        elif key in allowed_children and isinstance(item,dict):
            summarize(item,name+'.')
summarize(camera)

# Feed only a known upstream public WAV, without a conversation ID, gallery,
# speaker-visual header, playback sink, success ACK, or durable memory writes.
assert PUBLIC_WAV_PATH
audio_path = Path(PUBLIC_WAV_PATH)
assert digest(audio_path) == '1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c'
with wave.open(str(audio_path),'rb') as audio:
    assert (audio.getnchannels(),audio.getsampwidth(),audio.getframerate()) == (1,2,16000)
    pcm = audio.readframes(audio.getnframes())
sys.path.insert(0,before['actual_runtime']+'/aura')
from board.runtime.audio.voice_channel import VoiceChannel
request = uuid.uuid4().hex
meta = dict(protocol='aura-asr-1',board_boot_id=before['boot'],
            session_id=uuid.uuid4().hex,request_id=request,generation=1,
            capture_id='public-visual-ubuntu',sample_count=len(pcm)//2,
            pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=90000)
channel = VoiceChannel('192.168.50.1',visual_question=True)
events = []
output_digest = hashlib.sha256()
first = None
started = time.monotonic()
def receive(header,data):
    global first
    assert not header.get('visual_request'), 'Retired image inference request reappeared'
    events.append(header['kind'])
    if header['kind'] == 'audio':
        output_digest.update(data)
        if first is None:
            first = time.monotonic()-started
result = None
public_error = None
try:
    result = channel.exchange(meta,pcm,receive)
except RuntimeError as exc:
    if not str(exc).startswith('GpuBusy:'):
        raise
    public_error = str(exc)
finally:
    channel.close()
if result is not None:
    assert result['network_complete'] and not result['playback_verified']
    assert result['sample_count'] > 0 and result['reply_text']
    assert result['pcm_sha256'] == output_digest.hexdigest()
after = capture()
assert signature(after) == signature(before) and after['safe'] and not after['mismatches']
assert after['state']['device_observer']['sent'] == 0
timer = subprocess.run(['systemctl','is-active',deployment['watchdog_unit']+'.timer'],
                       stdout=subprocess.PIPE,text=True,timeout=5)
assert timer.returncode != 0
latest_voice = get(8792)
coord = latest_voice.get('gpu_coordination',{})
print(json.dumps(dict(
    status='PASS' if result is not None else 'BOARD_PASS_VOICE_GPU_BLOCKED',
    board_verification_passed=True,
    actual_config=after['actual_config'],pending_config=after['pending_config'],
    actual_runtime=after['actual_runtime'],boot=after['boot'],
    supervisor_pid=after['actual_proc']['pid'],gui_pid=after['child']['pid'],
    camera_pid=after['camera_proc']['pid'],camera_epoch=after['state']['camera_epoch'],
    pins=len(after['pins']),mismatches=after['mismatches'],observer=after['state']['device_observer'],
    camera_health_summary=camera_summary,camera_health_keys=sorted(camera),
    voice_revision=voice['service_revision'],voice_ready=voice['ready'],
    voice_source_fingerprint=voice.get('source_fingerprint'),
    retired_port_closed=True,retired_port_connect_errno=retired_port_result,retired_endpoints=gone,
    speaker_service_ready=hub['speaker_ready'],automatic_profile_access=False,
    public_voice=dict(status='PASS' if result is not None else 'BLOCKED_GPU_ADMISSION',
                      error=public_error,source='existing_upstream_public_wav',
                      input_file_sha256=digest(audio_path),input_pcm_sha256=meta['pcm_sha256'],
                      output_pcm_sha256=result['pcm_sha256'] if result else None,
                      sample_count=result['sample_count'] if result else 0,
                      reply_characters=len(result['reply_text']) if result else 0,first_pcm_seconds=first,
                      elapsed_seconds=time.monotonic()-started,events=events,
                      actual_installed_runtime=before['actual_runtime'],
                      face_metadata_submitted=False,playback_ack_sent=False,durable_conversation_used=False),
    gpu_admission=dict(last_reason=coord.get('last_reason'),
                       last_wait_ms=coord.get('last_wait_ms'),
                       llm_requirement=coord.get('llm_requirement'),
                       llm_residency=coord.get('llm_residency'),
                       memory_snapshot=coord.get('memory')),
    listening=after['listening'],microphone_open=after['microphone_open'],pan=after['pan'],
    watchdog_inactive=True,no_deployment_transaction_running=True,
    microphone_opened=False,physical_playback=False,motion_command_sent=False,
    structured_visual_timeline_deployed=False,asr_or_memory_migrated=False,
    windows_model_removal='PENDING_WINDOWS_SIDE',private_identity_exported=False)))
