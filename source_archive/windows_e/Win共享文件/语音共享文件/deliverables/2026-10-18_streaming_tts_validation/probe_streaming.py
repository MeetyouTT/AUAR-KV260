"""Actual candidate PCM arrival timing; header bytes never count as speech."""
import array
import hashlib
import http.client
import json
import os
from pathlib import Path
import statistics
import sys
import time
import wave

HERE = Path(os.environ.get('AURA_TTS_TRIAL_DIR',str(Path(__file__).resolve().parent)))
TEXTS = ('今天有你陪着聊天，我也觉得很开心。你今天遇到了什么有趣的事呀？', '别着急，我们可以一步一步来。先把最重要的事情做好，剩下的慢慢安排。')

def request(text, *, stream=True, chunk_tokens=25, name='probe'):
    # v0.2.0 /tts reads `format`; its README incorrectly shows response_format.
    body = json.dumps({'text': text, 'voice': 'xilan', 'mode': 'zero-shot', 'format': 'pcm', 'stream': stream, 'chunk_tokens': chunk_tokens, 'seed': 8701, 'speed': 1.0}, ensure_ascii=False).encode()
    connection = http.client.HTTPConnection('127.0.0.1', 51889, timeout=120)
    row = {'text': text, 'stream': stream, 'chunk_tokens': chunk_tokens, 'cached_audio': False, 'actual_playback': False}
    raw = bytearray(); chunks = []; first_signal = None
    started = time.perf_counter()
    try:
        connection.request('POST', '/tts', body=body, headers={'Content-Type': 'application/json'})
        response = connection.getresponse()
        row.update(status=response.status, header_ms=round((time.perf_counter()-started)*1000, 2), content_type=response.getheader('Content-Type'))
        if response.status != 200: raise RuntimeError(response.read(8192).decode(errors='replace'))
        assert (row['content_type'] or '').split(';')[0]=='audio/pcm', 'Only explicit raw PCM is accepted'
        while True:
            data = response.read1(65536)
            if not data: break
            if not raw: assert not data.startswith((b'RIFF',b'RF64',b'ID3',b'OggS',b'fLaC')), 'Unexpected encoded audio/container'
            elapsed = time.perf_counter() - started
            row.setdefault('first_pcm_ms', round(elapsed * 1000, 2))
            raw.extend(data)
            chunks.append([round(elapsed * 1000, 2), len(raw)])
            if first_signal is None and len(raw) >= 2:
                samples = array.array('h', raw[:len(raw)//2*2])
                if any(abs(value) > 100 for value in samples): first_signal = elapsed
        row.update(total_ms=round((time.perf_counter()-started)*1000, 2), first_signal_arrival_ms=None if first_signal is None else round(first_signal*1000, 2))
        assert raw and len(raw)%2 == 0, 'Incomplete or empty PCM16'
        samples = array.array('h', raw)
        row.update(duration_s=len(samples)/24000, peak=max(abs(v) for v in samples), rms=(sum(float(v)*v for v in samples)/len(samples))**.5, pcm_sha256=hashlib.sha256(raw).hexdigest(), network_reads=len(chunks))
        assert row['peak'] > 100, 'Silent candidate output'
        # Earliest continuous playback start implied by measured byte arrivals.
        # This is a buffering estimate, not a measured speaker start.
        required_start = max(arrival/1000 - (chunks[i-1][1] if i else 0)/48000 for i,(arrival,_) in enumerate(chunks))
        row['earliest_no_underflow_start_ms'] = round(required_start*1000, 2)
        row['buffer_needed_after_first_pcm_ms'] = round(max(0, required_start*1000-row['first_pcm_ms']), 2)
        row['arrival_trace'] = chunks
        row['rtf'] = round(row['total_ms']/1000/row['duration_s'], 3)
        target = HERE / f'{name}.wav'
        with wave.open(str(target), 'wb') as audio:
            audio.setparams((1,2,24000,0,'NONE','not compressed')); audio.writeframes(raw)
        row['wav'] = str(target)
        return row
    finally: connection.close()

def main():
    report = {'status': 'RUNNING', 'candidate': 'CosyVoice3-2512_Q8_0', 'main_27b_unchanged': True, 'audio_quality_listening': 'PENDING', 'cases': []}
    report['warmup'] = request('嗯，我在听。', chunk_tokens=25, name='warmup')
    for repeat, tokens in enumerate((0,25,50,50,25,0)):
        for index,text in enumerate(TEXTS):
            row = request(text, stream=tokens!=0, chunk_tokens=tokens, name=f'candidate-{repeat}-{index}')
            row['repeat'] = repeat
            report['cases'].append(row)
            (HERE/'streaming.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({k:v for k,v in row.items() if k!='arrival_trace'},ensure_ascii=True), flush=True)
    report['status'] = 'COMPLETE_AUDIO_NOT_YET_ACCEPTED'
    report['summary'] = {str(tokens): {'n':len(rows), 'first_pcm_median_ms':statistics.median(r['first_pcm_ms'] for r in rows), 'continuous_start_median_ms':statistics.median(r['earliest_no_underflow_start_ms'] for r in rows), 'rtf_median':statistics.median(r['rtf'] for r in rows)} for tokens in (0,25,50) for rows in [[r for r in report['cases'] if r['chunk_tokens']==tokens]]}
    (HERE/'streaming.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)

if __name__ == '__main__': main()
