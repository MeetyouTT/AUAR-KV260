"""Opt-in metadata-only loopback GET sampler. Import/default CLI do no I/O.

No image, conversation, identity value, device/proc read, command POST or model
call is retained or performed. CPU/PSS must be paired from the publisher's
existing explicitly PID-pinned resource sampler; /api/state has no such data.
"""
import argparse
import json
import math
import time
import urllib.error
import urllib.request


URL = 'http://127.0.0.1:8783/api/state'
PAIR = 'xuefei-yuki-board-v1-candidate'
PROMPT = '11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e'
FIELDS = {
    'sequence': 'number', 'playing': 'bool', 'paused': 'bool',
    'avatar_command_pending': 'number',
    'avatar_display.frames': 'number', 'avatar_display.paint_at': 'number',
    'avatar_display.age_ms': 'number', 'avatar_display.visible': 'bool',
    'avatar_display.frame_scheduling_active': 'bool', 'avatar_display.target_fps': 'number',
    'avatar_display.rejected_controls': 'number', 'avatar_display.stale_frames': 'number',
    'avatar_display.elapsed_dropped_seconds': 'number',
    'avatar_display.native_call_ms': 'number', 'avatar_display.evaluate_ms': 'number',
    'avatar_display.submit_ms': 'number', 'avatar_display.egl_bind_ms': 'number',
    'avatar_display.egl_swap_ms': 'number', 'avatar_display.gtk_callback_ms': 'number',
    'portrait_offload.ready': 'bool', 'portrait_offload.target_fps': 'number',
    'portrait_offload.pending': 'number', 'portrait_offload.inflight_limit': 'number',
    'portrait_offload.offered': 'number', 'portrait_offload.replaced': 'number',
    'portrait_offload.fallback_allowed': 'bool',
    'character_pair.target_fps': 'number', 'character_pair.fallback_allowed': 'bool',
    'local_transcription.service.enabled': 'bool', 'local_transcription.service.pending': 'bool',
    'local_transcription.service.board_owned': 'bool', 'local_transcription.service.streaming': 'bool',
    'local_transcription.service.conversation': 'bool', 'local_transcription.service.feedback_ready': 'bool',
    'local_transcription.service.capabilities.ordinary_dialogue': 'bool',
    'local_transcription.service.capabilities.explicit_memory': 'bool',
    'local_transcription.service.capabilities.history_routing': 'bool',
    'handsfree_dialogue.enabled': 'bool', 'handsfree_dialogue.microphone_open': 'bool',
    'voice_barge_in.listening': 'bool', 'voice_barge_in.continuation_listening': 'bool',
    'automatic_conversation.enabled': 'bool', 'local_recording.sample_count': 'number',
    'manual_pan.pulse_us': 'nullable_number', 'manual_pan.target_us': 'nullable_number',
    'manual_pan.automatic_following': 'bool',
}
ENUMS = {
    'phase': {'IDLE','VOICE_PREPARING','VOICE_STARTING','SPEAKING','ACTION','THINKING','THINKING_FEEDBACK','DIALOGUE_WAITING'},
    'avatar_display.kind': {'native_yuki_egl'},
    'avatar_display.presentation_state': {'visible','hidden'},
    'character_pair.state': {'PREPARED','READY','FAILED'},
    'portrait_offload.mode': {'native','blocked'},
    'local_recording.state': {'IDLE','CANCELLED','READY','RECORDING','ERROR'},
    'local_transcription.state': {'IDLE','DISABLED','TRANSCRIBING','GENERATING','PLAYING','ANSWERED','CANCELLED','READY','EMPTY','ERROR'},
    'handsfree_dialogue.state': {'PAUSED','WAITING_WAKE','WAITING_SPEECH','WAITING_SERVICE','COOLDOWN','CONVERSATION','CHECKING_WAKE','WAITING_AUDIO_IDLE'},
    'manual_pan.state': {'FAULT','UNAVAILABLE','CONNECTING','READY','MOVING','STOPPING','CONFIGURING'},
    'ui_runtime.snapshot.modules.motion.state': {'FAULT','DISARMED','NEEDS_REFERENCE','ARMED','TRACKING','AT_LIMIT','UNKNOWN'},
}
MISSING = object()


