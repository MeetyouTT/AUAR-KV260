"""Prepare only a local two-file numeric timing candidate from the live-pinned sources."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    'board/runtime/board_dialogue.py': 'f5998983494b028850688eb06528d4088c86b41b29742bbea9aed390b4e9ee7c',
    'board/runtime/audio/board_dialogue_jobs.py': '580b2cf796275104cf15f2295afa2de29f82f32eabdd783a4b3aff858840a464',
}
source = {}
for relative, expected in EXPECTED.items():
    raw = (HERE/'source_snapshot'/relative).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    source[relative] = raw.decode('utf-8')

controller = source['board/runtime/board_dialogue.py']
anchor = 'class StaleGeneration(InterruptedError):\n'
assert controller.count(anchor) == 1
declarations = '''# Numeric-only observations from the last accepted LLM result in a completed
# prepare. Host-relative backend times remain separate from board RPC wall time.
LLM_BACKEND_METRIC_KEYS = frozenset({
    'prompt_eval_count', 'eval_count', 'load_duration_ms', 'prompt_eval_duration_ms',
    'eval_duration_ms', 'total_duration_ms', 'first_packet_ms', 'first_content_ms',
    'first_json_closed_ms', 'backend_done_ms', 'json_closed_to_done_ms',
    'thinking_characters', 'content_characters', 'trailing_whitespace_characters',
    'prompt_eval_cached_count',
})
LLM_BACKEND_METRIC_FIELDS = frozenset('llm_last_backend_' + key for key in LLM_BACKEND_METRIC_KEYS)


'''
controller = controller.replace(anchor, declarations + anchor)
anchor = '            speaker_first_audio_measured=False)\n        def timed_request(kind,**fields):\n'
assert controller.count(anchor) == 1
controller = controller.replace(anchor, '''            speaker_first_audio_measured=False,llm_backend_metrics_calls=0)
        self.last_prepare_metrics = dict(metrics)
        def timed_request(kind,**fields):
''')
anchor = '''            try:
                return self._request(kind,turn,**fields)
            finally:
'''
assert controller.count(anchor) == 1
controller = controller.replace(anchor, '''            if kind == 'llm':
                # A retry with missing/rejected metrics cannot retain its predecessor.
                for name in LLM_BACKEND_METRIC_FIELDS:
                    metrics.pop(name, None)
            try:
                result, owner = self._request(kind,turn,**fields)
                if kind == 'llm':
                    backend = result.get('metrics')
                    observed = False
                    if isinstance(backend, dict):
                        for name in LLM_BACKEND_METRIC_KEYS:
                            value = backend.get(name)
                            if type(value) in (int, float) and 0 <= value < 1e15:
                                metrics['llm_last_backend_' + name] = value
                                observed = True
                    if observed:
                        metrics['llm_backend_metrics_calls'] += 1
                return result, owner
            finally:
''')
anchor = '''            metrics['complete'] = True
            return plan

        finally:
'''
assert controller.count(anchor) == 1
controller = controller.replace(anchor, '''            metrics['complete'] = True
            return plan

        except Exception:
            # Failed/cancelled prepares publish no backend-result observation.
            for name in LLM_BACKEND_METRIC_FIELDS:
                metrics.pop(name, None)
            metrics['llm_backend_metrics_calls'] = 0
            raise
        finally:
''')

jobs = source['board/runtime/audio/board_dialogue_jobs.py']
anchor = 'from board.runtime.board_dialogue import PlaybackPlan, StaleGeneration\n'
assert jobs.count(anchor) == 1
jobs = jobs.replace(anchor, 'from board.runtime.board_dialogue import PlaybackPlan, StaleGeneration, LLM_BACKEND_METRIC_FIELDS\n')
anchor = '''                    metrics = getattr(self.controller, 'last_prepare_metrics', {})
                    phase['prepare'] = {k:v for k,v in metrics.items()
                        if k in allowed and (type(v) is bool or type(v) in (int,float) and math.isfinite(v) and v>=0)}
'''
assert jobs.count(anchor) == 1
jobs = jobs.replace(anchor, '''                    metrics = getattr(self.controller, 'last_prepare_metrics', {})
                    numeric_backend = LLM_BACKEND_METRIC_FIELDS | {'llm_backend_metrics_calls'}
                    phase['prepare'] = {k:v for k,v in metrics.items()
                        if (k in allowed and (type(v) is bool or type(v) in (int,float) and math.isfinite(v) and v>=0))
                        or (k in numeric_backend and type(v) in (int,float) and math.isfinite(v) and 0<=v<1e15)}
''')

changed = {'board/runtime/board_dialogue.py': controller,
           'board/runtime/audio/board_dialogue_jobs.py': jobs}
manifest = {'schema': 'aura-numeric-llm-timing-local-candidate-1',
            'production_changed': False, 'restart_or_deployment_requested': False,
            'inference_behavior_changed': False, 'speedup_claimed': False,
            'maximum_backend_fields_per_prepare': 16, 'files': {}}
diffs = []
for relative, text in changed.items():
    ast.parse(text)
    target = HERE/'numeric_candidate'/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)
    manifest['files'][relative] = {'before_sha256': EXPECTED[relative],
                                   'after_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    diffs.extend(difflib.unified_diff(source[relative].splitlines(True), text.splitlines(True),
                                   fromfile='a/'+relative, tofile='b/'+relative))
with (HERE/'NUMERIC_TIMING_PATCH.diff').open('x', encoding='utf-8') as stream:
    stream.writelines(diffs)
with (HERE/'NUMERIC_TIMING_CANDIDATE_MANIFEST.json').open('x', encoding='utf-8') as stream:
    json.dump(manifest, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(manifest))
