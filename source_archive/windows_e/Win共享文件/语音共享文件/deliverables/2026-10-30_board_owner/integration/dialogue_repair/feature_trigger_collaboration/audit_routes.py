"""Read pinned local sources and probe routing with synthetic, inert handlers.

No camera, microphone, model, network, user store or profile access is used.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'aura'))
sys.path.insert(0, str(HERE / 'runtime_v16'))
from board.runtime.visual_policy import requested, _kind


def route_function(path):
    tree = ast.parse(path.read_bytes())
    paired = path.name == 'yuki_jobs_candidate.py'
    if paired:
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_route')
    else:
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BoardDialogueJobs')
        fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_route')
    module = ast.Module(body=[fn], type_ignores=[])
    env = {'re': __import__('re')}
    from board.runtime.audio.board_dialogue_jobs import BoardCapabilityNotReady
    env['BoardCapabilityNotReady'] = BoardCapabilityNotReady
    if paired:
        from tools.yuki_business_candidate import LocalRecordText,LocalRecordController
        env.update(LocalRecordText=LocalRecordText,LocalRecordController=LocalRecordController)
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), env)
    return env['_route'], hashlib.sha256(ast.dump(fn).encode()).hexdigest()


def probe(fn, text, active=False, disabled=()):
    trace = []
    def handler(name):
        def call(*args, **kwargs):
            trace.append(name)
            return name
        return call
    names = ('identity_enrollment', 'identity_query', 'speaker_identity',
             'history_delete_preview', 'structured_visual_query', 'reasoning_dialogue')
    router = SimpleNamespace(
        controller=SimpleNamespace(command_handler=object(),board_boot_id='synthetic'),
        special_handlers={n: handler(n) for n in names if n not in disabled},
        visual_intent_matcher=requested,
        _enrollment_state=lambda: {'active': active},
        _check=lambda job: None, _current=lambda job: True,
        history_router=None, wall_clock=lambda: 1793440000., timezone='America/Los_Angeles')
    job = SimpleNamespace(scope={'kind': 'conversation', 'id': 'synthetic'},
                          cancelled=threading.Event(),meta=dict(request_id='synthetic-request',
                          board_boot_id='synthetic',session_id='synthetic-session',generation=1))
    from tools.yuki_business_candidate import CharacterSpeechPolicy
    router.character_pair=SimpleNamespace(require_ready=lambda:None,speech=CharacterSpeechPolicy(),
                                          identity=SimpleNamespace(display_name='雪妃'))
    try:
        result = fn(router, job, text)
        route = trace[-1] if trace else ('history' if result[1] else 'ordinary_or_memory')
        return {'route': route, 'error': None,
                'visual_kind': _kind(text) if route == 'structured_visual_query' else None}
    except Exception as exc:
        return {'route': trace[-1] if trace else None, 'error': type(exc).__name__}


CASES = [
    ('vision_current', '你现在看到了什么', 'structured_visual_query'),
    ('vision_count', '现在镜头前有几个人', 'structured_visual_query'),
    ('vision_count_plain', '这里有几个人', 'structured_visual_query'),
    ('vision_can_see_me', '你能看见我吗', 'structured_visual_query'),
    ('vision_position_plain', '我左边有几个人', 'structured_visual_query'),
    ('vision_position_explicit', '镜头左边有几个人', 'structured_visual_query'),
    ('vision_history', '刚才看到几个人', 'structured_visual_query'),
    ('vision_history_events', '查询昨天的视觉记录', 'structured_visual_query'),
    ('vision_unsupported', '我手里是什么颜色的杯子', 'structured_visual_query'),
    ('identity_current', '我是谁呀', 'identity_query'),
    ('identity_known_status', '我登记过身份吗', 'identity_query'),
    ('face_enroll', '帮我登记身份，我叫测试甲', 'identity_enrollment'),
    ('face_update', '确认更新登记', 'identity_enrollment'),
    ('face_cancel', '取消登记', 'identity_enrollment'),
    ('speaker_status', '声纹现在可用吗', 'speaker_identity'),
    ('speaker_registered', '我登记过声纹吗', 'speaker_identity'),
    ('speaker_identify', '听声音知道我是谁吗', 'speaker_identity'),
    ('speaker_recognize', '请识别我的声纹', 'speaker_identity'),
    ('speaker_enroll', '登记我的声纹，我叫测试甲', 'speaker_identity'),
    ('speaker_remember', '记住我的声音，我叫测试甲', 'speaker_identity'),
    ('speaker_delete', '删除声纹，名字是测试甲', 'speaker_identity'),
    ('speaker_cancel', '取消声纹登记', 'speaker_identity'),
    ('speaker_confirm', '确认保存声纹', 'speaker_identity'),
    ('ordinary_chat', '今天比较开心，陪我聊聊', 'ordinary_or_memory'),
    ('ordinary_people', '项目有几个人参加', 'ordinary_or_memory'),
    ('ordinary_quote', '解释一下“登记我的声纹”是什么意思', 'ordinary_or_memory'),
    ('ordinary_denial', '不要识别我的声纹', 'ordinary_or_memory'),
    ('ordinary_voice', '这首歌的声音很好听', 'ordinary_or_memory'),
    ('memory_set', '记住我喜欢蓝色', 'ordinary_or_memory'),
    ('memory_forget', '忘记我喜欢的颜色', 'ordinary_or_memory'),
    ('history_conversation', '我们昨天聊了什么', 'history'),
]


def main():
    source = HERE/'runtime_v16/tools/yuki_jobs_candidate.py'
    if len(sys.argv) > 1:
        source = Path(sys.argv[1]).resolve()
    fn, route_sha = route_function(source)
    cases = []
    for name, text, expect in CASES:
        observed = probe(fn, text)
        cases.append(dict(id=name, synthetic_text=text, expected_route=expect,
                          observed=observed, matched_expectation=observed['route'] == expect))
    out = dict(schema='aura.feature-route-audit.v1', level='code_or_fake_verified',
               source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
               route_ast_sha256=route_sha,
               effects=dict(devices=False, network=False, models=False, user_store=False), cases=cases)
    destination = HERE / ('ROUTE_AUDIT_CANDIDATE_PAIRED.json' if len(sys.argv) > 1 else 'ROUTE_AUDIT_BASELINE_PAIRED.json')
    destination.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(report=str(destination), cases=len(cases),
                         mismatches=[r['id'] for r in cases if not r['matched_expectation']],
                         positional_result=next(r['observed'] for r in cases if r['id']=='vision_position_explicit')),
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
