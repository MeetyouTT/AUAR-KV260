import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import wave

HERE = Path(__file__).resolve().parent
sys.path.insert(0, r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_principle_video_16x9\.build\pydeps')
import edge_tts
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
DATA = json.loads((HERE / 'narration.json').read_text(encoding='utf-8'))
AUDIO = HERE / 'audio'
AUDIO.mkdir(exist_ok=True)


async def one(i, scene):
    mp3 = AUDIO / f'{i+1:02d}.mp3'
    metadata = AUDIO / f'{i+1:02d}-boundaries.json'
    if mp3.is_file() and metadata.is_file() and mp3.stat().st_size > 1000:
        print(f'reuse scene {i+1}', flush=True)
    else:
        for attempt in range(3):
            try:
                client = edge_tts.Communicate(scene['text'], DATA['voice'], rate=DATA['rate'], pitch=DATA['pitch'], boundary='WordBoundary')
                bounds = []
                with mp3.open('wb') as out:
                    async for chunk in client.stream():
                        if chunk['type'] == 'audio':
                            out.write(chunk['data'])
                        else:
                            bounds.append(chunk)
                metadata.write_text(json.dumps(bounds, ensure_ascii=False, indent=2), encoding='utf-8')
                print(f'synthesized scene {i+1}: {mp3.stat().st_size} bytes / {len(bounds)} boundaries', flush=True)
                break
            except Exception as error:
                print(f'scene {i+1} attempt {attempt+1}: {type(error).__name__}: {error}', flush=True)
                if attempt == 2:
                    raise
                await asyncio.sleep(2)
    pcm = AUDIO / f'{i+1:02d}.wav'
    subprocess.run([FFMPEG, '-y', '-v', 'error', '-i', str(mp3), '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', str(pcm)], check=True)
    with wave.open(str(pcm), 'rb') as wav:
        duration = wav.getnframes() / wav.getframerate()
    return {**scene, 'clip': str(pcm), 'speech_duration': duration, 'boundaries': json.loads(metadata.read_text(encoding='utf-8'))}


async def main():
    result = []
    for i, scene in enumerate(DATA['scenes']):
        result.append(await one(i, scene))
    (HERE / 'speech.json').write_text(json.dumps({'voice': DATA['voice'], 'rate': DATA['rate'], 'pitch': DATA['pitch'], 'scenes': result, 'ffmpeg': FFMPEG}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'speech_seconds': sum(s['speech_duration'] for s in result), 'durations': [s['speech_duration'] for s in result]}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
