"""Run the installed ARM client, public PCM in RAM, no playback or enrollment."""
import base64,datetime,hashlib,json,sys,wave
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'2026-10-29_audio_animation_polish'))
from board_guard import capture,same
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import base64,hashlib,json,sys,time,uuid
from pathlib import Path
payload=json.loads(PAYLOAD_JSON)
sys.path.insert(0,payload['runtime']+'/aura')
from board.runtime.audio.voice_channel import VoiceChannel
from board.runtime.audio.channel_jobs import ChannelConversationJobs
from board.runtime.audio.face_gallery_readback import FaceGalleryReadback
from common.speaker_visual import unavailable,encode_visual_header
pcm=base64.b64decode(payload['pcm'],validate=True)
meta=dict(protocol='aura-asr-1',board_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 session_id=uuid.uuid4().hex,request_id=uuid.uuid4().hex,generation=1,capture_id='public-final-arm',
 sample_count=len(pcm)//2,pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=120000)
assert meta['pcm_sha256']==payload['sha256']
visual=unavailable(meta,'SYNTHETIC_AUDIO_NO_CAPTURE')
assert encode_visual_header(visual,meta)
reader=FaceGalleryReadback.configured();assert reader is not None
packet=reader.read(meta,ChannelConversationJobs._identity_snapshot())
channel=VoiceChannel('192.168.50.1');events={};digest=hashlib.sha256();end={};start=time.monotonic()
def receive(header,data):
 kind=header['kind'];events.setdefault(kind,round((time.monotonic()-start)*1000,2))
 if kind=='audio':digest.update(data)
 if kind=='end':end.update(header)
try:
 assert channel.submit_face_gallery(meta,packet),'Actual gallery route was not accepted'
 # The public synthetic input has no durable CID or real capture boundary.
 # Omit speaker observations rather than claiming a visible person spoke it.
 result=channel.exchange(meta,pcm,receive,face_gallery=packet)
finally:channel.close()
assert result['network_complete'] and not result['playback_verified'] and result['sample_count']>0
assert result['pcm_sha256']==digest.hexdigest()
assert events['audio']>0 and 'end' in events
print(json.dumps(dict(status='PASS',python_version=sys.version.split()[0],
 actual_installed_runtime=payload['runtime'],network_complete=True,pcm_sha256=result['pcm_sha256'],
 output_samples=result['sample_count'],first_pcm_ms=events['audio'],total_ms=round((time.monotonic()-start)*1000,2),
 reply_characters=len(result['reply_text']),tts_cache_hits=end.get('tts_cache_hits'),
 gallery=dict(accepted=True,model_id=packet['gallery']['model_id'],revision=packet['gallery']['revision'],
 template_count=len(packet['inventory'])),speaker_visual_omitted_reason='SYNTHETIC_AUDIO_NO_CAPTURE',
 microphone_opened=False,physical_playback=False,playback_ack_sent=False,durable_conversation_used=False,
 identity_enrollment_performed=False,private_templates_exported=False)))
'''

report=dict(status='CHECKING',checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
try:
 deployment=json.loads((H/'board_deployment.json').read_text(encoding='utf-8'))
 assert deployment['status']=='COMMITTED'
 before=capture();assert before['safe'] and not before['mismatches']
 assert before['actual_runtime']==deployment['runtime'] and len(before['pins'])==286
 entries=json.loads((H/'final_public_inputs.json').read_text(encoding='utf-8'))['inputs']
 entry=next(v for v in entries if v['label']=='medium')
 with wave.open(str(H/entry['file']),'rb') as audio:
  assert audio.getnchannels()==1 and audio.getframerate()==16000 and audio.getsampwidth()==2
  pcm=audio.readframes(audio.getnframes())
 payload=dict(runtime=before['actual_runtime'],pcm=base64.b64encode(pcm).decode(),sha256=hashlib.sha256(pcm).hexdigest())
 script=REMOTE.replace('PAYLOAD_JSON',repr(json.dumps(payload)))
 result=json.loads(ssh('python3 -B -',script,timeout=140))
 assert result['status']=='PASS'
 after=capture();same(before,after)
 report.update(result,board_safe_before_after=True,source_pin_count=len(after['pins']),
  ui_pid=after['ui']['MainPID'],camera_pid=after['camera']['MainPID'],camera_epoch=after['state']['camera_epoch'])
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'arm_bridge_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
