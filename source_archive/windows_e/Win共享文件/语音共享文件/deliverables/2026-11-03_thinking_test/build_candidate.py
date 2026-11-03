from pathlib import Path
import hashlib
import json

TASK = Path(__file__).resolve().parent
relative = 'board/runtime/board_dialogue.py'
source = (TASK / 'baseline' / relative).read_text(encoding='utf-8')

def replace_once(old, new):
    global source
    assert source.count(old) == 1, old[:80]
    source = source.replace(old, new, 1)

replace_once('import hashlib\n', 'from copy import copy\nfrom pathlib import Path\nimport hashlib\n')
replace_once('\n\nclass StaleGeneration', '''

# /run is volatile: enabling this test never changes the saved default.
THINKING_TEST_PATH = Path('/run/aura-dialogue-thinking-test.json')


def dialogue_thinking_test_options(board_boot_id):
    """Read one bounded, boot-bound local test selection; default stays off."""
    try:
        if THINKING_TEST_PATH.is_symlink():
            return {}
        with THINKING_TEST_PATH.open('rb') as stream:
            raw = stream.read(1025)
        if len(raw) > 1024:
            return {}
        value = json.loads(raw)
        if (not isinstance(value, dict)
                or set(value) != {'version', 'enabled', 'board_boot_id', 'num_predict'}
                or type(value['version']) is not int or value['version'] != 1
                or value['enabled'] is not True
                or value['board_boot_id'] != board_boot_id
                or type(value['num_predict']) is not int or value['num_predict'] != 192):
            return {}
        return {'think': True, 'num_predict': 192}
    except (OSError, ValueError):
        return {}


class StaleGeneration''')
replace_once('    context_source_id: object = None', '    context_source_id: object = None\n    llm_options: dict = field(default_factory=dict)')
replace_once('''        if self.context_builder is not None:
            return self.context_builder(context, text, history)
''', '''        if self.context_builder is not None:
            builder = self.context_builder
            metrics_target = builder
            if not turn.llm_options.get('think'):
                return builder(context, text, history)
            if turn.llm_options.get('think'):
                # Reserve thinking tokens before selecting whole memory items.
                # A per-turn copy leaves the normal context/summary budget intact.
                from board.runtime.board_memory_policy import BoardContextBuilder, ContextLimitError
                if isinstance(builder, BoardContextBuilder):
                    builder = copy(builder)
                    builder.reserve = max(builder.reserve, turn.llm_options['num_predict'])
                else:
                    # Retain the selected character's ready check and speech policy.
                    from tools.yuki_business_candidate import PairedContextBuilder
                    if (not isinstance(builder, PairedContextBuilder)
                            or not isinstance(builder.original, BoardContextBuilder)):
                        raise RuntimeError('Thinking test requires the bounded context builder')
                    metrics_target = builder.original
                    bounded = copy(builder.original)
                    bounded.reserve = max(bounded.reserve, turn.llm_options['num_predict'])
                    builder = PairedContextBuilder(bounded, builder.pair)
            try:
                messages = builder(context, text, history)
            except ContextLimitError:
                # Longer current input keeps the original accepted reserve.
                # Keep the whole input, persona and recognition note intact.
                turn.llm_options['num_predict'] = 120
                if isinstance(builder, BoardContextBuilder):
                    builder.reserve = 120
                else:
                    builder.original.reserve = 120
                messages = builder(context, text, history)
            if turn.llm_options.get('think'):
                metrics_target.metrics = dict(builder.metrics)
            return messages
''')
replace_once('''                messages = self._messages(turn, text, history_query)
                metrics['context_ms']''', '''                turn.llm_options = dialogue_thinking_test_options(self.board_boot_id)
                metrics['thinking_test_enabled'] = bool(turn.llm_options.get('think'))
                messages = self._messages(turn, text, history_query)
                metrics['llm_num_predict'] = turn.llm_options.get('num_predict', 120)
                metrics['context_ms']''')
replace_once("                    result, _ = timed_request('llm', task='dialogue', messages=messages)", '''                    if turn.llm_options.get('think'):
                        from board.runtime.board_memory_policy import message_cost
                        if message_cost(messages, turn.llm_options['num_predict']) > 2048:
                            raise ReplyRejected('Thinking test exceeds the safe context capacity')
                    result, _ = timed_request('llm', task='dialogue', messages=messages,
                                              options=dict(turn.llm_options))''')
compile(source, relative, 'exec')
target = TASK / 'candidate' / relative
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(source, encoding='utf-8', newline='')
manifest = dict(path=relative, before_sha256=hashlib.sha256((TASK/'baseline'/relative).read_bytes()).hexdigest(),
                after_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                thinking_tokens=192, default_enabled=False, lifetime='current board boot only')
(TASK/'CANDIDATE.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
print(json.dumps(manifest))
