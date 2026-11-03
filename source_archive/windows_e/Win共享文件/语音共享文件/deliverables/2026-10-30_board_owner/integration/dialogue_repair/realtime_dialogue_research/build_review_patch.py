"""Build a review patch ONLY inside this research directory; never apply it."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT.parent.parent / 'response_latency/streaming_candidate/after/board/runtime/board_dialogue.py'
TARGET = 'board/runtime/board_dialogue.py'
EXPECTED = 'bce1f21962d083275d9e8a966f244d8c227d0d62e9a30314767453d04c05b475'

WRAPPER = '''

def split_dialogue_sentences(text, max_chars=220):
    """Candidate grouping AFTER complete reply validation; no provisional TTS."""
    from board.runtime.dialogue_chunk_policy import ChunkPolicyError, segment_reply
    try:
        return segment_reply(text, max_chars=max_chars)
    except ChunkPolicyError:
        raise ReplyRejected('Sentence segmentation failed') from None
'''


def patched_source():
    raw = REFERENCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError('reference_source_changed')
    baseline = json.loads((ROOT.parent / 'frontend_balance_candidate/baseline_manifest.json').read_text(encoding='utf-8-sig'))
    if baseline['component_sha256'][TARGET] != EXPECTED:
        raise ValueError('baseline_pin_changed')
    before = raw.decode('utf-8')
    tree = ast.parse(before)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'split_sentences')
    lines = before.splitlines(keepends=True)
    after = ''.join(lines[:node.end_lineno]) + WRAPPER + ''.join(lines[node.end_lineno:])
    old_branch = '            if reply is None:\n                context_started = self.clock()'
    new_branch = '            model_reply = reply is None\n' + old_branch
    old_split = '            sentences = split_sentences(reply.text)'
    new_split = ('            sentences = (split_dialogue_sentences(reply.text) if model_reply\n'
                 '                         else split_sentences(reply.text))')
    if after.count(old_branch) != 1 or after.count(old_split) != 1:
        raise ValueError('unexpected_source_shape')
    after = after.replace(old_branch, new_branch, 1).replace(old_split, new_split, 1)
    # Reversing ONLY these three reviewed edits must recover the complete AST.
    # Local command replies and cue sequences keep the original splitter.
    restored = after.replace(WRAPPER, '', 1).replace(new_branch, old_branch, 1).replace(new_split, old_split, 1)
    if ast.dump(ast.parse(restored)) != ast.dump(tree):
        raise ValueError('unexpected_source_delta')
    return before, after


if __name__ == '__main__':
    before, after = patched_source()
    delta = ''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                    fromfile='a/' + TARGET, tofile='b/' + TARGET))
    policy = (ROOT / 'candidate/dialogue_chunk_policy.py').read_text(encoding='utf-8')
    policy_target = 'board/runtime/dialogue_chunk_policy.py'
    delta += ''.join(difflib.unified_diff([], policy.splitlines(keepends=True),
                     fromfile='/dev/null', tofile='b/' + policy_target))
    (ROOT / 'integration_review.patch').write_text(delta, encoding='utf-8', newline='\n')
    print(json.dumps({'status': 'REVIEW_PATCH_ONLY_NOT_APPLIED', 'base_sha256': EXPECTED,
                      'patch_bytes': len(delta.encode('utf-8')), 'changed_existing_functions': ['_prepare (model reply grouping only)'],
                      'new_runtime_module': policy_target}))
