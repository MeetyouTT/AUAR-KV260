"""Record one bounded MCP01 utterance without changing the running UI service."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
import wave

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))
from board.runtime.audio.capture import Mcp01Capture


def playback_active():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8783/api/state', timeout=2) as response:
        state = json.load(response)
    if type(state.get('playing')) is not bool or type(state.get('paused')) is not bool:
        raise ValueError('Playback owner did not provide a valid state')
    return state['playing'] or state['paused'] or state.get('phase') != 'IDLE'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New WAV path; existing files are never replaced')
    args = parser.parse_args(argv)
    if not .2 <= args.seconds <= 20:
        parser.error('--seconds must be between 0.2 and 20')
    metadata_path = args.output.with_suffix(args.output.suffix + '.json')
    if args.output.exists() or metadata_path.exists():
        parser.error('Output or metadata already exists')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with Mcp01Capture(playback_active, max_seconds=args.seconds) as capture:
        capture.start()
        deadline = time.monotonic() + args.seconds + 1
        while capture.snapshot()['state'] == 'RECORDING' and time.monotonic() < deadline:
            time.sleep(.05)
        capture.stop()
        clip = capture.take()
    fd = os.open(str(args.output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        with wave.open(stream, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(clip.pcm)
    metadata = clip.metadata()
    metadata.update(wav=str(args.output), wav_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),
                    scope='ACTUAL_MCP01_CAPTURE_NOT_ASR_OR_NETWORK_ACCEPTANCE')
    with metadata_path.open('x', encoding='utf-8') as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(metadata, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