def get(value, path):
    for key in path.split('.'):
        if not isinstance(value, dict) or key not in value:
            return MISSING
        value = value[key]
    return value


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def sanitize(state):
    if not isinstance(state, dict):
        raise ValueError('state_not_object')
    result, missing = {}, []
    for path, kind in FIELDS.items():
        value = get(state, path)
        if value is MISSING:
            missing.append(path)
        elif (kind == 'bool' and type(value) is bool or
              kind in ('number','nullable_number') and number(value) or
              kind == 'nullable_number' and value is None):
            result[path] = value
        else:
            result[path + '.type_invalid'] = True
    for path, allowed in ENUMS.items():
        value = get(state, path)
        if value is MISSING:
            missing.append(path)
        else:
            result[path] = value if isinstance(value, str) and value in allowed else 'OTHER'
    for path in ('error','character_pair.error','portrait_offload.error',
                 'local_transcription.service.feedback_error','local_transcription.service.cleanup_error'):
        value = get(state, path)
        if value is not MISSING:
            result[path + '.present'] = bool(value)
    result['pair_version_matches'] = get(state, 'character_pair.profile_version') == PAIR
    result['prompt_sha_matches'] = get(state, 'character_pair.prompt_sha256') == PROMPT
    result['missing_fields'] = missing
    return result


def observed_fps(rows):
    frames = elapsed = 0
    for previous, current in zip(rows, rows[1:]):
        a, b = previous.get('state', {}), current.get('state', {})
        if not all(x.get('avatar_display.visible') is True and x.get('avatar_display.frame_scheduling_active') is True for x in (a,b)):
            continue
        f0,f1 = a.get('avatar_display.frames'),b.get('avatar_display.frames')
        t0,t1 = a.get('avatar_display.paint_at'),b.get('avatar_display.paint_at')
        if all(number(v) for v in (f0,f1,t0,t1)) and f1 > f0 and t1 > t0:
            frames += f1-f0; elapsed += t1-t0
    return dict(visible_swap_frames=frames, visible_swap_span_seconds=elapsed,
                visible_swap_fps=frames/elapsed if elapsed else None,
                measurement='Delta native frames / delta successful EGL swap paint_at; not physical scanout or per-frame percentile')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('redirect_rejected')


def sample(duration=30., interval=.5):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    start = time.monotonic(); rows = []
    while time.monotonic()-start < duration:
        tick = time.monotonic(); row = {'sample_elapsed_seconds':tick-start}
        try:
            request = urllib.request.Request(URL, method='GET', headers={'Accept':'application/json'})
            with opener.open(request, timeout=1.) as response:
                if response.status != 200:
                    raise ValueError('http_status')
                payload = response.read(2*1024*1024+1)
                if len(payload) > 2*1024*1024:
                    raise ValueError('response_size')
                row['state'] = sanitize(json.loads(payload))
        except (OSError, ValueError, urllib.error.URLError):
            row['state_unavailable'] = True  # Never retain raw body/error strings.
        rows.append(row)
        time.sleep(max(0., interval-(time.monotonic()-tick)))
    return dict(kind='sanitized_ui_state_sample_v1', started_monotonic=start,
                ended_monotonic=time.monotonic(), rows=rows, fps=observed_fps(rows),
                cpu_pss_in_this_endpoint=False, hardware_or_model_commands=0,
                limitations=['No direct BoardBusinessRuntime.started flag is exported.',
                             'No exact native frame interval P95/P99 from coarse sampling.',
                             'No physical display, microphone electrical or model inference proof.'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', action='store_true', help='Explicitly perform bounded loopback GETs')
    parser.add_argument('--seconds', type=float, default=30.)
    parser.add_argument('--interval', type=float, default=.5)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 1 <= args.seconds <= 60 or not math.isfinite(args.interval) or not .25 <= args.interval <= 2:
        parser.error('Bound duration1..60s and interval0.25..2s')
    result = sample(args.seconds, args.interval) if args.sample else dict(
        status='DESCRIBE_ONLY_NO_HTTP', url=URL, fields=FIELDS, enums={k:sorted(v) for k,v in ENUMS.items()},
        sampling_seconds=args.seconds, interval=args.interval,
        no_images_identity_conversation=True, cpu_pss='Not present in/api/state; pair existing PID-pinned resource sampling separately')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
