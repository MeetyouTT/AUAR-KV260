"""Read-only preflight capture. Does not start a candidate TTS or run a model."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path.insert(0, str(PROJECT/'aura'))
from tools.model_inference_host import LocalModelBackend


def main():
    backend = LocalModelBackend.from_config(voice_python=
        r'C:\Users\35870\.codex\visualizations\2026\10\09\01a12110-3ba4-7651-b3d7-2e6560916eb6\omnivoice-runtime-py310\Scripts\python.exe')
    try:
        value = backend.preflight(deadline=time.monotonic()+2.)
        value.update(captured_utc=datetime.now(timezone.utc).isoformat(),
                     real_model_inference_performed=False,
                     candidate_tts_spawned=backend.voice.process is not None,
                     services_stopped_or_reloaded=False)
    finally:
        backend.close()
    path = HERE/'preflight_readonly.json'
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(path), 'candidate_tts_spawned': value['candidate_tts_spawned'],
                     'tts_ownership': value['tts_ownership'], 'tts_admission': value['admission']['tts'],
                     'startup': value['startup']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
