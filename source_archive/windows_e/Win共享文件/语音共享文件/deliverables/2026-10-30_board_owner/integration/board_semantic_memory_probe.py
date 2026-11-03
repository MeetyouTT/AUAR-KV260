"""Actual ARM+Ethernet+27B compaction; synthetic data and simulated UTC only."""
import hashlib
import json
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import threading
import time
import urllib.request

# Updated from SHA-pinned local manifests immediately before this reviewed run.
BASE = 'http://192.168.50.1:54087'
PIN = '3ae2bf9e6a08aaee48bd7113d5845ebad978297580cc233356242c77a231a58c'
ROOT = Path('/home/root/aura-board-owner-candidate-20261030/semantic-9b2159a4c7fb6899')
MODEL_PORT = 51537


def main():
    signal.alarm(50)
    started = time.monotonic()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(BASE+'/manifest.json',timeout=3) as response:
        raw = response.read(65537)
    assert len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == PIN
    manifest = json.loads(raw)
    assert manifest['purpose'] == 'synthetic_arm_semantic_memory'
    assert manifest['candidate_root'] == str(ROOT)
    assert ROOT.parent == Path('/home/root/aura-board-owner-candidate-20261030')
    assert not ROOT.is_symlink() and shutil.disk_usage('/home/root').free > 8*1024*1024
    ROOT.mkdir(parents=True,exist_ok=True)
    for entry in manifest['entries']:
        relative = Path(entry['name'])
        assert not relative.is_absolute() and '..' not in relative.parts
        target = ROOT/relative
        assert ROOT.resolve() in target.resolve().parents and not target.is_symlink()
        target.parent.mkdir(parents=True,exist_ok=True)
        with opener.open(BASE+'/assets/'+entry['sha256'],timeout=3) as response:
            data = response.read(entry['bytes']+1)
        assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256']
        if target.exists():
            assert target.read_bytes() == data
        else:
            with target.open('xb') as stream:
                stream.write(data)
    for package in ('common','board','board/runtime'):
        init = ROOT/'code'/package/'__init__.py'
        if not init.exists():
            init.write_bytes(b'')
    sys.path.insert(0,str(ROOT/'code'))
    from common.board_memory import BoardMemoryStore, BoardMemoryWorker
    from board.runtime.board_dialogue_client import InferenceHttpClient
    from board.runtime.board_memory_policy import BoardContextBuilder, BoardSummaryClient
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    client = InferenceHttpClient('192.168.50.1',MODEL_PORT)
    class Clock:
        value = 1000.
        def __call__(self):
            return self.value
    clock = Clock()
    scope = dict(kind='conversation',id='synthetic-semantic-probe')
    with tempfile.TemporaryDirectory(prefix='synthetic-only-',dir=str(ROOT)) as temporary:
        store = BoardMemoryStore(Path(temporary)/'synthetic.sqlite3',clock=clock)
        store.append_event(scope,'synthetic-source','user_said','小林计划周五买3本书，尚未购买。',
                           metadata=dict(names=['小林'],numbers=[3],negated=True,status='planned',evidence='statement'))
        assert store.health()['active_bodies'] == 1
        clock.value += 301
        summarize = BoardSummaryClient(client,board_boot_id=boot,budget_ms=30000)
        worker = BoardMemoryWorker(store,summarize,idle=lambda:True,max_events=2)
        stage_started = time.monotonic()
        committed = worker.step()
        result = dict(actual_arm=True,real_windows_llm=True,model='existing_27b',
                      synthetic_database=True,simulated_utc_window=True,
                      actual_playback=False,tts_requested=False,production_changed=False,
                      compaction_committed=committed,worker_error=worker.health()['error'],
                      elapsed_model_seconds=round(time.monotonic()-stage_started,3))
        if committed:
            assert store.health()['active_bodies'] == 0
            history = store.history(scope)
            assert len(history) == 1 and history[0]['source'] == 'timeline_summary'
            narrative = history[0]['text']
            assert '小林' in narrative and '3' in narrative
            result.update(active_bodies_after_commit=0,
                          summary_sha256=hashlib.sha256(narrative.encode()).hexdigest(),
                          summary_source_count=len(history[0]['source_refs']))
            builder = BoardContextBuilder('你是汐蓝。只根据已保存资料自然回答。')
            builder(store.context(scope),'接着聊书单')
            assert builder.metrics['continuity_summary']
            result['continuity_summary_selected'] = True
            store.forget(scope,event_ids=('synthetic-source',),operation_id='synthetic-forget')
            assert store.history(scope) == [] and store.health()['valid_summaries'] == 0
            result['forget_after_body_cleanup'] = True
        else:
            # Rejection must retain the source, never silently pass a fallback.
            assert store.health()['active_bodies'] == 1
            result['active_bodies_preserved_on_failure'] = True
        # A second, public source verifies preemption while the real request is
        # in flight. It does not manufacture a hardware playback ACK.
        clock.value += 1
        store.append_event(scope,'synthetic-cancel-source','user_said','计划先列书单，还没有购买。')
        clock.value += 301
        outcomes = []
        background = threading.Thread(target=lambda:outcomes.append(worker.step()),daemon=True)
        background.start()
        time.sleep(.15)
        store.begin_turn(scope,'synthetic-foreground','公开的新问题',generation=1)
        background.join(timeout=3)
        assert not background.is_alive() and outcomes == [False]
        assert any(row.get('event_id') == 'synthetic-cancel-source' for row in store.history(scope))
        result.update(new_input_preempted_summary=True,source_preserved_on_preemption=True,
                      elapsed_total_seconds=round(time.monotonic()-started,3),candidate_root=str(ROOT))
    signal.alarm(0)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
