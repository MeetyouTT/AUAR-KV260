"""Eliminate the second body-cleaning traversal in metadata-only publication."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RELATIVE = 'tools/production_memory_presentation.py'
REPLACEMENTS = (
    (b'    def _projection(self, state):', b'    def _projection(self, state, *, metadata_only=False):'),
    (b"        state['reply'] = self.reply", b"        state['reply'] = '' if metadata_only else self.reply"),
    (b"        local['text'] = self.transcript", b"        local['text'] = '' if metadata_only else self.transcript"),
    (b'bridge.state = _clean(self._projection(bridge.state))',
     b'bridge.state = self._projection(bridge.state, metadata_only=True)'),
    (b'original_publish(_clean(lifecycle._projection(state)), frame)',
     b'original_publish(lifecycle._projection(state, metadata_only=True), frame)'),
)


def main():
    before = (HERE / 'baseline' / RELATIVE).read_bytes()
    assert hashlib.sha256(before).hexdigest() == '414ed67c68ad5f6ad3e0f89608e4f7ccef71d7b8765dfffc4f071eb806cc081a'
    after = before
    for old, new in REPLACEMENTS:
        assert after.count(old) == 1
        after = after.replace(old, new, 1)
    ast.parse(after.decode('utf-8'))
    destination = HERE / 'presentation_candidate' / RELATIVE
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        assert destination.read_bytes() == after
    else:
        with destination.open('xb') as handle:
            handle.write(after)
    proof = dict(schema='aura-single-metadata-projection-candidate-1',
                 status='LOCAL_CANDIDATE_NOT_DEPLOYED',
                 baseline_startup='226b5a20f0089f5c534b1d540dd3605d805c17f7f1bd371a6ab5b3a4b287ad15',
                 source=RELATIVE, before_sha256=hashlib.sha256(before).hexdigest(),
                 after_sha256=hashlib.sha256(after).hexdigest(), before_bytes=len(before), after_bytes=len(after),
                 exact_bounded_replacements=len(REPLACEMENTS),
                 ttl_or_invalidation_or_lock_order_changed=False,
                 microphone_camera_model_or_store_changed=False,
                 device_access=False, production_modified=False)
    (HERE / 'presentation_candidate_manifest.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(proof))


if __name__ == '__main__':
    main()
