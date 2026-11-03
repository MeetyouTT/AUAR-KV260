"""Exclusive actual-model ABBA: same free-generated reply and uncached TTS."""
import hashlib
import argparse
import io
import json
from pathlib import Path
import statistics
import sys
import time
from types import SimpleNamespace
import uuid
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'aura'))
from common.voice_channel import ChannelState, read_frame
from tools import dialogue_stream
from tools.selected_voice_service import VoiceWorker
from tools.voice_channel_source import channel_frames

folder = HERE / ('profile_' + uuid.uuid4().hex[:10])
folder.mkdir()
worker = VoiceWorker(folder / 'voice', python=sys.executable,
                     model_path=ROOT / 'aura/models/tts/OmniVoice', engine='omnivoice')
original_generate = worker.generate
original_body = dialogue_stream.stream_body
case_number = [0]


def uncached(text):
    key, _ = worker.synth.identity(text)
    # Preserve only this benchmark's synthetic clips instead of reusing them.
    archive = folder / 'previous_clips' / str(case_number[0])
    archive.mkdir(parents=True, exist_ok=True)
    for suffix in ('.wav', '.json'):
        source = worker.cache / (key + suffix)
        target = archive / (key + suffix)
        if source.exists():
            assert source.resolve().parent == worker.cache.resolve()
            assert archive.resolve().is_relative_to(folder.resolve())
            source.replace(target)
    return original_generate(text)


def seeded(*args, **kwargs):
    body = original_body(*args, **kwargs)
    body['options']['seed'] = 42
    return body


report = {'actual_27b': True, 'actual_omnivoice16': True, 'actual_playback': False,
          'playback_ack_sent': False, 'free_generation': True, 'seed': 42, 'cases': []}
parser = argparse.ArgumentParser()
parser.add_argument('--multi', action='store_true')
args = parser.parse_args()
worker.generate = uncached
try:
    worker.warmup()
    assert worker.ready, worker.error
    with patch.object(dialogue_stream, 'stream_body', seeded):
        # Prime native discovery and the unchanged system prefix once.
        stream = dialogue_stream.OllamaReplyStream('http://127.0.0.1:11435',
            'aura-qwen3.8-27b-abliterated:iq4_xs', [], '你好', 90,
            reply_first=True, compact_grammar=True)
        for _ in stream:
            pass
        prompts = ['讲一个简短的两句话小故事，别太复杂。',
                   '如果我今天心情不太好，你会怎么陪我？', '你叫什么名字？']
        if args.multi:
            prompts = ['用两句完整的话回答：你想怎么陪我？再问我一个问题。',
                       '能不能先安慰我一句，然后问问我为什么难过？']
        for prompt in prompts:
            # Prime both actual synthesis shapes before the ABBA comparison.
            order = (False, True, False, True, True, False) if args.multi else (False, True, True, False)
            for index, enabled in enumerate(order):
                case_number[0] += 1
                models = SimpleNamespace(voice=worker, histories={}, latency_options={
                    'reply_first': True, 'early_sentence': True, 'coalesce_chat': True,
                    'compact_grammar': True, 'first_sentence_chat': enabled})
                meta = {'protocol': 'aura-asr-1', 'board_boot_id': 'latency-profile',
                    'session_id': uuid.uuid4().hex, 'request_id': uuid.uuid4().hex,
                    'capture_id': 'synthetic', 'generation': 1, 'sample_count': 3200,
                    'pcm_sha256': hashlib.sha256(b'\1\0'*3200).hexdigest(), 'budget_ms': 120000}
                state = ChannelState(meta)
                row = {'prompt': prompt, 'first_sentence_chat': enabled, 'audio_segments': []}
                started = time.perf_counter()
                seen = set()
                for packet in channel_frames(models, meta, prompt, 120,
                        model='aura-qwen3.8-27b-abliterated:iq4_xs', host='http://127.0.0.1:11435'):
                    header, pcm = read_frame(io.BytesIO(packet))
                    state.accept(header, pcm)
                    elapsed = round((time.perf_counter() - started)*1000, 2)
                    if header['kind'] == 'error':
                        raise RuntimeError(header['error'])
                    if header['kind'] == 'audio':
                        row.setdefault('first_pcm_ms', elapsed)
                        segment = header['segment_id']
                        if segment not in seen:
                            seen.add(segment)
                            row['audio_segments'].append({'id': segment, 'first_arrival_ms': elapsed,
                                'start_sample': header['start_sample']})
                    if header['kind'] == 'end':
                        row['end'] = header
                row.update(reply=state.text, samples=state.samples, audio_sha256=state.digest.hexdigest())
                assert state.ended and row['end']['tts_cache_hits'] == 0
                if args.multi and index < 2:
                    print(json.dumps({'warmup_excluded': True, 'enabled': enabled}, ensure_ascii=False), flush=True)
                    continue
                segments = row['audio_segments']
                row['estimated_second_segment_late_ms'] = (max(0, round(
                    segments[1]['first_arrival_ms'] - segments[0]['first_arrival_ms'] -
                    segments[1]['start_sample']/24, 2)) if len(segments)>1 else 0)
                report['cases'].append(row)
                (folder / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps({'prompt': prompt, 'enabled': enabled, 'first_pcm_ms': row['first_pcm_ms'],
                    'clauses': row['end']['clauses'], 'estimated_late_ms': row['estimated_second_segment_late_ms'],
                    'reply': row['reply']}, ensure_ascii=False), flush=True)
    report['summary'] = []
    for prompt in prompts:
        rows = [row for row in report['cases'] if row['prompt'] == prompt]
        same_reply = len({row['reply'] for row in rows}) == 1
        medians = {str(enabled): statistics.median(row['first_pcm_ms'] for row in rows
                   if row['first_sentence_chat'] == enabled) for enabled in (False, True)}
        report['summary'].append({'prompt': prompt, 'same_reply': same_reply,
            'first_pcm_median_ms': medians, 'improvement_ms': round(medians['False']-medians['True'], 2),
            'max_estimated_second_segment_late_ms': max(row['estimated_second_segment_late_ms'] for row in rows)})
    (folder / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (HERE / 'latest_profile.json').write_text(json.dumps({'folder':str(folder),'summary':report['summary']},ensure_ascii=False,indent=2), encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False), flush=True)
finally:
    worker.close()
