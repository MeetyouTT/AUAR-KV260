"""Reproduce current compaction decisions with public text and fake inference."""
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
BASE = REPAIR/'feature_trigger_collaboration/board_integration_v17/local_runtime_v17'
STORE_PATH = REPAIR/'feature_trigger_collaboration/candidate_h01/after/common/board_memory.py'
POLICY_PATH = REPAIR/'memory_observation_candidate_r2/after/board/runtime/board_memory_policy.py'
DIALOGUE_PATH = REPAIR/'feature_trigger_collaboration/candidate_h01/after/board/runtime/board_dialogue.py'
SPEC_PATH = REPAIR/'release_v18_minor_ui_candidate/applied_spec_1793496827180069100.json'
EXPECTED_SPEC = 'c46d44e8583a8ccb8e02d9321b5c6edb9a681474913ba2689dd681d912c50cb2'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


assert digest(SPEC_PATH) == EXPECTED_SPEC
PINS = json.loads(SPEC_PATH.read_bytes())['component_sha256']
assert digest(STORE_PATH) == PINS['common/board_memory.py']
assert digest(POLICY_PATH) == PINS['board/runtime/board_memory_policy.py']
assert digest(DIALOGUE_PATH) == PINS['board/runtime/board_dialogue.py']
sys.path.insert(0, str(BASE))
STORE = load('common.board_memory', STORE_PATH)
load('board.runtime.board_dialogue', DIALOGUE_PATH)
POLICY = load('board.runtime.public_negation_policy', POLICY_PATH)
from common.model_inference_wire import Owner, make_response


class FakeInference:
    def __init__(self, summary):
        self.summary = summary
        self.calls = 0

    def request(self, kind, payload, **kwargs):
        assert kind == 'llm' and payload['task'] == 'summary'
        self.calls += 1
        return make_response(Owner.from_dict(payload), result={'text':json.dumps(
            {'summary':self.summary, 'keywords':['公开测试']}, ensure_ascii=False)})

    def cancel(self, owner):
        pass


# The semantic labels are explicit reviewer judgments about these public cases.
# They are not inferred from production text or from the mechanical validator.
CASES = [
    ('question_can', '你能不能识别声纹？', '用户询问声纹识别能力。', {}, False, 'faithful_question_paraphrase'),
    ('question_will', '你会不会唱歌？', '用户询问唱歌能力。', {}, False, 'faithful_question_paraphrase'),
    ('question_is', '你是不是雪妃？', '用户询问对方是否为雪妃。', {'names':['雪妃']}, False, 'faithful_question_paraphrase'),
    ('question_have', '你有没有看到杯子？', '用户询问是否观察到杯子。', {}, False, 'faithful_question_paraphrase'),
    ('question_may', '可不可以识别声纹？', '用户询问声纹识别能力。', {}, True, 'faithful_question_paraphrase'),
    ('question_positive', '你可以识别声纹吗？', '用户询问声纹识别能力。', {}, True, 'faithful_question_paraphrase'),
    ('negative_synonym', '声纹尚未校准，不能可靠确认身份。', '声纹未校准，暂无法可靠确认身份。', {}, False, 'faithful_negative_paraphrase'),
    ('different_identity', '这不是小林。', '此人与小林身份不同。', {'names':['小林']}, False, 'faithful_negative_paraphrase'),
    ('metadata_negative', '该项未准备就绪。', '该项仍待准备。', {'negated':True}, False, 'faithful_incomplete_paraphrase'),
    ('negative_retained', '声纹尚未校准，不能可靠确认身份。', '声纹尚未校准，不能可靠确认身份。', {}, True, 'faithful_literal_clause'),
    ('actual_negative_loss', '声纹尚未校准，不能可靠确认身份。', '声纹已经校准，可以可靠确认身份。', {}, False, 'incorrect_polarity_reversal'),
    ('unrelated_negative', '小林没有喝咖啡。', '小林喝了咖啡，小王没有出门。', {'names':['小林']}, True, 'incorrect_other_clause_masks_reversal'),
]


def counts(path):
    with closing(sqlite3.connect(path)) as db:
        return dict(bodies=db.execute('SELECT COUNT(*) FROM bm_bodies').fetchone()[0],
                    summaries=db.execute('SELECT COUNT(*) FROM bm_summaries').fetchone()[0])


def run_case(case):
    name, source, summary_text, metadata, expected, judgment = case
    with tempfile.TemporaryDirectory(prefix='aura-public-negation-') as directory:
        temporary = Path(directory)
        now = [1000.]
        store = STORE.BoardMemoryStore(temporary/'public.sqlite3', clock=lambda:now[0])
        store.append_event({'kind':'conversation','id':'public-conversation'},
            'public-source', 'user_said', source, topic='公开测试', metadata=metadata)
        before = counts(store.path)
        now[0] = 1400.
        fake = FakeInference(summary_text)
        client = POLICY.BoardSummaryClient(fake, board_boot_id='public-boot')
        worker = STORE.BoardMemoryWorker(store, client, idle=lambda:True)
        committed = worker.step()
        after = counts(store.path)
        assert committed is expected
        assert fake.calls == 1
        assert before == dict(bodies=1, summaries=0)
        assert after == (dict(bodies=0, summaries=1) if expected else before)
        diagnostics = client.failure_metadata()
        if not expected:
            assert diagnostics['rejection_reasons'] == ('negation_missing',)
        result = dict(name=name, public_source=source, public_candidate=summary_text,
            semantic_review=judgment, source_matches=STORE.NEGATION.findall(source),
            candidate_matches=STORE.NEGATION.findall(summary_text), metadata_negated=metadata.get('negated',False),
            committed=committed, before=before, after=after, diagnostics=diagnostics,
            model_requests=fake.calls)
    result['temporary_directory_removed'] = not temporary.exists()
    assert result['temporary_directory_removed']
    return result


if __name__ == '__main__':
    threads_before = {thread.ident for thread in threading.enumerate()}
    results = [run_case(case) for case in CASES]
    leaked = [thread.name for thread in threading.enumerate() if thread.ident not in threads_before]
    assert not leaked
    report = dict(status='CURRENT_BEHAVIOR_REPRODUCED', cases=len(results), results=results,
        source_pins={'common/board_memory.py':digest(STORE_PATH),
                     'board/runtime/board_memory_policy.py':digest(POLICY_PATH),
                     'board/runtime/board_dialogue.py':digest(DIALOGUE_PATH)},
        source_spec_sha256=digest(SPEC_PATH), fake_inference_only=True,
        private_database_or_model_accessed=False, current_production_cause_confirmed=False,
        semantic_review_is_public_case_assessment=True, temporary_directories_removed=True,
        leaked_threads=0)
    target = HERE/'PUBLIC_REPLAY_02.json'
    with target.open('x', encoding='utf8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'status':report['status'],'cases':len(results),'output':str(target),
                      'sha256':digest(target),'temporary_directories_removed':True}))
