"""Real board -> fixed 27B -> RAM OmniVoice; no speaker or playback claim."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-root', type=Path, required=True)
    parser.add_argument('--utc-min', type=float, required=True)
    parser.add_argument('--utc-max', type=float, required=True)
    args = parser.parse_args()
    root = args.candidate_root
    assert root.parent == Path('/home/root/aura-board-owner-candidate-20261030') and not root.is_symlink()
    manifest = json.loads((root/'manifest.json').read_text())
    assert manifest['purpose'] == 'source_only_board_business_candidate'
    signal.alarm(80)
    sys.path.insert(0, str(root/'code'))
    from common.board_memory import BoardMemoryStore
    from common.board_timeline_clock import StableTimelineClock
    from board.runtime.board_dialogue import BoardDialogueController
    from board.runtime.board_dialogue_client import InferenceHttpClient
    from board.runtime.board_memory_policy import BoardContextBuilder
    from tools.dialogue_host_ollama import fast_system_prompt
    from common.device_policy import MODEL_HINT
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert boot == manifest['source_boot']
    client = InferenceHttpClient('192.168.50.1', 8797)
    began = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='public-model-chain-', dir=str(root)) as directory:
        timeline = StableTimelineClock(boot, client.health_date_source_id(), client.validate_sample,
            utc_bounds=(args.utc_min, args.utc_max), anchor_path=Path(directory)/'clock.json')
        client.sample_health_date(timeline, deadline=time.monotonic()+3)
        store = BoardMemoryStore(Path(directory)/'public-only.sqlite3', data_origin='board', clock=timeline.event_time)
        prompt = fast_system_prompt()+MODEL_HINT
        controller = BoardDialogueController(store, client, board_boot_id=boot, system_prompt=prompt,
                                             context_builder=BoardContextBuilder(prompt))
        scope = dict(kind='conversation', id='public-ram-model-check')
        started = time.monotonic()
        plan = controller.prepare_text('你好，今天一起看看书吧。', scope=scope,
            session_id='public-ram-model-session', generation=1, budget_ms=60000,
            metadata=dict(source_id='public-ram-model-conversation'))
        duration = time.monotonic()-started
        assert plan.sample_rate == 24000 and plan.samples > 0
        assert len(plan.pcm) == plan.samples*2 and hashlib.sha256(plan.pcm).hexdigest() == plan.sha256
        assert plan.reply.text.strip() and all(chunk.sample_rate == 24000 for chunk in plan.chunks)
        # Receiving PCM is not evidence of hearing it. Cancel this unplayed plan.
        controller.cancel(plan.session_id, generation=plan.generation)
        assert controller.idle
        assert not any(message['role'] == 'assistant' for message in store.context(scope)['messages'])
        result = dict(status='PASS', actual_arm=True, real_fixed_27b=True, real_omnivoice_16=True,
            accepted_persona_used=True, model_seconds=round(duration, 3), total_seconds=round(time.monotonic()-began, 3),
            reply_characters=len(plan.reply.text), reply_sha256=hashlib.sha256(plan.reply.text.encode()).hexdigest(),
            pcm_sha256=plan.sha256, samples=plan.samples, sample_rate=plan.sample_rate,
            pcm_channels=1, sample_width=2, chunks=len(plan.chunks), received_pcm_verified=True,
            unplayed_plan_cancelled=True, assistant_not_recorded_as_heard=True,
            audio_archived=False, existing_business_database_accessed=False,
            actual_microphone_opened=False, actual_audio_played=False, production_entry_changed=False)
    signal.alarm(0)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
