"""Build an isolated candidate from frozen reviewed source files."""
import ast
import difflib
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
IDENTITY = REPAIR / 'feature_trigger_collaboration/identity_cooperation_v90'
SOURCES = {
    'board/runtime/board_business.py': (
        IDENTITY / 'combined_with_frozen_M03/board/runtime/board_business.py',
        '7c5cef7b648af0d8f3aad026c97ee82dace5911a7bdb88d040fc2d0c01038662'),
    'board/runtime/board_speaker_business.py': (
        IDENTITY / 'after/board/runtime/board_speaker_business.py',
        '134466a85599d73697b11aceaeec97c1e0b5d9db4b125f4accd50bf14f525e25'),
    'common/board_memory.py': (
        REPAIR / 'feature_trigger_collaboration/candidate_m03_v90_stage/public_runtime_v90/common/board_memory.py',
        'c27d4d3c39e5de293cbc7fed8899de8b0d39ea6ccc99c0e7f64f22c8a90a2c0b'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1
    return text.replace(old, new)


def build():
    manifest = {'schema': 'aura.speaker-evidence-retry.public-candidate.v1',
                'status': 'LOCAL_ONLY_NOT_DEPLOYED', 'files': {}}
    diffs = []
    for relative, (source, expected) in SOURCES.items():
        original = source.read_bytes()
        assert sha(original) == expected
        text = original.decode('utf-8')
        if relative.endswith('/board_business.py'):
            text = replace_once(text,
                'from common.board_memory import BoardMemoryStore, BoardMemoryWorker',
                'from common.board_memory import BoardMemoryStore, BoardMemoryWorker, MemoryBusy')
            start = text.index('        def evidence(value):\n', text.index('    def _submit_speaker_analysis('))
            end = text.index('        try:\n            result = self.speaker_business.submit_analysis(', start)
            old = text[start:end]
            new = '''        def evidence(value):
            if (not is_current() or cancel_event.is_set() or self.clock() >= job.deadline
                    or value.get('status') != 'COMPLETE'):
                return
            # Keep the event identity, occurrence time and payload across retries.
            event_id = 'speaker:' + job.meta['request_id']
            metadata = dict(source_id=source, evidence='device_confirmed', speaker_known=False,
                occurred_utc=self.timeline.event_time(),
                claims=[dict(field='attribution', value='unconfirmed')])
            def check_current():
                if not is_current() or cancel_event.is_set() or self.clock() >= job.deadline:
                    raise StaleGeneration('Speaker evidence no longer owns its capture')
            # The existing speaker worker owns this bounded, cancellable retry.
            # Candidate IDs/vectors remain outside the shared timeline.
            for attempt in range(3):
                try:
                    check_current()
                    self.store.append_event(job.scope, event_id, 'device_event',
                        '本轮语音已形成归属线索，说话者身份仍未确认。', topic='语音归属',
                        metadata=metadata, guard=check_current)
                    return
                except StaleGeneration:
                    return
                except MemoryBusy:
                    if attempt == 2:
                        raise
                    delay = .025 * (attempt + 1)
                    if (not is_current() or cancel_event.is_set()
                            or self.clock() + delay >= job.deadline or cancel_event.wait(delay)):
                        return
'''
            text = replace_once(text, old, new)
        elif relative.endswith('/board_speaker_business.py'):
            text = replace_once(text,
                "'RuntimeError','OSError','ClockUnavailable') else",
                "'RuntimeError','OSError','ClockUnavailable','MemoryBusy','ScopeDenied',\n"
                "                        'IdempotencyConflict') else")
        else:
            text = replace_once(text,
                '    def append_event(self, scope, event_id, source, text, *, closed=True, topic="", metadata=None):\n',
                '    def append_event(self, scope, event_id, source, text, *, closed=True, topic="", metadata=None, guard=None):\n'
                '        # An optional pure validity check raises to roll back a stale append.\n'
                '        if guard is not None and not callable(guard):\n'
                '            raise ValueError("Event guard must be callable or None")\n')
            text = replace_once(text,
                '        with self._scope(scope) as owner, self._db(True) as db:\n'
                '            row = self._insert_event(db, owner, event_id, source, text, topic, meta, self._now(), closed=closed)\n'
                '            return {"event_id": row["event_id"], "revision": row["revision"], "state": row["state"]}\n',
                '        with self._scope(scope) as owner, self._db(True) as db:\n'
                '            if guard is not None:\n'
                '                guard()  # BEGIN IMMEDIATE may have waited for another writer.\n'
                '            row = self._insert_event(db, owner, event_id, source, text, topic, meta, self._now(), closed=closed)\n'
                '            if guard is not None:\n'
                '                guard()  # The existing transaction rolls back on invalidation.\n'
                '            return {"event_id": row["event_id"], "revision": row["revision"], "state": row["state"]}\n')
        ast.parse(text)
        updated = text.encode('utf-8')
        for folder, data in [('before', original), ('after', updated)]:
            path = HERE / folder / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        diffs.extend(difflib.unified_diff(original.decode('utf-8').splitlines(True),
            text.splitlines(True), fromfile='before/' + relative, tofile='after/' + relative))
        manifest['files'][relative] = dict(before_sha256=expected,
            sha256=sha(updated), bytes=len(updated), before_path=str(source))
        assert sha(source.read_bytes()) == expected
    (HERE / 'CANDIDATE.diff').write_text(''.join(diffs), encoding='utf-8')
    (HERE / 'SOURCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, separators=(',', ':')))


if __name__ == '__main__':
    build()
