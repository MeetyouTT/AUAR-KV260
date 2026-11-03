"""Actual archived-ASR input through production channel; no capture/playback/ACK."""
import argparse
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time
import uuid
import wave

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'aura'))
from common.asr_wire import encode_context
from common.voice_channel import ChannelState, read_frame

parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
args = parser.parse_args()
with wave.open(str(ROOT / 'deliverables/2026-10-18_stream_playback/chat_input.wav'), 'rb') as audio:
    assert (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) == (16000, 1, 2)
    pcm = audio.readframes(audio.getnframes())
meta = {'protocol': 'aura-asr-1', 'board_boot_id': 'latency-diagnosis',
        'session_id': uuid.uuid4().hex, 'request_id': uuid.uuid4().hex,
        'capture_id': 'archived-latency-input', 'generation': 1,
        'sample_count': len(pcm)//2, 'pcm_sha256': hashlib.sha256(pcm).hexdigest(),
        'budget_ms': 120000}
connection = http.client.HTTPConnection('192.168.50.1', 8792, timeout=125)
state = ChannelState(meta)
started = time.perf_counter()
row = {'actual_models': True, 'actual_playback': False, 'archived_input': True,
       'playback_ack_sent': False, 'synthetic_conversation_id': uuid.uuid4().hex}
try:
    connection.request('POST', '/v1/voice/channel', pcm, {
        'Content-Type': 'application/octet-stream', 'X-Aura-Asr': encode_context(meta),
        'X-Aura-Conversation': 'v1:' + row['synthetic_conversation_id']})
    response = connection.getresponse()
    if response.status != 200:
        raise RuntimeError(response.read(1024).decode())
    while not state.ended:
        header, raw = read_frame(response)
        state.accept(header, raw)
        elapsed = round((time.perf_counter() - started)*1000, 2)
        if header['kind'] == 'error':
            raise RuntimeError(header['error'])
        if header['kind'] == 'text':
            row.setdefault('first_text_ms', elapsed)
        if header['kind'] == 'audio':
            row.setdefault('first_pcm_ms', elapsed)
        if header['kind'] == 'end':
            row['end'] = header
    row['reply'] = state.text
finally:
    connection.close()
    (HERE / (args.name + '.json')).write_text(json.dumps(row, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(row, ensure_ascii=False), flush=True)
