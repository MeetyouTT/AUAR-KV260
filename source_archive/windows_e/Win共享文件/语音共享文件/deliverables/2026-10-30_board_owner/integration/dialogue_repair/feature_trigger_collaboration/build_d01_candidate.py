"""Independent D01 diff against exact v17; does not overwrite H01 or policy."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

H = Path(__file__).resolve().parent
DEST = H/'candidate_d01'
BASE = H/'board_integration_v17/local_runtime_v17'


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Non-unique edit anchor: '+old[:100])
    return source.replace(old, new)


def edit(relative, source):
    if relative.endswith('board_business.py'):
        return once(source, '        handlers = dict(extra_handlers or {})',
            '''        handlers = dict(extra_handlers or {})
        from board.runtime.reasoning_dialogue import LocalReasoningDialogue
        handlers.setdefault('reasoning_dialogue', LocalReasoningDialogue())''')
    source = once(source, '                for attempt in range(2):\n                    result, _ = timed_request(\'llm\', task=\'dialogue\', messages=messages)',
        '''                from common.thinking_policy import route as thinking_route
                inference = {'options': {'think': True}} if thinking_route(text)['mode'] == 'reasoning' else {}
                for attempt in range(2):
                    result, _ = timed_request('llm', task='dialogue', messages=messages, **inference)''')
    return source


def main():
    pins=json.loads((H/'board_integration_v17/source_mapping.json').read_bytes())['component_pins']
    files={}
    for relative in ('board/runtime/board_business.py','board/runtime/board_dialogue.py'):
        raw=(BASE/relative).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==pins[relative]
        before=raw.decode().replace('\r\n','\n'); after=edit(relative,before)
        ast.parse(after,feature_version=(3,9))
        for kind,data in [('before',raw),('after',after.encode())]:
            path=DEST/kind/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        (DEST/(Path(relative).name+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),
            after.splitlines(True),fromfile='before/'+relative,tofile='after/'+relative)),encoding='utf-8')
        files[relative]=dict(before_sha256=pins[relative],sha256=hashlib.sha256(after.encode()).hexdigest(),source=str(DEST/'after'/relative))
    relative='board/runtime/reasoning_dialogue.py';raw=(DEST/'after'/relative).read_bytes()
    ast.parse(raw,feature_version=(3,9))
    files[relative]=dict(before_sha256=None,sha256=hashlib.sha256(raw).hexdigest(),source=str(DEST/'after'/relative))
    (DEST/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(status='LOCAL_CANDIDATE_NOT_DEPLOYED',
        baseline_startup_sha256='0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a',files=files,
        models_changed=False,model_options_changed_only='think=True for existing reasoning policy',
        context_limit=2048,num_predict=120,real_model_answer_and_latency_pending=True,
        overlaps_h01='board/runtime/board_dialogue.py; apply disjoint patch or root three-way merge, never overwrite',
        board_memory_policy_changed=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Root-reviewable combined local overlay; never a production write.
    combined=H/'candidate_h01_d01/after'
    for relative in json.loads((H/'candidate_h01/SOURCE_MANIFEST.json').read_bytes())['files']:
        dest=combined/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        raw=(H/'candidate_h01/after'/relative).read_bytes()
        if relative.endswith('board_dialogue.py'):raw=edit(relative,raw.decode()).encode()
        dest.write_bytes(raw)
    for relative in ('board/runtime/board_business.py','board/runtime/reasoning_dialogue.py'):
        dest=combined/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((DEST/'after'/relative).read_bytes())
    print(json.dumps(files,ensure_ascii=False))


if __name__=='__main__':main()
