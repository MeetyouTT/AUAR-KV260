"""Read-only source provenance for an independent review; no runtime imports."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=HERE.parents[4]


def record(path):
    raw=path.read_bytes()
    return dict(path=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


def main():
    paths=[
        REPAIR/'playback_idle_candidate/after/tools/gstreamer_audio_worker.py',
        REPAIR/'playback_idle_candidate/before/tools/gstreamer_audio_worker.py',
        REPAIR/'playback_idle_candidate/tests/test_idle_worker.py',
        REPAIR/'presentation_idle_candidate/after/tools/board_avatar_gtk.py',
        REPAIR/'presentation_idle_candidate/before/tools/board_avatar_gtk.py',
        REPAIR/'presentation_idle_candidate/tests/test_presentation_idle.py',
        REPAIR/'ui_budget_candidate/after/tools/production_memory_presentation.py',
        REPAIR/'ui_budget_candidate/after/tools/realtime_controller.py',
        PROJECT/'aura/tools/realtime_audio.py',PROJECT/'aura/tools/gstreamer_audio.py',
        PROJECT/'aura/tools/streaming_controller.py',PROJECT/'aura/tools/gstreamer_persistent_engine.py']
    value=dict(status='INDEPENDENT_SOURCE_REVIEW_NO_BLOCKER',
        review=record(HERE/'REVIEW.txt'),sources=[record(path) for path in paths],
        hardware_or_model_or_db_actions=[],candidate_sources_modified=False,
        idle_audio_stale_gate_found=False,hardware_performance_claimed=False)
    path=HERE/'REVIEW.json'
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(status=value['status'],review_sha256=record(path)['sha256'])))


if __name__=='__main__':main()
