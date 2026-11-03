"""Prepare a metadata-only observer; the main chat never executes it on a device."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE.parent / 'probe.py'
spec = importlib.util.spec_from_file_location('source_metadata_probe', PROBE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

EXTRA = r'''
def opaque_hash(value):
 return hashlib.sha256(value.encode()).hexdigest() if isinstance(value,str) and value else None
trans=state.get('local_transcription',{})
ack=dialogue.get('last_playback_ack') or {}
current=opaque_hash(trans.get('request_id'))
ack_token=opaque_hash(ack.get('request_id'))
page=state.get('ui_page')
avatar=state.get('avatar_display',{})
observed={key:out[key] for key in ('observed_mono','startup_sha256','board_boot_id',
 'phase','playing','listening','latency','prepare_latency','audio_output',
 'producer_diagnostics','stream_diagnostics','runtime_faults','capture_performance','last_capture_failure')}
observed.update(kind='sample',request_token=current,ack_request_token=ack_token,
 ack_committed=ack.get('committed') is True,
 ack_matches_current_request=bool(current and current==ack_token),
 transcription_state=stage(trans.get('state')),
 ui_page=page if page in ('main','vision','settings','devices','conversation') else 'UNKNOWN',
 native_visible=avatar.get('visible') if type(avatar.get('visible')) is bool else None,
 native_frame_scheduling_active=avatar.get('frame_scheduling_active') if type(avatar.get('frame_scheduling_active')) is bool else None,
 native=scalar(avatar), capture_counts=scalar(state.get('safe_capture_diagnostics',{}).get('counters',{})))
'''

assert module.REMOTE.count('print(json.dumps(out))') == 1
source = module.REMOTE.replace('print(json.dumps(out))', EXTRA)
remote = '"""Device-owner-only observer; inject EXPECTED_STARTUP and EXPECTED_BOOT before exec."""\n'
remote += 'import hashlib,http.client,json,time\nSOURCE=' + repr(source) + '\n'
remote += r'''
assert isinstance(EXPECTED_STARTUP,str) and len(EXPECTED_STARTUP)==64
assert isinstance(EXPECTED_BOOT,str) and EXPECTED_BOOT
began=time.monotonic(); deadline=began+180.
initial_request=None;first=True;ready=False;completed=set();last_probe=None
while time.monotonic()<deadline:
 tick=time.monotonic();cpu=time.process_time()
 exec(SOURCE)
 if observed['startup_sha256']!=EXPECTED_STARTUP or observed['board_boot_id']!=EXPECTED_BOOT:
  print(json.dumps(dict(kind='complete',status='CONTEXT_CHANGED')),flush=True)
  break
 if first:
  initial_request=observed['request_token'];first=False
 h=observed['listening']
 if (not ready and observed['phase']=='IDLE' and observed['playing'] is False
     and h.get('enabled') is True and h.get('microphone_open') is True
     and h.get('state')=='WAITING_SPEECH'):
  ready=True
  print(json.dumps(dict(kind='ready',status='READY_FOR_ONE_NEW_TURN',observed_mono=observed['observed_mono'],
    startup_sha256=EXPECTED_STARTUP,deadline_mono=deadline,
    acoustic_first_sound_measured=False,raw_text_audio_or_images_saved=False)),flush=True)
 print(json.dumps(observed,allow_nan=False),flush=True)
 last_probe=dict(wall_ms=(time.monotonic()-tick)*1000,cpu_ms=(time.process_time()-cpu)*1000)
 print(json.dumps(dict(kind='observer_cost',**last_probe)),flush=True)
 token=observed['request_token']
 if (ready and token and token!=initial_request and observed['ack_committed']
     and observed['ack_matches_current_request'] and observed['latency'].get('complete') is True):
  completed.add(token)
  print(json.dumps(dict(kind='complete',status='ONE_NEW_TURN_COMPLETE',request_token=token,
    observed_mono=observed['observed_mono'],raw_text_audio_or_images_saved=False)),flush=True)
  break
 time.sleep(max(0.,1.-(time.monotonic()-tick)))
else:
 print(json.dumps(dict(kind='complete',status='WINDOW_TIMEOUT',ready_observed=ready,
   completed_new_turns=len(completed))),flush=True)
'''
compile(remote, '<metadata-observer>', 'exec')
target = HERE / 'live_observer_remote.py'
with target.open('x', encoding='utf-8', newline='\n') as handle:
    handle.write(remote)
proof = dict(schema='aura-joint-live-observer-source-1',
             status='PREPARED_NOT_EXECUTED_BY_MAIN_CHAT',
             sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
             base_projector_sha256=hashlib.sha256(PROBE.read_bytes()).hexdigest(),
             injected_context=('EXPECTED_STARTUP', 'EXPECTED_BOOT'),
             interval_seconds=1, maximum_window_seconds=180,
             device_control_or_model_requests=False,
             one_fresh_request_and_matching_complete_ack_required=True,
             acoustic_end_of_speech_or_first_sound_measured=False,
             raw_text_audio_images_or_identity_exported=False)
(HERE / 'live_observer_manifest.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
print(json.dumps(proof))
