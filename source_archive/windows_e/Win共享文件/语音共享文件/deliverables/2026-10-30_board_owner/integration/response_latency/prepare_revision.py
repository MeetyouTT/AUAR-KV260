"""Assemble reviewed source-only latency revision, retaining every frontend setting."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
before=json.loads((HERE/'source_manifest.json').read_text(encoding='utf-8'))
baseline=json.loads((HERE/'board_baseline.json').read_text(encoding='utf-8'))
live=json.loads((HERE.parent/'PRODUCTION_BUSINESS_LIVE.json').read_text(encoding='utf-8'))
assert live['startup_sha256']==baseline['startup_sha256']
files={
 'board/runtime/board_dialogue.py':HERE/'streaming_candidate/after/board/runtime/board_dialogue.py',
 'board/runtime/audio/board_dialogue_jobs.py':HERE/'streaming_candidate/after/board/runtime/audio/board_dialogue_jobs.py',
 'common/board_memory.py':HERE/'memory_candidate/after/common/board_memory.py',
 'common/board_memory_backoff.py':HERE/'memory_backoff_candidate/after/common/board_memory_backoff.py',
 'board/runtime/board_business.py':HERE/'memory_backoff_candidate/after/board/runtime/board_business.py',
 'board/runtime/audio/board_asr.py':HERE/'asr_threads_candidate/after/board/runtime/audio/board_asr.py',
}
value=dict(stage='response-latency-v1-streamed-replies',before_startup_sha256=live['startup_sha256'],
 before_manifest_sha256=live['source_manifest_sha256'],business_options=dict(live['frontend_options'],asr_threads=3),
 sources={rel:dict(source=path.relative_to(PROJECT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  before_sha256=before[rel]['sha256'] if rel in before else None) for rel,path in files.items()},
 queue_frames=8,model_or_threshold_changes=False,source_only=True)
(HERE/'revision.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps(value))
