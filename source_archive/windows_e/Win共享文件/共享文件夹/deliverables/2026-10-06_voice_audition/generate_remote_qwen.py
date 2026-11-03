"""Generate fixed audition lines with Qwen's public Gradio demo API."""
import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = 'https://qwen-qwen3-tts.hf.space'


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def call(data):
    request = urllib.request.Request(
        BASE + '/gradio_api/call/generate_custom_voice',
        json.dumps({'data': data}, ensure_ascii=False).encode('utf-8'),
        {'Content-Type': 'application/json'}, method='POST')
    event = json.load(urllib.request.urlopen(request, timeout=30))['event_id']
    event_type = None
    started = time.monotonic()
    with urllib.request.urlopen(BASE + '/gradio_api/call/generate_custom_voice/' + event, timeout=45) as stream:
        while time.monotonic() - started < 180:
            raw = stream.readline()
            if not raw:
                raise RuntimeError('Official demo stream ended before completion')
            line = raw.decode('utf-8').strip()
            if line.startswith('event:'):
                event_type = line.partition(':')[2].strip()
            elif line.startswith('data:'):
                result = json.loads(line.partition(':')[2].strip())
                if event_type == 'complete':
                    return result, event
                if event_type == 'error':
                    raise RuntimeError('Official demo returned an SSE error: ' + repr(result))
    raise TimeoutError('Official demo did not complete within the bounded wait')


def generate(voices, only_scene=None):
    plan = json.loads((HERE / 'audition_plan.json').read_text(encoding='utf-8'))
    directory = HERE / 'raw'
    directory.mkdir(exist_ok=True)
    report_path = HERE / 'qwen_remote_generation.json'
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {'provider': BASE, 'environment': 'official remote demo; not board inference', 'clips': [], 'errors': []}
    for voice in voices:
        for scene in plan['scenes']:
            if only_scene and scene['id'] != only_scene:
                continue
            target = directory / (voice.lower() + '_' + scene['id'] + '.wav')
            instruction = plan.get('voice_instructions', {}).get(voice, {}).get(scene['id'], scene['instruction'])
            if target.exists() and any(row['file'] == target.name for row in report['clips']):
                print('EXISTING ' + target.name, flush=True)
                continue
            started = time.perf_counter()
            print('GENERATING ' + voice + ' / ' + scene['label'], flush=True)
            try:
                result, event_id = call([scene['text'], 'Chinese', voice, instruction, plan['qwen_model_size']])
                if not isinstance(result, list) or not result or result[0] is None:
                    raise RuntimeError('No generated audio: ' + repr(result))
                audio = result[0]
                url = audio.get('url') or (BASE + '/gradio_api/file=' + urllib.parse.quote(audio['path'], safe='/'))
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme != 'https' or parsed.netloc != urllib.parse.urlparse(BASE).netloc:
                    raise ValueError('Unexpected audio download origin')
                # Save the generated audition artifact, not a pre-existing media sample.
                with urllib.request.urlopen(url, timeout=45) as stream:
                    payload = stream.read(20 * 1024 * 1024 + 1)
                if len(payload) > 20 * 1024 * 1024:
                    raise ValueError('Unexpected audio size')
                temporary = target.with_suffix('.wav.tmp')
                temporary.write_bytes(payload)
                with wave.open(str(temporary), 'rb') as wav:
                    seconds = wav.getnframes() / wav.getframerate()
                    rate = wav.getframerate()
                temporary.replace(target)
                row = {'voice': voice, 'scene': scene['id'], 'text': scene['text'],
                       'instruction': instruction, 'model_size': plan['qwen_model_size'],
                       'file': target.name, 'sample_rate': rate, 'duration_seconds': seconds,
                       'generation_wall_seconds_including_remote_queue': time.perf_counter() - started,
                       'sha256': hashlib.sha256(payload).hexdigest(), 'event_id': event_id,
                       'status': result[1] if len(result) > 1 else None}
                report['clips'].append(row)
                dump(report_path, report)
                print('SAVED ' + target.name + f' ({seconds:.2f}s)', flush=True)
            except Exception as exc:
                report['errors'].append({'voice': voice, 'scene': scene['id'], 'error': str(exc), 'elapsed_seconds': time.perf_counter() - started})
                dump(report_path, report)
                raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--voices', nargs='+', choices=['Serena', 'Vivian'], default=['Serena', 'Vivian'])
    parser.add_argument('--scene', choices=['greeting', 'explanation', 'excited', 'gentle'])
    args = parser.parse_args()
    generate(args.voices, args.scene)
